"""list_profiles tool."""
from executor.tool_dispatch.context import list_profiles as _list_profiles, render_profiles
from executor.tool_dispatch.tools.base import Tool
class ListProfilesTool(Tool):
    names = ("list_profiles",)
    def run(self, args, ctx):
        profiles = _list_profiles()
        if not ctx.verbose:
            render_profiles(profiles)
        return profiles
