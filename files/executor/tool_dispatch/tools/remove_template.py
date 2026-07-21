"""remove_template tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class RemoveTemplateTool(Tool):
    names = ("remove_template",)
    def run(self, args, ctx):
        return context.manager.remove_template(args["name"])
