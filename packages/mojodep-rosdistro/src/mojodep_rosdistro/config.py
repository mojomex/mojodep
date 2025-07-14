import mojodep_core.config as core_config

ROSDISTRO_REPO_URL = core_config.get_mojodep_env_var(
    "ROSDISTRO_REPO_URL", "https://github.com/ros/rosdistro.git"
)

ROSDISTRO_REPO_PATH = core_config.CACHE_DIR / "rosdistro" / "repository"
ROSDISTRO_RESOLVED_PACKAGES_PATH = (
    core_config.CACHE_DIR / "rosdistro" / "resolved_packages.yaml"
)
