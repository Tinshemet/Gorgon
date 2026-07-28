"""Fetch, ensure, or achieve? The one thing the author cannot know.

The operator's framing, and the neat part is that the three intents ARE the three words —
there is no separate vocabulary sitting above the language, describing it:

  FETCH     "how many are there? list them." Retrieval. It reads and reports VALUES, and
            answers with data.
  ENSURE    "verify this. ground me." A truth check. It reads and reports a VERDICT, and
            answers true or false. Nothing changes.
  ACHIEVE   "do this, and make sure it is done." A command, and the only autonomous one.
            The harness may create, attach, launch, delete — and must say what done
            means.

They nest. A verification may need to fetch; a command may need to do both. So authority
is a ladder — fetch ⊆ ensure ⊆ achieve — and a program is refused when it reaches above
the rung it was given.

That is why `ENSURE` and `ACHIEVE` could not be told apart by a better prompt. *"Make
sure exactly three carry the prod label"* is a verification if the operator wants to KNOW
and a command if the operator wants it TRUE, and nothing in the sentence, the world, or the
model decides which. The fact lives in a person's head and was never written down. A
model asked to infer it will infer confidently, and a wrong inference does not merely
pick the wrong keyword — it either acts on a lab that was only meant to be inspected, or
inspects a lab that was meant to be changed. Those are not symmetrical mistakes.

So intent is SUPPLIED, the same way consent is, and it is ENFORCED rather than suggested:
a program that reaches above the rung it was given is refused, because the operator did
not authorise that much. Three ways to supply it, cheapest first:

  1. A PREFIX — `fetch: how many carry prod` / `achieve: 3 vms carry prod`. Unambiguous,
     free, and the right form for a saved mission or a script.
  2. WORDS THE OPERATOR ALREADY USED. "how many" and "list" are a person asking for data;
     "verify" and "confirm" for a verdict; "spin up" and "bring" for a change. These live
     in the MANIFEST, not here, and are deliberately few — a marker set, not a vocabulary
     trying to parse English. A sentence using none of them is not guessed at. A sentence
     using SEVERAL is not a conflict: it takes the highest rung, because that is the
     authority the program needs and the lower words describe parts of it.
  3. ONE QUESTION, before anything runs.

With nobody to ask, the answer is FETCH — the bottom rung. Reading a lab you meant to
change wastes a run; changing a lab you meant to read cannot be undone.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config

FETCH, ENSURE, ACHIEVE = "fetch", "ensure", "achieve"

_PREFIXES = {"achieve:": ACHIEVE, "command:": ACHIEVE, "do:": ACHIEVE,
             "ensure:": ENSURE, "verify:": ENSURE, "check:": ENSURE,
             "fetch:": FETCH, "list:": FETCH, "count:": FETCH}

# The ladder. Each intent permits its own ops and everything below it; `if` rides along
# everywhere because a branch is only as consequential as the block it runs, and that
# block's own statements are checked when the walk reaches them.
_PERMITS = {
    FETCH:   {"fetch", "if"},
    ENSURE:  {"fetch", "ensure", "if"},
    ACHIEVE: None,                # the whole language
}

# Height on the ladder, for picking the authority a sentence actually needs.
_RUNG = {FETCH: 0, ENSURE: 1, ACHIEVE: 2}


def _markers() -> Dict[str, list]:
    """The operator's own words, from the manifest, so they stay data."""
    return (getattr(config, "INTENT", None) or {}).get("markers") or {}


def declared(goal: str) -> Optional[str]:
    """What the operator already said, or None if they did not say.

    None rather than a nearest match. A marker set that reaches is a vocabulary, and
    vocabularies are the thing this language exists to delete.
    """
    if not isinstance(goal, str) or not goal.strip():
        return None
    text = goal.strip().lower()

    for prefix, meaning in _PREFIXES.items():
        if text.startswith(prefix):
            return meaning

    hits = {meaning for meaning, words in _markers().items()
            for w in words if text.startswith(w + " ") or f" {w} " in f" {text} "}
    if not hits:
        return None
    # SEVERAL MARKERS IS NOT AMBIGUITY. "check golden exists, then spin up two" wants a
    # verification AND a command, and the ladder already says a command may contain both.
    # So the answer is the HIGHEST rung named — the authority the program needs — and the
    # lower words describe parts of it rather than competing with it. This is the three
    # working together rather than three choices to pick between.
    return max(hits, key=_RUNG.__getitem__)


