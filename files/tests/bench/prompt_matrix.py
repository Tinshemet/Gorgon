"""prompt_matrix.py — six kinds of prompt, through the whole pipeline.

The rungs are all VALID requests. That is what a benchmark is for and it is also its blind
spot: a system measured only on well-formed input has never been asked what it does with a
typo, a half-sentence, or a request about a world that does not exist. Those are most of what
an operator actually types.

    VALID       an ordinary, complete request
    SPELLING    the same request, misspelt — meaning intact, surface damaged
    MISSING     a required detail absent: "create a vm" with no name
    AMBIGUOUS   two readings, and nothing in the sentence chooses
    IMPOSSIBLE  well-formed and unreachable: no tool can do it
    BROKEN      not a request at all — noise, or about nothing mounted

WHAT IS BEING GRADED IS NOT THE ANSWER, IT IS THE OUTCOME CODE. A system that refuses a
broken prompt with `UNCLAIMED` is behaving correctly; one that produces a confident program
for it is not, however plausible the program looks. So each case declares what it should do,
and the failure that matters is a WRONG KIND of response — silence where a refusal belongs,
or work where a question belongs.

Run:  PYTHONPATH=. python3 -m tests.bench.prompt_matrix
      PYTHONPATH=. python3 -m tests.bench.prompt_matrix --stub   (no model)
"""
import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from engines import (Channel, MedusaEngine, Orchestrator, Registry,
                                     WebCrawlEngine)

from engines import extract as _extract
from .seams import seams
from .sim_world import SimWorld

# `expect` is a SET, because more than one outcome can be right. "Create a vm" with no name
# may reasonably be refused OR answered with a generated name; what it may not do is crash,
# or silently invent a machine the operator did not ask for and report success.
CASES: List[Dict[str, Any]] = [
    {"kind": "VALID", "text": "create a vm named alpha",
     "expect": {"DONE"},
     "note": "the ordinary case — it should just work"},

    {"kind": "SPELLING", "text": "creat a vm nammed alpha",
     "expect": {"DONE", "UNTRANSLATED"},
     "note": "meaning intact, surface damaged. Working is better; refusing is honest"},

    {"kind": "MISSING", "text": "create a vm",
     "expect": {"DONE", "UNTRANSLATED", "UNMET"},
     "note": "no name given. It may name one itself, or say it cannot — never invent "
             "and claim the operator asked"},

    # THE FIRST VERSION OF THIS CASE WAS A BAD TEST. "Make sure the machines are fine"
    # expected a refusal, and the extractor answered `observe alive` — which is HELPFUL, not
    # hallucinated. A test that punishes a reasonable reading measures nothing.
    #
    # The ambiguity that matters is the one where ACTING IS DESTRUCTIVE. "Clean up the lab"
    # could mean delete the stopped machines, or remove some labels, or nothing at all — and
    # the difference is not recoverable afterwards. Here confidence is the failure.
    {"kind": "AMBIGUOUS", "text": "clean up the lab",
     "expect": {"UNTRANSLATED", "UNMET", "UNCLAIMED", "PROMOTION_DECLINED"},
     "note": "could mean delete machines. An irreversible reading of a vague sentence is "
             "the one thing that must never be chosen confidently"},

    {"kind": "IMPOSSIBLE", "text": "change the operating system of alpha to windows",
     "expect": {"UNMET", "PROMOTION_DECLINED", "UNTRANSLATED"},
     "note": "well-formed and unreachable — no tool changes os_type after birth. The "
             "writer must refuse rather than improvise"},

    {"kind": "BROKEN", "text": "asdkjh qwe ;;; 42",
     "expect": {"UNCLAIMED", "UNTRANSLATED"},
     "note": "not a request. Anything other than a refusal is a system hallucinating a job"},
]


def _rig(stub_table: Optional[Dict] = None):
    world = SimWorld()
    world.execute("create_vm", {"name": "alpha", "os_type": "linux"})
    reg = Registry()

    class SimMedusa(MedusaEngine):
        """Medusa over the bench's sim — the same engine, a test world."""

    reg.mount(SimMedusa(_SimAdapter(world)))
    reg.mount(WebCrawlEngine())
    return world, reg


class _SimAdapter:
    """The mount contract over `SimWorld`, which predates it and does not carry `seams`."""

    def __init__(self, world):
        self._w = world
        from planner.ir import config
        self.kinds = config.KINDS

    @property
    def seams(self):
        return seams(self._w)

    def execute(self, tool, args):
        return self._w.execute(tool, args)

    def names(self):
        return self._w.names()

    @property
    def state(self):
        return {"vm": self._w.vms}


def _model_channel(model: str):
    def answer(gap, world=None):
        from engines.channel import Answer
        try:
            raw = _extract.extract(str(gap), model)
        except Exception as e:
            return Answer(None, "extractor", f"{type(e).__name__}: {e}")
        got = _extract.to_goals(raw, str(gap))
        if not got:
            return Answer(None, "extractor",
                          _extract.declined(raw) or "no usable goal")
        return Answer(got, "extractor", json.dumps(raw)[:90])
    answer.name = "extractor"
    return Channel([answer])


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--stub", action="store_true",
                   help="no model — proves the matrix itself, not the extractor")
    p.add_argument("-m", "--model", default=None)
    a = p.parse_args(argv)

    from .ladder import BENCH_MODEL
    model = a.model or BENCH_MODEL
    if not a.stub and not _extract.assert_enforced(model):
        print("REFUSING TO RUN: the schema is not enforced.")
        return 2

    print(f"prompt matrix · {'STUB (no model)' if a.stub else 'model=' + model}")
    good = 0
    for case in CASES:
        world, reg = _rig()
        channel = Channel() if a.stub else _model_channel(model)
        orch = Orchestrator(reg, channel)
        try:
            r = orch.handle(case["text"])
            outcome = r["outcome"]
            why = str(r.get("why") or "")[:70]
        except Exception as e:
            # A CRASH IS ALWAYS WRONG, whatever the prompt. An operator typing nonsense is
            # entitled to a refusal, not a traceback — and a system that raises on bad input
            # has no outcome code at all, which is the one thing this matrix cannot grade.
            outcome, why = f"CRASHED:{type(e).__name__}", str(e)[:70]
        ok = outcome in case["expect"]
        good += ok
        print(f"  {case['kind']:<11} {'ok ' if ok else 'BAD'} {outcome:<20} {why}")
        if not ok:
            print(f"              expected one of {sorted(case['expect'])}")
            print(f"              {case['note']}")
    print(f"\n  {good}/{len(CASES)} prompts handled with an appropriate outcome")
    return 0 if good == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
