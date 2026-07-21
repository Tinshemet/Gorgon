"""open_shell tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class OpenShellTool(Tool):
    names = ("open_shell",)
    def run(self, args, ctx):
        return context.manager.open_shell(args["name"])
