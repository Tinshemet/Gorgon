"""door_probe.py — WHERE THE LADDER SENDS EACH KEYED REQUEST, AND WHICH WAY ITS MISSES GO.

    PYTHONPATH=. python3 -m tests.bench.door_probe            # the fixture lab
    PYTHONPATH=. python3 -m tests.bench.door_probe --lab      # the REAL lab, if one is running
    PYTHONPATH=. python3 -m tests.bench.door_probe --misses   # only what it got wrong

# ⇒⇒ IT REPORTS BY DIRECTION AND NEVER AS ONE NUMBER, AND THAT RULE PREDATES THE RUN

`door_key`'s scoring rules were written before a line of the ladder existed, and the first of
them is that an accuracy figure over these rows would average a question against a destruction.
Four cells are named CRITICAL, one of them measured rather than feared: routing `create a vm`
UP the ladder reaches an unfiltered `count(vm) = 1`, satisfied against a real lab by deleting
eight machines.

    ⚠ CRITICAL   any lab -> CHAT · PROGRAM -> TOOL · TOOL -> PROGRAM · GOVERNANCE -> lab
      up / down  the ladder is ordered by WHO VERIFIED THE ARTIFACT, so a direction says
                 whether the door reached past the verification it had or fell short of it
      recorded   a row the key marked `hard` still prints, and is counted apart

# ⇒⇒ THE TWO INPUTS ARE DECLARED, BECAUSE WITHOUT THEM THE MEASUREMENT MEANS SOMETHING ELSE

    THE WORLD    `door_key.FIXTURE_MEMBERS` — the lab these rows were written against. With no
                 world at all, `db` and `grubnash` are the same shape to the door, and the
                 whole ASK rung fires on every request naming a machine
    THE LIBRARY  `door_key.FIXTURE_PROCEDURES` — rung 2 collides by construction against an
                 empty library, so a PROCEDURE row would pass or fail for the wrong reason

⇒ **BOTH ARE STUBS AND BOTH ARE PRINTED**, so a reader never has to guess which lab produced a
  number. `--lab` swaps the fixture for whatever is actually running, which is the honest run
  and the one that needs a machine.

# ⇒ WHAT THIS CANNOT TELL YOU

It measures ROUTE — did the door pick the right kind of destination. It says nothing about
READ (the seam's own probes own that) and nothing about RESOLVE, which is whether what the
destination then does is right. Those are the operator's three, and only one of them is here.
"""
import sys
from collections import Counter
from typing import List, Optional, Tuple

from orchestrator.door import facts, route
from tests.bench import door_key as K
from tests.bench.rungs import RUNGS


class FixtureWorld:
    """The lab the key's rows were written against. `select` is never reached from the door."""

    def __init__(self, names: Tuple[str, ...]):
        self._names = list(names)

    def names(self) -> List[str]:
        return list(self._names)

    def select(self, *a, **k) -> list:
        return []


def _world(use_lab: bool):
    """The fixture, or the real lab when asked for one. Returns (world, what to print)."""
    if not use_lab:
        return FixtureWorld(K.FIXTURE_MEMBERS), f"fixture ({len(K.FIXTURE_MEMBERS)} members)"
    try:
        from orchestrator.ai.chat.shortcuts.plan import Plan
        got = Plan._seam_world()
    except Exception as e:                                        # pragma: no cover
        return None, f"⚠ no lab — {type(e).__name__}"
    if got is None:                                               # pragma: no cover
        return None, "⚠ no lab — every bare name stays kindless"
    return got, "THE REAL LAB"


def rows() -> List[Tuple[str, str, bool, str]]:
    """Every keyed request: (text, keyed destination, hard, where it came from)."""
    out = [(k.text, k.goes, k.hard, "control") for k in K.CONTROLS]
    out += [(r.goal, K.RUNG_DESTINATION[r.n], False, f"rung {r.n}") for r in RUNGS]
    return out


