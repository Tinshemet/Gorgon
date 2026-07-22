"""
orchestrator/http/execute_endpoint.py — the /execute tool-dispatch handler.

Server-side preflight (authoritative — real VM/disk state) plus the executor_client
dispatch behind /execute, and the manager proxy the preflight checks run against.
Kept out of api_server.py so that module stays routing + auth.
"""
from typing import Any

from fastapi import HTTPException

from . import context


def manager_proxy() -> object:
    """Return a QemuManager wrapper in local mode, or a thin executor_client proxy in remote mode.

    Both branches filter list_vms() by ALLOWED_VMS. Without this, preflight's own VM-existence
    checks (launch_vm, resize_disk, etc. — anything calling manager.list_vms() directly) would see
    hidden VMs as real and skip its "not found" handling, a side channel that leaks a hidden VM's
    existence through preflight's response shape even though the tool call itself would still
    correctly deny it — before this fix, this was only guarded against in remote mode.
    """
    from orchestrator.executor_client import API_URL, execute_tool as _exec
    if not API_URL or API_URL == "local":
        from executor.tool_dispatch.tool_executor import manager as _real_manager
        class _LocalProxy:
            def list_vms(self, *a, **k) -> list:
                """Filter the real manager's list_vms() by ALLOWED_VMS."""
                vms = _real_manager.list_vms(*a, **k)
                names = context.filter_allowed([v["name"] for v in vms], context.ALLOWED_VMS)
                return [v for v in vms if v["name"] in names]
            def __getattr__(self, attr: str):
                return getattr(_real_manager, attr)
        return _LocalProxy()
    class _Proxy:
        def scan_isos(self) -> dict:
            """Proxy scan_isos to the executor via the HTTP /execute path."""
            return _exec("scan_isos", {})
        def list_vms(self) -> dict:
            """Proxy list_vms to the executor via the HTTP /execute path."""
            return _exec("list_vms", {})
    return _Proxy()


def handle_execute(req: Any) -> Any:
    """Dispatch a tool call via executor_client and return its result (or raise HTTP 4xx on access/preflight failure)."""
    from orchestrator.executor_client import execute_tool
    import orchestrator.preflight.validator as _pf
    manager = manager_proxy()

    # Tool/VM allowlist enforcement lives solely in executor_client.execute_tool() below (the
    # same point /chat already relies on with no pre-check of its own) — a prior duplicate
    # pre-check here returned a differently-shaped response (HTTP 403, {"ok": False, ...}) with
    # leakier wording than the deeper check, and disagreed with /chat's behavior for the same
    # violation. One enforcement point, one consistent response shape.

    # ── Server-side preflight (authoritative — uses real VM/disk state) ──────
    pf     = _pf._preflight_check(req.tool_name, req.args, manager, req.verbose)
    action = pf.get("action", "ok")
    args   = req.args

    if action == "abort":
        return {
            "ok": True,
            "result": {
                "success":    False,
                "preflight":  True,
                "error":      pf.get("reason", "Pre-flight check failed."),
                "correction": pf.get("correction", ""),
            },
        }

    if action == "auto_fix":
        args = pf.get("fixed_args", args)

    if action == "ask_user":
        fix_field = pf.get("fix_field")
        question  = pf.get("question", "Please confirm.")
        options   = pf.get("options", [])
        return {
            "ok": True,
            "result": {
                "success":             False,
                "preflight":           True,
                "clarify":             True,
                "question":            question,
                "options":             options,
                "needs_clarification": fix_field,
                "missing": (
                    [{"field": fix_field, "question": question, "options": options}]
                    if fix_field else []
                ),
                "error":  pf.get("reason", "Pre-flight requires clarification."),
                "hint":   pf.get("correction", ""),
            },
        }

    # ── Remote display override ───────────────────────────────────────────────
    if req.tool_name == "launch_vm":
        args = dict(args)
        if args.get("display", "sdl") in context.LOCAL_ONLY_DISPLAYS or "display" not in args:
            args["display"] = "vnc"
        args["vnc_bind_local"] = True

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        result = execute_tool(req.tool_name, args, req.verbose, log=req.log)
        if action == "auto_fix" and isinstance(result, dict):
            result["_preflight_auto_fixed"] = pf.get("correction", "Pre-flight corrected args.")
        # Filter list_vms results to only show allowed VMs
        if req.tool_name == "list_vms" and context.ALLOWED_VMS and isinstance(result, list):
            result = [v for v in result if v.get("name") in context.ALLOWED_VMS]
        elif req.tool_name == "list_vms" and context.ALLOWED_VMS and isinstance(result, dict) and "vms" in result:
            result["vms"] = [v for v in result["vms"] if v.get("name") in context.ALLOWED_VMS]
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
