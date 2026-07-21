"""delete_vm tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert
from executor.tool_dispatch.tools.base import Tool
class DeleteVmTool(Tool):
    names = ("delete_vm",)
    def run(self, args, ctx):
        _clear_revert()
        return context.manager.delete_vm(args["name"], delete_disks=True)
