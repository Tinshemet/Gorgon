"""templates — list VM templates."""

from typing import List

from .base import Command
from . import context as ctx


class TemplatesCommand(Command):
    names = ("templates",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        ctx.render_templates(ctx.manager.list_templates())
