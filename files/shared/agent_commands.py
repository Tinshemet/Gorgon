"""
agent_commands.py — per-agent declarative command macros.

An agent bundle may declare its OWN commands in ``commands.json`` — a map of
``verb → {tool, args, help}``. Each is a DECLARATIVE macro (a named tool call), not
executable code: bundles are shareable data, so running Python from one would be
code injection. When that agent is active, the direct-CLI dispatcher tries these
macros for a verb the global registry doesn't own, so "add an agent = get its
commands" without touching the global command set.

    { "recon": {"tool": "fleet", "args": {"label": "redteam", "action": "status"},
                "help": "status of the redteam fleet"} }
"""

import json

from shared.bundle import Bundle


def load_agent_commands(agent: str) -> dict:
    """The active agent's declarative command macros ({} if none / unreadable).
    Only well-formed ``{verb: {tool, args?, help?}}`` entries are returned."""
    try:
        with open(Bundle(agent).commands_path) as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for verb, spec in data.items():
        if isinstance(spec, dict) and isinstance(spec.get("tool"), str):
            out[verb] = {
                "tool": spec["tool"],
                "args": dict(spec.get("args") or {}),
                "help": str(spec.get("help") or ""),
            }
    return out
