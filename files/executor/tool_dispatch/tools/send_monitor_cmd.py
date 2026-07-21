"""send_monitor_cmd tool."""
from executor.tool_dispatch import context
from executor.tool_dispatch.tools.base import Tool
class SendMonitorCmdTool(Tool):
    names = ("send_monitor_cmd",)
    def run(self, args, ctx):
        return context.manager.send_monitor_cmd(args["name"], args.get("cmd", "info status"))
