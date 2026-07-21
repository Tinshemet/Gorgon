"""get_vm_logs tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_vm_failure, _TOOL_DEFS
from executor.tool_dispatch.tools.base import Tool
class GetVmLogsTool(Tool):
    names = ("get_vm_logs",)
    def run(self, args, ctx):
        result = context.manager.get_vm_logs(args["name"], lines=int(args.get("lines", _TOOL_DEFS["log_lines"])))
        if not ctx.verbose:
            render_vm_failure(result)
        return result
