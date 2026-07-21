"""snapshot_create tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _set_revert, _TOOL_DEFS
from executor.tool_dispatch.tools.base import Tool
class SnapshotCreateTool(Tool):
    names = ("snapshot_create",)
    def run(self, args, ctx):
        _snap = args.get("snap_name", _TOOL_DEFS["snap_name"])
        result = context.manager.snapshot_create(args["name"], _snap)
        if result.get("success"):
            _set_revert(
                "snapshot_delete",
                {"name": args["name"], "snap_name": _snap},
                f"undo snapshot_create '{_snap}' on '{args['name']}'",
            )
        return result
