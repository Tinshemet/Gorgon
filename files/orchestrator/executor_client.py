"""
executor_client.py — Executor Client

Single import point for tool execution used by server/ai/cli.py.
Supports two modes controlled by connection_config.json (or API_URL env var):

  url = "local"          — direct in-process call (default, single-machine setup)
  url = "http://host:8001" — HTTP call to a remote executor.server instance

Remote mode enables running the AI orchestrator and the QEMU engine on
separate machines. The executor server (executor/server.py) must be running
on the target host.
"""

import json
import os
import time

import requests as _requests

with open(os.path.join(os.path.dirname(__file__), "connection_config.json")) as _f:
    _CFG = json.load(_f)
_SHARED_CFG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "executor", "api", "config.json"
)
with open(_SHARED_CFG_PATH) as _sf:
    _SHARED_CFG = json.load(_sf)
API_URL           = os.environ.get("API_URL",   _CFG.get("url",   "local"))
_TOKEN            = os.environ.get("API_TOKEN", _CFG.get("token", ""))
_TIMEOUT          = int(os.environ.get("API_TIMEOUT", _CFG.get("timeout", 120)))
_CA_CERT          = os.environ.get("API_CA_CERT", _CFG.get("ca_cert") or None)
_VERIFY           = (
    False if os.environ.get("API_VERIFY_SSL", "1") == "0"
    else (_CA_CERT or _CFG.get("verify_ssl", True))
)
_ALLOWED_VMS:         list = _CFG.get("client_allowed_vms",      [])
_ALLOWED_PROFILES:    list = _CFG.get("client_allowed_profiles", [])
_ALLOWED_TOOLS:       set  = set(_CFG.get("allowed_remote_tools", []))
_LOCAL_ONLY_DISPLAYS: set  = set(_SHARED_CFG.get("local_only_displays", ["sdl", "gtk"]))

_VM_TOOLS = {"launch_vm", "stop_vm", "delete_vm", "clone_vm", "resize_disk",
             "vm_status", "create_snapshot", "restore_snapshot", "delete_snapshot",
             "list_snapshots", "show_qemu_cmd", "setup_done", "generate_guest_setup"}

from orchestrator.event_log import log_event as _log_event  # noqa: E402


def __getattr__(name: str):
    # Lazily resolved so mock.patch("shared.executioner.tool_executor.execute_tool")
    # and module deletion/reimport by tests always return the current binding.
    if name == "_execute_tool":
        import shared.executioner.tool_executor as _te
        return _te.execute_tool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")




def execute_tool(tool_name: str, args: dict, verbose: bool = False) -> dict:
    """Wrapper around shared execute_tool that overrides local-only displays
    and enforces client tool/VM/profile access control.

    Args:
        tool_name: Name of the tool to call (e.g. ``"launch_vm"``).
        args:      Tool arguments dict.
        verbose:   Pass through to the underlying executor.

    Returns:
        Tool result dict, always containing ``"success": bool``.

    Example::

        execute_tool("list_vms", {})
        # → {"success": True, "vms": [...]}
        execute_tool("launch_vm", {"name": "myvm"})
        # → display overridden to "vnc"; {"success": True, ...}
    """
    # Enforce tool allowlist (covers both /execute and /chat paths)
    if _ALLOWED_TOOLS and tool_name not in _ALLOWED_TOOLS:
        return {"success": False, "error": f"Tool '{tool_name}' is not available."}

    if tool_name == "launch_vm":
        args = dict(args)
        if args.get("display", "sdl") in _LOCAL_ONLY_DISPLAYS or "display" not in args:
            args["display"] = "vnc"
        args["vnc_bind_local"] = False

    # Enforce VM allowlist — report as "not found" to avoid leaking existence
    if tool_name in _VM_TOOLS and _ALLOWED_VMS:
        vm_name = args.get("name", "")
        if vm_name not in _ALLOWED_VMS:
            return {"success": False, "error": f"VM '{vm_name}' not found."}

    # Enforce profile allowlist
    if tool_name in ("create_vm", "apply_profile", "check_profile_compatibility") and _ALLOWED_PROFILES:
        profile = args.get("profile", "") or args.get("profile_name", "")
        if profile and profile not in _ALLOWED_PROFILES:
            return {"success": False, "error": f"Profile '{profile}' is not available."}

    # Filter list_vms to only show allowed VMs
    _t0 = time.monotonic()
    if API_URL and API_URL != "local":
        try:
            resp = _requests.post(
                f"{API_URL}/execute",
                json={"tool_name": tool_name, "args": args, "verbose": verbose},
                headers={"Authorization": f"Bearer {_TOKEN}"},
                timeout=_TIMEOUT,
                verify=_VERIFY,
            )
            resp.raise_for_status()
            result = resp.json()
        except _requests.RequestException as exc:
            result = {"success": False, "error": f"Executor unreachable: {exc}"}
    else:
        import shared.executioner.tool_executor as _te
        result = _te.execute_tool(tool_name, args, verbose)
    _log_event(tool_name, args, result, (time.monotonic() - _t0) * 1000)

    if tool_name == "list_vms" and _ALLOWED_VMS:
        if isinstance(result, list):
            result = [v for v in result if v.get("name") in _ALLOWED_VMS]
        elif isinstance(result, dict) and "vms" in result:
            result["vms"] = [v for v in result["vms"] if v.get("name") in _ALLOWED_VMS]
    return result
