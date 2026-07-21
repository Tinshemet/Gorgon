"""list_labels tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class ListLabelsTool(Tool):
    names = ("list_labels",)
    def run(self, args, ctx):
        return context.manager.list_labels()
