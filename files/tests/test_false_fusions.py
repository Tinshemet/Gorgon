"""test_false_fusions.py — the declared VETO SETS are all still ALIVE, and still needed.

⇒ TWO SETS, ONE PRINCIPLE — *a real English word is never repaired*. `FALSE_FUSIONS` holds
  the split pass to it; `FALSE_TYPOS` holds stage 2's closed-phrase repair to it (operator
  ruling 2026-09-17: **"forgot it stays as typed"**). Both are veto-only, both were derived
  off-line from a dictionary that is not a dependency, and both rot the same two ways.

⇒⇒ **A DECLARED SET IS A CACHE OF A COMPUTATION, AND CACHES DRIFT.** `codex.FALSE_FUSIONS` is
`known` INTERSECT English: every English word that `_split_pass`'s symmetric rule would tear into
two closed words. It was derived once, off-line, from a dictionary — which is the right way to
build a closed class here, and also the way a closed class silently stops being true. Two
directions of rot, and this file catches one of them:

    DEAD ENTRIES    a word listed that no rule would ever tear — the vocabulary moved, or the
                    rule narrowed, and the list is now carrying weight for nothing. CAUGHT HERE.
    MISSING ENTRIES a closed class grew a word, minting collisions the list does not have.
                    NOT CAUGHT HERE, and it cannot be: finding them needs the word list again.
                    That belongs to whoever adds the closed word, and this docstring is where
                    they are told so.

⇒ **THE VETO MUST ALSO ACTUALLY FIRE.** A set nothing consults is this project's dominant defect
  class in its purest form — data that loads and never runs. The behavioural half below reads a
  sample of the declared words through the real door and asserts none of them is SPLIT — which
  is the one thing the veto promises, and deliberately not "comes back unchanged": other passes
  may still repair such a word, and that is their bucket in the corpus, not this file's business.

⇒ **AND IT MUST NOT HAVE EATEN THE REAL FUSIONS.** `isnot`, `onthe`, `stopalpha` are what the
  split pass EXISTS for; a list that quietly contained one of them would disable the capability
  and every existing test would still pass, because they assert the split works — not that the
  veto is absent.

MODEL-FREE. The codex is data and `front_door` makes no model call.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english import codex
from orchestrator.languages.english.seam import front_door as FD
from orchestrator.languages.english.seam.scan import BOUNDARIES, PARTICLES as _PARTS

# The lab the split pass needs before a NAME half can license anything — the same declaration
# `pipeline.run` makes from `world.names()`.
LAB = ("alpha", "beta", "web", "db", "test", "core", "lab", "dmz")

# The fusions the pass exists to open. None may ever be declared a false fusion.
REAL_FUSIONS = ("isnot", "onthe", "stopalpha", "thedb", "testvms", "ifalpha", "vmand", "achance")

# The typo'd phrase words stage 2 exists to repair. None may ever be declared a false typo.
REAL_TYPOS = (("no wati, stop alpha", "no wait"), ("i mesnt alpha", "i meant"),
              ("forgte it", "forget it"), ("tlel me which vms are up", "tell me"),
              ("cancle that", "cancel that"), ("nevre mind", "never mind"),
              ("as you wree", "as you were"),
              ("wehn you get a chance, stop alpha", "when you get a chance"))


def _phrase_words() -> set:
    from orchestrator.languages.english.seam import self_repair as _sr
    from orchestrator.languages.english.seam.speech_act import WRAPPERS, COURTESY
    return {w for p in (tuple(_sr.CORRECTIONS) + tuple(_sr.RETRACTIONS) + WRAPPERS + COURTESY)
            for w in p.split() if len(w) >= 4 and len(p.split()) >= 2}


def _reader_vocabulary() -> set:
    """The word set `_split_pass` treats as closed — assembled exactly as it assembles it."""
    _, _, _, known = FD._vocab(None)
    return known | {b for b in BOUNDARIES if b.isalpha()} | {
        "not", "no", "these", "those", "this", "that", "there", "their", "they",
        "than", "have", "has", "had"}


def _symmetric_fits(word: str, known: set) -> list:
    """Split points the SYMMETRIC rule licenses — the only one the veto exists to block.

    Re-derived from the rule rather than read off the door, so this test says something about
    whether the LIST is right rather than merely echoing what the code currently does.
    """
    out = []
    for i in range(1, len(word)):
        a, b = word[:i], word[i:]
        if len(b) < 2:
            continue
        if len(a) == 1:
            if a == "a" and b in known:
                out.append(i)
        elif a in known and b in known and not (a in _PARTS and b in _PARTS):
            out.append(i)
    return out


def test_the_set_is_well_formed_and_non_empty():
    s = codex.FALSE_FUSIONS
    assert len(s) >= 100, f"only {len(s)} declared — the derivation did not run to completion"
    bad = [w for w in s if not w.isalpha() or w != w.lower() or len(w) < 4]
    assert not bad, f"malformed entries (must be lowercase alpha, >=4): {sorted(bad)[:8]}"


def test_no_declared_word_is_dead():
    """Every member must still be one the symmetric rule WOULD tear. A dead entry means the
    vocabulary or the rule moved and nobody re-derived the list."""
    known = _reader_vocabulary()
    dead = [w for w in sorted(codex.FALSE_FUSIONS) if len(_symmetric_fits(w, known)) != 1]
    assert not dead, (
        f"{len(dead)} DEAD entries — no rule would tear these any more, so the list is carrying "
        f"them for nothing: {dead[:12]}\n"
        f"  Re-derive: every dictionary word (4-14 letters, not in the reader's vocabulary) with "
        f"EXACTLY ONE split into two closed words.")


def test_the_veto_actually_fires():
    """A sample of the declared words, through the real door, must not be SPLIT.

    ⇒ SPLIT, NOT "UNCHANGED", AND THE DIFFERENCE IS A FINDING. The first draft asserted the word
      came back byte-identical and caught `dome` -> `some` — which is not the split pass at all
      but stage 3's SIM CHECK repairing a declared English word by one substitute print. The veto
      promises one thing (this token is not a fusion) and must be tested for that one thing;
      `dome` is a PRECISION TRAP of the same family as `forgot it` -> `forget it`, it belongs to
      the corpus's must_not_touch bucket, and asserting it here would hide which pass to fix.
      A split adds a token, so counting tokens separates the two exactly.
    """
    rng = random.Random(20260917)
    sample = rng.sample(sorted(codex.FALSE_FUSIONS), 60)
    torn = []
    for w in sample:
        for frame in (f"stop the {w} vm", f"the {w} is up", f"check the {w} now"):
            got = FD.read(frame, known=LAB).text
            if len(got.split()) > len(frame.split()):
                torn.append((frame, got))
    assert len(sample) == 60, "the sample shrank — this test stopped probing"
    assert not torn, f"{len(torn)} declared non-fusions were still SPLIT, first 5: {torn[:5]}"


def test_the_real_fusions_were_not_eaten():
    """The capability the split pass exists for must survive the veto."""
    inside = [w for w in REAL_FUSIONS if w in codex.FALSE_FUSIONS]
    assert not inside, (
        f"{inside} are declared NON-fusions, which disables the split pass for them. Every "
        f"existing split test would still pass — they assert the split works, not that the veto "
        f"is absent — so this is the only place that would catch it.")
    # and they still open, which is the behaviour those declarations would have killed
    for text, want in (("isnot running", "is not"), ("onthe lab network", "on the"),
                       ("stopalpha", "stop alpha"), ("restart thedb vm", "the db"),
                       ("ifalpha is stopped, launch it", "if alpha")):
        assert want in FD.read(text, known=LAB).text, f"{text!r} no longer opens to {want!r}"


def test_false_typos_is_well_formed_and_none_is_dead():
    """Every member must still be an English word one edit from a phrase word AND not already
    vetoed by the `known` guard — otherwise the list is carrying it for nothing."""
    s = codex.FALSE_TYPOS
    assert len(s) >= 50, f"only {len(s)} declared — the derivation did not run to completion"
    known = _reader_vocabulary()
    targets = _phrase_words()
    dead = sorted(w for w in s
                  if w in known or not any(FD._damerau1(w, t) for t in targets))
    assert not dead, (
        f"{len(dead)} DEAD entries in FALSE_TYPOS — either now covered by the `known` guard or "
        f"no longer one edit from any phrase word: {dead[:12]}")


def test_the_typo_veto_actually_fires():
    """The ruling, in the frames that motivated it."""
    still = []
    for text in ("forgot it, stop alpha", "no want, stop alpha", "never find the vm",
                 "i meat alpha", "tall me which vms are up", "take that snapshot",
                 "i mean alpha"):
        got = FD.read(text, known=LAB).text
        if got != text:
            still.append((text, got))
    assert not still, f"declared non-typos were still repaired: {still}"


def test_the_real_typos_were_not_eaten():
    """The capability stage 2 exists for must survive the veto."""
    inside = [w for w in ("wati", "mesnt", "forgte", "tlel", "cancle", "nevre", "wree", "wehn")
              if w in codex.FALSE_TYPOS]
    assert not inside, f"{inside} are declared NON-typos, which disables the repair for them"
    for text, want in REAL_TYPOS:
        assert want in FD.read(text, known=LAB).text, f"{text!r} no longer repairs to {want!r}"


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined below
# this guard is never defined when the suite runs.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the declared non-fusions"))


if __name__ == "__main__":
    main()
