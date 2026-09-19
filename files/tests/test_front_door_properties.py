"""test_front_door_properties.py — what must hold for EVERY input, on inputs nobody chose.

⇒⇒ **THE FRONT DOOR HAD 14 TESTS AND NO NUMBER** (2026-09-17 audit). Every one of them is a
hand-written case: a filled pause here, a typo'd marker there, six of them precision traps. Good
tests, and they answer *"does this closed rule do what its docstring says"* — which is not the
question an operator asks. The question is *"what fraction of real junk does it catch, and how
often does it damage something it should not have touched"*, and that needs a corpus.

⇒ **THIS FILE IS THE HALF OF THAT WHICH NEEDS NO CORPUS AT ALL.** The front door is a pure
`str -> str` with an offset map: several of its contracts are PROPERTIES, true of every input,
checkable without anybody annotating anything. A property test cannot be satisfied by luck and
cannot be tuned to — the inputs are generated, not chosen, and a rule that holds on 440 of them
because somebody special-cased the four in the unit tests will not hold here.

⇒ **THE CONTRACTS, taken from the module's own docstring:**

    text      a working VIEW, never a rewrite — clean text returns the identity
    back      view offset -> original offset, `len(text)+1` entries, every one a real index
    notices   one line per fix, surfaced — "recognition is visible, NEVER SILENT"
    never     a NAME · an operation verb · anything in QUOTES

⇒ **WHAT THE FIRST RUN FOUND, AND IT IS NOW FIXED.** `_despace` rewrote a non-breaking space to
a space and said NOTHING. Same length, semantically neutral, and a real violation of "never
silent": a request pasted from a rendered doc was edited and the operator was never told. The
operator ruled on 2026-09-17 that it must announce itself — one notice per view however many
folded — so `_SILENT_PASSES` is now EMPTY and this file holds the door to its contract with no
exception at all. The mechanism stays so that a future exemption has to be written down.

⇒ WHAT THIS CANNOT PROVE. Not accuracy. A front door that repairs nothing at all passes every
property below. Recall and precision need the gold corpus (phase A2); these are the invariants
that must hold WHATEVER those numbers turn out to be, and that a later repair must not break.

⇒ MODEL-FREE AND DETERMINISTIC. `front_door` makes no model call; the corpus is seeded. A run
that needs `ollama serve` is a run that gets skipped.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english.seam import front_door as FD

# ⇒ PASSES ALLOWED TO EDIT WITHOUT A NOTICE. **EMPTY, and that is the ruling** (2026-09-17):
#   `_despace` was the only member and now emits its own notice, so the door's contract holds
#   without exception. The set survives as the place an exemption would have to be WRITTEN DOWN
#   — a silent pass nobody declared turns `test_no_undeclared_silent_edit` red.
_SILENT_PASSES = set()

_VERBS = ["stop", "start", "restart", "snapshot", "delete", "create", "launch", "clone"]
_DETS  = ["the", "a", "every", "all the", ""]
_NOUNS = ["vm", "network", "snapshot", "machine", "container"]
_NAMES = ["alpha", "beta", "web", "db", "grubnash", "core", "web-01"]
_TAILS = ["at 10.0.0.5", "on lab", "with 8gb", "at 9pm", ""]
_PAUSE = ["um", "uh", "erm", "hmm", "eh"]
_NBSP  = " "

# ⇒ STRATIFIED, NOT RANDOM. One bucket per junk kind, K each, so every property below can assert
#   it actually EXERCISED its path. A fuzz corpus that happens to generate no quoted text would
#   make the quote-opacity test pass while proving nothing — the vacuity failure this project
#   keeps paying for, most recently in `test_harness_integrity` itself.
_KINDS = ("clean", "pause_front", "pause_mid", "pause_end", "nbsp", "quoted", "quoted_junk",
          "flag", "path", "fused", "two_clause", "typo_marker", "typo_name")
_PER_KIND = 40


def _base(rng: random.Random) -> str:
    parts = [rng.choice(_VERBS), rng.choice(_DETS),
             rng.choice(_NOUNS) if rng.random() < 0.5 else rng.choice(_NAMES),
             rng.choice(_TAILS)]
    return " ".join(p for p in parts if p)


def _junk(kind: str, s: str, rng: random.Random) -> str:
    w = s.split()
    if kind == "pause_front":  return f"{rng.choice(_PAUSE)}, {s}"
    if kind == "pause_mid" and len(w) > 2:
        w.insert(1, rng.choice(_PAUSE)); return " ".join(w)
    if kind == "pause_end":    return f"{s} {rng.choice(_PAUSE)}"
    if kind == "nbsp":         return s.replace(" ", _NBSP, 1)
    if kind == "quoted":       return f"{s} called 'the label'"
    # ⇒ JUNK INSIDE QUOTES THAT WOULD BE REPAIRED OUTSIDE THEM — otherwise the opacity test
    #   proves only that the door leaves harmless text alone, which it would anyway.
    if kind == "quoted_junk":  return f"{s} called 'no wati um'"
    if kind == "flag":         return f"{s} --all-the-vms"
    if kind == "path":         return f"{s} /etc/web/temp.cfg"
    if kind == "fused" and len(w) > 1: return s.replace(" ", "-", 1)
    if kind == "two_clause":   return f"{s} then {_base(rng)}"
    if kind == "typo_marker":  return f"no wati, {s}"
    if kind == "typo_name":    return f"{rng.choice(_VERBS)} alpah"
    return s


def _corpus(seed: int = 20260917) -> list:
    rng = random.Random(seed)
    return [(k, _junk(k, _base(rng), rng)) for k in _KINDS for _ in range(_PER_KIND)]


def _far_names() -> list:
    """Names at Damerau distance >= 2 from every word the door may draw a repair from.

    COMPUTED AGAINST THE LIVE VOCABULARY, not hardcoded: if a closed class grows a word that
    collides with one of these, the name stops being a fair probe and must drop out rather than
    turn this file red for the wrong reason.
    """
    _, _, _, known = FD._vocab(None)
    return [n for n in ("grubnash", "zortlan", "xqvim", "plonkard", "vurmish", "kreppan")
            if n not in known and not any(FD._damerau1(n, k) for k in known)]


def _repair_notices(notices) -> list:
    """Notices that claim an EDIT, as opposed to `_shape_pass` naming a shape it left alone.

    The shape pass emits `'/etc/x.cfg' looks like a path — left whole`, which is a DETECTION:
    the text is untouched. Counting it as a repair would make the identity contract look broken
    on every input containing a path — the first draft of this file did exactly that.
    """
    return [n for n in notices if "left whole" not in n]


# ⇒ 1 — THE OFFSET MAP. Everything downstream reports spans against the ORIGINAL bytes.
def test_the_offset_map_is_total_in_range_and_monotonic():
    bad = []
    for _, s in _corpus():
        v = FD.read(s)
        if len(v.back) != len(v.text) + 1:
            bad.append(("length", s, len(v.back), len(v.text) + 1)); continue
        if any(not (0 <= b <= len(s)) for b in v.back):
            bad.append(("range", s, [b for b in v.back if not (0 <= b <= len(s))][:3])); continue
        if any(v.back[i] > v.back[i + 1] for i in range(len(v.back) - 1)):
            bad.append(("monotonic", s)); continue
    assert not bad, f"{len(bad)} offset-map violations, first 3: {bad[:3]}"


# ⇒ 2 — IDEMPOTENCE. A normaliser that keeps changing its own output has no fixed point, and
#   every consumer that re-reads a view would drift.
def test_reading_a_view_again_changes_nothing():
    edited = 0
    bad = []
    for _, s in _corpus():
        once = FD.read(s).text
        if once != s:
            edited += 1
        twice = FD.read(once).text
        if twice != once:
            bad.append((s, once, twice))
    assert edited >= 100, f"only {edited} inputs were edited at all — the corpus stopped probing"
    assert not bad, f"{len(bad)} inputs are not a fixed point, first 3: {bad[:3]}"


# ⇒ 3 — THE IDENTITY CONTRACT. "A working VIEW, never a rewrite of the request."
def test_text_with_nothing_to_repair_comes_back_byte_identical():
    checked = 0
    bad = []
    for kind, s in _corpus():
        if kind != "clean":
            continue
        checked += 1
        v = FD.read(s)
        if v.text != s or _repair_notices(v.notices):
            bad.append((s, v.text, v.notices))
    assert checked >= _PER_KIND, f"only {checked} clean inputs — the corpus lost its control arm"
    assert not bad, f"{len(bad)} clean inputs were edited, first 3: {bad[:3]}"


# ⇒ 4 — NEVER SILENT. The contract the audit found broken; see `_SILENT_PASSES`.
def test_no_undeclared_silent_edit():
    silent = []
    edited = 0
    for _, s in _corpus():
        v = FD.read(s)
        if v.text == s:
            continue
        edited += 1
        if _repair_notices(v.notices):
            continue
        # the ONLY change was unicode-space folding -> the one declared silent pass
        if "despace" in _SILENT_PASSES and v.text == FD._despace(s):
            continue
        silent.append((s, v.text, v.notices))
    assert edited >= 100, f"only {edited} inputs were edited — nothing to prove about silence"
    assert not silent, (
        f"{len(silent)} EDITS WITH NO NOTICE, and they are not the declared `_despace` fold: "
        f"{silent[:3]}\n"
        f"  'recognition is visible, never silent' is the door's own contract. Either emit a "
        f"notice for the pass that did this, or declare it in _SILENT_PASSES with a reason.")


# ⇒ 5 — QUOTES ARE OPAQUE. "Evidence is opaque testimony" — the operator's ruling.
def test_quoted_text_is_never_touched():
    checked = 0
    bad = []
    for kind, s in _corpus():
        if kind not in ("quoted", "quoted_junk"):
            continue
        regions = FD._quoted(s.lower())
        if not regions:
            continue
        checked += 1
        v = FD.read(s)
        for qs, qe in regions:
            if s[qs:qe] not in v.text:
                bad.append((s, s[qs:qe], v.text))
    assert checked >= _PER_KIND, (
        f"only {checked} quoted probes survived — `_quoted` stopped matching the corpus's "
        f"quoting style, so this test is no longer exercising opacity")
    assert not bad, f"{len(bad)} quoted regions were edited, first 3: {bad[:3]}"


# ⇒ 6 — A NAME IS NEVER REWRITTEN. The operator's rule: a typo'd name is the name.
def _cut_corpus(seed: int = 20260919) -> list:
    """Inputs that ACTUALLY reach pass 4 — because none of the 520 above do.

    ⇒⇒ **THE GENERATED CORPUS TRIGGERS ZERO CLAUSE CUTS: 0 of 520, measured.** Property 7 was
      written against it first and was VACUOUS — the silent-comma mutation went uncaught,
      because with no cut anywhere both sides of the equality are 0 and the assertion holds for
      a door that does nothing. The mutation harness found it, which is what it is for.

    ⇒ THE FRAMES ARE THE EIGHT CUT RULES' OWN SHAPES, filled with varied names so the property
      sweeps a population rather than eight examples. They are INPUTS, not gold: this file never
      asks whether the cut BELONGS there — that is READ's question and READ's seal — only
      whether the door applies faithfully whatever it was handed.
    """
    rng = random.Random(seed)
    names = ["alpha", "beta", "web", "db", "core", "dmz", "lab", "test"]
    frames = [
        "when you get a chance stop {a}",              # r1 courtesy literal
        "if you get a chance restart the {a} vm",
        "stop {a} tell me when it is down",            # r2 wrapper mid-clause
        "stop {a} anyway restart {b}",                 # r3 release word
        "restart {a} if it is down",                   # r4 condition head
        "stop the {a} vm unless it is the last one",
        "if {a} is stopped launch it",                 # r5 subordinate end
        "unless the {a} vm is running restart it",
        "dont stop the {a} vm stop the {b} vm",        # r6 second imperative
        "restart the {a} vm snapshot the {b} vm",
        "{a}2 is not working it boots to a bluescreen",  # r7 testimony elaboration
    ]
    out = []
    for f in frames:
        for _ in range(8):
            out.append(("cut", f.format(a=rng.choice(names), b=rng.choice(names))))
    return out


# ⇒ 7 — THE COMMA THE DOOR ADDS IS THE COMMA IT ANNOUNCED, AND NO OTHER.
def test_every_restored_comma_is_announced_and_every_announcement_lands():
    """Pass 4 measured as an APPLICATION question, which is the only part that is the door's.

    ⇒⇒ **OPERATOR RULING 2026-09-19: the clause cut is READ's taxonomy, not the door's.**
      `pass2._first_cut` decides WHERE a clause ends; the door only puts the comma back so
      pass 1's span walk can see the boundary (N3, operator-approved `db32859` 2026-08-19,
      after 5 certified span losses). Rescoping the seal away from the cut rule left pass 4
      with regression examples and **no measurement at all** — a blind pass inside a sealed
      surface. This is that measurement.

    ⇒ IT ASSERTS FIDELITY, NOT CORRECTNESS, AND THAT SEPARATION IS THE POINT. Whether a cut
      belongs where the rule says is READ's question and is adjudicated in READ's seal. Whether
      the door faithfully applies the answer it was given is the door's, and it holds **even if
      every cut rule is wrong** — which is exactly what makes it a fair measurement of this
      surface rather than a second opinion on someone else's.

    ⇒ THE TWO HALVES, because either alone is vacuous:
        a  every comma the door INSERTED carries a clause-break notice — no silent boundary
        b  every notice LANDS as a comma before the word it named — no announced boundary that
           was never applied
      Insertions are identified through the BACK-MAP, not by counting commas: a comma already
      in the operator's text is not an insertion, and a pause drop can remove one (`um, stop
      alpha`), so arithmetic on raw counts would be wrong in both directions.
    """
    import re as _re

    bad = []
    probed = 0
    for _, src in _corpus() + _cut_corpus():
        v = FD.read(src)
        named = [m.group(1) for n in v.notices
                 if (m := _re.search(r"clause break before '([^']*)'", n))]
        inserted = [i for i, ch in enumerate(v.text)
                    if ch == "," and not (v.back[i] < len(src) and src[v.back[i]] == ",")]
        if len(inserted) != len(named):
            bad.append(("count", src, v.text, named, len(inserted))); continue
        probed += len(inserted)
        for w in named:
            if not w:
                continue
            if not any(v.text[i:].lstrip(", ").startswith(w) for i in inserted):
                bad.append(("unlanded", src, v.text, w)); break
    # ⇒ AND THE PROPERTY MUST HAVE SOMETHING TO MEASURE. Without this the assertion above is
    #   satisfied by a door that never cuts at all, which is how the first draft passed against
    #   the silent-comma mutation.
    assert probed >= 20, (
        f"only {probed} restored commas across the whole sweep — pass 4 is not being exercised, "
        f"so this property proves nothing. Fix `_cut_corpus`, not this number.")
    assert not bad, (
        f"{len(bad)} clause-break fidelity violations. `count` = the door inserted a comma it "
        f"never announced, or announced one it never inserted; `unlanded` = a notice names a "
        f"word that no restored comma precedes. First 3: {bad[:3]}")


def test_a_name_far_from_every_closed_word_survives_byte_identical():
    far = _far_names()
    assert far, (
        "no probe name is far enough from the live vocabulary — every candidate collided, so "
        "this test cannot distinguish 'names are safe' from 'the probes were repairable'")
    rng = random.Random(20260917)
    bad = []
    checked = 0
    for name in far:
        for _ in range(20):
            s = f"{rng.choice(_VERBS)} {name}"
            checked += 1
            got = FD.read(s).text
            if name not in got:
                bad.append((s, got))
    assert checked >= 40, f"only {checked} name probes ran"
    assert not bad, f"{len(bad)} names were rewritten, first 3: {bad[:3]}"


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined below
# this guard is never defined when the suite runs.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the front door's invariants"))


if __name__ == "__main__":
    main()
