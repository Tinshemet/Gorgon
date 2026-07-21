"""list_vms tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_vm_list
from executor.tool_dispatch.tools.base import Tool
class ListVmsTool(Tool):
    names = ("list_vms",)
    def run(self, args, ctx):
        vms = context.manager.list_vms(label=args.get("label"))
        if not ctx.verbose:
            render_vm_list(vms)
        return vms
