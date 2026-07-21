"""snapshot_delete tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert
from executor.tool_dispatch.tools.base import Tool
class SnapshotDeleteTool(Tool):
    names = ("snapshot_delete",)
    def run(self, args, ctx):
        _clear_revert()
        return context.manager.snapshot_delete(args["name"], args["snap_name"])
