"""show_config tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class ShowConfigTool(Tool):
    names = ("show_config",)
    def run(self, args, ctx):
        return context.manager.show_config(args["name"])
