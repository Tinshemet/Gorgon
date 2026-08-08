"""INVERT THE QUESTION — ask per DECLARED KIND, so a non-thing cannot be named.

    PYTHONPATH=. python3 -m tests.bench.twopass.kindfirst

# WHY, FROM THE MEASUREMENT RATHER THAN FROM TASTE

Item 3 showed pass 1 CHUNKING the sentence instead of identifying objects:

    "create a vm named alpha"   ->   vm · named · alpha
    "create a network called lab and a vm named web, then put web on lab"
                                ->   a network · called lab · a vm · named web · web · lab

Asked *"list every distinct thing this sentence talks about"*, an OPEN question, every noun
phrase and participle qualifies — so it segments. 24 surplus rows across 14 requests, and the
type garbage downstream follows from it: once a name is a fragment like `the fleet label`, the
type question is being asked about something that is not an object and any answer is arbitrary.

⇒ **SO STOP ASKING AN OPEN QUESTION.** The kinds are a CLOSED SET the manifest declares. Ask,
  per kind, *"how many separate machines or groups of machines does this sentence talk
  about?"*, and only then ask for their names. **A verb cannot be a kind**, so `ping` and
  `named` stop being representable rather than being filtered out afterwards.

That is the only move with a track record here — make the wrong answer unrepresentable, never
repair it after ([[gorgon-detectors-not-producers]]).

# AND THE SECOND FIX, SMALLER AND ALSO MINE

The payload used to read `the sentence: {request}`, and rungs 5 and 7 declared a thing called
**`sentence`**. The scaffolding word became an object. The request is now passed bare.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    Y1  SURPLUS ROWS COLLAPSE, from 24 toward single digits. The count is fixed before any
        name is asked for, so the model cannot pad the list.
    Y2  `ping`, `named` AND `sentence` DISAPPEAR as declared objects. They can still appear as
        a name, but a name OF a machine is a smaller error than a machine that is a verb.
    Y3  RUNG 11 NEEDS THE COUNT TO BE 2 — all the machines, and the non-answering subset. If
        the count question says 1, the residual set is never asked for and the design fails
        at the first question. THIS IS THE CELL THAT MATTERS.
    Y4  SET RECOGNITION HOLDS AT OR ABOVE THE BASELINE's 13/14. The count question names
        groups explicitly, so it should help rather than hurt — unlike the paired fix, which
        collapsed it to 4/14.
    Y5  RISK, NAMED: asking per kind costs 6 calls before any naming, and a kind the sentence
        never mentions may still come back non-zero. Over-counting is the new failure mode to
        watch, and it would show up as surplus rows returning by another route.
"""
import argparse
from collections import Counter
from typing import Dict, List, Optional

from ..formula.legal import Board
from . import schema as S
from .pass1 import EXPECTED, grade

# ONE QUESTION PER KIND. The kind is named in the question, so the answer cannot be a verb.
COUNT_Q = (
    "How many separate {plural} does this request talk about?\n\n"
    "Count a GROUP of them as one. Count something only if the request really is about it. "
    "If the request does not mention {plural} at all, answer 0."
)

NAME_Q = (
    "The request talks about {n} {plural}. Give the request's own words for each one, in the "
    "order they appear. Give exactly {n}."
)

PLURAL = {"vm": "machines or groups of machines", "network": "networks",
          "snapshot": "snapshots", "template": "templates or golden images",
          "profile": "hardware profiles", "file": "files"}


def _count_schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "integer", "minimum": 0, "maximum": 6}}}


def _names_schema(n: int) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "array", "minItems": n, "maxItems": n,
                                      "items": {"type": "string", "minLength": 1}}}}


