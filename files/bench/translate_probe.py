"""
translate_probe.py — show what the translator actually does to each rung's paraphrase.

The ladder tells you whether a rung passed. This tells you WHY, which is the part you
need while tuning a prompt: it prints each rung's paraphrase next to the canonical form
the translator produced, so a bad restatement is visible in seconds instead of after a
25-minute ladder run.

Deliberately NOT a test and NOT a checker — it asserts nothing and grades nothing. It
exists so the translation can be READ. Judging a restatement automatically would mean
writing a second vocabulary to judge it against, which is the thing this whole line of
work is trying to delete.

Run:  PYTHONPATH=. python3 -m bench.translate_probe            # every rung
      PYTHONPATH=. python3 -m bench.translate_probe -r 4 -r 6  # some rungs
      PYTHONPATH=. python3 -m bench.translate_probe --literal   # the literal wording too
"""
import argparse
import sys

from orchestrator.ai.planner.translator import normalize_goal

from .ladder import BENCH_MODEL, make_call_model
from .rungs import RUNGS


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Show the translator's output per rung")
    p.add_argument("-r", "--rung", type=int, action="append", help="rung(s) (default: all)")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("--literal", action="store_true",
                   help="also translate the LITERAL wording — it should come back "
                        "essentially unchanged; if it doesn't, the translator is "
                        "rewriting goals that already worked, which is a regression risk "
                        "for the literal column.")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    call_model = make_call_model(a.model, a.temp, 300)
    print(f"translate probe · model={a.model} temp={a.temp}\n")

    for rung in rungs:
        print(f"── rung {rung.n} ({rung.name})")
        for kind, text in ([("literal", rung.goal)] if a.literal else []) + \
                          ([("paraphrase", rung.paraphrase)] if rung.paraphrase else []):
            out, clauses = normalize_goal(text, call_model)
            print(f"   {kind:10} in : {text}")
            if clauses is None:
                print(f"   {'':10} out: (unchanged — already canonical, or translation failed)")
            else:
                for i, c in enumerate(clauses, 1):
                    print(f"   {'':10} {i:>3}. {c}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
