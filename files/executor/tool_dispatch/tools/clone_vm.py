"""clone_vm tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _set_revert
from executor.tool_dispatch.tools.base import Tool
class CloneVmTool(Tool):
    names = ("clone_vm",)
    def run(self, args, ctx):
        result = context.manager.clone_vm(args["source_name"], args["new_name"])
        if result.get("success"):
            _set_revert("delete_vm", {"name": args["new_name"]}, f"undo clone_vm '{args['new_name']}'")
        return result
