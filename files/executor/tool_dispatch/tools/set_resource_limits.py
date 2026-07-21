"""set_resource_limits tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class SetResourceLimitsTool(Tool):
    names = ("set_resource_limits",)
    def run(self, args, ctx):
        return context.manager.set_resource_limits(
            args["name"],
            cpu_percent=args.get("cpu_percent"),
            memory_mb=args.get("memory_mb"),
        )
