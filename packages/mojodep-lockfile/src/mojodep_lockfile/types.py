from dataclasses import dataclass

from mojodep_colcon.discovery import ColconSourcePackage
from mojodep_rosdep.discovery import ResolvedRosdep
from mojodep_rosdistro.resolve import ReleasedPackage


@dataclass
class Lockfile:
    version: int
    project_packages: dict[str, ColconSourcePackage]
    rosdistro_packages: dict[str, ReleasedPackage]
    system_packages: dict[str, ResolvedRosdep]
