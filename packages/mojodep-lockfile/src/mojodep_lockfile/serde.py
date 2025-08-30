from typing import BinaryIO

from mojodep_lockfile.types import Lockfile


def dumps(lockfile: Lockfile):
    return tosholi.format.dumps(lockfile)


def dump(lockfile: Lockfile, fp: BinaryIO):
    tosholi.format.dump(lockfile, fp)


def loads(data: str) -> Lockfile:
    return tosholi.parse.loads(Lockfile, data)


def load(fp: BinaryIO) -> Lockfile:
    return tosholi.parse.load(Lockfile, fp)
