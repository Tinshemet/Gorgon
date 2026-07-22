"""-tf — show a fingerprint report for a VM."""

from typing import List

from .base import Command
from . import context as ctx


class FingerprintCommand(Command):
    names = ("-tf",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        ctx.tf_report(rest[0])
