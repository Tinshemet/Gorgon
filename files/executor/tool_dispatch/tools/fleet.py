"""fleet tool — broadcast an action across a labelled fleet."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_fleet
from executor.tool_dispatch.tools.base import Tool
class FleetTool(Tool):
    names = ("fleet",)
    def run(self, args, ctx):
        result = context.manager.fleet(
            args["label"], args["action"],
            command=args.get("command"),
            args=args.get("args"),
            timeout=args.get("timeout"),
        )
        if not ctx.verbose:
            render_fleet(result)
        return result
