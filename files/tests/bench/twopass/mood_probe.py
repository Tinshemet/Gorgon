"""CAN CLOSED CLASSES TELL AN ORDER FROM A QUESTION — scored against a key written first.

    PYTHONPATH=. python3 -m tests.bench.twopass.mood_probe
    PYTHONPATH=. python3 -m tests.bench.twopass.mood_probe --controls   # the hard half only

# ⇒⇒ WHAT IS BEING MEASURED, AND THE TWO GRAINS ARE NOT THE SAME CLAIM

    PROJECTION   order · question · neither, over the whole sentence. This is what a caller
                 would route on, and it is the number that matters.
    TYPE         the speech act of each clause. Strictly harder, and mostly UNSETTLED today —
                 `DECLARATION` and `COMMISSIVE` have no rules at all yet.

Reporting only the projection would let a reader look finished while five of eight sentence
types are unread. Reporting only the type would call an abstention a failure. So both, always,
side by side.

# ⇒ THE CONTROL THAT MAKES IT A MEASUREMENT RATHER THAN A DEMO

**THE KEY WAS COMMITTED BEFORE THE READER EXISTED** (`tests/bench/sentence_key.py`), and it
imports nothing it grades. It caught the first rule draft — *"inversion + a manifest verb ->
an order"* would have served *"is alpha running?"* — before a line of `speech_act.py` was
written. The arms are the regression; **the CONTROLS are the measurement**, and a reader can
score 56/56 on the arms while being nothing but a question-mark detector.

⚠ AND THE STANDING CEILING: the controls are sentences I wrote. A perfect score is a claim
  about the rules, never about English. A1 on [[gorgon-open-list]] — held-out prompts, the
  operator's — is the only thing that changes that.
"""
import argparse
from collections import Counter
from typing import Dict, List, Tuple

from orchestrator.seam import speech_act as SA
from planner.formula.legal import Board
from tests.bench import sentence_key as KEY
from tests.bench.mutate import apply as mutate
from tests.bench.rungs import RUNGS


def _vocabularies_agree() -> List[str]:
    """The key and the reader must name the types with the SAME STRINGS, and prove it.

    They are declared separately on purpose — production must not import from `tests/`, and a
    key sharing a symbol with what it grades is not a key. Agreement by value is the price of
    that, and an unasserted agreement is how twins start.
    """
    mismatched = []
    for name in ("DIRECTIVE_ACT", "DIRECTIVE_INFORM", "ASSERTIVE", "DECLARATION",
                 "META_CONTROL", "EXPRESSIVE", "COMMISSIVE"):
        a, b = getattr(KEY, name), getattr(SA, name, None)
        if a != b:
            mismatched.append(f"{name}: key={a!r} reader={b!r}")
    return mismatched


def arms(board: Board) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
    """Every rung × every arm, scored on the PROJECTION. Returns (per-arm tally, misses)."""
    tally: Dict[str, Tuple[int, int]] = {}
    misses: List[str] = []
    for arm in KEY.ARM_VERDICT:
        right = 0
        for r in RUNGS:
            text = r.goal if arm == "literal" else mutate(r.goal, arm)
            want = KEY.expected(r.n, arm)
            got = SA.verdict(text, board)
            if got == want:
                right += 1
            else:
                misses.append(f"  {arm:8} rung {r.n:2}  want {want:8} got {got:8}  {text[:64]}")
        tally[arm] = (right, len(RUNGS))
    return tally, misses


def controls(board: Board):
    """The hand-written half — where the design is tested rather than regressed."""
    proj_right = type_right = type_unsettled = 0
    rows = []
    for k in KEY.CONTROLS:
        got_acts = [a for _, a in SA.read(k.text, board)]
        got_verdict = SA.verdict(k.text, board)
        ok_proj = got_verdict == k.says
        proj_right += ok_proj
        # ⇒ TYPE IS SCORED AS A SET OVER THE CLAUSES, not positionally: the key's clause cut and
        #   `clauses_of`'s cut are independent, and demanding they align would measure the
        #   splitter rather than the reader.
        want_types, got_types = set(k.clauses), {a for a in got_acts if a}
        if want_types == got_types:
            type_right += 1
        elif not got_types:
            type_unsettled += 1
        rows.append((k, got_verdict, got_acts, ok_proj, want_types == got_types))
    return rows, proj_right, type_right, type_unsettled


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", action="store_true", help="the controls only")
    ap.add_argument("--verbose", action="store_true", help="every control, not only misses")
    args = ap.parse_args(argv)

    bad = _vocabularies_agree()
    if bad:
        print("⚠ KEY AND READER DISAGREE ON THE TYPE NAMES:")
        print("\n".join("   " + b for b in bad))
        return 1

    board = Board()

    if not args.controls:
        print("── THE ARMS · projection · the REGRESSION half ──────────────────────")
        tally, misses = arms(board)
        for arm, (right, total) in tally.items():
            flag = "" if right == total else "   ⚠"
            print(f"  {arm:8} -> {KEY.ARM_VERDICT[arm]:8} {right:2}/{total}{flag}")
        if misses:
            print("\n  MISSES")
            print("\n".join(misses))
        total_right = sum(r for r, _ in tally.values())
        total_all = sum(t for _, t in tally.values())
        print(f"\n  ARMS {total_right}/{total_all}")

    print("\n── THE CONTROLS · the MEASUREMENT half ──────────────────────────────")
    rows, proj_right, type_right, type_unsettled = controls(board)
    for k, got_verdict, got_acts, ok_proj, ok_type in rows:
        if ok_proj and ok_type and not args.verbose:
            continue
        mark = "ok  " if ok_proj else "MISS"
        hard = " ⚠hard" if k.hard else ""
        print(f"  [{mark}] want {k.says:8} got {got_verdict:8}{hard}\n"
              f"         {k.text}\n"
              f"         key  {'·'.join(k.clauses)}\n"
              f"         read {'·'.join(str(a) for a in got_acts)}")
    print(f"\n  CONTROLS  projection {proj_right}/{len(rows)}"
          f"   ·   type {type_right}/{len(rows)}"
          f"   ·   fully unsettled {type_unsettled}")

    # ⇒ WHICH TYPES THE READER CAN ACTUALLY PRODUCE. A type the key covers and the reader has
    #   never once emitted is a rule that does not exist, and that is worth seeing as a number
    #   rather than inferring from misses.
    produced = Counter(a for k, _, acts, _, _ in rows for a in acts if a)
    print("\n  TYPES THE READER EMITTED")
    for t in KEY.TYPES:
        n = produced.get(t, 0)
        note = "   ⚠ NO RULE — nothing ever produces this" if not n else ""
        print(f"    {t:18} {n:2}{note}")
    return 0


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
