"""clarify tool — pass a clarification question straight back to the caller."""
from executor.tool_dispatch.tools.base import Tool
class ClarifyTool(Tool):
    names = ("clarify",)
    def run(self, args, ctx):
        return {"clarify": True, "question": args.get("question", ""), "options": args.get("options", [])}
