"""test_seal_front_door.py — the seal still describes the thing it sealed.

⇒⇒ **A SEAL WHOSE HASHES HAVE MOVED IS VOID, AND IT HAS TO SAY SO ITSELF.** `SEAL-front-door.md`
records what was measured, over which exact bytes, at what numbers. Every one of those is a claim
about artifacts that live beside it and can change without anybody editing the seal — a corpus
re-frozen, a closed class grown, a veto set re-derived. A seal nobody re-checks is a certificate
of something that used to be true, which is worse than none: it carries the operator's name.

⇒ WHAT IS AN INVARIANT AND WHAT IS A RECORD. The corpus hashes, the vocabulary fingerprint and
  the declared set sizes are INVARIANTS — if they move, the seal is stale and this goes red. The
  **git HEAD is a RECORD** of when the seal was written, not an invariant, and is deliberately
  NOT asserted: it would void the seal on the next commit to any file in the repo.

⇒ THIS PROVES NOTHING ABOUT WHETHER THE MEASUREMENT IS RIGHT. It proves the seal has not silently
  come to describe a different system. Whether the GOLD is right is section 5 of the seal, it is
  unadjudicated, and no test can close that — only the operator can.

MODEL-FREE.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english import codex

_HERE = os.path.dirname(os.path.abspath(__file__))
SEAL = os.path.join(_HERE, "bench", "SEAL-front-door.md")
DOOR = os.path.join(_HERE, "bench", "door_eval", "cases.jsonl")
CUT = os.path.join(_HERE, "bench", "cut_eval", "cases.jsonl")


def _seal_text() -> str:
    assert os.path.exists(SEAL), f"no seal at {SEAL} — the front door is unsealed"
    return open(SEAL).read()


def _sha16(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def _declared(pattern: str) -> str:
    m = re.search(pattern, _seal_text())
    assert m, f"the seal no longer declares {pattern!r} — it was edited into a shape this cannot read"
    return m.group(1)


def test_the_sealed_corpora_are_the_corpora_on_disk():
    for name, path, pat in (("door", DOOR, r"door corpus\s+cases\.jsonl\s+([0-9a-f]{16})"),
                            ("cut", CUT, r"cut corpus\s+cases\.jsonl\s+([0-9a-f]{16})")):
        want, now = _declared(pat), _sha16(path)
        assert want == now, (
            f"THE {name.upper()} CORPUS HAS BEEN RE-FROZEN SINCE THE SEAL WAS WRITTEN.\n"
            f"    sealed  {want}\n    now     {now}\n"
            f"  Every number in the seal was measured over the sealed bytes. Re-run both scorers, "
            f"update the seal, and have the operator re-attest — a hash change invalidates the "
            f"attestation, not just the figure.")


def test_the_sealed_vocabulary_fingerprint_still_holds():
    want = _declared(r"vocabulary fingerprint\s+([0-9a-f]{16})")
    assert want == codex.VETO_SETS_DERIVED_FROM, (
        f"the closed-set vocabulary has moved since the seal: sealed {want}, now "
        f"{codex.VETO_SETS_DERIVED_FROM}. The veto sets are derived from it, so the seal's "
        f"numbers describe a different door.")


def test_the_sealed_set_sizes_still_hold():
    text = _seal_text()
    for name, live in (("FALSE_FUSIONS", codex.FALSE_FUSIONS),
                       ("FALSE_TYPOS", codex.FALSE_TYPOS),
                       ("FALSE_PRINTS", codex.FALSE_PRINTS)):
        m = re.search(rf"{name} (\d+)", text)
        assert m, f"the seal no longer declares a size for {name}"
        assert int(m.group(1)) == len(live), (
            f"{name}: sealed at {m.group(1)}, now {len(live)}")
    m = re.search(r"CUT_NEGATION\s+(\d+) forms", text)
    assert m and int(m.group(1)) == len(codex.CUT_NEGATION), (
        f"CUT_NEGATION: sealed at {m.group(1) if m else '?'}, now {len(codex.CUT_NEGATION)}")
    m = re.search(r"DUAL_CLASS_VERBS\s+([a-z, ]+)", text)
    assert m, "the seal no longer declares DUAL_CLASS_VERBS"
    assert sorted(w.strip() for w in m.group(1).split(",")) == sorted(codex.DUAL_CLASS_VERBS), (
        f"DUAL_CLASS_VERBS: sealed {m.group(1)!r}, now {sorted(codex.DUAL_CLASS_VERBS)}")


def test_the_seal_still_declares_who_wrote_the_gold():
    """The honest half must survive editing, or the seal becomes a marketing document.

    ⇒ THIS IS NOT PEDANTRY. Section 5 says Claude authored every case and the operator has
      adjudicated none. That sentence is what tells a reader — a teacher, an auditor, a future
      session — what the 100%s are worth. A seal that loses it still shows six green rows and
      means something entirely different.
    """
    text = _seal_text()
    for must in ("Claude wrote all", "adjudicated none",
                 "Which cases exist is Claude's choice"):
        assert must in text, (
            f"the seal no longer says {must!r}. Section 5 is the line that decides what this "
            f"seal is worth; it may be REVISED by the operator, never dropped.")


def test_an_unsigned_seal_says_so():
    """Until the operator attests, the seal must not read as though they had."""
    text = _seal_text()
    signed = re.search(r"CERTIFIED BY:\s*(\S.*)", text)
    if signed:
        return                                   # attested — nothing more to assert here
    assert "Status: UNSIGNED" in text or "UNSIGNED" in text.split("\n")[2], (
        "the attestation block is empty but the seal does not declare itself UNSIGNED — a reader "
        "would take six green rows as certified when nobody has certified anything.")


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined below
# this guard is never defined when the suite runs.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the front door's seal"))


if __name__ == "__main__":
    main()
