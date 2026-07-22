"""snapshot — list/create/restore/delete VM snapshots."""

from typing import List

from .base import Command
from . import context as ctx


class SnapshotCommand(Command):
    names = ("snapshot",)
    min_args = 2

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        sub = rest[0]
        if sub == "list" and len(rest) >= 2:
            r = ctx.manager.snapshot_list(rest[1])
            ctx.render_snapshots(r)
        elif sub == "create" and len(rest) >= 3:
            r = ctx.manager.snapshot_create(rest[1], rest[2])
            ctx.console.print(f"[success]{r.get('message', r.get('error'))}[/success]")
        elif sub == "restore" and len(rest) >= 3:
            r = ctx.manager.snapshot_restore(rest[1], rest[2])
            ctx.console.print(f"[success]{r.get('message', r.get('error'))}[/success]")
        elif sub == "delete" and len(rest) >= 3:
            r = ctx.manager.snapshot_delete(rest[1], rest[2])
            ctx.console.print(f"[success]{r.get('message', r.get('error'))}[/success]")
