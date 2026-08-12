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

# ⇒⇒ RESULTS: 9/13 SINGLE-ACTION, ~11/13 MULTI-ACTION. NEITHER BEATS GLOSSING. CLOSED.

    U1  CONFIRMED, and it is the only thing that ever fixed it. `web` under "put web on the
        lab network" failed in 6 of 6 synonym pairs and in every glossed cell; asking what the
        request DOES to it returns `add_label` / `add_vm_to_network`, which derives to `use`.
    U2  FAILED. `golden` returns `clone_vm`, never "used as the thing copied from". The source
        role was offered and not taken.
    U3  FAILED. 9/13 single-action, ~11/13 multi-action against glossing's 11/13.
    U4  CONFIRMED. Misses split 2 toward make and 2 toward use. **Deriving the intent instead
        of asking for it killed the one-sided create-bias completely** — that half of the
        theory held even though the score did not.

## the two failure modes it introduced, both mine and not the model's

  * **ONE ACTION WHEN THE REQUEST DOES SEVERAL.** "create a vm named beta AND THEN LAUNCH IT"
    does two things to `beta`; the schema forced a choice, it took the last, and the creating
    action — the one that decides existence — was discarded. THE MULTI-ACTION REPAIR FIXES
    THIS: `beta` -> [create_vm, launch_vm] -> make, and `the 3 new vms` likewise.
  * **ACTIONS THAT BELONG TO A DIFFERENT OBJECT.** "take a snapshot of every running vm"
    returns `create_snapshot` FOR THE VMS — true of the sentence, false of the object. The
    multi-action repair does NOT touch this, and neither does anything else tried today. It is
    the same object-versus-sentence limit wearing a new costume.

## and what the repair cost

The unbounded array TIMED OUT at 300s — a 19-option enum with an unbounded list is expensive
to decode. Bounded to 3 it returned noisy lists: `add_label` three times over, `create_vm`
asserted for machines that are cloned rather than created.

⇒ **SETTLED: the glossed two-option question at 11/13 is the design.** Slower, equal-scoring
  and noisier is not a trade worth taking.

⇒ PARKED, NOT CHASED: the miss sets are COMPLEMENTARY. Glossing misses `web` and `golden`;
  multi-action misses `every running vm` and `golden`. A design that asked both and reconciled
  would leave only `golden` — 12/13. Untested, and it doubles the calls per object.
"""
import argparse
from collections import Counter
from typing import List, Tuple

from tests.bench.twopass.condition_probe import operators
from tests.bench.twopass.intent_probe import CASES, MAKE, REFER

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


def derive_all(actions: List[str], made: set) -> str:
    """MULTI-ACTION: a thing is MADE if ANY action applied to it brings it into being.

    The single-action run lost `beta` ("create a vm named beta AND THEN LAUNCH IT") and
    `the 3 new vms` ("clone golden into 3 new vms AND LAUNCH ALL OF THEM") because a request
    can do several things to one object and the schema forced a choice — it took the last,
    and the creating action, the one that decides existence, was discarded.

    ⇒ RISK, NAMED IN ADVANCE: letting it pick several invites the over-selection measured
      twice today. If it returns everything, everything derives to `make` and the cure is
      worse than the disease.
    """
    return MAKE if any(a in made for a in actions) else REFER


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
