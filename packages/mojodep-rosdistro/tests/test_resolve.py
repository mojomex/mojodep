import shutil
import mojodep_rosdistro.config as config

from mojodep_rosdistro.resolve import (
    ReleaseRepoInfo,
    TagInfo,
    get_or_clone_rosdistro_repo,
)


def test_clone():
    shutil.rmtree(config.ROSDISTRO_REPO_PATH, ignore_errors=True)

    assert (
        not config.ROSDISTRO_REPO_PATH.exists()
    ), "Repository path should not exist before cloning"

    # Repo is cloned freshly
    repo = get_or_clone_rosdistro_repo()
    assert (
        config.ROSDISTRO_REPO_PATH.exists()
    ), "Repository path should exist after cloning"
    assert repo.working_tree_dir == str(
        config.ROSDISTRO_REPO_PATH
    ), "Cloned repository path does not match expected path"

    # Invoking a second time should return the existing repo
    repo = get_or_clone_rosdistro_repo()


def test_extract_released_repos():
    from mojodep_rosdistro.resolve import extract_released_repos

    # Ensure the repository is cloned
    get_or_clone_rosdistro_repo()

    # Extract released repositories for a known distribution
    result = extract_released_repos("humble")

    successful_repos = result.release_info

    assert (
        len(successful_repos) > 100
    ), "There should be at least 100 released repositories"


def test_fetch_remote_tags():
    from mojodep_rosdistro.resolve import fetch_remote_tags

    tags = fetch_remote_tags("https://github.com/mojomex/mojodep.git")

    expected = TagInfo("initial-commit", "decf36b64e0b6c955477d7848784a8a963b58950")
    assert expected in tags, "Expected tag not found in fetched tags"


def test_extract_released_packages_and_versions():
    from mojodep_rosdistro.resolve import extract_released_packages_and_versions

    release_repo_info = ReleaseRepoInfo(
        "https://github.com/ros2-gbp/rclcpp-release.git",
        "release/humble/{package}/{version}",
    )

    # Extract released packages and versions for a known distribution
    packages = extract_released_packages_and_versions(release_repo_info)

    expected_package_name = "rclcpp"
    expected_version = (16, 0, 4, 2)
    expected_commit_hash = "88d5e85c795fd0f815a2848bf5bf3ba9cfd9a314"

    matching_packages = filter(lambda pkg: pkg.name == expected_package_name, packages)
    found_package = next(matching_packages, None)

    assert found_package is not None, f"Package {expected_package_name} not found"

    matching_versions = filter(
        lambda ver: ver.commit_hash == expected_commit_hash, found_package.versions
    )
    found_version = next(matching_versions, None)

    assert (
        found_version is not None
    ), f"Version {expected_version} not found for package {expected_package_name}"
    assert (
        found_version.version == expected_version
    ), f"Expected version {expected_version}, but got {found_version.version}"
