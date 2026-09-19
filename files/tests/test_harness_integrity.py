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



# ── 5 · THE SUITE'S OWN ENVIRONMENT IS SEALED ────────────────────────────────────────────────

# ⇒ THINGS THAT MUST RESOLVE INSIDE THE SANDBOX. Each is a MODULE-LEVEL singleton that reads
#   `GORGON_HOME` when its module is imported — which is during COLLECTION, before any fixture
#   runs. `tests/conftest.py` binds the variable at import for exactly this reason.
SANDBOXED_STORES = {
    "orchestrator.languages.english.seam.archive": "ARCHIVE",
    "orchestrator.languages.english.seam.verb_alias": "ALIASES",
    "orchestrator.ai.books.ledger": "LEDGER",
    "planner.procedures": "LIBRARY",
    # ⇒ CLOSED 2026-09-18. Both hardcoded `Path.home()` and so bound the operator's REAL
    #   credential store at import; they now read GORGON_HOME like every other store. They are
    #   Path constants, not store objects, so conftest records them the same way.
    "orchestrator.auth.store": "OPERATORS_FILE",
    "orchestrator.auth.sessions": "SESSIONS_FILE",
}

# ⇒ AND THE ONES THAT ARE *NOT* GORGON_HOME-ROOTED, DECLARED RATHER THAN HIDDEN. `shared.config`
#   resolves these from the config file at import, under `~/` directly — so sandboxing
#   `GORGON_HOME` does not move them and this file must not pretend otherwise. They are listed
#   so that a NEW leak is distinguishable from a KNOWN one; closing any of them means deleting
#   its line here, and leaving a stale line red is the point.
DECLARED_OUTSIDE = set()
# ⇒⇒ **EMPTY AS OF 2026-09-19, AND THAT IS THE POINT OF THE MANIFEST.** It held 57 entries on
#   2026-09-18: the credential store, the signing key, the executor token, the audit log, the
#   agent bundle root, the session file, and the executor's VM directories — every one of them
#   bound to the operator's REAL `~/.gorgon` at import, where no `GORGON_HOME` sandbox reached.
#   `vm_state.STATE_FILE` was being WRITTEN by suite runs.
#
#   ⇒ THEY WERE CLOSED IN THREE PLACES, NOT ~50. Each family resolved from ONE config reader, so
#     re-rooting the reader carried every constant that derives from it:
#         shared/config/_path              6 · signing key · token · audit log · agents · …
#         executor/api/_vm_constants._rooted   24 · vm base · templates · workspace · profiles
#         three direct `Path.home()` sites + `chat/session`
#     The CONSTANTS stayed constants — `orchestrator/auth` proved on 09-18 that the patch-one-
#     name idiom is load-bearing in the tests, and converting to functions would break it.
#
#   ⇒ PRODUCTION IS UNCHANGED THROUGHOUT: with `GORGON_HOME` unset every helper is exactly
#     `expanduser`, verified both ways for each family.
#
#   ⇒ **A NEW ENTRY HERE IS A DECISION, NOT A CHORE.** The sweep below goes red on an undeclared
#     bind; adding a line says "this one stays outside the sandbox and here is why". An empty set
#     is the state to defend.


_PATH_ATTRS = ("root", "dir", "home", "path", "_root", "_dir", "_home", "_path")


def _as_path(v):
    """A bound path is a str, a PathLike, or a zero-arg callable returning either.

    ⇒ `ARCHIVE.path` is a `PosixPath` and `LIBRARY.path` is a `str`. A check that accepted only
      `str` passed `LIBRARY` and reported `ARCHIVE` as having no path at all — which would have
      read as "nothing to see" on the one store the front door's `known` could have come from.
    """
    # ⇒⇒ **IT NEVER CALLS ANYTHING.** The first draft invoked any zero-arg callable to see whether
    #   it returned a path — and promptly triggered `RuntimeWarning: coroutine '_startup' was
    #   never awaited` by calling a product coroutine during a sweep. A check that runs arbitrary
    #   product code to find out where files live can itself touch the operator's files, which is
    #   the opposite of what this asserts. Attributes are READ, never invoked.
    if isinstance(v, os.PathLike):
        v = os.fspath(v)
    return v if isinstance(v, str) and v else None


def _bound_path(obj):
    direct = _as_path(obj)
    if direct:
        return direct
    for a in _PATH_ATTRS:
        got = _as_path(getattr(obj, a, None))
        if got:
            return got
    return None


