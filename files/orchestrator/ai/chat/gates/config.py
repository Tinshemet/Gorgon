"""
config.py — config-derived constants shared by the interactive gates.

Loaded from ``chat/config.json`` (the parent package's config file), so the
gates read one authored source rather than each re-loading it.
"""

import json
import os

from ...agent.contract import FLEET_CONFIRM_ACTIONS

_CFG            = json.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")))
_OS_KEYWORDS    = set(_CFG["os_keywords_gate"])
_RENDERS_OUTPUT = set(_CFG.get("rendered_tools", []))
# The fleet actions needing a y/n, derived from the contract (single source — the
# fleet test asserts the CLI and HTTP paths agree, which deriving guarantees).
_FLEET_CONFIRM_ACTIONS = set(FLEET_CONFIRM_ACTIONS)
_RECENT_CONTEXT_WINDOW = _CFG["chat"].get("recent_context_window", 6)  # msgs kept for multi-turn context
