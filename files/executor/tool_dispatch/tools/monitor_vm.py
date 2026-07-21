"""monitor_vm tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_monitor
from executor.tool_dispatch.tools.base import Tool
class MonitorVmTool(Tool):
    names = ("monitor_vm",)
    def run(self, args, ctx):
        if args["name"] == "all":
            result = context.manager.monitor_all()
            if not ctx.verbose:
                for r in result.values():
                    render_monitor(r)
            return result
        result = context.manager.monitor_vm(args["name"])
        if not ctx.verbose:
            render_monitor(result)
        return result
