"""mark_as_template tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class MarkAsTemplateTool(Tool):
    names = ("mark_as_template",)
    def run(self, args, ctx):
        return context.manager.mark_as_template(args["name"])
