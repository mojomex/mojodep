from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class GitVersion:
    ref_name: str | None
    commit_hash: str
    is_dirty: bool


def _find_git():
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is not installed or not found in PATH")
    return git


def find_repository_containing(path: Path) -> Path | None:
    """
    Find the nearest parent directory that is a Git repository.
    Returns the path to the repository or None if not found.
    """

    git = _find_git()
    result = subprocess.run(
        [git, "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    return Path(result.stdout.strip()).resolve()


def get_branch_name(repo: Path) -> str | None:
    git = _find_git()
    result = subprocess.run(
        [git, "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to get Git branch name: {result.stderr.strip()}")

    # This returns either the branch name, if a branch is checked out, or "HEAD" if in a detached state.
    ref_name = result.stdout.strip()

    # Detached, return None
    if ref_name == "HEAD":
        return None

    return ref_name


def get_tag_name(repo: Path) -> str | None:
    git = _find_git()
    result = subprocess.run(
        [git, "-C", str(repo), "describe", "--tags", "--exact-match"],
        capture_output=True,
        text=True,
    )

    # If no tag describes the current commit, the command fails with a non-zero exit code.
    if result.returncode != 0:
        return None

    tag_name = result.stdout.strip()
    if not tag_name:
        raise RuntimeError("Failed to get Git tag name")

    return tag_name


def get_commit_hash(repo: Path) -> str:
    git = _find_git()
    result = subprocess.run(
        [git, "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to get Git commit hash: {result.stderr.strip()}")

    return result.stdout.strip()


def is_dirty(repo: Path) -> bool:
    """
    Check if the Git repository at the given path has uncommitted changes.
    Returns True if there are uncommitted changes, False otherwise.
    """

    git = _find_git()
    result = subprocess.run(
        [git, "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to check Git repository status: {result.stderr.strip()}"
        )

    # The output contains a list of uncommitted changes. If empty, the repo is clean.
    return bool(result.stdout.strip())


def get_repository_version(repo: Path) -> GitVersion:
    """
    Get the current Git version information for the repository at the given path.
    Returns a GitVersion object with ref_name, commit_hash, and is_dirty attributes.
    """

    ref_name = get_branch_name(repo)

    if ref_name is None:
        ref_name = get_tag_name(repo)

    if ref_name is None:
        ref_name = None

    commit_hash = get_commit_hash(repo)

    dirty = is_dirty(repo)

    return GitVersion(ref_name=ref_name, commit_hash=commit_hash, is_dirty=dirty)
