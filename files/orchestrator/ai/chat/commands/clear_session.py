"""clear-session — wipe the saved AI chat session."""

from typing import List

from .base import Command
from . import context as ctx


class ClearSessionCommand(Command):
    names = ("clear-session",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        ctx.clear_session()
