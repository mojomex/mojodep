from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import git
import yaml
from mojodep_rosdistro import config

import logging

logger = logging.getLogger(__name__)


def get_or_clone_rosdistro_repo():
    repo_url = config.ROSDISTRO_REPO_URL
    repo_path = config.ROSDISTRO_REPO_PATH

    if repo_path.exists():
        return git.Repo(repo_path)

    repo_path.parent.mkdir(parents=True, exist_ok=True)
    return git.Repo.clone_from(repo_url, repo_path, depth=1)


def get_distribution_file_path(distro_name: str) -> Path:
    return config.ROSDISTRO_REPO_PATH / distro_name / "distribution.yaml"


INVALID_REPO_NO_RELEASE = "No release data"
INVALID_REPO_NO_RELEASE_REPO_URL = "No release repository URL"
INVALID_REPO_NO_RELEASE_TAG_PATTERN = "No release tag pattern"


@dataclass
class ReleaseRepoInfo:
    release_repo_url: str
    release_tag_pattern: str


@dataclass
class RepoExtractionResult:
    release_info: dict[str, ReleaseRepoInfo]
    invalid_repos: dict[str, str]


def extract_released_repos(distro_name: str) -> RepoExtractionResult:
    """Extract released repositories from the rosdistro repository."""

    distro_file_path = get_distribution_file_path(distro_name)
    if not distro_file_path.exists():
        raise FileNotFoundError(f"Distribution file {distro_file_path} does not exist.")

    with open(distro_file_path, "r") as f:
        distro_data = yaml.safe_load(f)

    if "repositories" not in distro_data:
        print("No repositories found in distribution file")
        return {}

    release_info = {}
    invalid_repos = {}

    for repo_name, repo_data in distro_data["repositories"].items():
        if "release" not in repo_data:
            invalid_repos[repo_name] = INVALID_REPO_NO_RELEASE
            continue

        release_data = repo_data["release"]

        # Extract the information we need
        if "url" not in release_data:
            invalid_repos[repo_name] = INVALID_REPO_NO_RELEASE_REPO_URL
            continue
        release_repo_url = release_data["url"]

        if "tags" not in release_data or "release" not in release_data["tags"]:
            invalid_repos[repo_name] = INVALID_REPO_NO_RELEASE_TAG_PATTERN
            continue
        release_tag_pattern = release_data["tags"]["release"]

        release_info[repo_name] = ReleaseRepoInfo(
            release_repo_url=release_repo_url, release_tag_pattern=release_tag_pattern
        )

    return RepoExtractionResult(release_info=release_info, invalid_repos=invalid_repos)


@dataclass
class TagInfo:
    tag: str
    ref: str


def fetch_remote_tags(repo_url: str) -> list[TagInfo]:
    tags_output = subprocess.run(
        ["git", "ls-remote", "--tags", repo_url],
        capture_output=True,
        text=True,
        check=True,
    )

    lines = tags_output.stdout.strip().split("\n")
    tags = []
    for line in lines:
        parts = line.split()
        if len(parts) != 2:
            logger.warning(f"Unexpected line format in git ls-remote output: {line}")
            continue

        if not parts[1].startswith("refs/tags/"):
            logger.warning(f"Skipping non-tag reference: {parts[1]}")
            continue

        parts[1] = parts[1].removeprefix("refs/tags/")

        tags.append(TagInfo(tag=parts[1], ref=parts[0]))
    return tags


@dataclass
class ReleasedPackageVersion:
    version: tuple[int, int, int, int]  # (major, minor, patch, increment)
    tag: str
    commit_hash: str


@dataclass
class ReleasedPackage:
    name: str
    release_repo_url: str
    versions: list[ReleasedPackageVersion]

def release_tag_pattern_to_regex(pattern: str) -> re.Pattern:
    pattern = re.escape(pattern)

    if r"\{package\}" not in pattern:
        raise ValueError("Pattern must contain {package} placeholder")
    if r"\{version\}" not in pattern:
        raise ValueError("Pattern must contain {version} placeholder")

    pattern = pattern.replace(r"\{version\}", r"(?P<version_maj>\d+)\.(?P<version_min>\d+)\.(?P<version_patch>\d+)-(?P<version_increment>\d+)")
    pattern = pattern.replace(r"\{package\}", r"(?P<package_name>\w+)")

    return re.compile(pattern)

def extract_released_packages_and_versions(release_repo_info: ReleaseRepoInfo) -> list[ReleasedPackage]:
    tags = fetch_remote_tags(release_repo_info.release_repo_url)

    if not tags:
        logger.warning(f"No tags found for repository {release_repo_info.release_repo_url}")
        return []
    
    tag_pattern = release_tag_pattern_to_regex(release_repo_info.release_tag_pattern)

    released_packages: dict[str, ReleasedPackage] = {}
    for tag_info in tags:
        match = tag_pattern.match(tag_info.tag)
        if not match:
            continue

        package_name = match.group("package_name")
        version = (
            int(match.group("version_maj")),
            int(match.group("version_min")),
            int(match.group("version_patch")),
            int(match.group("version_increment")),
        )

        if package_name not in released_packages:
            released_packages[package_name] = ReleasedPackage(
                name=package_name,
                release_repo_url=release_repo_info.release_repo_url,
                versions=[]
            )

        released_packages[package_name].versions.append(
            ReleasedPackageVersion(
                version=version,
                tag=tag_info.tag,
                commit_hash=tag_info.ref
            )
        )

    return list(released_packages.values())
