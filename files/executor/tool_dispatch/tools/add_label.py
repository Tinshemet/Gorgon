"""add_label tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class AddLabelTool(Tool):
    names = ("add_label",)
    def run(self, args, ctx):
        return context.manager.add_label(args["name"], args["label"])
