"""snapshot_restore tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert
from executor.tool_dispatch.tools.base import Tool
class SnapshotRestoreTool(Tool):
    names = ("snapshot_restore",)
    def run(self, args, ctx):
        _clear_revert()
        return context.manager.snapshot_restore(args["name"], args["snap_name"])
