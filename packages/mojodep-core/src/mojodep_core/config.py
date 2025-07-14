import os
from pathlib import Path

MOJODEP_ENV_PREFIX = "MOJODEP_"

def get_mojodep_env_var(var_name: str, default: str) -> str:
    return os.getenv(MOJODEP_ENV_PREFIX + var_name, default)

def _require_env_var(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise EnvironmentError(f"Environment variable '{var_name}' is not set.")
    return value

HOME: Path = Path(_require_env_var("HOME"))

DATA_DIR: Path = Path(get_mojodep_env_var("DATA_DIR", HOME / ".mojodep"))
CACHE_DIR: Path = Path(get_mojodep_env_var("CACHE_DIR", HOME / ".cache" / "mojodep"))