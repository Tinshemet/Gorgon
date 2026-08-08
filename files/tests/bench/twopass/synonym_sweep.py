"""IS IT READING INTENT, OR DID TWO WORDS HAPPEN TO WORK?

    PYTHONPATH=. python3 -m tests.bench.twopass.synonym_sweep

The operator, 2026-08-08: *"Does that mean we have a 6/6 word combo out there, or is it just
word bias? Could you test it with synonyms now?"*

`use` / `create` scored 77% where `refer` / `make` scored 62% — and the 62% was a CONSTANT,
not a partial signal. That gap could mean either of two very different things:

    READING     the model understands the distinction, and only needs it put in the request's
                own vocabulary. Then every CONCRETE synonym pair should land in the same
                band, and the remaining errors should be the SAME cases every time.

    WORD BIAS   two particular tokens happened to sit well with this model, and we are
                fishing. Then scores scatter across synonyms and the failing cases move
                around with them.

The question template is held IDENTICAL and only the two words are substituted, so word
choice is the single variable.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    S1  CONCRETE PAIRS CLUSTER — I expect a spread under ~15 points across them. A wide
        scatter means word bias and the design needs a different question, not a better word.
    S2  NO PAIR REACHES 13/13, and this is the direct answer to the operator's question. The
        three failures — `golden`, `web` under "put", `every vm that is currently stopped` —
        are a SENTENCE-level versus OBJECT-level limit, not a vocabulary one. If some pair
        does hit 13/13 I am wrong about the mechanism and it is worth knowing loudly.
    S3  THE SAME CASES FAIL in every concrete pair. Stable failures = a structural limit.
        Moving failures = noise, and then none of the scores mean much.
    S4  The abstract control stays lowest and stays a near-constant.
"""
import argparse
from collections import Counter
from typing import Dict, List, Tuple

from .intent_probe import CASES, MAKE, REFER

# the question, with two holes. NOTHING ELSE CHANGES BETWEEN CELLS.
TEMPLATE = ("Read the request. For the thing named, answer {a!r} if the request asks you to "
            "bring it into existence, or {b!r} if the request talks about one that already "
            "exists and only acts on it.")

# (word-for-make, word-for-refer). The first is the measured baseline; the last is the
# measured null, kept as an anchor rather than dropped.
PAIRS: List[Tuple[str, str]] = [
    ("create", "use"),
    ("make", "take"),
    ("build", "find"),
    ("new", "existing"),
    ("provision", "select"),
    ("add", "reuse"),
    ("make", "refer"),
]


def ask(request: str, thing: str, a: str, b: str, order: List[str],
        model=None, temp=0.0, timeout=300):
    from engines.channel import constrained
    schema = {"type": "object", "additionalProperties": False, "required": ["answer"],
              "properties": {"answer": {"type": "string", "enum": order}}}
    try:
        got = constrained(TEMPLATE.format(a=a, b=b),
                          f"the request: {request}\n\nthe thing: {thing}",
                          schema, model=model, temp=temp, timeout=timeout) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<{type(exc).__name__}>"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--both-orders", action="store_true",
                    help="the previous run showed 0 order-flips; off by default to halve cost")
    args = ap.parse_args()

    scored = [c for c in CASES if c.expect != "ambiguous"]
    print("=" * 100)
    print(f"SYNONYM SWEEP — same question, only the two words change. "
          f"{len(scored)} scored cases per pair.")
    print("=" * 100)

    results: Dict[Tuple[str, str], int] = {}
    failures: Dict[Tuple[str, str], List[str]] = {}

    for a, b in PAIRS:
        correct = 0
        missed: List[str] = []
        for case in scored:
            got = ask(case.request, case.thing, a, b, [b, a], model=args.model)
            answer = MAKE if got == a else REFER if got == b else "?"
            if args.both_orders:
                other = ask(case.request, case.thing, a, b, [a, b], model=args.model)
                if (MAKE if other == a else REFER if other == b else "?") != answer:
                    answer = "flipped"
            if answer == case.expect:
                correct += 1
            else:
                missed.append(f"{case.thing[:26]}→{answer}")
        results[(a, b)] = correct
        failures[(a, b)] = missed
        pct = 100 * correct / len(scored)
        print(f"\n  {a + '/' + b:<22} {correct:>2}/{len(scored)}  {pct:>3.0f}%")
        for m in missed:
            print(f"      missed  {m}")

    print(f"\n{'=' * 100}")
    concrete = [v for k, v in results.items() if k != ("make", "refer")]
    spread = (max(concrete) - min(concrete)) if concrete else 0
    print(f"  concrete pairs: best {max(concrete)}/{len(scored)}, worst {min(concrete)}"
          f"/{len(scored)}, SPREAD {spread} cases "
          f"({100 * spread / len(scored):.0f} points)")
    print(f"  abstract anchor make/refer: {results[('make', 'refer')]}/{len(scored)}")
    print(f"  ⇒ S1 wanted a spread under ~15 points.")
    print(f"  ⇒ S2 said NO pair reaches {len(scored)}/{len(scored)}. "
          f"Best was {max(results.values())}.")

    every = Counter()
    for k, missed in failures.items():
        if k == ("make", "refer"):
            continue
        for m in missed:
            every[m.split("→")[0]] += 1
    print(f"\n  WHICH CASES FAIL, and in how many of the {len(concrete)} concrete pairs:")
    for thing, n in every.most_common():
        tag = "  ⇐ fails everywhere — structural" if n == len(concrete) else ""
        print(f"      {n}/{len(concrete)}  {thing}{tag}")


if __name__ == "__main__":
    main()
