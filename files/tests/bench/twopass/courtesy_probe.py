"""courtesy_probe.py — DOES `please` CHANGE THE READING? The measurement N2 asked for.

    PYTHONPATH=. python3 -m tests.bench.twopass.courtesy_probe
    PYTHONPATH=. python3 -m tests.bench.twopass.courtesy_probe --only 7
    PYTHONPATH=. python3 -m tests.bench.twopass.courtesy_probe --no-lab

# ⇒⇒ THE ITEM, IN THE OPERATOR'S WORDS

N2 on [[gorgon-open-list]]: *"how do we deal with unnecessary words in a prompt like 'please'
or 'thank you', because they are pleasantries but can poison the model's judgement."*

And the list's own answer, which is why this file is a probe and not a stop-word list: **the
risk is not that a courtesy becomes a noun.** It is that a word with no referent still occupies
a slot, shifts the governing verb, or reads as MOOD — the one field the whole frame is derived
from. *"please delete the vms"* and *"delete the vms"* must produce the same reading, **and
nothing has ever asserted that they do.**

⇒ **THE MEASURE COMES BEFORE ANY FIX**, and the list says so: *"nobody knows whether this costs
  anything."* A `PLEASANTRIES` constant would be a hand-written English list — an OPEN class,
  competing with a competence the model already has — which is H1-3's defect and the thing the
  Encyclopedia's rule forbids outright. So this measures; it does not repair.

# ⇒⇒ THE DESIGN POINT THAT MAKES IT MEAN ANYTHING — AND ONE RUN CANNOT DO IT

**A literal-versus-filler diff, run once, measures the courtesy AND the model's own
nondeterminism together, and cannot tell you which you are looking at.**
[[ladder-is-not-a-feedback-loop]]: *temp 0 is NOT deterministic; never diagnose from n=1.*
[[gorgon-ladder-noise-exceeds-the-effect]]: run model-stability FIRST, before trusting any cell.

⇒ So every rung is read THREE times:

        literal, sample 1     ─┐
        literal, sample 2      ├─ these two differing is THE NOISE FLOOR
        filler                ─┘   this differing from sample 1 is THE CANDIDATE EFFECT

  **A courtesy difference is reported as an effect only on a rung whose two literal readings
  were byte-identical.** On an unstable rung the arms are not comparable and the probe says so
  rather than counting it — which is the discipline that was missing when a ±2 cell was being
  read as progress.

⇒ ⚠ **AND THE SEED IS HELD, NOT VARIED, WHICH IS THE OPPOSITE OF THE USUAL RULE HERE.**
  [[gorgon-seed-dependence]] says vary `PYTHONHASHSEED` because two runs of one command are two
  samples of a variable nobody declared — and that is right when the question is *how good is
  this*. **Here the question is *does one added word change anything*, so everything except
  that word must be held still**, and the seed is part of everything. Run the whole probe again
  under a different `PYTHONHASHSEED` to check the floor itself is stable; do not vary it
  between the arms of one comparison.

# ⇒ WHAT COUNTS AS "THE READING", AND WHY THE ASK TEXT IS NOT IN IT

The reading is what was BUILT: the declarations, the operations, the conditions and the goals,
plus the outcome. Those are the things a courtesy could displace.

⇒ **THE ASK AND BOUNCE PROSE IS DELIBERATELY EXCLUDED FROM THE BYTE COMPARISON**, because it
  QUOTES THE REQUEST — every filler arm would differ on the courtesy words themselves, and the
  probe would report a 14/14 effect that is entirely an artifact of the question being asked.
  Their COUNT is compared instead, and a change in it is reported separately.
"""
import argparse
from typing import Dict, List, NamedTuple, Optional, Tuple

from planner.formula.legal import Board
from orchestrator.seam import pass1
from orchestrator.seam.pipeline import run
from tests.bench.mutate import filler
from tests.bench.twopass.metrics import Lab


class Reading(NamedTuple):
    """What was BUILT from a request. Compared byte-exact; prose is not in it."""
    handles: Tuple[str, ...]
    operations: Tuple[Tuple, ...]
    conditions: Tuple[str, ...]
    goals: Tuple[str, ...]
    outcome: str
    asks: int
    bounces: int

    @property
    def built(self) -> Tuple:
        """The comparison key — everything except the counts of prose."""
        return (self.handles, self.operations, self.conditions, self.goals, self.outcome)

    def line(self) -> str:
        return (f"{self.outcome:6} ops={list(self.operations) or '—'} "
                f"decl={list(self.handles) or '—'} goals={list(self.goals) or '—'}")


