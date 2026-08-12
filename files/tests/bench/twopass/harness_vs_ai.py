"""WHAT THE HARNESS SPEWS vs WHAT THE PURE AI SPEWS — the same sentence, both ways.

    PYTHONPATH=. python3 -m tests.bench.twopass.harness_vs_ai --runs 2

    ⚠ NEEDS THE MODEL. V4: never beside a suite.

# ⇒⇒ WHY THE SENTENCES ARE IN LAB VOCABULARY AND THE VACUUM PROBE'S ARE NOT

`vacuum_probe` asks about caches, racks and proxies — deliberately, so no corpus phrase leaks
into a prompt. But the HARNESS only knows the lab's kinds, so it cannot read a sentence about a
rack at all, and "the harness missed it" would mean nothing.

⇒ **SO THIS FILE ASKS THE SAME PHENOMENA IN THE LAB'S OWN NOUNS.** Same distinction, same
  control pairs, but every sentence is one the pipeline can actually process — which is the
  only way "the AI saw it and we did not" is a fair sentence to write.

# ⇒ WHAT EACH SIDE IS ASKED

    THE AI      one closed question about the sentence, no lab, no schema, no symbol table.
                Just: does it see the distinction?
    THE HARNESS the full chain — pass 1, settle, gates, pass 2, linguistics, gate 3 — and what
                comes out the other end: the verdict, and whether any finding NAMES the
                phenomenon.

⇒ **AND THE COMPARISON IS NOT A SCORE, IT IS A DIAGNOSIS.** Four outcomes, and each says
  something different about where the work belongs:

    AI yes · harness yes    covered
    AI yes · harness NO     ⇐ OURS. The model has it and the pipeline throws it away.
    AI no  · harness yes    the computed check is carrying the model — keep computing it.
    AI no  · harness no     nobody has it. It has to be built from the request's markers.
"""
import argparse
from typing import Dict, List, NamedTuple


class Pair(NamedTuple):
    tag: str
    phenomenon: str
    request: str                 # in the LAB's vocabulary, so the harness can read it
    question: str                # what the AI is asked, in a vacuum
    options: List[str]
    want: str                    # the correct answer to that question
    harness_rule: str            # the finding that WOULD name it, if we have one
    note: str


PAIRS: List[Pair] = [
    # MOOD — the operator's own phenomenon
    Pair("mood-a", "mood", "make sure exactly two vms are running",
         "Does this sentence name the action to carry out, or does it name only the end state "
         "and leave the action open?",
         ["it names the action to carry out", "it names only the end state"],
         "it names only the end state", "mood-achieve",
         "the harness computes this from a marker list; the AI is asked outright"),
    Pair("mood-b", "mood", "launch two vms",
         "Does this sentence name the action to carry out, or does it name only the end state "
         "and leave the action open?",
         ["it names the action to carry out", "it names only the end state"],
         "it names the action to carry out", "",
         "CONTROL — the harness must stay silent here"),

    # DISTRIBUTIVE vs COLLECTIVE — NOT BUILT in the harness
    Pair("dist-a", "distributive", "put the vms on a network",
         "Does this mean one network holding all of them, or a separate network for each?",
         ["one network for all of them", "a separate network for each"],
         "one network for all of them", "",
         "NOT BUILT — the harness has no distributive check at all"),
    Pair("dist-b", "distributive", "put each vm on its own network",
         "Does this mean one network holding all of them, or a separate network for each?",
         ["one network for all of them", "a separate network for each"],
         "a separate network for each", "",
         "NOT BUILT — and this is the one that changes the PROGRAM, not just a flag"),

    # RECIPROCITY — NOT BUILT
    Pair("recip-a", "reciprocity", "make sure the vms can reach each other",
         "Does this describe something true of each vm on its own, or something that must hold "
         "between PAIRS of vms?",
         ["true of each vm on its own", "between pairs of vms"], "between pairs of vms", "",
         "NOT BUILT — the lab has no pairwise operation, so this is unserviceable"),
    Pair("recip-b", "reciprocity", "make sure the vms are running",
         "Does this describe something true of each vm on its own, or something that must hold "
         "between PAIRS of vms?",
         ["true of each vm on its own", "between pairs of vms"], "true of each vm on its own",
         "", "CONTROL"),

    # LIGHT VERB / effected — partly built
    Pair("light-a", "light-verb", "take a snapshot of every running vm",
         "In this sentence, is 'snapshot' the name of a thing that already exists, or the name "
         "of the action being requested?",
         ["a thing that already exists", "the action being requested"],
         "the action being requested", "light-verb-object",
         "rung 12 — the harness declares the snapshot as an OBJECT and pass 2 targets it"),
    Pair("light-b", "light-verb", "delete the snapshot called nightly",
         "In this sentence, is 'snapshot' the name of a thing that already exists, or the name "
         "of the action being requested?",
         ["a thing that already exists", "the action being requested"],
         "a thing that already exists", "", "CONTROL — a contentful verb"),

    # DEFINITENESS / uniqueness — NOT BUILT (gate 2 checks existence only)
    Pair("def-a", "definiteness", "stop the vm",
         "Does this sentence take for granted that there is only ONE vm?",
         ["yes, only one", "no, there could be several"], "yes, only one", "",
         "NOT BUILT — gate 2 checks EXISTENCE for a named thing and never UNIQUENESS"),
    Pair("def-b", "definiteness", "stop a vm",
         "Does this sentence take for granted that there is only ONE vm?",
         ["yes, only one", "no, there could be several"], "no, there could be several", "",
         "CONTROL"),

    # NEGATION SCOPE — NOT BUILT
    Pair("neg-a", "negation-scope", "do not stop every vm",
         "Does this forbid stopping any vm at all, or only forbid stopping all of them?",
         ["forbids stopping any", "only forbids stopping all of them"],
         "only forbids stopping all of them", "",
         "NOT BUILT — and this is the reading that silently INVERTS a program"),

    # RELATIVE MEASURE — NOT BUILT
    Pair("degree-a", "relative-measure", "give the vm two more cores",
         "Is 'two' the number it should end up with, or the number to add to what it has?",
         ["the number it ends up with", "the number to add"], "the number to add", "",
         "NOT BUILT — the manifest has only ABSOLUTE setters"),

    # VAGUE QUANTIFIER — NOT BUILT
    Pair("vague-a", "vague-quantifier", "stop most of the vms",
         "Does 'most' name an exact number?", ["yes", "no"], "no", "",
         "NOT BUILT — no count exists to compute"),

    # COUNT BOUND — built, as `count-ignored`
    Pair("count-a", "count-bound", "make sure exactly three vms carry the fleet label",
         "Does this sentence state a number that the end result must match exactly?",
         ["yes", "no"], "yes", "count-ignored", "BUILT — the harness reports this one"),
]


