"""test_harness_integrity.py — the instruments are measured before anything they measure.

⇒⇒ **EVERY DEFECT FOUND ON 2026-09-17 WAS AN INSTRUMENT THAT LIED, NOT CODE THAT BROKE.**
Four of them, in one audit, each one silent for weeks and each one quoted as a result:

    the eval scored `operations_by_clause`; production calls `operations_for`, and neither
      wraps the other — three months of READ scoring described a code path that never ran
    the frozen ruler's persona layer failed 2000/2000 and fell back to `clean.lower()`, so a
      corpus built to be adversarial contained no noise at all and said nothing about it
    a length-changing front-door repair is discarded before the rule layer, so the door's
      PRIMARY operation (dropping a filled pause always changes length) was invisible to
      every rule in every run ever made
    a results file records its overlap threshold and its temperature, but not WHICH BUILDER
      produced it — so no stored number can be attributed to a code path after the fact

⇒ **THEY SHARE THE SHAPE `rig.py` WAS WRITTEN FOR, ONE LAYER UP.** An injectable seam left at
`None` does not fail — it does not run, and nothing distinguishes that from working. An
instrument pointed at the wrong function does not fail either: it returns a number, the number
is plausible, and it is wrong about a different thing. `rig.py` asserts that nobody shipped a
`None`. **The measurement stack had no equivalent, and that is the whole of 09-17.**

⇒ WHAT THIS CAN AND CANNOT PROVE. It cannot prove a measurement is CORRECT — only a control
run does that. It proves the instrument is pointed at the thing it claims to measure, that the
corpus contains what the corpus claims to contain, and that a stored result can be attributed
to a code path. Those are exactly the four failures above, and every one of them would have
been caught the day it appeared.

⇒ **IT MUST RUN WITHOUT THE MODEL.** An integrity check that needs `ollama serve` is an
integrity check that gets skipped, and a skipped check is the same silence this file exists to
break. Every assertion below reads source, corpus or results — nothing calls the model.

STATE AT BIRTH (2026-09-17): five of six RED, deliberately. They are the defects, not the test
being wrong. Each failure message names the fix.
"""
from __future__ import annotations

import ast
import glob
import inspect
import json
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HERE     = os.path.dirname(os.path.abspath(__file__))
_MARATHON = os.path.join(_HERE, "bench", "read_eval", "marathon")
_RESULTS  = os.path.join(_HERE, "bench", "read_eval", "results")

# THE TWO FUNCTIONS IN `pass2` THAT BUILD OPERATIONS. Named rather than discovered, because a
# discovery rule ("anything called operations_*") would quietly accept a third builder as the
# fourth instance of this defect class. Adding one here is a deliberate act.
BUILDERS = {"operations_for", "operations_by_clause"}

# POLICY FLOORS, NOT MEASUREMENTS — the operator's to set. They exist to catch a SYSTEMATIC
# failure (the gate refusing every single row), not to grade Serpent. A freeze that messifies
# half its rows is doing its job; one that messifies none is broken, and 0.5 is far enough from
# both edges that it can only fire on the broken case.
MIN_NOISED   = 0.5
MIN_FAITHFUL = 0.5


def _tok(s: str):
    return re.findall(r"[a-z0-9_]+", (s or "").lower())


