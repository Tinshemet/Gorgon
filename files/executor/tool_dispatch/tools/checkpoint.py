"""checkpoint tool — a named savepoint over a VM or the whole fleet."""
from executor.tool_dispatch import context
from executor.tool_dispatch.context import _clear_revert, _CKPT_TAG_PREFIX
from executor.tool_dispatch.tools.base import Tool
class CheckpointTool(Tool):
    names = ("checkpoint",)
    def run(self, args, ctx):
        label   = args["label"]
        snap    = f"{_CKPT_TAG_PREFIX}{label}"
        targets = [args["name"]] if args.get("name") else [
            v["name"] for v in context.manager.list_vms() if v.get("name")]
        done, errors = [], []
        for vm in targets:
            (done if context.manager.snapshot_create(vm, snap).get("success") else errors).append(vm)
        _clear_revert()
        return {
            "success": bool(done) or not targets,
            "checkpoint": label, "snapshot": snap, "vms": done, "errors": errors,
            "message": (f"Checkpoint '{label}' saved on {len(done)} VM(s)"
                        + (f"; {len(errors)} failed ({', '.join(errors)})" if errors else "") + "."),
        }
