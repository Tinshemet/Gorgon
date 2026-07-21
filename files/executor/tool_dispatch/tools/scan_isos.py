"""scan_isos tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class ScanIsosTool(Tool):
    names = ("scan_isos",)
    def run(self, args, ctx):
        return context.manager.scan_isos()
