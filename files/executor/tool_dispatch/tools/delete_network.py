"""delete_network tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert
from executor.tool_dispatch.tools.base import Tool
class DeleteNetworkTool(Tool):
    names = ("delete_network",)
    def run(self, args, ctx):
        _clear_revert()
        return context.manager.delete_network(args["net_name"])
