"""stop_vm tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _set_revert, _clear_revert
from executor.tool_dispatch.tools.base import Tool
class StopVmTool(Tool):
    names = ("stop_vm",)
    def run(self, args, ctx):
        if args["name"] == "all":
            _clear_revert()
            return context.manager.stop_all()
        result = context.manager.stop_vm(args["name"], force=args.get("force", False))
        if result.get("success"):
            _set_revert("launch_vm", {"name": args["name"]}, f"undo stop_vm '{args['name']}'")
        return result
