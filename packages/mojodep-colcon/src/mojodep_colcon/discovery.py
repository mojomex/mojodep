from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess


@dataclass(frozen=True)
class ColconSourcePackage:
    name: str
    path: Path
    type: str


def _find_colcon():
    colcon = shutil.which("colcon")
    if colcon is None:
        raise RuntimeError("colcon is not installed or not found in PATH")
    return colcon

def discover_packages():
    colcon = _find_colcon()

    result = subprocess.run(
        [colcon, "list"],
        capture_output=True,
        text=True,
        check=True,
    )

    re_list_entry = r"^(?P<name>\S+)\s+(?P<path>.+)\s+\((?P<type>\S+)\)$"
    matches = [
        m
        for line in result.stdout.splitlines()
        if (m := re.match(re_list_entry, line))
    ]
    packages = [
        ColconSourcePackage(
            name=m.group("name"),
            path=Path(m.group("path")).resolve(),
            type=m.group("type"),
        )
        for m in matches
    ]

    return packages
