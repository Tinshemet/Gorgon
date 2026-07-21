"""check_disk tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class CheckDiskTool(Tool):
    names = ("check_disk",)
    def run(self, args, ctx):
        return context.manager.check_disk(args["name"])
