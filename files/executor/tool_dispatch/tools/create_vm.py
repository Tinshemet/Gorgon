"""create_vm tool — delegates to the create_vm build logic."""
from executor.tool_dispatch.create_vm import execute_create_vm
from executor.tool_dispatch.tools.base import Tool
class CreateVmTool(Tool):
    names = ("create_vm",)
    def run(self, args, ctx):
        return execute_create_vm(args, ctx.verbose, ctx.raw_os_type,
                                 ctx.placeholder_vm_names, ctx.resolve_iso)
