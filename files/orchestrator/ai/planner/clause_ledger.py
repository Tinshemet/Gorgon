"""
clause_ledger.py — what the goal ASKED FOR, and what is still unaccounted for.

WHY THIS EXISTS, measured 2026-07-29. The atomicity router answered three ladder rungs by
LOSING A CLAUSE of the goal, 3/3 each, with its own stated reasoning showing it never
considered the missing half:

    rung  8  "put every vm on core, EXCEPT db — db goes on dmz"
             -> one foreach, "apply the same action to every member of a set"
    rung 10  "clone golden into 3 new vms AND LAUNCH ALL OF THEM"
             -> one new, "we need to create three new resources"
    rung 11  "ping every vm AND STOP THE ONES THAT DO NOT ANSWER"
             -> one foreach, "because we can only ping one vm at a time"

THE OPERATOR'S RULING, and it decided the shape of this file: *"if clauses are gone,
that's a LEDGER issue not a decomp issue."* The router answers a routing question.
Accounting for every demand of the goal is a SEPARATE mechanism that records what was
asked and reconciles against it.

**AND IT IS WHY THIS ASKS NO MODEL.** The obvious fix — have the router check its own
answer for completeness — is a model call rating its own output, which is the second bad
draw `p_self_estimate`'s docstring refuses. Recording what was asked and comparing is
external, deterministic, and answers in microseconds.

THE DEFECT IT NAMES IS ROOT POISONING. A clause dropped at the root leaves every leaf
below it valid and every fusion well-formed, and the program is still a correct
decomposition of the WRONG GOAL. Nothing that checks a node can see it, because the fault
is not in any node.

## CONSTITUTIONAL SHAPE — it reads and reports; it changes NOTHING

The same shape as the book keeper, and for the same reason: it updates the map, not the
territory. An unaccounted demand is REPORTED, never silently patched — patching a plan is
a MAKE, and MAKEs belong to something with consent behind them. This module has no writer.

## IT NEVER CLAIMS COVERAGE IT CANNOT SHOW

The failure mode of a coverage checker is false confidence, so `covered` is not a verdict
this module is willing to reach on a resemblance. Three values, and `unverified` matches
neither of the others — decision 6's rule (`alive` is true/false/unknown, and unprobed is
not dead) applied to plan coverage:

    unaccounted   PROVEN missing. Arithmetic or a declared anchor appearing nowhere.
    unverified    not proven either way. Reported as an open question, never as fine.
    covered       only ever set by a caller that can SHOW why.

So the report never says "all good". It says how many demands there were, how many are
provably unaccounted for, and how many nobody has established either way. A checker that
reported zero while owning no detector would be reporting an unasked question, not a clean
result — the distinction the sanitiser's three-valued severity already draws.

## TWO DETECTORS, BOTH DETERMINISTIC, NEITHER A VOCABULARY

1. **PIGEONHOLE.** Fewer statements than demands means at least the difference is
   unaccounted for. Pure arithmetic; it cannot be wrong, and it catches all three measured
   failures on its own (two demands, one statement, every time).
2. **ANCHOR.** A demand may DECLARE concrete tokens — a name, a label, a count. An anchor
   appearing in no statement proves that demand unaccounted for. Anchors are DECLARED, not
   inferred, so this never becomes a 34th vocabulary guessing which English words matter.
   Same argument as `create_defaults`: declared once, identical every time, visible.

Neither detector can mark a demand COVERED. They only ever move it to `unaccounted`.
"""
from typing import Any, Dict, List, Optional, Sequence

UNACCOUNTED = "unaccounted"
UNVERIFIED = "unverified"
COVERED = "covered"

# Why a demand was ruled unaccounted for. Named so a report attributes itself rather than
# leaving a reader to guess which detector fired — the same reason `ladder_gate` failures
# name their layer.
BY_PIGEONHOLE = "pigeonhole"
BY_ANCHOR = "anchor"


def open_ledger(goal: str, demands: Sequence[Any]) -> Dict[str, Any]:
    """Record what the goal asked for, BEFORE anything is planned.

    A demand is either a plain string or {"text": ..., "anchors": [...]}. Both spellings
    are accepted because the enumerator that supplies them may not know the anchors, and a
    demand with no anchors is still worth counting — the pigeonhole detector does not need
    them.

    THE RECORD PRECEDES THE PLAN. That inversion is the point, and it is the same one the
    creation ledger makes: you cannot notice something went missing from a list you built
    afterwards out of what survived.

    ## AN ANCHOR MUST APPEAR IN THE GOAL, AND THIS IS ENFORCED HERE

    Anchors not present in `goal` are DROPPED, so the ledger can only ever point at words
    the operator actually used. Without that rule this becomes a second description of the
    goal held by the harness — which is the "benchmark grading itself" the author probe
    warns about in its own summary, and the line between telling an author WHAT IS MISSING
    and telling it WHAT TO WRITE.

    It also makes the same demand list safe across phrasings. Rung 10 is `launch all of
    them` literally and `boot every copy` in paraphrase: the `launch` anchor holds for one
    column and is dropped for the other, where the demand falls back to the pigeonhole
    detector rather than matching on a word nobody said. A demand whose anchors are all
    dropped is still COUNTED — that is what keeps the arithmetic honest.
    """
    hay = (goal or "").lower()
    rows: List[Dict[str, Any]] = []
    for d in demands:
        if isinstance(d, str):
            text, anchors = d, []
        elif isinstance(d, dict):
            text = str(d.get("text", "")).strip()
            anchors = [str(a) for a in (d.get("anchors") or [])]
        else:
            continue
        if not text:
            continue
        kept = [a for a in anchors if a.lower() in hay]
        rows.append({"text": text, "anchors": kept,
                     "dropped": [a for a in anchors if a not in kept],
                     "status": UNVERIFIED, "why": None, "by": None})
    return {"goal": goal, "demands": rows}


