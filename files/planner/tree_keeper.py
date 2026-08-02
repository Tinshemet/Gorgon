"""
tree_keeper.py — THE TREE BOOK KEEPER. Corrects AFTER, because the tree has already acted.

THE DEFECT IT EXISTS FOR IS ROOT POISONING: a wrong decomposition high in a plan makes
everything under it wrong while EVERY INDIVIDUAL NODE STAYS LOCALLY VALID. Each child is a
sensible sub-goal, each closure is well-formed, and the plan is still built on something
false. Nothing that checks a node can see it, because the fault is not in any node.

## WHY IT CANNOT USE THE PROGRAM REGIME'S FIX

The program regime grades the whole artifact BEFORE anything runs — it can, because a
program is inert until assembled (`ir/lower.py:review`). **The tree has already acted.** By
the time a node's consequences are visible the world has changed, so it cannot review-
before; it must correct-after.

    The program regime reviews BEFORE, because its artifact is inert.
    The tree regime corrects AFTER, because it has already acted and can SEE THE RESULT.

Same defect, opposite mechanism — which is what the correspondence rule predicts, and the
reason neither is a port of the other. The tree has one thing the program regime lacks
while authoring: LIVE STATE.

## WIRED 2026-08-01, AND THE PREMISE LEDGER TURNED OUT NOT TO BE NEEDED

The in-session (`engines/insession.py`) owns a real tree now, and it re-visits a decomposed
parent behind its own children. That re-visit re-PLANS the parent against the world as it is,
so a stale split announces itself as WORK STILL TO DO — no recorded predicate, no separate
evaluator pass, nothing to keep in step. The plan length already said it.

So the engine builds this module's ROWS directly and calls `drift`/`report`. `with_premise`
and `inspect` remain for a tree somebody else builds — one whose nodes are not re-planned —
and the design below is what they are for. **The correcting is done by re-planning; this
module's job is telling somebody it was needed**, which is the half that was always the
point: a run served against a moving set and one served against a set that held still both
succeed, and they are not the same thing.

## THE FIRST REAL PIECE OF WORK, and it is why this file starts here

The design note's own open question: *"What marks a node 'infected'? The premise a node was
decomposed under is not currently recorded anywhere, so there is nothing to re-check it
against."* So a node has to CARRY THE ASSUMPTION IT WAS BUILT ON. `premise` is a Medusa
predicate that was true when the node was split — re-evaluable later by the same evaluator
that answers an ENSURE, so nothing new has to be invented to check it.

**A NODE WITH NO PREMISE IS `unknown`, NEVER `sound`.** Three-valued, and it is the same
rule decision 6 draws for `alive`: unprobed is not healthy. A keeper that reported zero
infected nodes while most of them recorded nothing would be reporting an unasked question,
not a clean tree.

## IT READS AND REPORTS. IT DOES NOT ACT.

Inherited from the world book keeper and it settles the authority question: a poisoned node
is MARKED, never silently re-planned. Re-planning is a MAKE, and MAKEs belong to something
with consent behind them — a keeper that quietly re-planned would be a background process
doing high-impact work with nobody asking. There is no writer in this module.
"""
from typing import Any, Callable, Dict, List, Optional

SOUND = "sound"          # premise recorded and still holds
INFECTED = "infected"    # premise recorded and NO LONGER holds — this node and its subtree
UNKNOWN = "unknown"      # nothing recorded; nobody asked. NOT the same as sound.


def with_premise(node: dict, predicate: Optional[dict]) -> dict:
    """Record what a node was decomposed UNDER. Returns a copy; mutates nothing.

    The premise is a Medusa predicate rather than prose so it can be re-evaluated by
    `ir.evaluate` — the same seam an ENSURE uses. Prose would need a model to re-check, and
    a keeper whose verdict came from a model would be the second bad draw `reward_cost`
    refuses, on the one number this is supposed to make trustworthy.
    """
    out = dict(node)
    out["premise"] = predicate
    return out


