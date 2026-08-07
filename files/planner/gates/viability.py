"""viability.py — GATE 4. Taken TOGETHER, does this work as intended?

    inspect(readings, verdicts=None) -> Report(unstable, compounded, routes)

## IT IS NOT A FOURTH CHECK IN A ROW

Gates 1, 2 and 3 each judge the reading. This one judges **what the other three did to it**.
Each of them RESOLVES something locally — gate 1 restores a mangled value, gate 2 supplies a
missing probe, gate 3 asks — and every one of those is reasonable alone. Three reasonable local
repairs can compound into something the operator never asked for, and that composition is
invisible to every gate that only sees its own question.

**AND IT NEEDS NO WORLD ORACLE**, which is what makes it buildable at all. It judges the
READINGS and the REQUEST, both of which the orchestrator already holds. `DONE_BUT_FALSE` stays
the engine's problem, downstream of the handover.

## ⇒ THE MEASUREMENT THAT DECIDED WHAT IS IN HERE

**READING INSTABILITY IS REAL AND IT IS STRONG.** Three draws per cell across the corpus:

    cells whose draws AGREE   54/71 pass  (76%)
    cells whose draws DIFFER   4/12 pass  (33%)

A request the system cannot settle on ONE reading of fails **more than twice as often**. That
is ambiguity-by-disagreement, it needs neither the world nor a checker, and it is the operator's
*"gate 4 flags paraphrasing, technically"* — paraphrase sensitivity and draw instability are
the same property measured two ways.

## ⇒ AND THE NEGATIVE RESULT, WHICH MATTERS MORE THAN THE POSITIVE

**THE DESTRUCTIVE-EMERGENCE CHECK CANNOT BE MADE STRUCTURALLY, AND IT IS NOT HERE.**

The case that started all of this: `count(vm) = 10` against a lab holding twelve is covered by
DELETING TWO, and gates 1-3 all pass it correctly. The obvious gate-4 rule — *the plan destroys
and no claim asked to remove* — was written and counted: **6 false alarms on PASSING readings
against 2 real catches.**

The reason is fatal to the idea. Rung 14 — *"make sure there are exactly two machines left"* —
is `count(vm) = 2`, removes machines, and is CORRECT: the claim is a TOTAL. "create 10 vms" is
`count(vm) = 10`, removes machines, and is WRONG: the request stated a DELTA. **The two are
structurally identical.** They differ only in what the operator meant, and no amount of reading
the artifact recovers that.

⇒ SO IT IS NOT DECIDABLE HERE, AND THE RIGHT ANSWER IS THE ONE ALREADY SHIPPED: a person
decides. `Orchestrator._grant` refuses an unauthorised destruction and re-asks a live consent
surface with the machines NAMED. A gate cannot replace that, and a gate that TRIED would have
accused six correct readings to catch two wrong ones.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

BAD_READ = "bad-read"
BAD_PROMPT = "bad-prompt"


class Report:
    """What gate 4 found, and where it sends it."""

    def __init__(self, unstable=None, compounded=None):
        # THE SAME REQUEST READ MORE THAN ONE WAY.
        self.unstable: List[Dict[str, Any]] = list(unstable or ())
        # THE EARLIER GATES BETWEEN THEM CHANGED THE READING MORE THAN ANY ONE OF THEM MEANT.
        self.compounded: List[Dict[str, Any]] = list(compounded or ())

    @property
    def legal(self) -> bool:
        return not (self.unstable or self.compounded)

    def findings(self) -> List[str]:
        out = []
        for u in self.unstable:
            out.append(f"this request reads {u['distinct']} different ways, and nothing in it "
                       f"decides which")
        for c in self.compounded:
            out.append(f"{c['gates']} each changed this reading; together they moved it "
                       f"further than any one of them meant to")
        return out

    def routes(self) -> List[Dict[str, str]]:
        """WHERE EACH FINDING GOES — gate 4 ROUTES rather than judges, and it can, because it
        knows which gate made which resolution.

            BAD READ    the seam misread a sentence that is itself clear -> back to the gate
            BAD PROMPT  the sentence genuinely admits several readings   -> back to the operator

        ⇒ INSTABILITY IS A BAD PROMPT, NOT A BAD READ, AND THAT IS THE HONEST ATTRIBUTION.
        If the same request drawn twice yields two readings, the deciding information is not in
        the sentence — another draw is another coin, not another look. Sending it back to a
        gate would spend a call to re-roll; sending it to the operator asks the one party who
        knows.
        """
        out = [{"to": BAD_PROMPT, "why": f} for f in
               (self.findings()[:len(self.unstable)] if self.unstable else [])]
        out += [{"to": BAD_READ, "why": c.get("gates", "")} for c in self.compounded]
        return out

    def questions(self) -> List[str]:
        """Gate 4's clarification is about the WHOLE — which reading was meant."""
        return [f"this can be read {u['distinct']} ways and they do different things. "
                f"Which did you mean?" for u in self.unstable]

    def __repr__(self) -> str:
        return (f"<Viability {'legal' if self.legal else 'ILLEGAL'} "
                f"unstable={len(self.unstable)} compounded={len(self.compounded)}>")


def _shape(goals) -> str:
    """A reading's identity, for comparing two draws of one request.

    THE GOALS THEMSELVES, CANONICALISED — not a summary. Two readings that differ anywhere
    differ here, which is the conservative direction: this is a check for DISAGREEMENT, and a
    comparison that smoothed differences away would report agreement it had manufactured.
    """
    return json.dumps(goals or [], sort_keys=True, default=str)


def inspect(readings: List[List[dict]], verdicts: Optional[Dict[str, Any]] = None) -> Report:
    """Gate 4 over one request's READINGS — plural, which is the whole point.

    `readings` is every draw taken of the same request. ONE reading cannot be unstable, so a
    single-element list is legal by construction and costs nothing; the check only has content
    when somebody paid for a second draw.

    `verdicts` is what gates 1-3 said, keyed by name. Gate 4 is the only one that sees them,
    because it is the only one asking what they did BETWEEN them.
    """
    report = Report()

    # ── 1 · DOES THE REQUEST READ MORE THAN ONE WAY? ─────────────────────────────────────
    shapes = {_shape(r) for r in (readings or []) if r}
    if len(shapes) > 1:
        report.unstable.append({"distinct": len(shapes), "of": len(readings)})

    # ── 2 · DID THE EARLIER GATES, BETWEEN THEM, MOVE THE READING? ───────────────────────
    #
    # EACH RESOLUTION IS REASONABLE ALONE. Gate 1 restores a value the model mangled; gate 2
    # supplies an observation the reading needed. Either on its own is a repair. BOTH, on one
    # reading, mean the artifact now differs from what the model produced in two independent
    # ways — and nobody has looked at the sum.
    #
    # ⇒ IT COUNTS RESOLUTIONS, NOT COMPLAINTS. A gate that merely OBJECTED changed nothing, so
    #   it cannot have contributed to a drift; only a gate that ACTED is implicated.
    acted = []
    for name, verdict in (verdicts or {}).items():
        if verdict is None:
            continue
        repairs = getattr(verdict, "repairs", None)
        supplied = getattr(verdict, "supply", None)
        try:
            if callable(repairs) and repairs():
                acted.append(name)
            elif callable(supplied) and supplied():
                acted.append(name)
        except Exception:
            continue
    if len(acted) > 1:
        report.compounded.append({"gates": " and ".join(sorted(acted)), "count": len(acted)})
    return report