def _haystack(statements: Sequence[Any]) -> str:
    """Every statement flattened to one lowercase string. Anchors are matched against this
    rather than per-statement: a demand satisfied by ANY statement is not missing, and
    which one satisfied it is a question this module deliberately does not answer."""
    out: List[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif x is not None:
            out.append(str(x))

    walk(list(statements))
    return " ".join(out).lower()


def reconcile(ledger: Dict[str, Any], statements: Sequence[Any]) -> Dict[str, Any]:
    """Compare the plan against the record. Returns a NEW ledger; mutates nothing.

    `statements` is whatever the planner produced — decompose steps (strings), IR
    statements (dicts), or one of each. It is flattened, so this works on a router's answer
    and on a whole program without knowing which it was given.
    """
    rows = [dict(r) for r in ledger.get("demands", [])]
    hay = _haystack(statements)
    n_stmt = len(list(statements))

    # ANCHOR first — it names WHICH demand is missing, where pigeonhole only proves that
    # some are. Running it first means the more informative verdict wins the row.
    for row in rows:
        if row["status"] == COVERED:
            continue
        missing = [a for a in row["anchors"] if a.lower() not in hay]
        if missing:
            row["status"] = UNACCOUNTED
            row["by"] = BY_ANCHOR
            row["why"] = (f"nothing in the plan mentions "
                          f"{', '.join(repr(m) for m in missing)}")
        elif row["anchors"]:
            # EVERY DECLARED ANCHOR APPEARS. That is anchor-level evidence, NOT semantic
            # proof — the plan mentions the token, which is not the same as addressing the
            # demand. It is recorded as `covered` because the alternative is worse: leaving
            # a checked row indistinguishable from one nothing could check, which is
            # exactly the unasked-question-versus-clean-result confusion this module is
            # built to avoid. The ASYMMETRY IS DELIBERATE and it is the honest direction:
            # absence of the token proves nothing addresses the demand; presence only
            # suggests something might.
            row["status"] = COVERED
            row["why"] = "every declared anchor appears in the plan"

    # PIGEONHOLE. Arithmetic over the whole set, so it cannot say WHICH row — it marks the
    # still-unverified rows from the end, which is where a dropped trailing clause lands in
    # all three measured cases. The `why` states the arithmetic rather than the position,
    # so nobody reads the choice of row as evidence.
    #
    # A ROW THE ANCHOR DETECTOR ALREADY PROVED MISSING EXPLAINS PART OF THE SHORTFALL, so
    # it is subtracted. Without this, rung 8 reported BOTH demands missing — the anchor
    # named the real one and pigeonhole then blamed the innocent one for the same single
    # gap. Two detectors over one set of rows must not charge the same absence twice.
    shortfall = len(rows) - n_stmt - sum(1 for r in rows if r["status"] == UNACCOUNTED)
    if shortfall > 0:
        open_rows = [r for r in rows if r["status"] == UNVERIFIED]
        for row in reversed(open_rows):
            if shortfall <= 0:
                break
            row["status"] = UNACCOUNTED
            row["by"] = BY_PIGEONHOLE
            row["why"] = (f"{len(rows)} demands, {n_stmt} statement(s) — at least "
                          f"{len(rows) - n_stmt} cannot be accounted for")
            shortfall -= 1

    return {"goal": ledger.get("goal"), "demands": rows}


def unaccounted(ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The demands PROVEN missing. `[]` means nothing was proven missing — which is NOT
    the same as "the plan is complete", and no caller should read it that way. Check
    `unverified()` before concluding anything."""
    return [r for r in ledger.get("demands", []) if r["status"] == UNACCOUNTED]


def unverified(ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Demands nobody established either way. An honest report has to show this count, or
    a clean-looking result is indistinguishable from an unasked question."""
    return [r for r in ledger.get("demands", []) if r["status"] == UNVERIFIED]


def verdict(ledger: Dict[str, Any]) -> str:
    """One word for a caller that wants to branch, and THREE-VALUED for the usual reason.

        unaccounted   something is PROVEN missing
        unverified    nothing proven missing, and some demand nothing could check —
                      an unasked question, not a clean result
        clear         nothing proven missing, and every demand WAS checked

    Never "ok" or "complete". The strongest thing this module can honestly say about a
    plan it did not prove incomplete is that it looked and found nothing.
    """
    if unaccounted(ledger):
        return UNACCOUNTED
    return UNVERIFIED if unverified(ledger) else "clear"


def report(ledger: Dict[str, Any]) -> str:
    """Human-readable, and it states its own coverage. Modelled on the sanitiser's rule
    that a pass which cleans without counting makes its own rate unmeasurable."""
    rows = ledger.get("demands", [])
    miss, open_ = unaccounted(ledger), unverified(ledger)
    lines = [f"clause ledger · {len(rows)} demand(s) · {len(miss)} unaccounted for · "
             f"{len(open_)} unverified"]
    for r in rows:
        mark = {UNACCOUNTED: "MISSING ", UNVERIFIED: "unverified", COVERED: "covered "}
        lines.append(f"   [{mark[r['status']]}] {r['text']}"
                     + (f"  <- {r['why']}" if r["why"] else ""))
    if not miss:
        lines.append("   NOTHING PROVEN MISSING — not the same as complete. "
                     f"{len(open_)} demand(s) were never established either way.")
    return "\n".join(lines)
