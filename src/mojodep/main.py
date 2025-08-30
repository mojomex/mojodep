import argparse

from mojodep import lock
from mojodep.lock import register_subcommand


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Mojodep - All In One Reproducible Build Tool for ROS 2"
    )

    parser.add_argument("--distro", help="Specify the ROS 2 distribution", default="humble")
    parser.add_argument("--project", help="Run mojodep in the given project directory")

    subparsers = parser.add_subparsers(title="command", dest="command")
    register_subcommand(subparsers)

    return parser.parse_args()


def main():
    args = parse_arguments()
    
    match args.command:
        case "lock":
            lock.on_lock_command(args)


if __name__ == "__main__":
    main()
