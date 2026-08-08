"""CAN THE MODEL READ INTENT — make it, or refer to it — WITHOUT KNOWING THE WORLD?

    PYTHONPATH=. python3 -m tests.bench.twopass.intent_probe

The operator, 2026-08-08:

> *"What if a resource exists so fetch is triggered, but the user asks for creation anyway?
> Gate 2 has to know the difference based on the information from the AI, which can happen —
> the AI can derive intent, it just can't understand the world. It can understand when
> something external is needed, it just makes the wrong call. It defaulted to create because
> it's easier, but intent is still correct. Test that."*

# WHY THIS DECIDES A DESIGN QUESTION RATHER THAN SATISFYING CURIOSITY

An hour ago I argued the opposite — that `existence` should never be asked, because the model
is known-bad at fetching and would answer "make" every time, so defaulting is free. If the
operator is right, that reasoning is wrong in an important way: **defaulting throws away a
signal the model actually has.**

    IF INTENT IS READABLE   the AI states what the REQUEST asked for, gate 2 checks it against
                            what the WORLD holds, and the DISAGREEMENT is the finding —
                            *"you asked me to create web and there is already a web"*. That is
                            gate 2 doing precisely its job, and it cannot do it without the
                            AI's stated intent to check against.

    IF INTENT IS NOT        default to ensure, compute the rest, ask nothing. Cheaper, and one
                            fewer slot to be wrong in.

**THE CLAIM UNDER TEST IS NARROW AND FAIR:** intent is carried by the VERB, not by the world.
"create a vm named web" and "put web on lab" differ in what they ask for, and you do not need
to know whether `web` exists to tell them apart. That is what is being measured.

# THE CONTROL THAT HAS TO BE HERE

Enum position was just measured to move answers on this stack, so every case is asked TWICE —
once with `refer` offered first, once with `make` first. **An answer that flips with the order
is not an intent reading, it is a coin.** Only order-stable answers count as correct.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    R1  INTENT IS READABLE at a high rate on unambiguous cases, because the verb carries it.
        I will call the operator right if order-stable accuracy is >= 80%.
    R2  RUNG 10 IS THE DISCRIMINATING CASE — "clone golden into 3 new vms" holds BOTH intents
        in one sentence, and `golden` must come back `refer` while the copies come back `make`.
        If it can split one sentence two ways, the signal is real and not a verb reflex.
    R3  THE SAME NAME UNDER TWO VERBS is the cleanest pair: "create a vm named web" vs "put web
        on the lab network". Identical noun, opposite intent, no world knowledge involved.
    R4  IF IT FAILS, it fails toward MAKE — matching the create-by-default already observed.
    R5  RUNG 8's `core` and `dmz` are GENUINELY AMBIGUOUS in the text and are marked so. They
        are scored separately and do not count toward R1 either way.
"""
import argparse
from collections import Counter
from typing import List, NamedTuple

MAKE, REFER = "make", "refer"


class Case(NamedTuple):
    request: str
    thing: str
    expect: str          # MAKE | REFER | "ambiguous"
    why: str             # the words in the request that decide it


CASES: List[Case] = [
    # ── R3's pair: one noun, two verbs, no world knowledge needed ─────────────────────
    Case("create a vm named web", "web", MAKE, "'create'"),
    Case("put web on the lab network", "web", REFER, "'put ... on' presupposes web"),

    # ── plainly MAKE ──────────────────────────────────────────────────────────────────
    Case("create a network called lab and a vm named web, then put web on lab",
         "lab", MAKE, "'create a network called'"),
    Case("create a vm named alpha", "alpha", MAKE, "'create'"),
    Case("create a vm named beta and then launch it", "beta", MAKE, "'create'"),

    # ── plainly REFER ─────────────────────────────────────────────────────────────────
    Case("ping every vm and stop the ones that do not answer",
         "every vm", REFER, "'every vm' ranges over what is there"),
    Case("ping every vm and stop the ones that do not answer",
         "the ones that do not answer", REFER, "a subset of what is there"),
    Case("take a snapshot of every running vm",
         "every running vm", REFER, "'every running vm' is existing state"),
    Case("launch every vm that is currently stopped",
         "every vm that is currently stopped", REFER, "'currently' is about now"),
    Case("put every vm on a network called core, except db — db goes on a network called dmz "
         "instead", "db", REFER, "'except db' carves out an existing machine"),
    Case("make sure there are exactly two machines left",
         "machines", REFER, "'left' means reduce what exists"),

    # ── R2: BOTH intents in one sentence ──────────────────────────────────────────────
    Case("clone golden into 3 new vms and launch all of them",
         "golden", REFER, "the source of a clone must already be there"),
    Case("clone golden into 3 new vms and launch all of them",
         "the 3 new vms", MAKE, "'3 new vms' are the product"),

    # ── R5: genuinely ambiguous, scored apart ─────────────────────────────────────────
    Case("put every vm on a network called core, except db — db goes on a network called dmz "
         "instead", "core", "ambiguous", "'a network called core' does not say if it exists"),
]

_QUESTION = (
    "Does the request ask for this thing to be BROUGHT INTO BEING, or does it refer to one "
    "that is already there?\n\n"
    "Answer only from the words of the request. You do NOT know what exists — do not guess "
    "about that, and do not let it change your answer. Judge only what is being ASKED FOR."
)


def _schema(order: List[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": order}}}


def ask(case: Case, order: List[str], model=None, temp=0.0, timeout=300):
    from engines.channel import constrained
    payload = f"the request: {case.request}\n\nthe thing: {case.thing}"
    try:
        got = constrained(_QUESTION, payload, _schema(order),
                          model=model, temp=temp, timeout=timeout) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<{type(exc).__name__}>"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    orders = {"refer-first": [REFER, MAKE], "make-first": [MAKE, REFER]}
    print("=" * 100)
    print("CAN IT READ INTENT?   every case asked in BOTH enum orders — a flip is a coin, "
          "not a reading")
    print("=" * 100)
    print(f"  {'thing':<36} {'want':<10} {'refer-1st':<11} {'make-1st':<11} verdict")

    tally: Counter = Counter()
    for case in CASES:
        answers = {name: ask(case, order, model=args.model) for name, order in orders.items()}
        a, b = answers["refer-first"], answers["make-first"]
        stable = a == b
        if case.expect == "ambiguous":
            verdict = f"AMBIGUOUS — said {a}" if stable else "AMBIGUOUS — flipped"
            tally["ambiguous"] += 1
        elif not stable:
            verdict = "FLIPPED (order decided it)"
            tally["flipped"] += 1
        elif a == case.expect:
            verdict = "correct"
            tally["correct"] += 1
        else:
            verdict = f"WRONG (wanted {case.expect})"
            tally["wrong"] += 1
            tally[f"wrong->{a}"] += 1
        print(f"  {case.thing[:35]:<36} {case.expect:<10} {str(a):<11} {str(b):<11} {verdict}")

    scored = tally["correct"] + tally["wrong"] + tally["flipped"]
    print(f"\n{'=' * 100}")
    print(f"  order-stable and correct : {tally['correct']} of {scored} scored")
    print(f"  wrong                    : {tally['wrong']}"
          f"   (toward make: {tally['wrong->make']}, toward refer: {tally['wrong->refer']})")
    print(f"  decided by enum order    : {tally['flipped']}")
    print(f"  ambiguous, not scored    : {tally['ambiguous']}")
    if scored:
        print(f"\n  ⇒ R1 asked for >= 80%. Result: {100 * tally['correct'] / scored:.0f}%")


if __name__ == "__main__":
    main()
