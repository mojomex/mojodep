import dataclasses
import logging
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Collection

import yaml
from git import Repo

from mojodep_rosdistro import config

logger = logging.getLogger(__name__)


def get_or_clone_rosdistro_repo():
    """Ensure the local rosdistro repository is available and return it.

    Returns:
        Repo: The rosdistro repository.
    """

    repo_url = config.ROSDISTRO_REPO_URL
    repo_path = config.ROSDISTRO_REPO_PATH

    if repo_path.exists():
        return Repo(repo_path)

    repo_path.parent.mkdir(parents=True, exist_ok=True)
    return Repo.clone_from(repo_url, repo_path, depth=1)


def get_distribution_file_path(rosdistro_repo: Repo, distro_name: str) -> Path:
    """Get the path to the distribution file for a given ROS distribution.

    Args:
        rosdistro_repo (Repo): The rosdistro repository.
        distro_name (str): The name of the distribution.

    Raises:
        ValueError: If the rosdistro repository is bare.
        FileNotFoundError: If the distribution file does not exist.

    Returns:
        Path: The path to the distribution file.
    """

    if rosdistro_repo.working_tree_dir is None:
        raise ValueError("Rosdistro repository is bare")

    path = Path(rosdistro_repo.working_tree_dir) / distro_name / "distribution.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Distribution file {path} does not exist.")
    return path


INVALID_REPO_NO_RELEASE = "No release data"
INVALID_REPO_NO_RELEASE_REPO_URL = "No release repository URL"
INVALID_REPO_NO_RELEASE_TAG_PATTERN = "No release tag pattern"


@dataclass(frozen=True)
class ReleaseRepoInfo:
    release_repo_url: str
    release_tag_pattern: str


@dataclass(frozen=True)
class RepoExtractionResult:
    release_info: dict[str, ReleaseRepoInfo]
    invalid_repos: dict[str, str]


def extract_released_repos(distro_file_path: Path) -> RepoExtractionResult:
    """Extract released repositories from the rosdistro repository.

    The result contains a dictionary {repo_name: repo_info} of all found,
    valid release repositories, along with a dictionary {repo_name: error_message}
    of all invalid repositories.

    Args:
        distro_file_path (Path): The path to the distribution file.

    Returns:
        RepoExtractionResult: The result of the extraction process.
    """

    with open(distro_file_path, "r") as f:
        distro_data = yaml.safe_load(f)

    if "repositories" not in distro_data:
        print("No repositories found in distribution file")
        return RepoExtractionResult({}, {})

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


@dataclass(frozen=True)
class TagInfo:
    tag: str
    ref: str


def _fetch_remote_tags(repo_url: str) -> list[TagInfo]:
    """For a given remote git repo URL, fetch all tags from the repository.

    Args:
        repo_url (str): The URL of the remote git repository.

    Returns:
        list[TagInfo]: A list of TagInfo objects representing the tags in the repository.
    """

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


@dataclass(frozen=True)
class BloomVersionNumber:
    major: int
    minor: int
    patch: int
    increment: int

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}-{self.increment}"


@dataclass(frozen=True)
class ReleasedPackageVersion:
    version: BloomVersionNumber
    tag: str
    commit_hash: str


@dataclass(frozen=True)
class ReleasedPackage:
    name: str
    release_repo_url: str
    versions: frozenset[ReleasedPackageVersion]


def _release_tag_pattern_to_regex(pattern: str) -> re.Pattern:
    """
    Convert a release tag pattern string into a regular expression.

    Specifically, the placeholders {package} and {version} will be converted into
    named capture groups in the regular expression.

    The resulting regular expression is guaranteed to have the following named groups:

    - package_name: The name of the package.
    - version_maj: The major version number.
    - version_min: The minor version number.
    - version_patch: The patch version number.
    - version_increment: The version increment number.

    Args:
        pattern (str): The release tag pattern string.

    Raises:
        ValueError: If one or both of the required placeholders are missing.

    Returns:
        re.Pattern: The compiled regular expression.
    """

    pattern = re.escape(pattern)

    if r"\{package\}" not in pattern:
        raise ValueError("Pattern must contain {package} placeholder")
    if r"\{version\}" not in pattern:
        raise ValueError("Pattern must contain {version} placeholder")

    pattern = pattern.replace(
        r"\{version\}",
        r"(?P<version_maj>\d+)\.(?P<version_min>\d+)\.(?P<version_patch>\d+)-(?P<version_increment>\d+)",
    )
    pattern = pattern.replace(r"\{package\}", r"(?P<package_name>\w+)")

    return re.compile(pattern)


def extract_released_packages_and_versions(
    release_repo_info: ReleaseRepoInfo,
) -> dict[str, ReleasedPackage]:
    """For a given release repo, extract a list of all released packages, along with their versions.

    Args:
        release_repo_info (ReleaseRepoInfo): The release repository information.

    Returns:
        dict[str, ReleasedPackage]: A dictionary mapping package names to their released package information.
    """

    tags = _fetch_remote_tags(release_repo_info.release_repo_url)

    if not tags:
        logger.warning(
            f"No tags found for repository {release_repo_info.release_repo_url}"
        )
        return {}

    tag_pattern = _release_tag_pattern_to_regex(release_repo_info.release_tag_pattern)

    released_packages: dict[str, ReleasedPackage] = {}
    for tag_info in tags:
        match = tag_pattern.match(tag_info.tag)
        if not match:
            continue

        package_name = match.group("package_name")
        version_num = BloomVersionNumber(
            int(match.group("version_maj")),
            int(match.group("version_min")),
            int(match.group("version_patch")),
            int(match.group("version_increment")),
        )

        if package_name not in released_packages:
            released_packages[package_name] = ReleasedPackage(
                name=package_name,
                release_repo_url=release_repo_info.release_repo_url,
                versions=frozenset(),
            )

        package = released_packages[package_name]
        version = ReleasedPackageVersion(
            version=version_num, tag=tag_info.tag, commit_hash=tag_info.ref
        )
        new_version_set = frozenset((*package.versions, version))

        package = dataclasses.replace(
            released_packages[package_name], versions=new_version_set
        )

        released_packages[package_name] = package

    return released_packages


def get_or_build_released_package_cache(repo_extraction_reult: RepoExtractionResult):
    release_info = repo_extraction_reult.release_info
    invalid_repos = repo_extraction_reult.invalid_repos

    if invalid_repos:
        print(f"Repos without source releases found: {invalid_repos}")

    valid_repos = set(release_info.values())

    all_packages = set()

    pool = ThreadPoolExecutor(max_workers=(os.cpu_count() or 1) * 4)
    extraction_results = pool.map(extract_released_packages_and_versions, valid_repos)

    all_packages = set()
    for result in extraction_results:
        # TODO: check whether any duplicated packages get overwritten
        all_packages.update(result.values())

    return all_packages


def resolve_keys_to_sources(keys: Collection[str], distro: str) -> set[ReleasedPackage]:
    repo = get_or_clone_rosdistro_repo()
    distro_file = get_distribution_file_path(repo, distro)
    result = extract_released_repos(distro_file)
    all_packages = get_or_build_released_package_cache(result)

    return {pkg for pkg in all_packages if pkg.name in keys}
