"""open_display tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class OpenDisplayTool(Tool):
    names = ("open_display",)
    def run(self, args, ctx):
        return context.manager.open_display(args["name"])
