"""list_networks tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class ListNetworksTool(Tool):
    names = ("list_networks",)
    def run(self, args, ctx):
        return context.manager.list_networks()
