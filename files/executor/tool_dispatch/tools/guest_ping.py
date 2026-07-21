"""guest_ping tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import console
from executor.tool_dispatch.tools.base import Tool
class GuestPingTool(Tool):
    names = ("guest_ping",)
    def run(self, args, ctx):
        result = context.manager.guest_ping(args["name"])
        if not ctx.verbose:
            if result.get("success"):
                style = "green" if result.get("alive") else "yellow"
                state = "alive" if result.get("alive") else "not responding"
                console.print(f"[{style}]{args['name']}: guest agent {state}[/{style}]")
            else:
                console.print(f"[red]{result.get('error', 'unknown error')}[/red]")
        return result
