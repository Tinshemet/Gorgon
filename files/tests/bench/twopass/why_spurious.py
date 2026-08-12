"""WHY DOES IT ADD A STEP NOBODY ASKED FOR?

    PYTHONPATH=. python3 -m tests.bench.twopass.why_spurious

The operator's question, 2026-08-08:

> *"Is it because it wanted to do something else and defaulted to that, or because it wanted
> to pick something, so it picked that? One got defaulted because it didn't exist, or it gave
> up and defaulted."*

Two hypotheses, and they call for different fixes, which is why it is worth an hour:

    A · REAL INTENT, NO OPERATOR   it is trying to express something the menu cannot say, and
                                   `add_label` is the nearest thing to hand. FIX: give the
                                   vocabulary the missing operation, or teach the gate to
                                   recognise the substitution.

    B · FILLER                     it has nothing particular in mind and picks a cheap option
                                   because emitting a step is easier than stopping. FIX: make
                                   stopping cheaper — the position result already hints this.

# THE CLUE THAT IS ALREADY IN THE DATA

The spurious step appeared on rungs 3 and 8 and NOT on 11 or 12. Rungs 3 and 8 are exactly the
requests that contain an explicit name to attach — *"a network called lab"*, *"a vm named
web"*, *"a network called core"*. Rung 11's objects (`fleet`, `unresponsive`) were named by US
in the symbol table and appear nowhere in the request.

⇒ SO THE STANDING GUESS IS A, WITH CONTENT: it is trying to say *"call it lab"*, and there is
  no operator for naming because a name is fixed at creation and `_settable()` excludes the key.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    Q1  DECOY. Offer `set_name`, an operator that would satisfy the naming intent.
        IF A -> the spurious step becomes `set_name lab` / `set_name web`.
        IF B -> it stays `add_label`, or moves to whatever else is cheap.
        THIS IS THE DISCRIMINATING CELL.

    Q2  REMOVAL. Take `add_label` off the menu entirely.
        IF A -> a DIFFERENT substitute appears, and it should still be a string-attaching one.
        IF B -> the substitute is whatever now sits early in the list, regardless of meaning.

    Q3  I expect the truth to be BOTH, and the position result is why: a latent naming intent
        that only surfaces when a plausible-enough operator is positionally cheap to reach.
        If Q1 shows `set_name` AND `label_last` still suppresses it, that is the answer.

# ⇒⇒ THE ANSWER: A. REAL INTENT, NO OPERATOR TO CARRY IT

    Q1 CONFIRMED, and decisively. Offer `set_name` and the model uses it — `set_name web`,
    3 of 3 on rung 3 — and rung 8's spurious `add_label db` DISAPPEARS entirely. So that
    `add_label` was standing in for a naming intent the whole time. It is not filler. It is
    not giving up. It is trying to say something the vocabulary cannot express.

    AND THE DETAIL THAT SETTLES IT: `set_name` sat at INDEX 16 of 18 and was still chosen.
    The model reaches past a whole menu to find the semantically right operator when one
    exists. **Position does not decide whether it substitutes — it only decides WHICH wrong
    thing it grabs when the right one is missing.**

# ⇒ SO THE FIX IS NOT `set_name`, AND THIS IS THE USEFUL PART

What is it trying to name? `web`, from *"a vm named web"*. But PASS ONE ALREADY CAPTURED THAT:
the declaration reads `web — a vm — the machine named web`. The model is re-stating in pass 2
something pass 1 has already settled.

⇒ **THE DEFECT IS DUPLICATION ACROSS THE TWO PASSES, NOT A MISSING OPERATOR.** Adding
  `set_name` would satisfy the urge and encode the same fact twice, which is how a symbol table
  and a program drift apart. The fix belongs one level up: pass 2 must be told that identity is
  already settled, or gate 3 must recognise an operation that merely restates a declaration.

# ⇒⇒ AND A CORRECTION I OWE THE RECORD

I reported the ordering result as *"n=3, every cell byte-identical across runs"*. **That was
overstated.** The same input later produced BOTH outcomes on rung 8 under `alpha` — clean in
one invocation, spurious in another — while six other repeats, across separate processes, were
identical. So this stack is mostly stable and not reliably so, and my n=3 was weaker evidence
than I claimed.

⇒ The ordering effect is REAL — `label_last` suppressed the substitute in every cell it was
  run in — but it is NOT the clean deterministic table the earlier docstring implies. Treat
  those exact counts as indicative, not settled. Rule V3 exists for this and I under-applied it.
"""
import argparse
from collections import Counter
from typing import Dict, List

from tests.bench.twopass.condition_probe import TABLES, _schema_a, _table_text, operators

CONTROL = "alpha"


def menu(variant: str) -> List[str]:
    """The operator list under each condition. One variable changes per cell."""
    ops = operators()
    if variant == "no_label":
        return [o for o in ops if o != "add_label"]
    if variant == "decoy":
        return sorted(ops + ["set_name"])
    if variant == "decoy_label_last":
        rest = sorted([o for o in ops if o != "add_label"] + ["set_name"])
        return rest + ["add_label"]
    if variant == "label_last":
        return [o for o in ops if o != "add_label"] + ["add_label"]
    return ops


def run(n: int, variant: str, model=None, temp=0.0, timeout=300) -> List[tuple]:
    from engines.channel import constrained

    entry = TABLES[n]
    names = [d[0] for d in entry["declared"]]
    ops = menu(variant)
    payload = (f"{_table_text(entry)}\n\n"
               f"the operations you may use: {', '.join(ops)}\n\n"
               f"the request: {entry['request']}")
    prompt = ("Say what has to be DONE, as a list of steps. Each step names one operation and "
              "the ONE already-identified thing it acts on. Some operations need a second thing "
              "as their value — otherwise leave value null. Use only the operations and the "
              "names offered. Do not invent a name.")
    try:
        got = constrained(prompt, payload, _schema_a(names, ops), model=model, temp=temp,
                          timeout=timeout) or {}
    except Exception as exc:
        return [("<failed>", type(exc).__name__, None)]
    return [(s.get("operator"), s.get("on"), s.get("value"))
            for s in (got.get("operations") or []) if isinstance(s, dict)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    variants = ["alpha", "no_label", "decoy", "decoy_label_last", "label_last"]
    print("=" * 98)
    print("WHY THE SPURIOUS STEP — real intent with no operator, or filler?")
    print("=" * 98)
    tally: Counter = Counter()

    for variant in variants:
        ops = menu(variant)
        where = f"add_label@{ops.index('add_label')}" if "add_label" in ops else "add_label ABSENT"
        extra = ", set_name offered" if "set_name" in ops else ""
        print(f"\n{'─' * 98}\n{variant}   ({len(ops)} operators · {where}{extra})")
        for n in (3, 8, 11):
            want = TABLES[n]["expect"]
            for i in range(args.runs):
                got = run(n, variant, model=args.model)
                spurious = [s for s in got if s not in want]
                for s in spurious:
                    tally[(variant, s[0])] += 1
                print(f"    rung {n:>2} run {i + 1}   "
                      f"{('spurious ' + str(spurious)) if spurious else 'clean'}")

    print(f"\n{'=' * 98}\nWHICH OPERATOR WAS THE SPURIOUS ONE")
    if not tally:
        print("    none in any cell")
    for (variant, op), count in sorted(tally.items()):
        print(f"    {variant:<20} {op:<22} {count}")


if __name__ == "__main__":
    main()
