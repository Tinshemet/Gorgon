"""fingerprint_vm tool."""
from executor.tool_dispatch.context import tf_report
from executor.tool_dispatch.tools.base import Tool
class FingerprintVmTool(Tool):
    names = ("fingerprint_vm",)
    def run(self, args, ctx):
        return tf_report(args["name"], summary=bool(args.get("summary", False)))
