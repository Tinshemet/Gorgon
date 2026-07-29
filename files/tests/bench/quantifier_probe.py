"""
quantifier_probe.py — can the model say ALL / ANY / SINGLE / NOT about one clause?

THE OPERATOR'S PROPOSAL, 2026-07-29: *"maybe we first filter commands based on the
all/any/single/not, so it can't pick commands that are not correct, this way we can even
enforce the dead_if in the statement because it comes up as a NOT, so if the AI needs to
pick IF it's already upgraded to IF NOT."*

It is the codebase's own doctrine with a new discriminator. `program_schema` already says
of INTENT: *"Offering only the permitted branches makes that program unrepresentable
instead of rejected — the same fact, moved from description to constraint."* This asks
whether the QUANTIFIER can do the same job, and it would collapse three live defects into
one mechanism:

    SINGLE       -> a `call` naming it; no `select` exists     kills rung 8's missing `kind`
    ALL-EXCEPT   -> a `foreach` with `not` REQUIRED            kills rung 8's absent carve-out
    NOT          -> a one-branch `IF NOT(cond)`                kills rung 11's `dead_if`

The third is the sharpest: today the model writes `IF X {} ELSE {Y}`, the validator
objects, the sanitiser strips the empty branch and counts an artifact. Routed as NOT, there
is no empty `then` to write. The artifact stops needing detection because it stops being
expressible — which RETIRES a sanitiser kind rather than adding one.

WHY IT MIGHT BEAT THE OPERATOR ROUTER. `atomicity_probe` scored 19/20 on "one operator or
decompose" but only 4/10 on WHICH operator. The quantifier is closer to the goal's own
words — "all the machines", "apart from db", "the ones that do not answer" — so it may be
the question the model can actually answer. That is the whole bet, and it is cheap to test.

WHAT THIS DOES NOT TEST. Whether clauses can be extracted from a goal automatically; the
clauses here are declared, as the clause ledger's demands are. Quantifier is a per-CLAUSE
property, not per-goal — rung 8 alone carries three — so in a real pipeline this runs
downstream of a decomposition. Measuring the router first is deliberate: if it cannot
answer on clean hand-cut clauses it certainly cannot on derived ones.

Run:  PYTHONPATH=. python3 -m tests.bench.quantifier_probe -n 3
"""
import argparse
import json
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from orchestrator.ai.planner.score import _first_tool_call

from .ladder import BENCH_MODEL, make_call_model

# ── THE FOUR, and what each licenses ────────────────────────────────────────────────────
# SHARPENED 2026-07-29 after the first run. `any` and `not` were the only confusions, and
# one was the TAXONOMY's fault, not the model's: "stop the ones that do not answer" came
# back `not`, which is defensible — the clause contains a negation — because the original
# wording separated them by *feel* rather than by a test.
#
# THE DISCRIMINATOR IS WHETHER A WHOLE IS NAMED TO SUBTRACT FROM.
#   "the ones that do not answer"  -> no whole; a CONDITION picks the members  -> any
#   "every vm EXCEPT db"           -> a whole (every vm) minus a named member  -> not
# A NEGATIVE CONDITION IS STILL A CONDITION. That is also exactly how Medusa spells them:
# `any` is a filter in the select, `not` is the carve-out key. A router cannot be graded
# against a distinction its own vocabulary does not draw.
QUANTIFIERS = {
    "all": "every member of the kind, with NO condition — 'all the machines', 'every vm'",
    "any": ("the members matching a CONDITION — 'every vm that is stopped'. The condition "
            "may be negative ('the ones that do not answer') and it is STILL a condition, "
            "because nothing is being subtracted from a named whole"),
    "single": "ONE identified object, named — 'the vm called web', 'db'",
    "not": ("a named WHOLE, MINUS named members — 'every vm except db'. There must be a "
            "whole to subtract from; without one it is a condition, not an exclusion"),
}

# ── GROUND TRUTH — written before any model ran ─────────────────────────────────────────
# Clauses lifted verbatim from the ladder's goals, both phrasings where they differ. The
# corpus is balanced across all four so no answer can win by being the safe default, and it
# deliberately includes the pairs that are easy to confuse:
#
#   'every vm' (all) vs 'every vm that is stopped' (any)   — the condition is the whole
#                                                            difference
#   'db goes on dmz' (single) vs 'apart from db' (not)     — SAME OBJECT, and the clause
#                                                            that produced rung 8's defect:
#                                                            db arrives as the exception to
#                                                            a set and inherits set-ness
CLAUSES: List[Tuple[str, str]] = [
    # ALL — no condition
    ("connect all the machines to a network named core", "all"),
    ("put every vm on a network called core", "all"),
    ("ping every vm", "all"),
    ("give them all the 'fleet' label", "all"),
    # ANY — a condition selects a subset
    ("launch every vm that is currently stopped", "any"),
    ("start up any machine that isn't already running", "any"),
    ("take a snapshot of every running vm", "any"),
    ("stop the ones that do not answer", "any"),
    # SINGLE — one identified object
    ("create a vm named alpha", "single"),
    ("db goes on a network called dmz", "single"),
    ("put web on lab", "single"),
    ("make a box called beta, then start it up", "single"),
    # NOT — an exclusion
    ("apart from db, which belongs on dmz", "not"),
    ("except db", "not"),
    ("label every vm except golden itself 'derived'", "not"),
    ("all of them apart from the golden image", "not"),
]

