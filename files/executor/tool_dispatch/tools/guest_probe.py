"""guest_probe tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import console
from executor.tool_dispatch.tools.base import Tool
class GuestProbeTool(Tool):
    names = ("guest_probe",)
    def run(self, args, ctx):
        result = context.manager.guest_probe(
            args["name"], args["assertion"], args["target"],
            value=args.get("value"), timeout=args.get("timeout")
        )
        if not ctx.verbose:
            if result.get("success"):
                holds = result.get("holds")
                style = "green" if holds else "yellow"
                console.print(f"[{style}]{args['name']}: {result['assertion']}"
                              f"({result['target']}) → {'holds' if holds else 'does not hold'}[/{style}]")
            else:
                console.print(f"[red]{result.get('error', 'unknown error')}[/red]")
        return result
