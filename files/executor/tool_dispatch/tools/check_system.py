"""check_system tool."""
from executor.tool_dispatch.context import check_system_capabilities, OVMF, render_system
from executor.tool_dispatch.tools.base import Tool
class CheckSystemTool(Tool):
    names = ("check_system",)
    def run(self, args, ctx):
        caps = check_system_capabilities()
        caps["ovmf_paths"] = OVMF
        if not ctx.verbose:
            render_system(caps)
        return caps
