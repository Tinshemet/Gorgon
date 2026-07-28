"""
sanitize.py — drop what provably does nothing, and SAY SO.

An authored program can carry residue: statements the run cannot reach anything through.
This removes them before the program is judged, and returns an account of every removal.

WHY THIS IS NOT PAPERING OVER A DEFECT. That was the objection when it was proposed, and
it is the right objection — hiding a reasoning error behind a cleaner would be the worst
possible trade. It waited for a measurement, and the measurement says the residue is not
reasoning. Rung 11 emits `IF IS($answer.alive) = true { }` in every phrasing, and that
cond is byte-identical to the ONE `if` among the few-shot examples: same variable
`answer`, same field `alive`, same `= true` polarity, none of which appear in the goal.
The goal's work belongs to the opposite case, so it will not fit in the copy, and a second
`if` is appended to hold it. The empty branch is the template with nothing that fits in
it. Flipping the example's polarity removes it outright; removing the example leaves the
model unable to emit a parseable `if` at all. That is one-example generalisation, and a
compiler drops its residue without comment.

THREE RULES, each earned:

  NEVER SILENT      every removal is returned, and the caller reports it. A pass that
                    quietly improved its input would make the artifact rate unmeasurable,
                    which is how a thing gets worse with nobody seeing.
  NEVER EMPTIES     dropping the last statement of a block would trade a dead statement
                    for a validation error about a block the author did fill in. A program
                    dead all the way down stays as written and is rejected on its terms.
  NEVER REWRITES    `IF X {} ELSE {Y}` is left exactly as written, so the validator's
                    objection still fires. Turning it into `IF NOT(X) THEN {Y}` would
                    change what the program SAYS, and a program should say what it means
                    rather than be edited into meaning it. This is the line between a
                    compiler pass and a correction, and it is the whole boundary of the
                    module.

Kinds live in the manifest (`config.SANITIZE`), never as literals here, and a kind is
EARNED BY MEASUREMENT. See _sanitize_doc for the two candidates already refused under that
rule — the schema gate scored 0/12 by inventing factors instead, and this file exists
downstream of that lesson.
"""
from typing import Any, Dict, List, Optional, Tuple

from . import config

# Blocks a statement can carry, spelled the way validate.py spells them in an objection.
# One program addressed two ways, in messages a reader sees side by side, is a small
# cruelty that costs nothing to avoid.
_BLOCKS = {"do": "foreach body", "then": "then", "else": "else", "ifails": "ifails"}


def _dead(st: Any) -> Optional[str]:
    """The artifact kind `st` is, or None.

    Only `if`. A `call` with no effect is not knowable from the text, a `foreach` over an
    empty set is a fact about the world rather than the program, and `new`/`fetch` bind
    names later statements may read. An `if` with no acting branch is the one statement
    whose inertness is decidable from the text alone — which is exactly the bar a kind has
    to clear to be removable at all.
    """
    if not isinstance(st, dict) or st.get("op") != "if":
        return None
    if st.get("then") or st.get("else"):
        return None
    return "dead_if"


def kinds() -> Dict[str, Dict[str, str]]:
    """The manifest's artifact table."""
    return config.SANITIZE.get("kinds") or {}


def severity(kind: str) -> str:
    return (kinds().get(kind) or {}).get("severity", "unclassified")


def sanitize(program: Any) -> Tuple[Any, List[Dict[str, str]]]:
    """(cleaned, removed) — the program with dead statements dropped, and an account.

    `program` is not mutated: every block that changes is rebuilt, so a caller holding the
    author's original still has it. That matters because the raw draft is evidence — the
    artifact rate is measured off it — and a pass that edited it in place would destroy
    the thing it exists to count.
    """
    removed: List[Dict[str, str]] = []

    def walk(stmts: Any, path: str) -> Any:
        if not isinstance(stmts, list):
            return stmts
        kept: List[Any] = []
        dropped: List[Tuple[str, str]] = []
        for i, st in enumerate(stmts):
            where = f"{path}statement {i + 1}"
            kind = _dead(st)
            if kind:
                dropped.append((where, kind))
                continue
            if isinstance(st, dict):
                st = dict(st)
                for block, spoken in _BLOCKS.items():
                    if isinstance(st.get(block), list):
                        st[block] = walk(st[block], f"{where} ({spoken}) → ")
            kept.append(st)
        if not kept and dropped:
            return stmts                       # NEVER EMPTIES — see the module docstring
        for where, kind in dropped:
            removed.append({"kind": kind, "where": where, "severity": severity(kind),
                            "why": (kinds().get(kind) or {}).get("why", "")})
        return kept

    if not isinstance(program, dict) or not isinstance(program.get("body"), list):
        return program, []
    out = dict(program)
    out["body"] = walk(program["body"], "")
    return out, removed


def account(removed: List[Dict[str, str]]) -> str:
    """One line per removal, for whoever has to report it."""
    return "; ".join(f"{r['where']}: {r['kind']} [{r['severity']}] — {r['why']}"
                     for r in removed)
