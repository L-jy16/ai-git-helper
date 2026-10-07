"""Git 변경 사항을 커밋 메시지 또는 PR 초안으로 변환하는 CLI."""
import argparse
import math
import os
import sys

from ai_client import call_ai
from git_utils import ensure_repository_root, get_git_status, get_git_diff, get_current_branch
from prompts import build_commit_prompt, build_pr_prompt
from safe_mode import sanitize_diff, mask_sensitive_data
from validators import validate_commit, validate_pr


def temperature_value(value):
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 2:
        raise argparse.ArgumentTypeError("temperature는 0~2 사이여야 합니다.")
    return value


def positive_int(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("토큰 수는 양의 정수여야 합니다.")
    return value


def add_options(parser, suppress=False):
    def default(value):
        return argparse.SUPPRESS if suppress else value
    parser.add_argument("--model", "-model", default=default(os.getenv("LLM_MODEL") or os.getenv("AI_MODEL") or "gpt-4.1-mini"), help="AI 모델 (LLM_MODEL / AI_MODEL 또는 gpt-4.1-mini)")
    parser.add_argument("--temperature", "-temperature", type=temperature_value, default=default(None), help="무작위성, 0~2 (일반 모델 기본 0.3, gpt-5-mini 생략)")
    parser.add_argument("--max-tokens", "-max-tokens", type=positive_int, default=default(1000), help="최대 출력 토큰 (기본 1000)")
    parser.add_argument("--safe-mode", "-safe-mode", action="store_true", default=default(False), help="민감정보 마스킹 및 diff 최대 10개 파일/200줄")


def create_parser():
    parser = argparse.ArgumentParser(description="Git 변경 사항에서 커밋 메시지와 PR 초안을 생성합니다.")
    add_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (("commit", "커밋 메시지 생성"), ("pr", "PR 초안 생성")):
        add_options(subparsers.add_parser(command, help=help_text), suppress=True)
    return parser


def main():
    args = create_parser().parse_args()
    calls = 0
    try:
        ensure_repository_root()
        status = get_git_status()
        if not status.strip():
            print("[INFO] 변경 사항이 없습니다. 커밋/PR 문구를 생성하지 않고 종료합니다.")
            return 0
        print("--- Changed Files ---")
        print(mask_sensitive_data(status) if args.safe_mode else status, end="" if status.endswith('\n') else '\n')
        if any(line.startswith("??") for line in status.splitlines()):
            print("[WARN] 미추적 파일의 내용은 diff에 포함되지 않습니다. 포함하려면 git add <파일> 후 실행하세요.")
        diff = get_git_diff()
        if not diff.strip():
            print("[INFO] 분석 가능한 텍스트 diff가 없습니다. 새 파일은 git add <파일> 후 다시 실행하세요.")
            return 0
        api_key = (os.getenv("LLM_API_KEY") or os.getenv("AI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError('LLM_API_KEY 또는 AI_API_KEY 환경변수가 설정되지 않았습니다. export LLM_API_KEY="YOUR_KEY"')
        if not args.model.strip():
            raise RuntimeError("모델명을 지정하세요: --model 또는 AI_MODEL")
        print(f"[INFO] Git diff 수집 완료: {len(diff.splitlines())}줄")
        branch = get_current_branch() if args.command == "pr" else ""
        if args.safe_mode:
            diff = sanitize_diff(diff)
            status = mask_sensitive_data(status)
            branch = mask_sensitive_data(branch)
            print("[INFO] Safe Mode: 마스킹 및 diff 최대 10개 파일/200줄 제한")
        if args.command == "commit":
            prompt = build_commit_prompt(status, diff)
            validate = validate_commit
        else:
            print(f"[INFO] 현재 브랜치: {branch}")
            prompt = build_pr_prompt(branch, status, diff)
            validate = validate_pr
        original_prompt = prompt
        for attempt in range(2):
            calls += 1
            print(f"[INFO] AI API 요청 중... ({calls}/2)")
            result = call_ai(api_key, prompt, args.model, args.temperature, args.max_tokens)
            errors = validate(result)
            if not errors:
                break
            if attempt == 1:
                raise RuntimeError("재생성 후에도 형식 검증 실패: " + "; ".join(errors))
            print("[WARN] 형식 검증 실패, 한 번 재생성합니다: " + "; ".join(errors))
            prompt = original_prompt + "\n\n[이전 응답의 형식 오류: 반드시 수정]\n" + "\n".join(errors)
        print("[DONE] 검증된 초안 생성 완료 (내용을 검토한 후 적용하세요)")
        if args.command == "commit":
            if len(result.splitlines()[0]) > 50:
                print("[INFO] 커밋 제목은 50자 이내를 권장합니다 (최대 72자 허용).")
            print("\n--- Commit Message ---")
        print(result)
        print("----------------------")
        return 0
    except RuntimeError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    finally:
        print(f"[INFO] AI API 호출 횟수: {calls}")


if __name__ == "__main__":
    sys.exit(main())