def test_the_stores_bind_inside_the_sandbox_not_the_operators_home():
    """⇒⇒ **THE SUITE WAS NOT HERMETIC AND NOTHING SAID SO.** Found 2026-09-18.

    `planner/procedures.py` ends in `LIBRARY = Store()` at module scope; `_home()` reads
    `GORGON_HOME` at IMPORT. Test modules import during COLLECTION, before the session fixture
    ran — so `LIBRARY` bound to the operator's real library, and a procedure they saved on
    2026-08-27 appeared in the planner's operation list:

        tests/test_temp_lifecycle.py:282: AssertionError: (['browser'], ['iwillhackyou', 'launch_vm'])

    **21 red items — 8 failures and 13 errors — were that, not defects.** And the direction
    nobody can see is worse: we noticed because it turned things RED. Nothing tells us what it
    turned GREEN. Every pass in this suite was a sample of an undeclared variable, the same
    defect class as PYTHONHASHSEED, the empty marathon and the builder divergence.

    ⇒⇒ **IT ASSERTS AGAINST `conftest.BOUND_AT_IMPORT`, NOT AGAINST A FRESH IMPORT, AND THAT
      DISTINCTION IS THE WHOLE TEST.** The first draft imported the four stores itself and
      passed against the UNFIXED conftest — because by the time a test body runs, the fixture
      has already sandboxed the variable and any late import binds correctly. A control caught
      it. Only conftest, at its own import, can witness collection-time state.

    ⇒ THIS ASSERTS THE ENVIRONMENT, NOT A RESULT — the one instrument the other four checks
      assume. A number measured in a leaky environment is not wrong; it is unattributable.
    """
    from tests import conftest

    sandbox = os.path.realpath(os.environ["GORGON_HOME"])
    bound = conftest.BOUND_AT_IMPORT
    missing = set(SANDBOXED_STORES) - {k.rsplit(".", 1)[0] for k in bound}
    assert not missing, (
        f"conftest recorded no import-time bind for {sorted(missing)} — either the store moved "
        f"or the recording block in conftest.py lost it. Without the record this check is blind.")

    for where, path in sorted(bound.items()):
        real = os.path.realpath(path)
        assert real.startswith(sandbox), (
            f"{where} BOUND OUTSIDE THE SANDBOX AT IMPORT TIME.\n"
            f"    bound at  {real}\n    sandbox   {sandbox}\n"
            f"  It reads GORGON_HOME when its module is imported, and that happens during "
            f"COLLECTION — before any fixture runs. conftest.py sets the variable at module "
            f"scope for exactly this reason. If this is a new singleton, make it bind lazily.")


def test_no_new_module_level_object_points_at_the_operators_home():
    """The DISCOVERING half — the list above cannot catch what nobody thought to list.

    ⇒ A DECLARED MANIFEST GOES RED TWO WAYS: on a NEW leak, and on one silently FIXED. Both
      are decisions. Deleting a line from `DECLARED_OUTSIDE` is how a fix gets recorded.
    """
    import importlib
    import pkgutil

    # ⇒⇒ **IMPORT EVERY PRODUCT MODULE, DELIBERATELY — DO NOT SWEEP `sys.modules` AS FOUND.**
    #   The first draft swept whatever happened to be loaded, so this check reported a different
    #   set of leaks when run alone than when run with the suite. A check whose verdict depends
    #   on which OTHER tests ran is precisely the undeclared variable this module exists to
    #   reject, and it would have been one more of them.
    for pkg_name in ("orchestrator", "planner", "shared", "engines", "executor"):
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue
        for mod in pkgutil.walk_packages(getattr(pkg, "__path__", []), pkg_name + "."):
            try:
                importlib.import_module(mod.name)
            except Exception:
                pass                      # a module that cannot import binds nothing
    real_home = os.path.realpath(os.path.expanduser("~/.gorgon"))
    found = set()
    for name, mod in list(sys.modules.items()):
        if not name.startswith(("orchestrator", "planner", "shared", "engines", "executor")):
            continue
        for attr in dir(mod):
            if attr.startswith("__"):
                continue
            try:
                val = getattr(mod, attr)
            except Exception:
                continue
            path = _bound_path(val)
            if not isinstance(path, str) or not path:
                continue
            try:
                real = os.path.realpath(path)
            except Exception:
                continue
            if real == real_home or real.startswith(real_home + os.sep) or real.startswith(real_home):
                found.add(f"{name}.{attr}")
    # a re-export of the same object under another module name is the same leak
    leaked = {f for f in found if f not in DECLARED_OUTSIDE
              and not any(f.endswith("." + a) for a in SANDBOXED_STORES.values())}
    assert not leaked, (
        "MODULE-LEVEL OBJECT(S) BOUND TO THE OPERATOR'S REAL ~/.gorgon:\n    "
        + "\n    ".join(sorted(leaked))
        + "\n  Either make it bind lazily, or add it to DECLARED_OUTSIDE with a reason. An "
          "undeclared one means this suite's results depend on what is in the operator's home.")

    stale = DECLARED_OUTSIDE - found
    assert not stale, (
        "DECLARED_OUTSIDE names leak(s) that no longer exist: " + ", ".join(sorted(stale))
        + "\n  If they were fixed, delete the line(s) — a manifest that outlives what it "
          "describes is the staleness this file exists to catch.")


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined
# below this guard is never defined when the suite runs. Seven tests were lost that way in
# `test_rig.py` and eleven across three suites on 2026-08-04.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the measurement stack"))


if __name__ == "__main__":
    main()
