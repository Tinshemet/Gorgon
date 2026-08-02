"""
answer.py — what the operator's typed reply to a confirmation MEANS.

WHY THIS EXISTS, MEASURED 2026-08-02. The HTTP chat asked *"create VM: test — Yes / Cancel"*,
the operator typed **cancel**, and the VM was created. Nothing in that path ever read the
reply: the client turned "there is a confirm pending" into `auto_confirm=True` and the server
executed the pending tool on that flag alone. Every answer was a yes — "cancel", "no", a
typo, an empty line.

THE TERMINAL PATH HAD IT RIGHT THE WHOLE TIME. `gates/safety.py` compares the answer against
`y/yes/1` and against the exact name, and refuses otherwise. So this was not a rule nobody
had written — it was a rule written on ONE of the two doors, which is the shape [[SSOT]]
exists to stop. The rule now lives here, in one place, and both doors ask it.

THE DEFAULT IS REFUSAL, and it is the same default the rest of the system already keeps:
`intent`, `consent` and `ask_destroy` all answer NO when there is nobody to ask. An answer
that does not clearly grant is not a grant. A confirmation whose unrecognised answers mean
"go ahead" is not a confirmation.

THE RULE IS PER CONFIRM TYPE, because the question is:

    confirm_yn        a yes/no question   → an affirmative word, or it is refused
    confirm_name      *type the name*     → that exact name, or it is refused
    confirm_critical  name, then name     → anything but a refusal; `chat_endpoint` then
                                            runs its two-step name check, which is the
                                            actual gate — this only lets "cancel" out of it
    preflight         a free-form choice  → anything but a refusal; the choice itself is not
                                            a yes/no and must not be read as one
    (absent)          an older session     → anything but a refusal

WHAT IT DELIBERATELY DOES NOT DO: turn an unrecognised answer into a re-ask. A retry loop is
a policy about a conversation and belongs to the caller that owns the transcript; this
answers one question about one string, and can be tested without either.
"""
import json
import os

_CFG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")))
_WORDS       = _CFG.get("confirm_answers", {})
_AFFIRMATIVE = {w.lower() for w in _WORDS.get("affirmative", [])}
_NEGATIVE    = {w.lower() for w in _WORDS.get("negative", [])}


def is_affirmative(said: str) -> bool:
    """True when *said* is a word that grants. An empty line never is."""
    return (said or "").strip().lower() in _AFFIRMATIVE


def is_negative(said: str) -> bool:
    """True when *said* explicitly refuses — cancel / no / abort / stop."""
    return (said or "").strip().lower() in _NEGATIVE


def reads_as_grant(confirm, said: str) -> bool:
    """Did the operator's reply GRANT the pending action?

    *confirm* is the ``{"type", "proposed"}`` block the asking side attached to the pending
    tool — the question that was actually put, carried forward so the answer is judged
    against it rather than against a guess. ``None`` for a session that predates it.

    Example::

        reads_as_grant({"type": "confirm_yn", "proposed": "test"}, "cancel")   # False
        reads_as_grant({"type": "confirm_name", "proposed": "test"}, "test")   # True
    """
    kind     = (confirm or {}).get("type") or ""
    proposed = (confirm or {}).get("proposed") or ""

    if kind == "confirm_yn":
        return is_affirmative(said)
    if kind == "confirm_name":
        # THE EXACT NAME, CASE AND ALL — the same comparison `safety.py`'s ask_name makes.
        # Typing the name IS the proof of intent, and a near miss is not proof.
        return (said or "").strip() == str(proposed).strip()
    # confirm_critical / preflight / an older session: the reply is not a yes/no, so the
    # only thing decided here is that a refusal is honoured. What grants is decided
    # downstream — the two-step name check for critical, the choice itself for preflight.
    return not is_negative(said)