def inspect(rows: List[dict], holds: Callable[[dict, dict], Any]) -> List[dict]:
    """Re-check every recorded premise against the world AS IT IS NOW.

    `holds(predicate, scope)` is the evaluator seam, injected exactly as `run()` injects it,
    so this module never touches a registry or a model directly.

    IT TAKES THE ROWS THE ENGINE ALREADY BUILDS, keyed by dotted path, and that is a change
    from the nested-node shape it was written with. Nothing ever called that shape: the
    engine builds path-keyed rows because its queue is breadth-first, and a keeper that
    demanded a tree object would have needed the engine to build a second structure for the
    auditor's benefit. Parents-first ordering, which the report depends on, falls out of
    sorting the paths — an infected parent explains every child under it, and a reader shown
    the children first chases symptoms.

    A ROW THE ENGINE ALREADY JUDGED IS LEFT ALONE. The witness re-visit is a stronger check
    than a premise — it RE-PLANS the goal against the world and asks whether work remains —
    so overwriting its verdict with this one would trade evidence for inference. This fills
    in the nodes that had no witness available, which is precisely where the engine's own
    method is silent.
    """
    out: List[dict] = []
    poisoned: Dict[str, str] = {}          # path prefix -> the goal whose premise broke
    for row in sorted(rows, key=lambda r: str(r.get("path") or "")):
        path = str(row.get("path") or "")
        by = next((g for pre, g in poisoned.items()
                   if path != pre and path.startswith(pre + ".")), None)
        premise = row.get("premise")
        if by is not None:
            state, why = INFECTED, f"built under {by!r}, whose premise no longer holds"
        elif row.get("state") in (SOUND, INFECTED):
            # ALREADY WITNESSED. See the docstring: evidence beats inference.
            state, why = row["state"], row.get("why") or ""
        elif premise is None:
            state, why = UNKNOWN, "no premise recorded — nobody asked"
        else:
            try:
                ok, detail = holds(premise, {})
            except Exception as exc:                 # a seam that cannot answer is UNKNOWN,
                ok, detail = None, f"{type(exc).__name__}: {exc}"   # never sound
            if ok is None:
                state, why = UNKNOWN, f"premise could not be evaluated ({detail})"
            elif ok:
                state, why = SOUND, "premise still holds"
            else:
                state, why = INFECTED, f"premise no longer holds ({detail})"

        # AN INFECTED NODE POISONS ITS SUBTREE, which is the whole shape of the defect: the
        # children are locally fine and wrong anyway. Marking them keeps the report honest
        # about scope without pretending each was independently checked.
        if state == INFECTED and by is None:
            poisoned[path] = row.get("goal")
        out.append({**row, "state": state, "why": why})
    return out


def drift(rows: List[dict]) -> Dict[str, Any]:
    """The report. Counts by state, and the ROOTS of infection — the nodes whose own
    premise broke, as distinct from those merely under one.

    `clear` is never claimed while anything is `unknown`: the strongest honest statement
    about a tree nothing could check is that nothing was PROVEN broken.
    """
    infected = [r for r in rows if r["state"] == INFECTED]
    unknown = [r for r in rows if r["state"] == UNKNOWN]
    origins = [r for r in infected if "built under" not in r["why"]]
    return {"nodes": len(rows), "infected": len(infected), "unknown": len(unknown),
            "origins": origins,
            "verdict": INFECTED if infected else (UNKNOWN if unknown else "clear")}


def report(rows: List[dict]) -> str:
    """Human-readable, and it states its own coverage — a keeper that printed only failures
    would look identical whether it checked everything or nothing."""
    d = drift(rows)
    lines = [f"tree book keeper · {d['nodes']} node(s) · {d['infected']} infected · "
             f"{d['unknown']} unknown · verdict {d['verdict']}"]
    for r in rows:
        mark = {SOUND: "ok      ", INFECTED: "INFECTED", UNKNOWN: "unknown "}[r["state"]]
        lines.append(f"   [{mark}] {r['path'] or 'root':6} {r['goal']}  <- {r['why']}")
    if not d["infected"]:
        lines.append("   NOTHING PROVEN INFECTED — not the same as sound. "
                     f"{d['unknown']} node(s) were never re-checked.")
    return "\n".join(lines)
