"""generate_guest_agent_setup tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import console
from executor.tool_dispatch.tools.base import Tool
class GenerateGuestAgentSetupTool(Tool):
    names = ("generate_guest_agent_setup",)
    def run(self, args, ctx):
        result = context.manager.generate_guest_agent_setup(args["name"])
        if not ctx.verbose:
            if result.get("success"):
                console.print(
                    f"[green]✓ Guest agent setup script ready: {result['path']}[/green]\n"
                    f"[dim]  Run inside the VM: {result['cmd_template']}[/dim]"
                )
            else:
                console.print(f"[red]{result.get('error', 'unknown error')}[/red]")
        return result
