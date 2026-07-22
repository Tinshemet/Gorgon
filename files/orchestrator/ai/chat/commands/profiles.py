"""profiles — list available hardware profiles."""

from typing import List

from .base import Command
from . import context as ctx


class ProfilesCommand(Command):
    names = ("profiles",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        ctx.render_profiles(ctx.list_profiles())
