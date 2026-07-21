"""rollback tool — restore a checkpoint tag on its member VMs (discovered by tag)."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert, _CKPT_TAG_PREFIX
from executor.tool_dispatch.tools.base import Tool
class RollbackTool(Tool):
    names = ("rollback",)
    def run(self, args, ctx):
        label = args["label"]
        snap  = f"{_CKPT_TAG_PREFIX}{label}"
        if args.get("name"):
            targets = [args["name"]]
        else:                                  # discover members by the checkpoint tag
            targets = []
            for v in context.manager.list_vms():
                sl = context.manager.snapshot_list(v.get("name"))
                if sl.get("success") and any(s.get("tag") == snap for s in sl.get("snapshots", [])):
                    targets.append(v["name"])
        if not targets:
            return {"success": False, "error": f"No checkpoint '{label}' found."}
        done, errors = [], []
        for vm in targets:
            (done if context.manager.snapshot_restore(vm, snap).get("success") else errors).append(vm)
        _clear_revert()
        return {
            "success": bool(done), "rolled_back_to": label, "vms": done, "errors": errors,
            "message": (f"Rolled back {len(done)} VM(s) to '{label}'"
                        + (f"; {len(errors)} failed ({', '.join(errors)})" if errors else "") + "."),
        }
