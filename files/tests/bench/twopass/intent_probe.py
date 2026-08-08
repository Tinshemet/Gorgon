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

# ── THE VOCABULARY IS ITSELF A VARIABLE, and it turned out to be THE variable ──────────
#
# ABSTRACT wording returned `refer` to all fourteen cases — a constant, not a reading, and
# the apparent 62% was only the case mix. CONCRETE wording, on the same model and the same
# sentences, read the intent. `refer` is a SYSTEMS word; `create` and `use` are the words the
# request is already written in.
VOCAB = {
    "abstract": (
        [REFER, MAKE],
        "Does the request ask for this thing to be BROUGHT INTO BEING, or does it refer to "
        "one that is already there?\n\nAnswer only from the words of the request. You do NOT "
        "know what exists — do not guess about that. Judge only what is being ASKED FOR.",
    ),
    "concrete": (
        ["use", "create"],
        "Read the request. For the thing named, answer 'create' if the request asks you to "
        "bring it into existence, or 'use' if the request talks about one that already "
        "exists and only acts on it.",
    ),
}


def normalise(answer) -> str:
    return MAKE if answer in (MAKE, "create") else REFER if answer in (REFER, "use") else "?"


def _schema(order: List[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": order}}}


def ask(case: Case, order: List[str], question: str, model=None, temp=0.0, timeout=300):
    from engines.channel import constrained
    payload = f"the request: {case.request}\n\nthe thing: {case.thing}"
    try:
        got = constrained(question, payload, _schema(order),
                          model=model, temp=temp, timeout=timeout) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<{type(exc).__name__}>"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    print("=" * 100)
    print("CAN IT READ INTENT?   both vocabularies, each in BOTH enum orders.")
    print("A flip with the order is a coin, not a reading — only order-stable answers score.")
    print("=" * 100)

    for vocab, (enum, question) in VOCAB.items():
        tally: Counter = Counter()
        print(f"\n{'─' * 100}\n{vocab.upper()}  —  options {enum!r}")
        print(f"  {'thing':<34} {'want':<10} {'as-given':<10} {'reversed':<10} verdict")
        for case in CASES:
            a = normalise(ask(case, enum, question, model=args.model))
            b = normalise(ask(case, list(reversed(enum)), question, model=args.model))
            if case.expect == "ambiguous":
                verdict = f"ambiguous — said {a}" if a == b else "ambiguous — flipped"
                tally["ambiguous"] += 1
            elif a != b:
                verdict = "FLIPPED (order decided it)"
                tally["flipped"] += 1
            elif a == case.expect:
                verdict = "correct"
                tally["correct"] += 1
            else:
                verdict = f"WRONG (wanted {case.expect})"
                tally["wrong"] += 1
                tally[f"wrong->{a}"] += 1
            print(f"  {case.thing[:33]:<34} {case.expect:<10} {a:<10} {b:<10} {verdict}")

        scored = tally["correct"] + tally["wrong"] + tally["flipped"]
        print(f"    correct {tally['correct']}/{scored}   wrong {tally['wrong']} "
              f"(toward make {tally['wrong->make']}, toward refer {tally['wrong->refer']})   "
              f"order-decided {tally['flipped']}   ambiguous {tally['ambiguous']}")
        if scored:
            print(f"    ⇒ {100 * tally['correct'] / scored:.0f}%   (R1 asked for >= 80%)")


if __name__ == "__main__":
    main()
