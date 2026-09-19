"""test_front_door_mutation.py — the property suite is still able to FAIL.

⇒⇒ **A GREEN SUITE THAT CANNOT GO RED IS THE MOST EXPENSIVE KIND OF COMFORT** — `conftest.py`'s
own words, written after 74 modules kept a `_FAIL` counter that nothing ever read and 674 PASSED
meant "nothing raised". `test_front_door_properties.py` is six assertions that are green today,
and green is exactly the state in which a test quietly stops being load-bearing: a refactor
narrows a probe, a corpus bucket drifts, an assertion is weakened to get a build through, and
nothing announces it. The properties would go on passing and would no longer mean anything.

⇒ **SO THE DOOR IS BROKEN ON PURPOSE, SEVEN WAYS, AND EACH BREAK MUST BE CAUGHT.** Every entry
in `MUTATIONS` names a defect and the property that exists to find it. If a mutation stops being
caught, the property that used to catch it has decayed — and this file says so, by name, instead
of the suite going on being green about it.

⇒ **THE SEVENTH IS TODAY'S FIX, GUARDED.** `_despace` folded unicode spaces in silence until the
operator ruled on 2026-09-17 that it must announce itself. The last mutation strips that notice
back off; `test_no_undeclared_silent_edit` has to notice. A fix nothing can un-fix quietly.

⇒ WHAT IT CANNOT PROVE. Not that the properties are the RIGHT properties — only that the ones we
have still bite. Choosing them was a reading of the door's contract; this is arithmetic.

⇒ HOW THE PATCHING IS KEPT SAFE. Every mutation is applied through `_mutated`, which snapshots
every patchable attribute, restores all of them in a `finally`, and is followed by a test that
asserts the module is byte-for-byte the one we found. A restore that silently failed would
poison every test that runs after this file — which would be this project's dominant defect
class, committed by the file written to police it.
"""
from __future__ import annotations

import contextlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english.seam import front_door as FD
import tests.test_front_door_properties as P

# Everything any mutation below replaces. Snapshotted and restored as one set, so a mutation
# that patches two names can never leave one of them behind.
_PATCHABLE = ("_apply", "_read_stages", "_quoted", "_damerau1", "_despace", "read")

# ⇒⇒ THE PRISTINE FUNCTIONS, CAPTURED AT IMPORT, BEFORE ANY MUTATION RUNS. **This line exists
#   because the first draft asked `importlib.import_module` for a clean copy to compare against
#   — and `import_module` returns the CACHED module, which is the very object being mutated.**
#   `getattr(FD, k) is getattr(pristine, k)` was therefore true whatever had leaked, and the
#   leak check could not fail. A test that cannot go red, inside the file written to prove the
#   others can: found 2026-09-17 while answering "is everything ready".
_PRISTINE = {k: getattr(FD, k) for k in _PATCHABLE}


@contextlib.contextmanager
def _mutated(break_it):
    saved = {k: getattr(FD, k) for k in _PATCHABLE}
    try:
        break_it(saved)
        yield
    finally:
        for k, v in saved.items():
            setattr(FD, k, v)


def _properties() -> list:
    """The property tests, in definition order — the order they are written to be read in."""
    import inspect
    fns = [(n, f) for n, f in vars(P).items() if n.startswith("test_") and callable(f)]

    def _at(fn):
        # ⇒ DEFINITION ORDER IS A COURTESY, NOT A CONTRACT, so it must never be able to throw.
        #   `getsourcelines` raises OSError for anything without a source file — a lambda, a
        #   decorated wrapper, a frozen build — and letting that escape would turn "a property
        #   decayed" into an ERROR in THIS file, where a reader would look for a bug in the
        #   mutation harness rather than in the property it is reporting on. Found the first
        #   time this file was asked to prove it could fail.
        try:
            return (0, inspect.getsourcelines(fn)[1])
        except (OSError, TypeError):
            return (1, 0)

    return sorted(fns, key=lambda nf: _at(nf[1]) + (nf[0],))


def _verdict(fn) -> str:
    try:
        fn()
        return "pass"
    except AssertionError:
        return "RED"
    except Exception as exc:                     # a mutation may break a property outright
        return f"ERR {type(exc).__name__}"


def _run_properties(only: str = "") -> dict:
    """Every property, or just one.

    ⇒ ONE IS THE FAST PATH AND IT IS THE PATH TAKEN WHEN NOTHING IS WRONG. Each property sweeps
      520 generated inputs, so running all six against all seven mutations is 42 sweeps and half
      a minute on a suite that otherwise finishes in seven seconds — a tax every developer pays
      forever to learn something that is almost always "yes, still caught". The nominated
      property is asked first; the other five are only run when it answered wrongly, which is
      exactly when the diagnostic table is worth having.
    """
    fns = _properties()
    if only:
        fns = [(n, f) for n, f in fns if n == only]
    return {n: _verdict(f) for n, f in fns}


# ── the seven defects ────────────────────────────────────────────────────────────────────────

def _m_offset(saved):
    """The back-map loses its final entry — every reported span lands one short."""
    inner = saved["_apply"]
    FD._apply = lambda t, e: (lambda r: (r[0], r[1][:-1]))(inner(t, e))


def _m_identity(saved):
    """The door rewrites a word it was never asked to touch."""
    inner = saved["_read_stages"]
    FD._read_stages = lambda r, b=None: (lambda v: FD.View(
        v.text.replace("stop", "halt"), v.back, v.notices, v.original))(inner(r, b))


def _m_no_notices(saved):
    """Every repair happens in silence."""
    inner = saved["_read_stages"]
    FD._read_stages = lambda r, b=None: (lambda v: FD.View(
        v.text, v.back, [], v.original))(inner(r, b))