def strip_prefix(goal: str) -> str:
    """The goal without its prefix — what the author should actually read."""
    if not isinstance(goal, str):
        return goal
    for prefix in _PREFIXES:
        if goal.strip().lower().startswith(prefix):
            return goal.strip()[len(prefix):].strip()
    return goal


def question(goal: str) -> Optional[str]:
    """The one question, or None when the operator has already answered it."""
    if declared(goal) is not None:
        return None
    return (f'"{goal}" — what do you want back?\n'
            f"  fetch    the numbers or the names. I read and report, nothing changes.\n"
            f"  ensure   a yes or no. I check whether it is so, nothing changes.\n"
            f"  achieve  it done. I do whatever is missing to make it true.")


def resolve(goal: str, asked: Any = None) -> str:
    """The operator's intent: declared, answered, or defaulted to FETCH — the bottom
    rung, which can do no harm."""
    said = declared(goal)
    if said is not None:
        return said
    if asked in _PERMITS:
        return asked
    if callable(asked):
        answer = asked(question(goal))
        if answer in _PERMITS:
            return answer
    return FETCH


def permits(intent: str) -> bool:
    """May a program written under this intent CHANGE anything?"""
    return _PERMITS.get(intent, _PERMITS[FETCH]) is None


def violations(program: Any, intent: str) -> List[str]:
    """Statements this intent is not authorised to contain.

    Enforced, not advised. The operator asked to be told something; a program that
    quietly creates a machine on the way to telling them has exceeded what it was given,
    and no postcondition makes that acceptable. Empty for an ACHIEVE, which sits at the
    top of the ladder and may use the whole language.

    `None` means NO INTENT WAS SUPPLIED, and nothing is refused. That is one word meaning
    one thing: `resolve()` is the only place absence becomes FETCH, because the safe
    default belongs where the operator is asked, not scattered through every consumer.
    This used to fall back to FETCH's set, which made the offer and the enforcement
    disagree on an unsupplied intent — the schema master offered the whole language while
    this function would have refused five sevenths of it. `run()` never hit it because it
    guards on `is not None`, so the disagreement was latent rather than live; it was found
    by asking the two sides the same question.
    """
    if intent is None:
        return []
    allowed = _PERMITS.get(intent, _PERMITS[FETCH])
    if allowed is None:
        return []
    from .consent import _walk
    from .validate import coerce_body
    out = []
    for i, st in enumerate(_walk(coerce_body(program) or [])):
        op = st.get("op")
        if op and op not in allowed:
            out.append(f"statement {i + 1}: `{op}` reaches above a {intent} — "
                       + (f"you asked to be TOLD something, and this changes the lab. "
                          f"Say `achieve:` if you meant to act."
                          if op not in ("fetch", "ensure") else
                          f"a {intent} answers with data, not a verdict. Say `ensure:` "
                          f"if you wanted it checked."))
    return out


def instruction(intent: str) -> str:
    """What to tell the author, once a human has settled it.

    Phrased as the operator's decision rather than as guidance, because it is one — the
    author is being handed a fact it had no way to derive, not steered toward a reading.
    """
    if intent == ACHIEVE:
        # "DO THE WORK" WAS THE OLD READING OF ACHIEVE, and it survived the 62160da
        # decision that replaced it. Once ACHIEVE is a MAKE — "make sure you exist" rather
        # than "certify what I just did" — what the operator wants is the state, not the
        # activity, and those differ precisely when the goal already holds. Rung 13 is that
        # case and the line argued for the wrong side of it: shown five machines already
        # labelled and networked, and told to "do the work", the author built five more.
        # A command is still a command; what it commands is an END, and the harness closes
        # whatever gap remains, so a gap of nothing is closed by doing nothing.
        return ("THIS IS A COMMAND. The operator wants this TRUE — an END STATE, not an "
                "activity. ACHIEVE is a MAKE: say what must be so and the harness closes "
                "whatever gap is left. So act on the DIFFERENCE between the lab you were "
                "shown and what was asked for: a goal that already holds needs no work "
                "doing twice. Open with ENSURE if something must already be true.")
    if intent == ENSURE:
        return ("THIS IS A VERIFICATION, NOT A COMMAND. The operator wants a yes or no. "
                "Use ENSURE, and FETCH if you need to read something first. Do NOT "
                "create, launch, label, attach or delete anything.")
    return ("THIS IS A RETRIEVAL. The operator wants the numbers or the names, nothing "
            "more. Use FETCH only. Do not check, and do not change anything.")
