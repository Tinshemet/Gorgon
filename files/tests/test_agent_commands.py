#!/usr/bin/env python3
"""
test_agent_commands.py — per-agent declarative command macros: a bundle's
commands.json maps a verb → {tool, args}, dispatched when that agent is active.
Macros are DATA (a named tool call), never executable code.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shared.bundle as _bundle
from shared import agent_commands as _ac

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1; print(f"  PASS {label}")
    else:
        _FAIL += 1; print(f"  FAIL {label}")


def main():
    _bundle.AGENTS_ROOT = tempfile.mkdtemp()

    print("load_agent_commands: well-formed only")
    b = _bundle.Bundle("zubin"); b.ensure()
    with open(b.commands_path, "w") as f:
        json.dump({
            "recon": {"tool": "fleet", "args": {"label": "redteam", "action": "status"}, "help": "fleet status"},
            "bad":   {"no_tool": True},                 # dropped: no tool
            "worse": "not-a-dict",                      # dropped: not a dict
        }, f)
    m = _ac.load_agent_commands("zubin")
    check("well-formed macro kept", m.get("recon", {}).get("tool") == "fleet")
    check("args normalized to a dict", m["recon"]["args"] == {"label": "redteam", "action": "status"})
    check("malformed entries dropped", "bad" not in m and "worse" not in m)
    check("missing bundle → {}", _ac.load_agent_commands("nobody") == {})

    print("\ndispatcher runs the macro for an unregistered verb (active agent)")
    from orchestrator.ai.chat.commands import _run_agent_macro
    from orchestrator.ai.chat.commands import context as ctx
    import orchestrator.ai.agent.contract as _contract
    calls = []
    ctx.execute_tool = lambda tool, args, v=False: calls.append((tool, dict(args))) or {"success": True}
    ctx.console.print = lambda *a, **k: None
    _contract.active_agent_key = lambda: "zubin"
    handled = _run_agent_macro("recon", False)
    check("macro handled", handled is True)
    check("macro dispatched the mapped tool call", calls == [("fleet", {"label": "redteam", "action": "status"})])
    check("unknown verb → not handled", _run_agent_macro("nosuch", False) is False)

    print("\nforge scaffolds an (empty) commands.json")
    from orchestrator.ai.agent import forge
    d = tempfile.mkdtemp()
    path, issues = forge.finalize_forge(
        {"persona": {"name": "shani"}, "tools": {"list": ["create_vm"], "mode": "whitelist"}},
        "redrum", write_dir=d)
    check("commands.json scaffolded beside the contract",
          os.path.isfile(os.path.join(os.path.dirname(path), "commands.json")))

    print(f"\n{'='*48}\n  {_PASS}/{_PASS + _FAIL} passed\n{'='*48}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
