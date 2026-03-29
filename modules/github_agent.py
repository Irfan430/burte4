"""modules/github_agent.py — Git and GitHub operations."""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_git(args: list[str], cwd: str | None = None, timeout: int = 60) -> dict:
    """Run a git command and return result."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return {"observation": result.stdout.strip() or "সম্পন্ন", "display": None}
        return {"observation": f"গিট ত্রুটি: {result.stderr.strip()}", "display": None}
    except subprocess.TimeoutExpired:
        return {"observation": "গিট কমান্ড টাইমআউট হয়েছে।", "display": None}
    except FileNotFoundError:
        return {"observation": "গিট ইনস্টল করা নেই।", "display": None}
    except OSError as exc:
        return {"observation": f"OS ত্রুটি: {exc}", "display": None}


def git_clone(url: str, path: str) -> dict:
    """Clone a git repository."""
    return _run_git(["clone", url, path])


def git_status(repo_path: str = ".") -> dict:
    """Get git status of a repository."""
    return _run_git(["status", "--short"], cwd=repo_path)


def git_diff(repo_path: str = ".") -> dict:
    """Get git diff."""
    return _run_git(["diff", "--stat"], cwd=repo_path)


def git_create_branch(branch_name: str, repo_path: str = ".") -> dict:
    """Create and checkout a new branch."""
    result = _run_git(["checkout", "-b", branch_name], cwd=repo_path)
    if "ত্রুটি" in result["observation"]:
        # Branch might already exist
        return _run_git(["checkout", branch_name], cwd=repo_path)
    return result


def git_commit(message: str, repo_path: str = ".") -> dict:
    """Stage all changes and commit."""
    _run_git(["add", "-A"], cwd=repo_path)
    return _run_git(["commit", "-m", message], cwd=repo_path)


def git_push(repo_path: str = ".", branch: str = "") -> dict:
    """Push current branch to remote."""
    args = ["push"]
    if branch:
        args += ["origin", branch]
    else:
        args += ["--set-upstream", "origin", "HEAD"]
    return _run_git(args, cwd=repo_path, timeout=120)


def git_pull(repo_path: str = ".") -> dict:
    """Pull latest changes from remote."""
    return _run_git(["pull"], cwd=repo_path, timeout=120)


def git_log(repo_path: str = ".", n: int = 10) -> dict:
    """Get recent commit log."""
    return _run_git(["log", f"-{n}", "--oneline"], cwd=repo_path)