def reading_of(got) -> Reading:
    """One `pipeline.Run` reduced to what a courtesy could have displaced."""
    return Reading(
        handles=tuple(got.handles),
        operations=tuple((o.operator, o.on, o.value) for o in got.operations),
        conditions=tuple(sorted(str(c) for c in (got.conditions or ()))),
        goals=tuple(sorted(str(g) for g in (got.goals or ()))),
        outcome=str(got.outcome),
        asks=len(got.asks or ()),
        bounces=len(got.bounces or ()),
    )


class Cell(NamedTuple):
    n: int
    request: str
    polite: str
    a: Reading
    b: Reading          # the second literal sample — the floor
    c: Reading          # the filler arm

    @property
    def stable(self) -> bool:
        """Did the SAME request read the same way twice? If not, nothing here is comparable."""
        return self.a.built == self.b.built

    @property
    def moved(self) -> bool:
        return self.a.built != self.c.built

    @property
    def prose_moved(self) -> bool:
        return (self.a.asks, self.a.bounces) != (self.c.asks, self.c.bounces)


def measure(only: Optional[int] = None, no_lab: bool = False,
            model: Optional[str] = None) -> List[Cell]:
    """Three readings per rung: literal, literal again, and the courtesy arm."""
    board = Board()
    world = None if no_lab else Lab()
    out: List[Cell] = []
    for n, want in sorted(pass1.EXPECTED.items()):
        if only and n != only:
            continue
        polite = filler(want.request)
        print(f"  rung {n:2} …", flush=True)
        a = reading_of(run(want.request, board=board, world=world, model=model))
        b = reading_of(run(want.request, board=board, world=world, model=model))
        c = reading_of(run(polite, board=board, world=world, model=model))
        out.append(Cell(n, want.request, polite, a, b, c))
    return out


def report(cells: List[Cell]) -> int:
    """Print the finding. Returns the number of rungs where a courtesy moved a STABLE reading."""
    stable = [c for c in cells if c.stable]
    noisy = [c for c in cells if not c.stable]
    effect = [c for c in stable if c.moved]
    prose = [c for c in stable if not c.moved and c.prose_moved]

    print("\n" + "=" * 100)
    print("THE NOISE FLOOR — the same request, read twice")
    print("=" * 100)
    print(f"  {len(stable)} of {len(cells)} rungs read IDENTICALLY twice in a row")
    for c in noisy:
        print(f"\n  ⚠ rung {c.n} IS UNSTABLE — the courtesy arm cannot be read for it")
        print(f"      sample 1  {c.a.line()}")
        print(f"      sample 2  {c.b.line()}")

    print("\n" + "=" * 100)
    print("THE COURTESY — a stable rung, wrapped in politeness")
    print("=" * 100)
    if not stable:
        print("  nothing to say: no rung held still, so nothing here is attributable")
    for c in stable:
        mark = "MOVED " if c.moved else "same  "
        print(f"  {mark} rung {c.n:2}  {c.polite[:78]}")
        if c.moved:
            print(f"           literal  {c.a.line()}")
            print(f"           polite   {c.c.line()}")
        elif c.prose_moved:
            print(f"           the program is identical; what a person is TOLD is not — "
                  f"asks {c.a.asks}->{c.c.asks}, bounces {c.a.bounces}->{c.c.bounces}")

    print("\n" + "=" * 100)
    print(f"  {len(effect)} of {len(stable)} STABLE rungs changed their reading when made polite")
    print(f"  {len(prose)} more kept the same program and changed what the operator is told")
    print(f"  {len(noisy)} rungs were too unstable to ask")
    if noisy:
        print(f"\n  ⚠ THE FLOOR IS NOT ZERO, so the number above is a CEILING on the courtesy's "
              f"cost,\n    not a measurement of it — those {len(noisy)} rungs move on their own.")
    print("  ⚠ ONE SEED, ONE SAMPLE PAIR. Re-run under another PYTHONHASHSEED before "
          "believing\n    a small number here; the floor itself is what has to be stable.")
    return len(effect)


def main() -> int:                                              # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--no-lab", action="store_true")
    args = ap.parse_args()
    print("=" * 100)
    print("N2 · DOES A COURTESY CHANGE THE READING?"
          f"{'  ·  NO LAB' if args.no_lab else '  ·  with a lab'}")
    print("  three readings per rung: literal, literal again (the floor), then polite")
    print("=" * 100)
    return report(measure(only=args.only, no_lab=args.no_lab, model=args.model))


if __name__ == "__main__":                                      # pragma: no cover
    raise SystemExit(0 if main() == 0 else 0)
