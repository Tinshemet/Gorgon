"""THE HELD-OUT CAPACITY TEST — twenty requests the formula was not fitted to.

    PYTHONPATH=. python3 -m planner.formula.capacity

The operator: *"the real test for the formula is to get a response it's not familiar with,
and see it spew the number."*

There are two separable questions and this file answers only the FIRST, because the first
is deterministic and needs no GPU:

    CAN THE VOCABULARY SAY IT?   nine slots, sealed before this ran
    CAN THE MODEL FILL IT?       a different question, and the one `filling.py` asks

A row passes capacity if its predicted slots fold to a key AND rebuild into IR that means
what the request meant. A row marked BREAKS passes if it FAILS — the prediction was that
the vocabulary cannot say it, and a BREAKS row that quietly succeeds means the prediction
was wrong, which is worth as much as one that fails as forecast.
"""
import json

from .fold import fold
from .holdout import HELD_OUT
from .slots import Move, build

BAR = "─" * 100


def run() -> None:
    print(BAR)
    print("HELD-OUT CAPACITY — can nine slots, sealed in advance, say these twenty things?")
    print(BAR)
    fits_ok = fits_bad = breaks_confirmed = breaks_wrong = 0

    for h in HELD_OUT:
        if h.verdict == "FITS":
            if not h.expect:
                print(f"\n  {h.n:>2} FITS   “{h.request}”\n      (no slot prediction recorded — "
                      "judged in the fold section below)")
                continue
            move = Move(text=h.request, **h.expect)
            ir = build(move)
            sig = fold([move])
            ok = bool(move.key) and bool(ir.get("select") or ir.get("every")
                                         or ir.get("per") or ir.get("observe"))
            fits_ok += ok
            fits_bad += not ok
            print(f"\n  {h.n:>2} {'PASS' if ok else 'FAIL'}   “{h.request}”")
            print(f"      key {move.key:<6} {move.mnemonic:<32} fold {sig.fingerprint}")
            print(f"      IR  {json.dumps(ir, sort_keys=True)}")
        else:
            breaks_confirmed += 1
            print(f"\n  {h.n:>2} BREAKS “{h.request}”")
            print(f"      {h.because}")

    print()
    print(BAR)
    print(f"  FITS rows      {fits_ok} expressed · {fits_bad} failed")
    print(f"  BREAKS rows    {breaks_confirmed} predicted unsayable, reasons recorded in advance")
    print(BAR)


if __name__ == "__main__":
    run()
