"""ASK WHAT THE REQUEST *DOES* TO THIS THING — and DERIVE the intent from the answer.

    PYTHONPATH=. python3 -m tests.bench.twopass.action_probe

Queued by the operator, 2026-08-08, from a finding parked earlier the same day.

# WHY THIS IS A DIFFERENT QUESTION, NOT A BETTER WORDING

Every previous cell asked the model to CHOOSE BETWEEN create and use. That question is about
the thing's status, and the model kept answering it from the SENTENCE — *"clone golden into 3
new vms"* is a creating sentence, so `golden` came back as create in 6 pairs out of 6.

This asks something it cannot answer from the sentence alone:

    **what does the request DO to this thing?**

An action has to attach to an object. *"Put web on the lab network"* does `add_vm_to_network`
to `web` — there is no reading of that sentence where the action applied to `web` is "create".
And `golden` in a clone is the thing COPIED FROM, which is a role the sentence names
explicitly.

⇒ **AND THE INTENT IS THEN COMPUTED, NEVER ASKED** (rule W8). If the chosen action is a
  creator applied to this thing, the intent is `make`; otherwise `use`. The model never sees
  the word "create" as an option to be biased toward, so the create-prior measured in the
  synonym sweep has nothing to act on.

That is the same move as `settled`: replace a judgement call with a derivation from an answer
the model is actually good at giving.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    U1  `web` IS FIXED. "put web on the lab network" -> add_vm_to_network -> use. This is the
        case that failed in every pair of the sweep, and it should fall out immediately.
        HIGH confidence — if this fails the whole idea is wrong.
    U2  `golden` IS FIXED, but only because "used as the thing copied from" is offered as an
        explicit option. MEDIUM confidence: the model still has to prefer that role over
        `clone_vm` for the source, and both are true-ish of the sentence.
    U3  TOTAL BEATS THE SWEEP'S CEILING of 11/13.
    U4  THE ERROR DIRECTION STOPS BEING ONE-SIDED. Every miss in the sweep was toward make;
        with intent derived rather than chosen, misses should scatter. If they are STILL all
        toward make, the bias is not in the question and I have misdiagnosed it twice.
"""
import argparse
from collections import Counter
from typing import List, Tuple

from .condition_probe import operators
from .intent_probe import CASES, MAKE, REFER

# roles a thing can play that are NOT an operation performed on it. Declared here rather than
# derived because the manifest describes what can be DONE, not what can be REFERRED TO.
SOURCE = "used as the thing copied from"
MENTIONED = "nothing is done to it — it is only mentioned"
EXTRA = [SOURCE, MENTIONED]

_QUESTION = (
    "What does the request do to the thing named? Choose the ONE option that the request "
    "applies to THAT thing specifically.\n\n"
    "Be careful: a request may do different things to different things it mentions. Answer "
    "only about the thing named, not about the request as a whole."
)


def menu() -> List[str]:
    """Manifest operations plus the two roles. `add_label` LAST, per the ordering result."""
    ops = [o for o in operators() if o != "add_label"] + ["add_label"]
    return ops + EXTRA


def creators() -> set:
    """Which options MEAN the thing is brought into being. Read from the manifest (W5)."""
    from planner.ir import config as _config
    out = set()
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        for name in (spec.get("creators") or {}):
            out.add(f"create_{kind}" if name == "create" else f"{name}_{kind}")
    return out


def derive(action: str, made: set) -> str:
    """THE INTENT IS COMPUTED, NEVER ASKED. This is the whole point of the probe."""
    if action in (SOURCE, MENTIONED):
        return REFER
    return MAKE if action in made else REFER


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    from engines.channel import constrained

    options = menu()
    made = creators()
    scored = [c for c in CASES if c.expect != "ambiguous"]
    schema = {"type": "object", "additionalProperties": False, "required": ["answer"],
              "properties": {"answer": {"type": "string", "enum": options}}}

    print("=" * 104)
    print(f"WHAT DOES THE REQUEST *DO* TO THIS THING?   {len(options)} options, "
          f"intent DERIVED from the answer")
    print("=" * 104)
    print(f"  creators (=> make): {sorted(made)}\n")
    print(f"  {'thing':<34} {'want':<7} {'action chosen':<28} {'derived':<8} verdict")

    tally: Counter = Counter()
    for case in scored:
        try:
            got = constrained(_QUESTION,
                              f"the request: {case.request}\n\nthe thing: {case.thing}",
                              schema, model=args.model, temp=0.0, timeout=300) or {}
            action = got.get("answer") or "?"
        except Exception as exc:
            action = f"<{type(exc).__name__}>"
        intent = derive(action, made)
        ok = intent == case.expect
        tally["correct" if ok else "wrong"] += 1
        if not ok:
            tally[f"wrong->{intent}"] += 1
        print(f"  {case.thing[:33]:<34} {case.expect:<7} {action[:27]:<28} {intent:<8} "
              f"{'correct' if ok else 'WRONG'}")

    n = len(scored)
    print(f"\n{'=' * 104}")
    print(f"  {tally['correct']}/{n}  ({100 * tally['correct'] / n:.0f}%)")
    print(f"  wrong toward make {tally['wrong->make']}, toward use {tally['wrong->refer']}")
    print(f"  ⇒ U3 wanted better than the sweep's ceiling of 11/{n}.")
    print(f"  ⇒ U4 wanted the misses to STOP being one-sided.")


if __name__ == "__main__":
    main()
