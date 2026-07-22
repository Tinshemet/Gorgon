"""logout — end this box's login session."""

from typing import List

from .base import Command
from . import context as ctx


class LogoutCommand(Command):
    names = ("logout",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        ctx._auth_sessions.invalidate_session(ctx._auth_sessions.read_current_session())
        ctx._auth_sessions.clear_current_session()
        ctx.console.print("[dim]Logged out.[/dim]")
