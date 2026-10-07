"""Git의 읽기 전용 명령으로 작업 트리 정보를 수집한다."""
from pathlib import Path
import subprocess


def run_git_command(args):
    try:
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


def ensure_repository_root():
    root = run_git_command(["rev-parse", "--show-toplevel"]).strip()
    if Path(root).resolve() != Path.cwd().resolve():
        raise RuntimeError(f"프로젝트 루트에서 실행하세요: {root}")


def get_git_status():
    return run_git_command(["status", "--short", "--untracked-files=all"])


def get_git_diff():
    # staged/unstaged는 서로 다른 비교이므로 명시적으로 구분한다.
    parts = []
    for label, args in (("Unstaged changes", []), ("Staged changes", ["--cached"])):
        diff = run_git_command(["diff", "--no-ext-diff", "--no-textconv", "--no-color"] + args)
        if diff.strip():
            parts.append(f"[{label}]\n{diff}")
    return "\n".join(parts)


def get_current_branch():
    return run_git_command(["branch", "--show-current"]).strip() or "(detached HEAD)"
