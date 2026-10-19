"""Git의 읽기 전용 명령으로 작업 트리 정보를 수집한다."""
from pathlib import Path
import subprocess


# Git을 별도 프로세스로 실행하고 표준 출력을 반환하며 실패는 공통 오류로 변환한다.
def run_git_command(args):
    try:
        # 인자를 목록으로 전달해 셸 해석을 피하고, 한글 경로와 실행 실패를 처리한다.
        return subprocess.run(
            ["git", "-c", "core.quotePath=false"] + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=True, timeout=30,
        ).stdout
    except FileNotFoundError as error:
        raise RuntimeError("Git이 설치되어 있지 않습니다.") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Git 명령 실행 시간이 30초를 초과했습니다.") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Git 명령 실행 실패: {error.stderr.strip()}") from error


# 심볼릭 링크를 해석한 실제 경로로 현재 위치와 저장소 루트를 비교한다.
def ensure_repository_root():
    root = run_git_command(["rev-parse", "--show-toplevel"]).strip()
    if Path(root).resolve() != Path.cwd().resolve():
        raise RuntimeError(f"프로젝트 루트에서 실행하세요: {root}")


# 변경 상태와 파일 목록을 짧은 형식으로 읽으며 미추적 파일도 각각 표시한다.
def get_git_status():
    return run_git_command(["status", "--short", "--untracked-files=all"])


# 스테이징 전후의 변경을 별도로 수집하며 파일이나 Git 인덱스를 변경하지 않는다.
def get_git_diff():
    # staged/unstaged는 서로 다른 비교이므로 명시적으로 구분한다.
    parts = []
    for label, args in (("Unstaged changes", []), ("Staged changes", ["--cached"])):
        # 외부 diff 프로그램·텍스트 변환·색상 코드를 제외하여 분석용 텍스트를 수집한다.
        diff = run_git_command(["diff", "--no-ext-diff", "--no-textconv", "--no-color"] + args)
        if diff.strip():
            parts.append(f"[{label}]\n{diff}")
    return "\n".join(parts)


# 현재 브랜치 이름을 읽고 브랜치가 없는 detached HEAD 상태도 표시한다.
def get_current_branch():
    return run_git_command(["branch", "--show-current"]).strip() or "(detached HEAD)"
