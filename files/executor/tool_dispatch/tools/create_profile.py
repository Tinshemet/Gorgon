"""create_profile tool — preflight-gated save of a custom hardware profile."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import (
    console, _set_revert, save_custom_profile,
    check_profile_compatibility as _check_compat,
)
from executor.tool_dispatch.tools.base import Tool
class CreateProfileTool(Tool):
    names = ("create_profile",)
    def run(self, args, ctx):
        verbose = ctx.verbose
        pname = args.pop("profile_name")
        notes = args.pop("notes", "")
        force = args.pop("force", False)
        if notes:
            args["_notes"] = notes
        if not force:
            preflight = ctx.preflight_check(
                "create_profile", {"profile_name": pname, **args}, manager, verbose
            )
            action = preflight.get("action", "ok")
            if action == "abort":
                return {
                    "success":    False,
                    "error":      preflight.get("reason", "Pre-flight check failed"),
                    "correction": preflight.get("correction"),
                }
            if action == "ask_user":
                if not verbose:
                    ctx.show_preflight_warning(preflight, console)
                return {
                    "success":    False,
                    "clarify":    True,
                    "question":   preflight.get("question"),
                    "options":    preflight.get("options", []),
                    "reason":     preflight.get("reason"),
                    "correction": preflight.get("correction"),
                    "issues":     preflight.get("issues", []),
                    "hint":       "To save anyway, call create_profile again with force=true",
                }
            if action == "auto_fix":
                fixed = preflight.get("fixed_args", {})
                args.update({k: v for k, v in fixed.items() if k not in ("profile_name", "force")})
                if not verbose:
                    console.print(f"  [yellow]⚠ Pre-flight auto-fixed: {preflight.get('reason')}[/yellow]")
                    for w in preflight.get("warnings", []):
                        console.print(f"  [dim]  ↳ {w}[/dim]")
        result = save_custom_profile(pname, args)
        if result["success"]:
            result["compatibility"] = _check_compat(result["profile_name"])
            _set_revert("delete_profile", {"profile_name": pname}, f"undo create_profile '{pname}'")
        return result
