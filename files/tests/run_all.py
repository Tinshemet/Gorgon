#!/usr/bin/env python3
"""
run_all.py — run EVERY suite and report one verdict.

WHY THIS EXISTS. On 2026-07-26 two suites were found rotted:
`test_root_predicate` had been failing 13/15 for a day (a behaviour change in 0aba77b
that nobody updated it for) and `test_epistemic_acceptance` broke the same morning and
was not noticed for hours. Neither was caught, because there was no way to run
everything: pytest collects only the handful of files written in pytest style, and the
other ~28 are hand-rolled scripts invoked one at a time by name. A suite that stopped
being mentioned stopped being run, and "the full suite is green" meant "the suites I
happened to list are green".

The suites are split into three kinds, and the split is the point:

  PYTEST      — files written with pytest fixtures/asserts. Run as one pytest invocation.
  STANDALONE  — hand-rolled scripts that print "N/M passed" and exit non-zero on failure.
  LIVE        — needs a running orchestrator and/or ollama. NOT run by default: it would
                fail on a clean checkout for reasons that are not defects. `--live` opts in.

Nothing is skipped silently. A suite that produces no recognisable result is reported as
NO-RESULT and fails the run, so a suite cannot rot by becoming unreadable either.

Usage:
    PYTHONPATH=. python3 tests/run_all.py           # everything except LIVE
    PYTHONPATH=. python3 tests/run_all.py --live    # include the live-integration suites
    PYTHONPATH=. python3 tests/run_all.py -k script # only suites whose name matches
"""
import argparse
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

# Needs a live orchestrator / ollama — opt in with --live.
LIVE = {"test_api"}

# Not suites: harnesses, fixtures and manual tools that live alongside the tests.
NOT_SUITES = {"shared", "renderer", "log_runner", "probe_tools", "chat_harness",
              "sim_live", "sim_autonomous", "smoke_commands", "smoke_tools",
              "bench_reasoning"}

_RESULT = re.compile(r"(\d+)\s*/\s*(\d+)\s+passed")


def _discover():
    """(pytest_files, standalone_files, live_files) — by how each declares itself.

    The discriminator is a `__main__` block, NOT an `import pytest`. A hand-rolled suite
    runs itself and prints its own tally; a pytest suite has no entry point and does
    nothing when executed as a script. Classifying on the import gets this wrong both
    ways — test_active_library_remote is pytest-style and never imports pytest, while
    test_contract has bare `def test_` functions but is a script with its own main.
    """
    pyt, alone, live = [], [], []
    for fn in sorted(os.listdir(_HERE)):
        if not fn.startswith("test_") or not fn.endswith(".py"):
            continue
        stem = fn[:-3]
        if stem in NOT_SUITES:
            continue
        bucket = live if stem in LIVE else None
        if bucket is None:
            src = open(os.path.join(_HERE, fn)).read()
            bucket = alone if "__main__" in src else pyt
        bucket.append(stem)
    return pyt, alone, live


def _run_standalone(stem):
    """(ok, label) for one hand-rolled suite."""
    env = dict(os.environ, PYTHONPATH=_ROOT)
    try:
        p = subprocess.run([sys.executable, os.path.join(_HERE, stem + ".py")],
                           capture_output=True, text=True, timeout=600, env=env, cwd=_ROOT)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (600s)"
    out = p.stdout + p.stderr
    hits = _RESULT.findall(out)
    if not hits:
        first = next((l for l in out.splitlines() if "Error" in l or "error" in l), "")
        return False, f"NO-RESULT (exit {p.returncode}) {first[:60]}"
    ok, total = hits[-1]
    return (ok == total and p.returncode == 0), f"{ok}/{total} passed"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run every Gorgon suite")
    ap.add_argument("--live", action="store_true", help="also run suites needing a server/ollama")
    ap.add_argument("-k", "--filter", default="", help="only suites whose name contains this")
    a = ap.parse_args(argv)

    pyt, alone, live = _discover()
    keep = lambda xs: [x for x in xs if a.filter in x]
    pyt, alone = keep(pyt), keep(alone)
    live = keep(live) if a.live else []

    failures = []
    print(f"gorgon suites · {len(pyt)} pytest · {len(alone)} standalone"
          f" · {len(live) if a.live else 0} live"
          f"{'' if a.live else f' ({len(LIVE)} live SKIPPED — use --live)'}\n")

    if pyt:
        env = dict(os.environ, PYTHONPATH=_ROOT)
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", *[f"tests/{s}.py" for s in pyt]],
                           capture_output=True, text=True, cwd=_ROOT, env=env)
        tail = [l for l in p.stdout.splitlines() if "passed" in l or "failed" in l or "error" in l]
        print(f"  {'pytest (' + str(len(pyt)) + ' files)':34} {tail[-1] if tail else 'NO-RESULT'}")
        if p.returncode != 0:
            failures.append("pytest")
            print(p.stdout[-2500:])

    for stem in alone + live:
        ok, label = _run_standalone(stem)
        print(f"  {stem:34} {label}{'' if ok else '   <== FAILING'}")
        if not ok:
            failures.append(stem)

    print()
    if failures:
        print(f"FAILED: {len(failures)} suite(s) — {', '.join(failures)}")
        return 1
    print("ALL SUITES GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
