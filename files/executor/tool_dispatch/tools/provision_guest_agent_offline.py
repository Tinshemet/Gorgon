"""provision_guest_agent_offline tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import console
from executor.tool_dispatch.tools.base import Tool
class ProvisionGuestAgentOfflineTool(Tool):
    names = ("provision_guest_agent_offline",)
    def run(self, args, ctx):
        result = context.manager.provision_guest_agent_offline(args["name"])
        if not ctx.verbose:
            if result.get("success"):
                console.print(f"[green]✓ Stealth serial-agent provisioned offline on '{args['name']}'[/green]")
            else:
                console.print(f"[red]{result.get('error', 'unknown error')}[/red]")
        return result