def ask_ai(pair: Pair, reversed_order: bool, model=None):
    from engines.channel import constrained
    options = list(reversed(pair.options)) if reversed_order else list(pair.options)
    schema = {"type": "object", "additionalProperties": False, "required": ["answer"],
              "properties": {"answer": {"type": "string", "enum": options}}}
    payload = (f"the sentence: {pair.request}\n\nthe question: {pair.question}\n\n"
               f"the options: " + " | ".join(options))
    try:
        got = constrained("Read the sentence and answer the question by choosing exactly one "
                          "of the options offered. Choose only from the options.",
                          payload, schema, model=model, temp=0.0, timeout=180) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<failed: {type(exc).__name__}>"


def run_harness(pair: Pair, board, world, model=None):
    """The whole chain, and what it SAYS about this sentence."""
    from orchestrator.seam import pipeline
    got = pipeline.run(pair.request, board=board, world=world, model=model, retries=0)
    rules = sorted({n.rule for n in (got.linguistics or ())})
    return got, rules


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    from planner.formula.legal import Board
    from .metrics import Lab
    board, world = Board(), Lab()

    rows: List[Dict] = []
    print("=" * 112)
    print("THE SAME SENTENCE, BOTH WAYS — the AI in a vacuum, and the whole harness")
    print("=" * 112)

    for pair in PAIRS:
        hits = 0
        answers = []
        for _ in range(args.runs):
            for rev in (False, True):
                a = ask_ai(pair, rev, args.model)
                answers.append(a)
                hits += (a == pair.want)
        total = args.runs * 2
        got, rules = run_harness(pair, board, world, args.model)
        named = pair.harness_rule and pair.harness_rule in rules
        rows.append({"pair": pair, "ai": f"{hits}/{total}", "ai_ok": hits == total,
                     "verdict": got.outcome, "rules": rules, "named": bool(named)})
        print(f"\n{pair.tag:<10} [{pair.phenomenon}] “{pair.request}”")
        print(f"           want          {pair.want}")
        print(f"           AI            {hits}/{total}   {sorted(set(map(str, answers)))}")
        print(f"           HARNESS       {got.outcome}   findings={rules or '—'}")
        print(f"           operations    {[(o.operator, o.on, o.value) for o in got.operations]}")
        print(f"           note          {pair.note}")

    print(f"\n{'=' * 112}")
    print(f"  {'case':<10} {'phenomenon':<18} {'AI':<7} {'harness names it':<18} {'verdict':<8}")
    print("  " + "-" * 68)
    for row in rows:
        p = row["pair"]
        expected = "—" if not p.harness_rule else ("yes" if row["named"] else "NO")
        print(f"  {p.tag:<10} {p.phenomenon:<18} {row['ai']:<7} {expected:<18} {row['verdict']:<8}")

    ours = [r for r in rows if r["ai_ok"] and not r["named"] and r["pair"].harness_rule]
    gap = [r for r in rows if r["ai_ok"] and not r["pair"].harness_rule
           and "CONTROL" not in r["pair"].note]
    print(f"\n  AI HAS IT AND THE HARNESS DROPS IT: {[r['pair'].tag for r in ours] or 'none'}")
    print(f"  AI HAS IT AND WE NEVER BUILT A CHECK: {[r['pair'].tag for r in gap] or 'none'}")


if __name__ == "__main__":
    main()
