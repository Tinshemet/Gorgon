"""DOES GIVING IT SYNONYMS HELP?

    PYTHONPATH=. python3 -m tests.bench.twopass.gloss_probe

The operator, 2026-08-08: *"Would giving it synonyms help? Did you test that?"*

No — the sweep tested one PAIR per call and never several words at once. This does.

# WHY IT SHOULD HELP, IF THE PRIOR EXPLANATION IS RIGHT

The sweep's finding was that the word pair sets a PRIOR toward creating, and the sentence's
evidence must overcome it. A weak "already exists" word (`find`) leaves a strong prior and
loses even the easy cases; a strong one (`existing`) holds. If that is the mechanism, then
STRENGTHENING THE WEAK WORD should recover most of the gap — and there are two ways to do it:

    GLOSS       keep the two options, define each in the question with synonyms.
                Enum stays at 2, so no enum-size or position risk is introduced.

    WIDE ENUM   offer several words per side and normalise the answer back.
                Semantically richer, but it adds members to an enum whose SIZE and ORDER were
                both measured to move answers on this stack — so it may pay with one hand and
                take with the other.

Run on the sweep's WORST pair and its BEST, so the question is whether glossing CLOSES THE
GAP between them rather than whether it nudges one number.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    T1  GLOSS LIFTS THE WEAK PAIR substantially — build/find at 7/13 should move most of the
        way toward new/existing at 11/13. This is the direct test of the prior explanation;
        if it does not move, the prior story is wrong and the sweep's ranking is unexplained.
    T2  THE CEILING DOES NOT RISE ABOVE 11/13, and `web` and `golden` still fail. Those are
        object-versus-sentence, and no amount of vocabulary reaches them.
    T3  WIDE ENUM is NO BETTER than gloss, because it trades semantic anchoring for enum
        width — and width has already cost us once today.
    T4  IF GLOSS LEVELS THE PAIRS, word choice stops being first-order and the fix is to gloss
        rather than to hunt for the perfect word. That would be the useful outcome.
"""
import argparse
from typing import List, Tuple

from .intent_probe import CASES, MAKE, REFER

BARE = ("Read the request. For the thing named, answer {a!r} if the request asks you to "
        "bring it into existence, or {b!r} if the request talks about one that already "
        "exists and only acts on it.")

GLOSS = ("Read the request. For the thing named:\n"
         "  answer {a!r} — meaning it must be brought into existence: created, built, "
         "provisioned, made new\n"
         "  answer {b!r} — meaning it is already there: existing, previously created, "
         "only being selected, reused or acted upon\n"
         "Judge only what the request asks for about THIS thing.")

# several words per side, normalised back. The sweep's own vocabulary, pooled.
WIDE_MAKE = ["create", "build", "provision", "new"]
WIDE_REFER = ["use", "existing", "select", "reuse"]

PAIRS: List[Tuple[str, str]] = [("build", "find"), ("new", "existing"), ("create", "use")]


def ask(request: str, thing: str, question: str, enum: List[str],
        model=None, temp=0.0, timeout=300):
    from engines.channel import constrained
    schema = {"type": "object", "additionalProperties": False, "required": ["answer"],
              "properties": {"answer": {"type": "string", "enum": enum}}}
    try:
        got = constrained(question, f"the request: {request}\n\nthe thing: {thing}",
                          schema, model=model, temp=temp, timeout=timeout) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<{type(exc).__name__}>"


def score(question: str, enum: List[str], makers: List[str], model=None) -> Tuple[int, list]:
    scored = [c for c in CASES if c.expect != "ambiguous"]
    correct, missed = 0, []
    for case in scored:
        got = ask(case.request, case.thing, question, enum, model=model)
        answer = MAKE if got in makers else REFER
        if answer == case.expect:
            correct += 1
        else:
            missed.append(case.thing[:26])
    return correct, missed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    n = len([c for c in CASES if c.expect != "ambiguous"])

    print("=" * 100)
    print(f"DOES GIVING IT SYNONYMS HELP?   {n} scored cases per cell")
    print("=" * 100)

    results = {}
    for a, b in PAIRS:
        for tag, question in (("bare", BARE), ("glossed", GLOSS)):
            correct, missed = score(question.format(a=a, b=b), [b, a], [a], model=args.model)
            results[(f"{a}/{b}", tag)] = correct
            print(f"\n  {a + '/' + b:<18} {tag:<9} {correct:>2}/{n}  "
                  f"{100 * correct / n:>3.0f}%")
            for m in missed:
                print(f"      missed  {m}")

    wide_q = ("Read the request. For the thing named, answer with ONE word describing what "
              "the request asks for: a word meaning it must be brought into existence, or a "
              "word meaning it is already there and only being acted upon.")
    correct, missed = score(wide_q, WIDE_REFER + WIDE_MAKE, WIDE_MAKE, model=args.model)
    results[("wide enum", "8 options")] = correct
    print(f"\n  {'wide enum':<18} {'8 options':<9} {correct:>2}/{n}  {100 * correct / n:>3.0f}%")
    for m in missed:
        print(f"      missed  {m}")

    print(f"\n{'=' * 100}")
    for (pair, tag), v in results.items():
        print(f"    {pair:<18} {tag:<10} {v}/{n}")
    bare = [v for (p, t), v in results.items() if t == "bare"]
    glossed = [v for (p, t), v in results.items() if t == "glossed"]
    if bare and glossed:
        print(f"\n    bare    spread {max(bare) - min(bare)} cases")
        print(f"    glossed spread {max(glossed) - min(glossed)} cases   "
              f"⇐ T4: does glossing LEVEL the pairs?")


if __name__ == "__main__":
    main()
