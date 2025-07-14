import shutil
import mojodep_rosdistro.config as config

from mojodep_rosdistro.resolve import TagInfo, get_or_clone_rosdistro_repo


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
