"""remove_vm_from_network tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class RemoveVmFromNetworkTool(Tool):
    names = ("remove_vm_from_network",)
    def run(self, args, ctx):
        return context.manager.remove_vm_from_network(args["net_name"], args["vm_name"])
