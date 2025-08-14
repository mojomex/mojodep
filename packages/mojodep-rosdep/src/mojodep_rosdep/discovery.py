from dataclasses import dataclass
import re
import shutil
import subprocess

@dataclass(frozen=True)
class ResolvedRosdep:
    key: str
    source: str
    packages: list[str]

def _find_rosdep():
    rosdep = shutil.which("rosdep")
    if rosdep is None:
        raise RuntimeError("rosdep is not installed or not found in PATH")
    return rosdep

def list_dependency_keys() -> list[str]:
    rosdep = _find_rosdep()

    result = subprocess.run(
        [rosdep, "keys", "--from-paths", ".", "--ignore-src"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to list rosdep keys: {result.stderr.strip()}")

    return result.stdout.splitlines()


def resolve_keys(keys: list[str]) -> list[ResolvedRosdep]:
    rosdep = _find_rosdep()

    result = subprocess.run(
        [rosdep, "resolve", *keys],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to resolve rosdep keys: {result.stderr.strip()}")

    # Expected format:
    # #ROSDEP[<key>]         -- rosdep_header
    # #<source>              -- rosdep_source
    # <resolved_package> ... -- rosdep_package_list

    resolved: list[ResolvedRosdep] = []

    re_rosdep_header = re.compile(r"^#ROSDEP\[(?P<key>\S+)\]")
    re_rosdep_source = re.compile(r"^#(?P<source>\S+)$")
    re_rosdep_package_list = re.compile(r"^(\S+)(?:\s+(\S+))*$")

    current_key = None
    current_source = None

    for line in result.stdout.splitlines():
        if current_key is None:
            m = re_rosdep_header.match(line)
            if not m:
                raise ValueError(f"Unexpected line format: {line}. Expected #ROSDEP[<key>].")
            current_key = m.group("key")
            continue

        if current_source is None:
            m = re_rosdep_source.match(line)
            if not m:
                raise ValueError(f"Unexpected line format: {line}. Expected #<source>.")
            current_source = m.group("source")
            continue

        m = re_rosdep_package_list.match(line)
        if not m:
            raise ValueError(f"Unexpected line format: {line}. Expected <resolved_package> ...")

        packages = list(filter(None, m.groups()))
        resolved.append(ResolvedRosdep(current_key, current_source, packages))

        # Reset for the next key
        current_key = None
        current_source = None

    if current_key is not None or current_source is not None:
        raise ValueError("Incomplete rosdep resolution, source header or source list.")

    return resolved