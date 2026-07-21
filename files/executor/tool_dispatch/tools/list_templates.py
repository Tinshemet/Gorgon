"""list_templates tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import render_templates
from executor.tool_dispatch.tools.base import Tool
class ListTemplatesTool(Tool):
    names = ("list_templates",)
    def run(self, args, ctx):
        templates = context.manager.list_templates()
        if not ctx.verbose:
            render_templates(templates)
        return templates