_BY_KIND = Counter(q for _, q in CLAUSES)

# Recovery for a call that arrives as JSON in `content` — measured on the atomicity probe,
# 3 of 39 calls, and scoring it as "no answer" blames the model for a channel fault.
_NAME_RE = re.compile(r'"quantifier"\s*:\s*"(all|any|single|not)"')


def _recover(reply: Any) -> Optional[str]:
    try:
        content = (reply or {}).get("message", {}).get("content") or ""
    except AttributeError:
        return None
    if not content.strip():
        return None
    try:
        obj = json.loads(content)
        args = obj.get("parameters") or obj.get("arguments") or obj
        if isinstance(args, dict) and args.get("quantifier") in QUANTIFIERS:
            return args["quantifier"]
    except (ValueError, TypeError):
        pass
    m = _NAME_RE.search(content)
    return m.group(1) if m else None


def _tool() -> Dict[str, Any]:
    menu = "\n".join(f"  {k} — {v}" for k, v in QUANTIFIERS.items())
    return {
        "type": "function",
        "function": {
            "name": "quantify",
            "description": ("Say HOW MANY things one clause is about.\n" + menu),
            "parameters": {
                "type": "object",
                "properties": {
                    "quantifier": {"type": "string", "enum": list(QUANTIFIERS),
                                   "description": "which of the four this clause is"},
                },
                "required": ["quantifier"],
            },
        },
    }


def _system() -> str:
    return (
        "You are given ONE clause of a larger goal. Say how many things it is about, by "
        "calling `quantify` exactly once.\n"
        "A clause naming ONE object is `single`, however many other things the goal "
        "mentions — do not inherit the count from the rest of the goal.\n"
        "TO TELL `any` FROM `not`, ASK WHETHER A WHOLE IS NAMED TO SUBTRACT FROM. "
        "'every vm except db' names a whole and removes a member — `not`. 'the ones that "
        "do not answer' names no whole; a condition picks the members — `any`, and a "
        "NEGATIVE condition is still a condition.\n"
        "Do not explain outside the call."
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Can the model answer ALL/ANY/SINGLE/NOT?")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("-n", "--repeats", type=int, default=3,
                   help="runs per clause. NEVER diagnose from n=1.")
    a = p.parse_args(argv)

    call_model = make_call_model(a.model, a.temp, 300)
    tools = [_tool()]
    print(f"quantifier probe · model={a.model} temp={a.temp} n={a.repeats}")
    print(f"corpus: {len(CLAUSES)} clauses · " +
          " · ".join(f"{k}:{v}" for k, v in sorted(_BY_KIND.items())) + "\n")

    hits = channel = errors = 0
    confusion: Counter = Counter()
    flaky: List[str] = []

    for text, want in CLAUSES:
        got: List[str] = []
        via_content = 0
        for _ in range(a.repeats):
            try:
                reply = call_model([{"role": "system", "content": _system()},
                                    {"role": "user", "content": text}], tools)
                name, args = _first_tool_call(reply)
            except Exception as e:
                got.append(f"ERR:{type(e).__name__}")
                errors += 1
                continue
            ans = (args or {}).get("quantifier") if name == "quantify" else None
            if ans is None:
                ans = _recover(reply)
                if ans:
                    via_content += 1
                    channel += 1
            got.append(ans or "none")

        tally = Counter(got)
        majority, count = tally.most_common(1)[0]
        if count != len(got):
            flaky.append(text[:28])
        ok = majority == want
        hits += 1 if ok else 0
        if not ok:
            confusion[f"{want}->{majority}"] += 1
        chan = f"  [channel {via_content}/{len(got)}]" if via_content else ""
        print(f"   {'OK ' if ok else 'MISS'}  want {want:6} got {majority:6} "
              f"{count}/{len(got)}  {text[:44]!r}{chan}")

    n = len(CLAUSES)
    floor = max(_BY_KIND.values())
    print(f"\n── summary · harness=quantifier_probe · model={a.model} · n={a.repeats}")
    print(f"   CORRECT            : {hits}/{n}   <- the number that decides the idea")
    print(f"   always-one-answer  : {floor}/{n}   <- the floor; read the headline "
          f"against THIS")
    if confusion:
        print(f"   confusions         : " +
              " · ".join(f"{k} ×{v}" for k, v in confusion.most_common()))
    if channel:
        print(f"   CHANNEL            : {channel} answer(s) arrived in `content`")
    if flaky:
        print(f"   NOT UNANIMOUS      : {flaky} — undecided, not data")
    if errors:
        print(f"   errors             : {errors}")
    print("\n   Compare against atomicity_probe: 19/20 on routing, 4/10 on WHICH operator.")
    print("   If the quantifier answers better than 4/10 it is the better discriminator,")
    print("   and `single` vs `not` on the SAME object is the pair that matters most.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
