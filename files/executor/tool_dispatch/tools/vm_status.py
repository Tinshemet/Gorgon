"""vm_status tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_status
from executor.tool_dispatch.tools.base import Tool
class VmStatusTool(Tool):
    names = ("vm_status",)
    def run(self, args, ctx):
        result = context.manager.vm_status(args["name"])
        if not ctx.verbose:
            render_status(result)
        return result
