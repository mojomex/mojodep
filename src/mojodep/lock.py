import argparse
from sys import stdout

import mojodep_colcon
import mojodep_colcon.discovery
import mojodep_lockfile
import mojodep_lockfile.serde
from mojodep_lockfile.types import Lockfile
import mojodep_rosdep
import mojodep_rosdep.discovery
import mojodep_rosdistro
import mojodep_rosdistro.resolve


def register_subcommand(subparsers: argparse._SubParsersAction):
    subparsers.add_parser("lock", help="Generate a lock file of the current project")


def on_lock_command(args):
    distro = args.distro

    resolved_project_packages = mojodep_colcon.discovery.discover_packages()
    rosdeps = mojodep_rosdep.discovery.list_dependency_keys()

    resolved_rosdistro_packages = mojodep_rosdistro.resolve.resolve_keys_to_sources(
        rosdeps, distro
    )

    rosdistro_keys = {pkg.name for pkg in resolved_rosdistro_packages}
    system_keys = rosdeps - rosdistro_keys

    resolved_system_keys = mojodep_rosdep.discovery.resolve_keys_to_system_deps(
        system_keys
    )

    project_packages = {pkg.name: pkg for pkg in resolved_project_packages}
    resolved_rosdistro_packages = {pkg.name: pkg for pkg in resolved_rosdistro_packages}
    resolved_system_keys = {pkg.key: pkg for pkg in resolved_system_keys}

    lockfile = Lockfile(
        0,
        project_packages,
        resolved_rosdistro_packages,
        resolved_system_keys
    )

    with open("mojodep.lock", "wb") as f:
        mojodep_lockfile.serde.dump(lockfile, f)

    print("Project:")
    for pkg in resolved_project_packages:
        print(f" - {pkg}")

    print("Distro source packages:")
    for pkg in resolved_rosdistro_packages:
        print(f" - {pkg}")

    print("System packages:")
    for pkg in resolved_system_keys:
        print(f" - {pkg}")
