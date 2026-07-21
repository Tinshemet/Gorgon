"""print_command tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import console, Panel
from executor.tool_dispatch.tools.base import Tool
class PrintCommandTool(Tool):
    names = ("print_command",)
    def run(self, args, ctx):
        result = context.manager.print_command(args["name"])
        if result.get("success") and not ctx.verbose:
            console.print(Panel(result["command"], title="QEMU Command", border_style="cyan"))
            return {"success": True, "command": result["command"]}
        return result
