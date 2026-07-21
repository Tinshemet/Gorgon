"""resize_disk tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert
from executor.tool_dispatch.tools.base import Tool
class ResizeDiskTool(Tool):
    names = ("resize_disk",)
    def run(self, args, ctx):
        _clear_revert()
        return context.manager.resize_disk(args["name"], args.get("disk_index", 0), args["new_size_gb"])
