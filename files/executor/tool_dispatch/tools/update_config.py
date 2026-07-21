"""update_config tool — captures old values so the change can be reverted."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _set_revert
from executor.tool_dispatch.tools.base import Tool
class UpdateConfigTool(Tool):
    names = ("update_config",)
    def run(self, args, ctx):
        _old_cfg = context.manager.show_config(args["name"])
        _updates = args.get("updates", {})
        result = context.manager.update_config(args["name"], _updates)
        if result.get("success") and _old_cfg.get("success"):
            _old_vals = {k: _old_cfg["config"].get(k) for k in _updates}
            _set_revert(
                "update_config",
                {"name": args["name"], "updates": _old_vals},
                f"undo update_config '{args['name']}' fields {list(_updates.keys())}",
            )
        return result
