"""run_guest_command tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import console
from executor.tool_dispatch.tools.base import Tool
class RunGuestCommandTool(Tool):
    names = ("run_guest_command",)
    def run(self, args, ctx):
        result = context.manager.run_guest_command(args["name"], args["command"], timeout=args.get("timeout"))
        if not ctx.verbose:
            if result.get("success"):
                if result.get("stdout"):
                    console.print(result["stdout"], end="" if result["stdout"].endswith("\n") else "\n")
                if result.get("stderr"):
                    console.print(f"[red]{result['stderr']}[/red]", end="")
                console.print(f"[dim]exit code: {result.get('exit_code')}[/dim]")
            else:
                console.print(f"[red]{result.get('error', 'unknown error')}[/red]")
        return result
