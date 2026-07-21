"""delete_profile tool."""
from executor.tool_dispatch.context import delete_custom_profile, _clear_revert
from executor.tool_dispatch.tools.base import Tool
class DeleteProfileTool(Tool):
    names = ("delete_profile",)
    def run(self, args, ctx):
        _clear_revert()
        return delete_custom_profile(args["profile_name"])
