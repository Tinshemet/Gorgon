"""check_profile_compatibility tool."""
from executor.tool_dispatch.context import check_profile_compatibility as _check_compat, render_compat
from executor.tool_dispatch.tools.base import Tool
class CheckProfileCompatibilityTool(Tool):
    names = ("check_profile_compatibility",)
    def run(self, args, ctx):
        result = _check_compat(args["profile_name"])
        if not ctx.verbose:
            render_compat(result)
        return result
