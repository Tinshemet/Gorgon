"""translation_table.py — what does the AI actually READ each rung as? No writer, no run.

    PYTHONPATH=. python3 tests/bench/translation_table.py [-n 3] [-r 8]

## THE READING, THE ASSISTANT AND THE GATE — AND NOTHING RUNS

Extraction, `to_goals`, the context assistant and the reading gate. A plan IS made, because
the assistant reads a program's CALLS and the gate asks what the reading WOULD do — and
`cover` plans against a scratch copy, so nothing real is touched and no rung checker is
consulted. **Nothing is executed.**

## IT DOUBLES AS THE NOISE MEASUREMENT

Each request is read `n` times and the DISTINCT readings are counted. That single column
answers the first of the four candidates in [[gorgon-why-the-noise]]: if a request yields one
reading every time, the model is stable on it and any run-to-run movement is downstream —
the gate, the loop, or the hint. If it yields three, this is the floor and everything above
it is amplification.

**READ THE `n=` COLUMN FIRST.** A rung that translates DIFFERENTLY on every draw cannot be
diagnosed from any single run of anything, and several arguments made on 2026-08-05 and 08-06
were about cells in exactly that state.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from engines import extract
from planner import reading_gate as gate
from engines.medusa.engine import MedusaEngine as _Medusa
from engines.orchestrator import Orchestrator as _Orch
from engines.registry import Registry as _Registry
from engines.rig import translator as _make_translator
from engines.session import Session as _Session
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

try:                                    # the only ground truth for a READING here
    from tests.test_ghost_writer import GOALS as KNOWN
except Exception:                       # pragma: no cover
    KNOWN = {}


def _world(rung) -> SimWorld:
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    return world


def _short(goal: dict) -> str:
    """One goal, compact enough for a table cell."""
    def sel(s):
        if not isinstance(s, dict):
            return str(s)
        bits = [f"{k}={v}" for k, v in s.items() if k != "kind"]
        return f"{s.get('kind')}" + (f"[{','.join(bits)}]" if bits else "")
    if "every" in goal:
        must = ",".join(f"{k}={v}" for k, v in (goal.get("must") or {}).items())
        return f"every {sel(goal['every'])} must {must}"
    if "per" in goal:
        return f"per {sel(goal['per'])} make {goal.get('make')}"
    if "observe" in goal:
        return f"observe {sel(goal['observe'])} {goal.get('fact')}"
    cmp_ = next((f"{k} {goal[k]}" for k in ("eq", "gte", "lte") if k in goal), "?")
    return f"count {sel(goal.get('select'))} {cmp_}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3)
    ap.add_argument("-r", "--rung", type=int, action="append")
    args = ap.parse_args(argv)
    wanted = set(args.rung or [r.n for r in RUNGS])

    # THE PRODUCTION MOUNT, built once. `read` needs an engine (for its manifest and its
    # world) and a channel; nothing here reaches the engine's executor.
    from engines.channel import Channel as _Channel
    _registry = _Registry()
    print(f"\n{'rung':<5}{'arm':<4}{'n=':<4}{'match':<10}{'gate':<8}{'gates hit':<12}reading "
          f"(most common of {args.repeats} draws)")
    print("─" * 126)
    unstable = 0
    scores = Counter()
    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm, request in (("lit", rung.goal), ("par", rung.paraphrase)):
            if not request:
                continue
            _world_for_engine = _world(rung)
            _engine = _Medusa(_world_for_engine)
            # ⇒ AN OPERATOR WHO LISTENS AND SAYS NOTHING. Silence leaves the refusal exactly
            #   where it was, so the OUTCOMES here are identical to a run with no operator at
            #   all — but the question is RECORDED, which is the only way this harness can
            #   tell a BOUNCE (gate 4 says a person could still rescue it) from a BLOCK
            #   (nothing an answer could change). Answering would measure the answers.
            _bounced: list = []

            def _listen(question, session, _b=_bounced):
                _b.append(question)
                return ""

            _orch = _Orch(_Registry(), _Channel([_make_translator()]), clarify=_listen)
            readings, store = Counter(), {}
            # ⇒ EVERY DRAW, KEPT, BECAUSE GATE 4 JUDGES THE SET AND NOT A MEMBER OF IT.
            #   The first port of this harness called gate 4 once per draw with a single
            #   reading — and one reading cannot disagree with itself, so it fired 0 times
            #   while the `n=` column beside it reported 5 rows that DID disagree. The same
            #   `built-and-never-called` shape fixed in `engines/rig.py` the same hour,
            #   reproduced here while copying it across. The draws were always in this loop.
            for _ in range(args.repeats):
                # ⇒ THE WHOLE FRONT DOOR, CORRECTIONS INCLUDED — `Orchestrator.read`.
                #
                #   Nothing is executed: `read` translates, runs the four gates, applies what
                #   they can safely fix and RE-ASKS where a violation is worth another draw.
                #   It stops before the engine, which is exactly the boundary this table wants.
                #
                #   IT CALLS PRODUCTION RATHER THAN IMITATING IT. This harness previously drove
                #   `extract`/`to_goals`/each gate by hand — a COPY of the wiring, which had
                #   already drifted: it ran its own gate-4 pass, with its own single-reading
                #   bug, an hour after the real one was fixed. A measurement harness that
                #   re-implements the thing it measures is measuring itself.
                session = _Session(request, _engine, intent="achieve")
                answer, closed = _orch.read(request, _engine, session)
                if answer is None:
                    goals, lost = [], [str((closed or {}).get("why") or "unreadable")]
                    flags = {"BOUNCE" if _bounced else "BLOCK": True}
                    warn, vetoed = list(_bounced), False
                else:
                    goals = list(answer.components or [])
                    lost = list(answer.dropped or [])
                    flags = {g: (ok is False)
                             for g, ok in (answer.gates or {}).items() if g != "reask"}
                    warn = list(answer.asks or []) + list(answer.fetch or [])
                    vetoed = (answer.gates or {}).get("reask") is False
                del _bounced[:]
                reasked = sum(1 for line in session.log if "re-standardis" in str(line))
                verdict = gate.Verdict(
                    gate.PROCEED if not any(flags.values()) else gate.ASK,
                    "+".join(sorted(k for k, v in flags.items() if v)) or "",
                    detail="; ".join((answer.illegal if answer else []) or []))
                if vetoed:
                    warn = ["gate 4 vetoed the re-ask: reads more than one way"] + warn
                elif reasked:
                    warn = [f"re-standardised x{reasked}"] + warn
                key = json.dumps([_short(g) for g in goals], sort_keys=True)
                readings[key] += 1
                store[key] = (goals, lost, verdict, warn)
            distinct = len(readings)
            unstable += distinct > 1
            top, _n = readings.most_common(1)[0]
            goals, lost, verdict, warn = store[top]
            flag = "  " if distinct == 1 else "!!"
            mark = {gate.PROCEED: "ok", gate.ASK: "ASK", gate.REFUSE: "REFUSE"}[verdict.outcome]
            # AGAINST THE KNOWN-GOOD READING, which is the only ground truth for a
            # TRANSLATION anywhere here — the hand-written goals the writer serves 13/13.
            truth = {_short(g) for g in (KNOWN.get(rung.n) or [])}
            mine = {_short(g) for g in goals}
            if not truth:
                match, bucket = "?", "?"
            elif truth == mine:
                match, bucket = "same", "same"
            elif truth & mine:
                match, bucket = f"partial {len(truth & mine)}/{len(truth)}", "partial"
            else:
                match, bucket = "DIFF", "DIFF"
            scores[bucket] += 1
            head = (f"{rung.n:<5}{arm:<4}{str(distinct) + flag:<4}{match:<10}{mark:<8}"
                    f"{verdict.caught or '-':<12}")
            if not goals:
                print(head + f"— nothing kept: {'; '.join(lost)[:52] or 'no reading'}")
            else:
                for i, g in enumerate(goals):
                    print((head if i == 0 else " " * 51) + _short(g)[:72])
                for m in sorted(truth - mine):
                    print(" " * 51 + f"MISSING: {m[:63]}")
            if warn:
                print(" " * 51 + f"assistant: {warn[0][:63]}")
    print("─" * 100)
    print("   vs the known-good reading: "
          + " · ".join(f"{k} {v}" for k, v in scores.most_common()))
    print(f"   `n=` is DISTINCT readings from {args.repeats} identical calls. "
          f"{unstable} row(s) marked !! disagree with themselves.")
    print("   A ROW THAT DISAGREES WITH ITSELF CANNOT BE DIAGNOSED FROM ONE RUN OF ANYTHING.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
