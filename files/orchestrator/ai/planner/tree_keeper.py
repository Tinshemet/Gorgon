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


def inspect(root: dict, holds: Callable[[dict, dict], Any]) -> List[dict]:
    """Re-check every recorded premise against the world AS IT IS NOW.

    `holds(predicate, scope)` is the evaluator seam, injected exactly as `run()` injects it,
    so this module never touches a registry or a model directly.

    Returns one row per node, PARENTS FIRST — because that is the order the report has to be
    read in. An infected parent explains every child under it, and a reader shown the
    children first would chase symptoms.
    """
    rows: List[dict] = []

    def walk(n: dict, path: str, poisoned_by: Optional[str]):
        premise = n.get("premise")
        if poisoned_by is not None:
            state, why = INFECTED, f"built under {poisoned_by!r}, whose premise no longer holds"
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

        rows.append({"goal": n.get("goal"), "path": path, "state": state, "why": why,
                     "op": n.get("op")})
        # AN INFECTED NODE POISONS ITS SUBTREE, which is the whole shape of the defect: the
        # children are locally fine and wrong anyway. Marking them keeps the report honest
        # about scope without pretending each was independently checked.
        deeper = poisoned_by or (n.get("goal") if state == INFECTED else None)
        for i, k in enumerate(n.get("children") or []):
            walk(k, f"{path}.{i}" if path else str(i), deeper)

    walk(root, "", None)
    return rows


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
