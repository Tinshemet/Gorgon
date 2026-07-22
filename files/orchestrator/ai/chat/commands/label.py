"""label — add/remove/list VM fleet labels."""

from typing import List

from .base import Command
from . import context as ctx


class LabelCommand(Command):
    names = ("label",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        # label add <vm> <label> · label remove <vm> <label> · label list
        sub = rest[0] if rest else None
        if sub in ("add", "remove") and len(rest) >= 3:
            r = (ctx.manager.add_label if sub == "add" else ctx.manager.remove_label)(rest[1], rest[2])
            style = "success" if r.get("success") else "error"
            ctx.console.print(f"[{style}]{r.get('message', r.get('error', 'unknown error'))}[/{style}]")
        elif sub == "list":
            ctx.render_fleets(ctx.manager.list_labels().get("usage", {}))
        else:
            ctx.console.print("[error]Usage: gorgon label add|remove <vm> <label>  |  "
                              "gorgon label list[/error]")