def run(use_lab: bool = False, stub_library: bool = True):
    """Route every keyed row. Returns (results, what the world was, what the library was)."""
    world, world_says = _world(use_lab)
    library_says = "the real store"
    if stub_library:
        import planner.procedures as P
        stored = list(P.LIBRARY.names())
        # ⇒ ADDED TO whatever is really stored, never substituted for it — a real procedure
        #   that would change a routing is a finding, not noise to be hidden.
        P.LIBRARY.names = lambda: sorted(set(stored) | set(K.FIXTURE_PROCEDURES))
        library_says = f"fixture ({', '.join(K.FIXTURE_PROCEDURES)})" + \
                       (f" + {len(stored)} stored" if stored else "")

    out = []
    for text, keyed, hard, where in rows():
        got = route(facts(text, world=world))
        out.append((text, keyed, got, hard, where))
    return out, world_says, library_says


def report(results, world_says: str, library_says: str, misses_only: bool = False) -> int:
    """Print the run and return the exit code. 1 when a CRITICAL cell fires on a keyed row."""
    print(f"\n  world    {world_says}")
    print(f"  library  {library_says}")

    hit = [r for r in results if r[1] == r[2].goes]
    miss = [r for r in results if r[1] != r[2].goes]
    directions = Counter(K.direction(keyed, got.goes) for _, keyed, got, _, _ in miss)
    critical = [r for r in miss if K.direction(r[1], r[2].goes) == "CRITICAL"]
    critical_soft = [r for r in critical if r[3]]
    critical_hard = [r for r in critical if not r[3]]

    if not misses_only:
        print(f"\n── EVERY ROW ───────────────────────────────────────────────────────")
        for text, keyed, got, hard, where in results:
            mark = "  " if keyed == got.goes else "->"
            flag = K.direction(keyed, got.goes)
            note = "" if keyed == got.goes else f"  [{flag}]"
            print(f"  {keyed:10} {mark} {got.goes:10} {text[:54]:54}{note}"
                  + ("  ⚠hard" if hard else ""))
            print(f"  {'':24} [dim]{got.rung}[/dim]".replace("[dim]", "").replace("[/dim]", ""))

    print(f"\n── WHERE THE MISSES WENT ───────────────────────────────────────────")
    for text, keyed, got, hard, where in miss:
        print(f"  {K.direction(keyed, got.goes):10} {keyed} -> {got.goes:10} {text}"
              + ("   ⚠hard" if hard else ""))
        print(f"  {'':10} the rung that said so: {got.rung}")

    print(f"\n── THE TALLY, BY DIRECTION AND NEVER AS ONE NUMBER ─────────────────")
    print(f"  {len(hit)} of {len(results)} rows reached the keyed destination")
    for name in ("CRITICAL", "up", "down", "off-ladder"):
        if directions.get(name):
            print(f"  {directions[name]:3} {name}")
    print(f"  {sum(1 for r in miss if r[3])} of the misses are rows the key marked HARD "
          f"— recorded decisions, not surprises")

    if critical_hard:
        print(f"\n  ⚠⚠ {len(critical_hard)} CRITICAL miss(es) on rows the key did NOT mark hard:")
        for text, keyed, got, _, _ in critical_hard:
            print(f"     {keyed} -> {got.goes}   {text}")
    if critical_soft:
        print(f"\n  ⚠ {len(critical_soft)} critical miss(es) on HARD rows — expected, and still "
              f"critical:")
        for text, keyed, got, _, _ in critical_soft:
            print(f"     {keyed} -> {got.goes}   {text}")
    if not critical:
        print(f"\n  no CRITICAL cell fired — nothing was served that should have been asked "
              f"about, and nothing lab-shaped reached the model ungated")
    return 1 if critical_hard else 0


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    argv = list(sys.argv[1:] if argv is None else argv)
    results, world_says, library_says = run(use_lab="--lab" in argv)
    return report(results, world_says, library_says, misses_only="--misses" in argv)


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