def _builders_called_by(fn) -> set:
    """Which pass-2 builders this function calls, read from its AST.

    BY AST AND NOT BY LINE NUMBER, deliberately: the 09-17 audit found this by reading
    `runner.py:171` and `pipeline.py:493`, and a test that pinned those numbers would go
    green the next time somebody added an import. The call is the fact; where it sits is not.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return {n.func.attr for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in BUILDERS}


def _frozen() -> list:
    path = os.path.join(_MARATHON, "frozen.jsonl")
    assert os.path.exists(path), f"no frozen ruler at {path} — phase 1 never ran"
    return [json.loads(l) for l in open(path) if l.strip()]


def _newest_results() -> tuple:
    """The most recent results file — the one anybody would quote.

    THE NEWEST, NOT ALL OF THEM. Five files from 2026-08-17 predate `trigger_hit`, and a
    sweep over history would go red for a metric that was legitimately added later. The
    invariant that matters is about the number you are ABOUT TO QUOTE, not the archive.
    """
    files = glob.glob(os.path.join(_RESULTS, "*.json"))
    assert files, f"no results files in {_RESULTS} — nothing has ever been scored"
    newest = max(files, key=os.path.getmtime)
    return newest, json.load(open(newest))


# ⇒ 1 — THE ONE THAT COST THREE MONTHS.
def test_the_eval_scores_the_builder_that_production_runs():
    """`read_case` and `pipeline.run` must ask pass 2 the same way.

    Neither builder wraps the other: `operations_for` is ~25 lines asking once over the whole
    request, `operations_by_clause` asks once per clause. They share `prepare()` downstream and
    nothing upstream. Scoring one and shipping the other makes every stored number a statement
    about code the operator does not run.
    """
    from tests.bench.read_eval import runner
    from orchestrator.languages.english.seam import pipeline

    scored   = _builders_called_by(runner.read_case)
    produced = _builders_called_by(pipeline.run)

    assert scored, "read_case calls no known pass-2 builder — add it to BUILDERS or fix the eval"
    assert produced, "pipeline.run calls no known pass-2 builder — add it to BUILDERS"
    assert scored == produced, (
        f"THE EVAL MEASURES A CODE PATH PRODUCTION DOES NOT RUN.\n"
        f"    eval  read_case    -> {sorted(scored)}\n"
        f"    prod  pipeline.run -> {sorted(produced)}\n"
        f"  Fix by pointing read_case at production's builder, or by promoting the eval's "
        f"builder into pipeline.run — but not by leaving two.")


# ⇒ 2 — A RULER WITH NO MARKINGS ON IT.
def test_the_frozen_ruler_actually_carries_noise():
    """`said` must differ from `clean` on most rows, or the marathon measures clean input.

    `messify_faithful` falls back to `clean.lower()` when every retry drops a value atom
    (broken_telephone.py:247). The fallback is correct — a case that measures Serpent's
    sloppiness is worse than no case. What is NOT correct is a whole corpus taking it in
    silence: the 2026-09-15 freeze fell back on all 2000 rows and reported DONE.
    """
    rows = [r for r in _frozen() if r.get("said")]
    assert rows, "every frozen row is missing `said` — phase 1 errored on all of them"
    noised = [r for r in rows if r["said"] != r["clean"]]
    frac = len(noised) / len(rows)
    assert frac >= MIN_NOISED, (
        f"THE FROZEN RULER CARRIES NO NOISE: {len(noised)}/{len(rows)} rows differ from "
        f"`clean` ({frac:.1%}, floor {MIN_NOISED:.0%}).\n"
        f"  Every number read off this corpus describes CLEAN input, whatever the docstring "
        f"says. Re-freeze with a reachable model, or lower MIN_NOISED deliberately and say so.")


# ⇒ 3 — THE SAME EVENT, FROM THE SIDE THAT SHOULD HAVE SHOUTED.
def test_the_faithfulness_gate_is_not_failing_silently():
    """The gate records its own success per row; nothing ever read it.

    `faithful` is written to every row and was False on all 2000. The freeze printed
    "DONE frozen.jsonl: 2000 rows, 2000 with said-text" — true, and useless, because
    `said` is populated by the fallback too.
    """
    rows = [r for r in _frozen() if r.get("said")]
    faithful = [r for r in rows if r.get("faithful")]
    frac = len(faithful) / len(rows)
    assert frac >= MIN_FAITHFUL, (
        f"THE FAITHFULNESS GATE REFUSED {len(rows) - len(faithful)}/{len(rows)} ROWS "
        f"({frac:.1%} faithful, floor {MIN_FAITHFUL:.0%}).\n"
        f"  A uniform refusal is systematic, not quality — check the model was reachable "
        f"during the freeze before touching the gate.")


# ⇒ 4 — THE DOOR'S PRIMARY OPERATION, INVISIBLE TO EVERY RULE.
def test_a_front_door_repair_survives_into_the_text_the_rules_read():
    """What the rule layer reads must carry the repairs the front door made.

    `read_case` keeps the repaired view only when it is the same LENGTH as the original,
    and falls back to `FD.defused` otherwise, because a length change means offsets moved.
    Sound reasoning, wrong consequence: dropping a filled pause ALWAYS changes length, so
    the door's first documented operation never reaches a rule.

    ASSERTED ON `defused` RATHER THAN ON `read_case`, so that no copy of the runner's
    conditional lives here to rot. If the fix instead teaches `read_case` to remap offsets
    and keep the repaired view, this test is the one to update — say so in the commit.
    """
    from orchestrator.languages.english.seam import front_door as FD

    lost, exercised = {}, 0
    for s in ("um, stop alpha", "uh stop alpha", "stop alpha um"):
        view = FD.read(s)
        if len(view.text) == len(s):
            continue                       # not a length-changing repair; nothing to prove here
        exercised += 1
        dropped = set(_tok(s)) - set(_tok(view.text))
        survived_into_fallback = dropped & set(_tok(FD.defused(s)))
        if survived_into_fallback:
            lost[s] = sorted(survived_into_fallback)

    # ⇒ NOT VACUOUSLY GREEN. Every probe above hitting `continue` would leave `lost` empty and
    #   pass this test while proving nothing — the same "a green that cannot go red" defect the
    #   conftest fixture was written for. If the door stops dropping filled pauses, this test
    #   must go RED and be rewritten, not quietly congratulate itself.
    assert exercised, (
        "no probe produced a length-changing repair — the front door no longer drops filled "
        "pauses, or FILLED_PAUSE changed. This test proves nothing until its probes are "
        "rewritten against whatever the door repairs now.")

    assert not lost, (
        f"A LENGTH-CHANGING REPAIR IS DISCARDED BEFORE THE RULE LAYER: {lost}\n"
        f"  `FD.read` drops these; `FD.defused` — what read_case falls back to whenever the "
        f"view changes length — keeps them. Every rule regex therefore reads the UNrepaired "
        f"text, and dropping a filled pause always changes length.")


# ⇒ 5 — A NUMBER YOU CANNOT ATTRIBUTE IS NOT A RESULT.
def test_the_newest_results_file_carries_every_denominator():
    """A rate must be stored as numerator and denominator, never as a percentage.

    41% attachment and 27% binding are the same run: the scorer bills pass 2 only for spans
    pass 1 found, so one figure is conditional and the other is not. Nothing but the two
    integers distinguishes them.
    """
    path, d = _newest_results()
    overall = (d.get("aggregate") or {}).get("overall")
    assert overall is not None, f"{os.path.basename(path)} has no aggregate.overall"
    pairs = [("detected", "gold_spans"), ("boundary_exact", "gold_spans"),
             ("actions_detected", "gold_actions"), ("attach_hit", "attach_total"),
             ("trigger_hit", "trigger_total")]
    missing = [f"{n}/{den}" for n, den in pairs if n not in overall or den not in overall]
    assert not missing, (
        f"{os.path.basename(path)} reports rates without their denominators: {missing}")


def test_a_results_file_records_which_builder_produced_it():
    """The config must name the pass-2 builder the run used.

    THE WHOLE OF 09-17 IN ONE ASSERTION. Sixty-five stored results carry an overlap threshold
    and a temperature, and not one of them says which builder ran — so after the divergence
    was found, no archived number could be attributed to a code path, and all of them had to
    be treated as describing the eval's builder by inference rather than by record.

    A run older than this requirement cannot satisfy it. That is the correct outcome: it is
    untrusted until re-run, and saying so in a test is cheaper than remembering it.
    """
    path, d = _newest_results()
    cfg = d.get("config") or {}
    named = [str(v) for v in cfg.values() if str(v) in BUILDERS]
    assert named, (
        f"{os.path.basename(path)} does not record which pass-2 builder produced it "
        f"(config keys: {sorted(cfg)}).\n"
        f"  Have the runner write the builder's __name__ into `config`, then re-run. Until "
        f"then this file's numbers cannot be attributed to a code path.")


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined
# below this guard is never defined when the suite runs. Seven tests were lost that way in
# `test_rig.py` and eleven across three suites on 2026-08-04.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the measurement stack"))


if __name__ == "__main__":
    main()
