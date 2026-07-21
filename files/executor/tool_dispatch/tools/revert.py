"""revert tool — undo the last reversible tool call (re-runs its recorded inverse)."""
import sys
from executor.tool_dispatch.context import console, _last_revert_action, _clear_revert
from executor.tool_dispatch.tools.base import Tool
class RevertTool(Tool):
    names = ("revert",)
    def run(self, args, ctx):
        if not _last_revert_action:
            return {"success": False, "error": "No reversible action to revert."}
        rev = dict(_last_revert_action)
        console.print(f"\n[yellow]↩ Revert: {rev['description']}[/yellow]")
        if not sys.stdin.isatty():
            console.print("[dim]Cancelled (no interactive terminal to confirm).[/dim]")
            return {"success": False, "error": "Revert cancelled: not running interactively."}
        try:
            answer = console.input("[bold cyan]Proceed? (y/n):[/bold cyan] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return {"success": False, "error": "Revert cancelled by user."}
        if answer != "y":
            return {"success": False, "error": "Revert cancelled by user."}
        _clear_revert()
        return ctx.redispatch(rev["tool"], rev["args"])
