"""test_harness_integrity.py — the instruments are measured before anything they measure.

⇒⇒ **EVERY DEFECT FOUND ON 2026-09-17 WAS AN INSTRUMENT THAT LIED, NOT CODE THAT BROKE.**
Four of them, in one audit, each one silent for weeks and each one quoted as a result:

    the eval scored `operations_by_clause`; production calls `operations_for`, and neither
      wraps the other — three months of READ scoring described a code path that never ran
    the frozen ruler's persona layer failed 2000/2000 and fell back to `clean.lower()`, so a
      corpus built to be adversarial contained no noise at all and said nothing about it
    a length-changing front-door repair is discarded before the rule layer, so the door's
      PRIMARY operation (dropping a filled pause always changes length) was invisible to
      every rule in every run ever made  — **CLOSED 2026-09-17**: rows now carry `vstart`/
      `vend` beside the reported offsets, `annotate_roles` enters view space and remaps on the
      way out, and test 4 asserts the invariant instead of the symptom
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

STATE AT BIRTH (2026-09-17): five of six RED, deliberately — they are the defects, not the test
being wrong, and each failure message names the fix.
STATE NOW: FOUR red. The length-cap fallback is closed; what remains is the two-builder
divergence, the noiseless frozen ruler, the faithfulness gate that failed 2000/2000 in silence,
and results files that cannot be attributed to a builder. The first is phase B2's whole subject
and the middle two are one re-freeze.
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


# ⇒ 4 — THE RULE LAYER READS WHAT THE DOOR REPAIRED, AT ANY LENGTH.
def test_the_rule_layer_reads_the_repaired_text():
    """`annotate_roles` must regex the text the front door actually produced.

    ⇒ THIS TEST WAS REWRITTEN ON 2026-09-17 AND ITS FIRST FORM SAID SO IN ADVANCE. It used to
      assert that `FD.defused` — what `read_case` fell back to whenever a repair changed length —
      still carried the repairs, which it never did and never will. Its own docstring named the
      alternative: *"if the fix instead teaches `read_case` to remap offsets and keep the
      repaired view, this test is the one to update."* That is the fix that landed, so the
      assertion now names the real invariant instead of the symptom.

    ⇒ THE DEFECT IT REPLACES, measured: five of the door's seven passes change length, so any of
      them firing sent the rule layer back to separator-only text. 6 of 137 gold cases, 46 of
      2000 frozen turns, and in every gold case the discarded repair was a RESTORED COMMA —
      which is what the negation-scope rule hunts for to find where a clause ends. The
      behavioural case below is the consequence: with the comma missing, `dont`'s scope ran to
      the end of the sentence and the whole `unless` clause was labelled EXCLUDED — five spans
      carved out of the action set that belong in it.

    ⇒ MODEL-FREE. The reading is built by hand from `FD.read`, so pass 1 and pass 2 never run.
    """
    import re
    from orchestrator.languages.english.seam import front_door as FD
    from tests.bench.read_eval.runner import annotate_roles

    lab = ("lab", "dmz", "alpha", "beta", "web", "db", "jumpbox")

    def reading_for(text, *, legacy):
        view = FD.read(text, known=lab)
        toks = [(m.group(0), m.start(), m.end())
                for m in re.finditer(r"[a-z']+", view.text.lower())]
        rows = [{"row": i, "type": "object", "span": w,
                 "start": view.back[a], "end": view.back[b], "vstart": a, "vend": b}
                for i, (w, a, b) in enumerate(toks)]
        out = {"sentence": FD.defused(text, None, lab) if legacy else text,
               "rows": rows, "operations": []}
        if not legacy:
            out["view"], out["back"] = view.text, view.back
        return out, view

    # (a) THE COORDINATE ROUND-TRIP IS EXACT. If the remap is wrong every reported span moves,
    #     which would be a far worse defect than the one being fixed.
    probes = ["stop alpha unless it is the jumpbox", "um, stop alpha",
              "stop the lab vms all at once", "it would be great if alpha were down"]
    exercised, moved = 0, []
    for text in probes:
        reading, view = reading_for(text, legacy=False)
        if len(view.text) == len(text):
            continue                       # not a length-changing repair; nothing to prove here
        exercised += 1
        annotate_roles(reading)
        assert reading["sentence"] == text, f"{text!r}: the sentence was not restored"
        for p in reading["rows"]:
            if p.get("start") is None or p.get("sub"):
                continue
            want, got = (p.get("span") or "").lower(), text[p["start"]:p["end"]].lower()
            if want and want not in got:
                moved.append((text, want, got))
    assert exercised >= 3, (
        f"only {exercised} probes produced a length-changing repair — the door stopped repairing "
        f"these, so this test proves nothing until its probes are rewritten")
    assert not moved, f"reported spans moved off their text: {moved[:4]}"

    # (b) AND THE RULES BEHAVE DIFFERENTLY BECAUSE THEY SEE THE REPAIR. Without the restored
    #     comma `dont`'s scope never ends and the whole subordinate is excluded.
    text = "dont stop alpha unless it is the jumpbox"
    fresh, _ = reading_for(text, legacy=False)
    annotate_roles(fresh)
    wrongly_excluded = sorted(p["span"] for p in fresh["rows"]
                              if p.get("role") == "excluded"
                              and (p.get("span") or "") in ("unless", "it", "is", "the",
                                                            "jumpbox"))
    assert not wrongly_excluded, (
        f"{wrongly_excluded} were labelled EXCLUDED — carved out of the action set. The "
        f"negation's scope ran past the clause boundary, which means the rule layer is not "
        f"reading the restored comma.")


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
