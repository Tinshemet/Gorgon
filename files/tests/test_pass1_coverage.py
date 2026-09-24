"""test_pass1_coverage.py — a GENERAL regression suite over EVERY pass-1 structural feature.

`tests/bench/structure_map.py` is the SSOT of "everything a sentence is built from" — 39
features across PHRASE / CLAUSE / TURN / SURFACE. This suite pins the DETERMINISTIC reading of
each (scan + speech_act cost no model call, so it is fast and reproducible) against a frozen
snapshot, `tests/bench/pass1_coverage_snapshot.json`.

⇒ WHY A SNAPSHOT AND NOT PER-FEATURE ASSERTIONS. The map already carries the hand-authored
  status of each feature (covered / hole / partial). What the code actually READS is a separate,
  moving thing — and that is what a regression is. Pinning the live reading of all 39 catches
  drift in BOTH directions:
    · a COVERED feature that regresses to unread            -> RED (a real regression)
    · a HOLE that the code newly closes                     -> RED (green-means-progress: a hole
                                                              moved, so update the snapshot + map)
  Either way the operator is told the moment pass-1's behaviour changes anywhere.

⇒ Two standing invariants on top of the snapshot, plus the marathon-found real-request defects
  (PP over-grab, verb-glob, temporal) pinned so the pass-1 fixes flip them and cannot regress.

    PYTHONPATH=. python3 -m pytest tests/test_pass1_coverage.py -q
    PYTHONPATH=. python3 tests/test_pass1_coverage.py            # human summary
"""
import json
import os

from tests.bench import structure_map as SM
from orchestrator.languages.english.seam import scan as SC, speech_act as SA
from planner.formula.legal import Board

_SNAP_PATH = os.path.join(os.path.dirname(__file__), "bench", "pass1_coverage_snapshot.json")
SNAP = json.load(open(_SNAP_PATH, encoding="utf-8"))
_BOARD = Board()


def _reading(example: str) -> dict:
    """The free readers' deterministic take — no model call. `anchors`/`unread` are token SETS,
    so they are sorted to stay stable under hash ordering; `acts` keep clause order."""
    try:
        return {"acts": [a for _, a in SA.read(example, _BOARD)],
                "anchors": sorted(SC.anchors_in(example, _BOARD)),
                "unread": sorted(SC.uncovered(example, [], _BOARD))}
    except Exception as e:                                    # a reader crash IS a regression
        return {"error": f"{type(e).__name__}: {e}"}


def _norm(reading: dict) -> dict:
    """Normalise a stored snapshot reading the same way `_reading` returns one."""
    if "error" in reading:
        return reading
    return {"acts": reading.get("acts", []),
            "anchors": sorted(reading.get("anchors", [])),
            "unread": sorted(reading.get("unread", []))}


# ── the snapshot: every feature reads exactly as it did when this was frozen ──────────────────

def test_every_feature_reads_as_snapshotted():
    drift = []
    for f in SM.MAP:
        assert f.name in SNAP, f"feature {f.name!r} is new — add it to the snapshot"
        want, got = _norm(SNAP[f.name]["reading"]), _reading(f.example)
        if got != want:
            kind = "PROGRESS? a hole may have closed" if SNAP[f.name]["hole"] else "REGRESSION"
            drift.append(f"[{kind}] {f.name!r} ({f.level})\n      was  {want}\n      now  {got}")
    assert not drift, ("pass-1 reading drifted on %d feature(s):\n  " % len(drift)) + "\n  ".join(drift)


# ── standing invariants ──────────────────────────────────────────────────────────────────────

def test_covered_features_still_read():
    """A feature the map calls COVERED must read something (acts or anchors). If it now reads
    nothing it has silently regressed to a hole — which the snapshot also catches, but this names
    it as the specific failure it is."""
    broken = [f.name for f in SM.MAP
              if not SNAP[f.name]["hole"] and not (_reading(f.example)["acts"] or _reading(f.example)["anchors"])]
    assert not broken, f"COVERED features that now read nothing (regressed to a hole): {broken}"


def test_hole_set_only_shrinks():
    """The map's declared hole set may lose members (a hole closed) but never gain one — a new
    declared hole is a regression written into the map itself."""
    now = {f.name for f in SM.holes()}
    was = {n for n, v in SNAP.items() if v["hole"]}
    added = now - was
    assert not added, f"NEW holes declared in the map since the snapshot: {sorted(added)}"


def test_dangerous_hole_set_is_known():
    """The holes that change WHAT RUNS are the highest-stakes; a new one must never appear
    unannounced."""
    now = {f.name for f in SM.holes() if f.danger}
    was = {n for n, v in SNAP.items() if v["hole"] and v["danger"]}
    added = now - was
    assert not added, f"NEW dangerous holes (change what runs) since the snapshot: {sorted(added)}"


# ── marathon-found real-request defects, pinned so a pass-1 fix flips them ────────────────────
#   Each maps an input to the tokens the free readers leave UNREAD today. When the fix lands the
#   set shrinks and the test goes red on purpose — update the pin and record the win.

MARATHON_DEFECTS = {
    "remove beta from lab":   ["beta", "lab"],           # PP over-grab — source `lab` unread
    "run uptime on gamma":    ["gamma", "uptime"],       # PP over-grab — target
    "move beta to dmz":       ["beta", "dmz", "move"],   # verb-glob — `move` not a known verb
    "stop web at 9pm":        ["9pm", "web"],            # temporal boundary — `9pm` unread
    "add db to lab":          ["db", "lab"],             # destination `lab` unread
    "snapshot the container": ["container"],             # clean input, `container` kind unread
}


def test_marathon_defects_hold_their_known_shape():
    moved = []
    for example, unread in MARATHON_DEFECTS.items():
        got = _reading(example).get("unread")
        if got != sorted(unread):
            moved.append(f"{example!r}: known-unread {sorted(unread)} -> now {got} "
                         f"(fixed? update MARATHON_DEFECTS and log the win)")
    assert not moved, "a marathon defect changed shape:\n  " + "\n  ".join(moved)


if __name__ == "__main__":
    holes = sum(1 for v in SNAP.values() if v["hole"])
    danger = sum(1 for v in SNAP.values() if v["hole"] and v["danger"])
    print(f"pass-1 coverage: {len(SM.MAP)} features · {holes} holes · {danger} change what runs")
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ok   {name}")
            except AssertionError as e:
                print(f"  FAIL {name}\n       {str(e)[:400]}")
