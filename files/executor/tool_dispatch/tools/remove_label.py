"""remove_label tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class RemoveLabelTool(Tool):
    names = ("remove_label",)
    def run(self, args, ctx):
        return context.manager.remove_label(args["name"], args["label"])
