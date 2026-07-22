"""isos — scan common locations for installer ISOs."""

from typing import List

from rich import box
from rich.table import Table

from .base import Command
from . import context as ctx


class IsosCommand(Command):
    names = ("isos",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        isos = ctx.manager.scan_isos()
        if isos:
            t = Table(box=box.ROUNDED, border_style="cyan")
            t.add_column("File")
            t.add_column("Size")
            t.add_column("Path", style="dim")
            for iso in isos:
                t.add_row(iso["name"], f"{iso['size_gb']}GB", iso["path"])
            ctx.console.print(t)
        else:
            ctx.console.print("[warn]No ISOs found in common locations.[/warn]")
