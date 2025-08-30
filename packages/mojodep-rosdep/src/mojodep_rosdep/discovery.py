import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Collection


@dataclass(frozen=True)
class ResolvedRosdep:
    key: str
    source: str
    packages: list[str]


@dataclass(frozen=True)
class AptVersion:
    version: str
    hash: str


@dataclass(frozen=True)
class PipVersion:
    version: str


def _find_rosdep():
    rosdep = shutil.which("rosdep")
    if rosdep is None:
        raise RuntimeError("rosdep is not installed or not found in PATH")
    return rosdep


def list_dependency_keys() -> set[str]:
    rosdep = _find_rosdep()

    result = subprocess.run(
        [rosdep, "keys", "--from-paths", ".", "--ignore-src"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to list rosdep keys: {result.stderr.strip()}")

    return set(result.stdout.splitlines())


def get_keys_in_rosdistro(keys: Collection[str], distro: str) -> set[str]:
    rosdep = _find_rosdep()

    result = subprocess.run(
        [rosdep, "where-defined", *keys],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to list rosdep keys for distro {distro}: {result.stderr.strip()}"
        )

    lines = result.stdout.splitlines()
    if len(lines) != len(keys):
        raise ValueError(
            f"Unexpected number of lines in rosdep output: queried {len(keys)}, got {len(lines)}."
        )

    expected_distro_uri = f"https://raw.githubusercontent.com/ros/rosdistro/master/{distro}/distribution.yaml"

    return {key for key, uri in zip(keys, lines) if uri.strip() == expected_distro_uri}


def resolve_keys_to_system_deps(keys: Collection[str]) -> list[ResolvedRosdep]:
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
                raise ValueError(
                    f"Unexpected line format: {line}. Expected #ROSDEP[<key>]."
                )
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
            raise ValueError(
                f"Unexpected line format: {line}. Expected <resolved_package> ..."
            )

        packages = list(filter(None, m.groups()))
        resolved.append(ResolvedRosdep(current_key, current_source, packages))

        # Reset for the next key
        current_key = None
        current_source = None

    if current_key is not None or current_source is not None:
        raise ValueError("Incomplete rosdep resolution, source header or source list.")

    return resolved


def _find_apt_cache():
    apt_cache = shutil.which("apt-cache")
    if apt_cache is None:
        raise RuntimeError("apt-cache is not installed or not found in PATH")
    return apt_cache


def get_apt_version(apt_package: str) -> AptVersion | None:
    apt_cache = _find_apt_cache()
    result = subprocess.run(
        [apt_cache, "show", apt_package],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise ValueError(
            f"Failed to get apt package version for {apt_package}: {result.stderr.strip()}"
        )

    re_version = re.compile(r"^Version:\s*(?P<version>\S+)$")
    re_hash = re.compile(r"^SHA256:\s*(?P<hash>\S+)$")

    version = re_version.search(result.stdout)
    hash = re_hash.search(result.stdout)

    if not version or not hash:
        raise ValueError(
            f"Failed to parse apt package version for {apt_package}: {result.stderr.strip()}"
        )

    return AptVersion(version.group("version"), hash.group("hash"))


def _find_pip3():
    pip3 = shutil.which("pip3")
    if pip3 is None:
        raise RuntimeError("pip3 is not installed or not found in PATH")
    return pip3


def get_pip_version(pip_package: str) -> PipVersion | None:
    pip3 = _find_pip3()
    result = subprocess.run(
        [pip3, "show", pip_package],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise ValueError(
            f"Failed to get pip package version for {pip_package}: {result.stderr.strip()}"
        )

    re_version = re.compile(r"^Version:\s*(?P<version>\S+)$")

    version = re_version.search(result.stdout)
    if not version:
        raise ValueError(
            f"Failed to parse pip package version for {pip_package}: {result.stderr.strip()}"
        )

    return PipVersion(version.group("version"))