def run(request: str, board: Optional[Board] = None, model=None, temp=0.0,
        timeout=150, trace: Optional[List] = None) -> List[S.Declared]:
    from engines.channel import constrained

    board = board or Board()

    def ask(question: str, built: dict):
        try:
            # THE REQUEST IS PASSED BARE. A scaffolding word becomes an object otherwise.
            got = constrained(question, request, built,
                              model=model, temp=temp, timeout=timeout) or {}
            return got.get("answer")
        except Exception:
            return None

    rows: List[S.Declared] = []
    for kind in board.kinds:
        plural = PLURAL.get(kind, f"{kind}s")
        n = ask(COUNT_Q.format(plural=plural), _count_schema())
        if not n:
            continue
        if trace is not None:
            trace.append((kind, n))
        names = ask(NAME_Q.format(n=n, plural=plural), _names_schema(int(n))) or []
        for name in names:
            object_type = ask(S.TYPE_Q.format(name=name, suffix=S.SET_SUFFIX, nouns=S.nouns_offered(board)),
                              S.type_schema(board))
            if not object_type:
                continue
            pairs = ask(S.WHERE_Q.format(name=name),
                        S.where_schema(object_type, board)) or []
            where = {p["attribute"]: p["value"] for p in pairs
                     if isinstance(p, dict) and "attribute" in p}
            existence = ask(S.EXISTENCE_Q.format(name=name, new=S.NEW, existing=S.EXISTING),
                            S.existence_schema()) or S.EXISTING
            rows.append(S.declare_from(name, object_type, where, existence, board))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    board = Board()
    tally: Counter = Counter()
    print("=" * 104)
    print("KIND-FIRST · the question is asked per DECLARED KIND, so a verb cannot be an object")
    print("=" * 104)

    # ⇒ A DIAGNOSTIC LABEL, NOT A RULE, AND IT IS RUNG-DERIVED ON PURPOSE. These are words
    #   the rungs actually produced as declared objects. Nothing branches on this list and no
    #   mechanism consults it — it exists so a verb-as-object is VISIBLE in the output. If it
    #   ever starts filtering, it has become per-rung tuning and must be deleted.
    banned = {"ping", "named", "sentence", "launch", "clone", "pinging", "currently"}
    for n, want in sorted(EXPECTED.items()):
        if args.only and n != args.only:
            continue
        trace: List = []
        rows = run(want.request, board=board, model=args.model, trace=trace)
        g = grade(rows, want)
        print(f"\n{'─' * 104}\nrung {n} · “{want.request[:84]}”")
        print(f"    counted  {trace}")
        for row in rows:
            mark = "  ⇐ RESIDUAL" if row.residual else ""
            bad = "  ⇐ NOT A THING" if row.name.strip().lower() in banned else ""
            where = ", ".join(f"{k}={v}" for k, v in row.where.items()) or "—"
            print(f"      {row.name[:28]:<30} {row.object_type:<14} {where:<24} "
                  f"{row.existence}{mark}{bad}")
        junk = sum(1 for r in rows if r.name.strip().lower() in banned)
        print(f"    names {g['identities']}  conditions {g['conditions']}  "
              f"invented {g['invented']}  sets {g['sets']}  residual {g['residual']}  "
              f"rows {g['rows']} (want {want.rows})  non-things {junk}")
        tally["identities_ok"] += g["identities_ok"]
        tally["conditions_ok"] += g["conditions_ok"]
        tally["sets_ok"] += g["sets_ok"]
        tally["residual_ok"] += g["residual_ok"]
        tally["invented"] += g["invented"]
        tally["extra_rows"] += max(0, g["extra_rows"])
        tally["junk"] += junk
        tally["cells"] += 1

    c = max(tally["cells"], 1)
    print(f"\n{'=' * 104}")
    print(f"  named things found       {tally['identities_ok']}/{c}"
          f"          baseline 14/14")
    print(f"  SURPLUS rows declared    {tally['extra_rows']}"
          f"           baseline 24   ⇐ Y1")
    print(f"  NON-THINGS declared      {tally['junk']}"
          f"           ⇐ Y2, baseline had ping / named / sentence")
    print(f"  every condition found    {tally['conditions_ok']}/{c}"
          f"          baseline 12/14")
    print(f"  groups declared as sets  {tally['sets_ok']}/{c}"
          f"          baseline 13/14   ⇐ Y4")
    print(f"  conditions invented      {tally['invented']}"
          f"           baseline 36")
    print(f"  residual correct         {tally['residual_ok']}/{c}"
          f"          ⇐ rung 11 is the only TRUE, and Y3 rides on its count being 2")


if __name__ == "__main__":
    main()
