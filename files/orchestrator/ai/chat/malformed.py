"""malformed.py — is this "answer" actually a tool call the model failed to make?

A model that means to call a tool and gets the mechanics wrong emits the ATTEMPT as ordinary
text, and the chat prints it as an assistant message. The operator then reads

    Assistant: CallCheck("Which VMs are running?", options=["Adams", "Becky", "Charlie"])

which is not an answer, is not true, and is not something anyone should have to interpret.
Observed 2026-07-31 on a real probe, with invented machine names.

WHY THIS IS WORTH ITS OWN MODULE. It is a display decision that must be identical on both
prompt paths — the REPL and the HTTP chat — and those two have drifted before (#26). One
authority, imported twice, is the shape that has held everywhere else in this codebase.

DELIBERATELY CONSERVATIVE. A false positive hides a real answer from the operator, which is
worse than showing them one odd line: every rule here requires the text to look like a CALL
and not like prose, so a sentence that merely mentions a tool name passes through untouched.
"""
from __future__ import annotations

import json
import re
from typing import Optional

# `name(...)` with nothing else around it — the shape a model emits when it "calls" a tool by
# writing it out. Anchored at both ends so a sentence containing a call is not caught.
_CALLISH = re.compile(r"^[A-Za-z_][\w.]*\s*\(.*\)[.\s]*$", re.DOTALL)

# Keys that only appear in a tool-call envelope. Prose does not carry these.
_ENVELOPE = {"tool_call", "tool_calls", "function", "function_call", "parameters",
             "arguments", "tool", "name"}


def looks_like_tool_call(text: str) -> Optional[str]:
    """A short reason if this text is a failed tool call, else None.

    Returns the REASON rather than a bool so the caller can tell the operator which kind of
    malformation happened. "It printed JSON" and "it wrote a function call as prose" are
    different mistakes, and an operator deciding whether to rephrase or re-run wants to know
    which.
    """
    body = (text or "").strip()
    if not body:
        return None

    # A JSON OBJECT CARRYING AN ENVELOPE KEY. Checked before the call-shape rule because a
    # JSON blob is unambiguous and the shape rule is a heuristic.
    if body.startswith("{") or body.startswith("["):
        try:
            parsed = json.loads(body)
        except Exception:
            # Malformed JSON that was TRYING to be an envelope is still not an answer — but
            # only when it names one, or every truncated sentence starting with a brace
            # would be swallowed.
            return ("a partial tool call, printed as text"
                    if any(f'"{k}"' in body for k in _ENVELOPE) else None)
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            if isinstance(item, dict) and (_ENVELOPE & set(item)):
                return "a tool call in JSON, printed as text instead of being called"
        return None

    # A BARE CALL EXPRESSION. Must be the whole message, and must not read as a sentence —
    # a space before the parenthesis usually means prose ("we ran create_vm (twice)").
    if _CALLISH.match(body) and "\n" not in body.strip() and len(body) < 400:
        head = body.split("(", 1)[0].strip()
        if head and " " not in head:
            return f"a call to `{head}` written out as text instead of being made"
    return None


def explain(reason: str, text: str, verbose: bool = False) -> str:
    """What to show the operator instead of the raw attempt.

    SAYS WHAT HAPPENED AND WHAT TO DO, and shows the raw text only under `verbose`. The
    operator's problem is that the request did not happen; the envelope is a detail for
    whoever is debugging the model, and printing it as though it were an answer is what made
    this a defect rather than a curiosity.
    """
    out = (f"The model tried to act but did not call anything — it returned {reason}. "
           f"Nothing has run. Try rephrasing the request, or say it as a direct "
           f"instruction.")
    if verbose:
        out += f"\n  raw: {text.strip()[:300]}"
    return out
