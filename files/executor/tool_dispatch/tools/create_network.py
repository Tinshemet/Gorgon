"""create_network tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _set_revert
from executor.tool_dispatch.tools.base import Tool
class CreateNetworkTool(Tool):
    names = ("create_network",)
    def run(self, args, ctx):
        result = context.manager.create_network(args["net_name"])
        if result.get("success"):
            _set_revert("delete_network", {"net_name": args["net_name"]}, f"undo create_network '{args['net_name']}'")
        return result
