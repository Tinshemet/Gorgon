"""launch_vm tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _set_revert
from executor.tool_dispatch.tools.base import Tool
class LaunchVmTool(Tool):
    names = ("launch_vm",)
    def run(self, args, ctx):
        result = context.manager.launch_vm(
            args["name"],
            display=args.get("display"),
            dry_run=args.get("dry_run", False),
            vnc_bind_local=args.get("vnc_bind_local"),
        )
        if result.get("success"):
            _set_revert("stop_vm", {"name": args["name"], "force": True}, f"undo launch_vm '{args['name']}'")
        return result
