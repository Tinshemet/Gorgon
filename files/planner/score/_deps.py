"""
_deps.py — the injected contract / registry / findings helpers.

Optional so the engine still imports in orchestrator-only checkouts / pure-unit
tests without the executor package. Kept as ONE all-or-nothing block (as the
original single try/except) so a sparse checkout degrades uniformly — steering
skipped, contract/findings defaults None/no-op — rather than half-wired.

RESOLVED LAZILY, ON FIRST CALL, NOT AT IMPORT. The planner is the LANGUAGE and
sits UNDER the engines that use it; an import-time edge up into `orchestrator`
is what made that a cycle. Deferring the same imports into a function body
removes the edge at import time and changes nothing in a full checkout, because
by the time any of this is CALLED everything is importable.

TWO SHAPES, AND THE DIFFERENCE MATTERS. A helper that is a callable in BOTH arms
(no-op default) is exposed as a plain wrapper function and called as before. A
helper whose degraded value is `None` or an empty collection is exposed as an
ACCESSOR THAT MUST BE CALLED — because a lazy wrapper is a function and a
function is always truthy, so `engine.gate or _default_gate` would have turned
"no gate" into "a gate that raises at call time" in the one path nobody looks at.
The accessors are also spelled differently from the old module-level names on
purpose: a call site missed in this conversion is a NameError, not a silent
change of the legal filter and the consent gate.
"""

from typing import Any, Dict, Optional

_BUNDLE: Optional[Dict[str, Any]] = None


def _bundle() -> Dict[str, Any]:
    """Resolve the optional dependency bundle once. All-or-nothing, as before."""
    global _BUNDLE
    if _BUNDLE is None:
        try:
            from executor.command_catalog import POST_CREATE_ATTACH
            from orchestrator.ai.chat.context_assistant import _NARROW_CORE_TOOLS
            from orchestrator.ai.agent.contract import (gate_action, success_criterion,
                                                        is_forbidden, consent_verb, tool_risk)
            from planner.findings import (yield_fact, extract_value,
                                                          finding_probe_spec)
            _BUNDLE = {
                "post_create_attach": POST_CREATE_ATTACH,
                "narrow_core_tools":  _NARROW_CORE_TOOLS,
                "gate":               gate_action,
                "criterion":          success_criterion,
                "legal":              is_forbidden,
                "consent_verb":       consent_verb,
                "tool_risk":          tool_risk,
                "yield_fact":         yield_fact,
                "extract_value":      extract_value,
                "finding_probe_spec": finding_probe_spec,
            }
        except ImportError:
            _BUNDLE = {
                "post_create_attach": {},
                "narrow_core_tools":  frozenset(),
                "gate":               None,
                "criterion":          None,
                "legal":              None,
                "consent_verb":       lambda t: t,
                "tool_risk":          lambda t: None,
                "yield_fact":         lambda *a, **k: None,
                "extract_value":      lambda r, s: r,
                "finding_probe_spec": lambda *a, **k: None,
            }
    return _BUNDLE


# --- accessors: the degraded value is None / empty, so these MUST be called ---

def _post_create_attach() -> Dict[str, Dict[str, str]]:
    return _bundle()["post_create_attach"]


def _narrow_core_tools():
    return _bundle()["narrow_core_tools"]


def _gate_default():
    """The active contract's gate_action, or None when unavailable."""
    return _bundle()["gate"]


def _criterion_default():
    """The active contract's success_criterion, or None when unavailable."""
    return _bundle()["criterion"]


def _legal_default():
    """The active contract's is_forbidden, or None when unavailable."""
    return _bundle()["legal"]


# --- wrappers: a callable in both arms, so calling through one is transparent ---

def _consent_verb(tool):
    return _bundle()["consent_verb"](tool)


def _tool_risk(tool):
    return _bundle()["tool_risk"](tool)


def _yield_fact(*a, **k):
    return _bundle()["yield_fact"](*a, **k)


def _extract_value(result, spec):
    return _bundle()["extract_value"](result, spec)


def _finding_probe_spec(*a, **k):
    return _bundle()["finding_probe_spec"](*a, **k)
