"""add_vm_to_network tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class AddVmToNetworkTool(Tool):
    names = ("add_vm_to_network",)
    def run(self, args, ctx):
        return context.manager.add_vm_to_network(args["net_name"], args["vm_name"])
