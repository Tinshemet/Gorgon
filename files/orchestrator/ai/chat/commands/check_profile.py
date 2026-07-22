"""check-profile — show host compatibility for a profile."""

from typing import List

from .base import Command
from . import context as ctx


class CheckProfileCommand(Command):
    names = ("check-profile",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        ctx.render_compat(ctx.check_profile_compatibility(rest[0]))