def _m_open_quotes(saved):
    """Quoted evidence stops being opaque and becomes repairable like any other text."""
    FD._quoted = lambda low: []


def _m_damerau(saved):
    """Every word is one edit from every other — so a NAME becomes a repair candidate."""
    FD._damerau1 = lambda a, b: True


def _m_nonidempotent(saved):
    """Normalising never reaches a fixed point; re-reading a view keeps changing it."""
    inner = saved["_despace"]
    FD._despace = lambda t: inner(t) + " "


def _m_silent_despace(saved):
    """TODAY'S FIX, REVERTED: fold unicode spaces without announcing it (operator ruling 09-17)."""
    inner = saved["read"]
    FD.read = lambda request, board=None, known=None: (lambda v: FD.View(
        v.text, v.back, [n for n in v.notices if not n.startswith("folded ")], v.original
    ))(inner(request, board, known))


def _m_silent_comma(saved):
    """PASS 4 GOES SILENT: restore the clause break, drop the notice that announces it.

    ⇒ The half that matters most. A comma the door inserts without saying so changes where every
      downstream reader thinks a clause ends — pass 1's span walk, iso, self_repair and both act
      channels all key off it (N3, `db32859`) — and nothing in the view records that the door,
      not the operator, put it there.
    """
    inner = saved["read"]
    FD.read = lambda request, board=None, known=None: (lambda v: FD.View(
        v.text, v.back, [n for n in v.notices if "clause break before" not in n], v.original
    ))(inner(request, board, known))


def _m_phantom_comma_notice(saved):
    """THE OTHER HALF: announce a clause break that was never applied."""
    inner = saved["read"]
    FD.read = lambda request, board=None, known=None: (lambda v: FD.View(
        v.text, v.back, list(v.notices) + ["read a clause break before 'zzz'"], v.original
    ))(inner(request, board, known))


MUTATIONS = [
    ("back-map truncated",           _m_offset,          "test_the_offset_map_is_total_in_range_and_monotonic"),
    ("clean text rewritten",         _m_identity,        "test_text_with_nothing_to_repair_comes_back_byte_identical"),
    ("every notice dropped",         _m_no_notices,      "test_no_undeclared_silent_edit"),
    ("quotes no longer opaque",      _m_open_quotes,     "test_quoted_text_is_never_touched"),
    ("every word one edit apart",    _m_damerau,         "test_a_name_far_from_every_closed_word_survives_byte_identical"),
    ("no fixed point",               _m_nonidempotent,   "test_reading_a_view_again_changes_nothing"),
    ("comma restored in silence",    _m_silent_comma,    "test_every_restored_comma_is_announced_and_every_announcement_lands"),
    ("clause break announced only",  _m_phantom_comma_notice, "test_every_restored_comma_is_announced_and_every_announcement_lands"),
    ("despace notice removed",       _m_silent_despace,  "test_no_undeclared_silent_edit"),
]


# ⇒ 1 — THE VACUITY GUARD, AND IT RUNS FIRST. Mutation evidence is worth nothing if the suite is
#   already red: "the mutation was caught" and "it was broken before I touched it" look the same.
def test_the_property_suite_is_green_before_any_mutation():
    base = _run_properties()
    assert base, "no property tests were discovered — this file is testing nothing"
    red = {k: v for k, v in base.items() if v != "pass"}
    assert not red, f"the property suite is not green to begin with: {red}"


# ⇒ 2 — EVERY DEFECT IS CAUGHT BY THE PROPERTY THAT EXISTS TO CATCH IT.
def test_every_mutation_turns_its_own_property_red():
    known = {n for n, _ in _properties()}
    missed, table = [], []
    for label, break_it, must_catch in MUTATIONS:
        assert must_catch in known, f"{must_catch!r} is not a property test — rename or remove it"
        with _mutated(break_it):
            got = _run_properties(only=must_catch)
            if got[must_catch] != "pass":
                continue                         # caught by its own property; nothing to diagnose
            # ⇒ ONLY NOW is the full sweep worth its seconds: something that should have been
            #   caught was not, and the operator needs to know whether ANYTHING noticed.
            got = _run_properties()
        others = sorted(k for k, v in got.items() if v != "pass")
        table.append((label, {k: v for k, v in got.items() if v != "pass"}))
        missed.append((label,
                       f"{must_catch} no longer catches it; {', '.join(others)} still does"
                       if others else "NOTHING in the suite catches it any more"))
    assert not missed, (
        "THE PROPERTY SUITE HAS DECAYED — these defects are no longer caught:\n"
        + "\n".join(f"    {lab}\n        {why}" for lab, why in missed)
        + "\n\n  full cross-table (only non-passing shown):\n"
        + "\n".join(f"    {lab:<28} {red}" for lab, red in table))


# ⇒ 3 — AND THE MODULE IS PUT BACK. A leaked patch would fail tests in OTHER files, where nobody
#   would think to look here for the cause.
def test_the_front_door_module_is_left_exactly_as_found():
    leaked = [k for k in _PATCHABLE if getattr(FD, k) is not _PRISTINE[k]]
    assert not leaked, (
        f"mutation leaked into the live module: {leaked}\n"
        f"  Every test that runs after this file is now reading a broken front door, and "
        f"nothing in their output would point here.")
    # and it still behaves: one probe per contract the mutations above suspend
    v = FD.read("um, stop alpha")
    assert v.text == "stop alpha" and any("filled pause" in n for n in v.notices)


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined below
# this guard is never defined when the suite runs.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the property suite's teeth"))


if __name__ == "__main__":
    main()
