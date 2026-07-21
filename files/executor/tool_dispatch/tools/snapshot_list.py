"""snapshot_list tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_snapshots
from executor.tool_dispatch.tools.base import Tool
class SnapshotListTool(Tool):
    names = ("snapshot_list",)
    def run(self, args, ctx):
        result = context.manager.snapshot_list(args["name"])
        if not ctx.verbose:
            render_snapshots(result)
        return result
