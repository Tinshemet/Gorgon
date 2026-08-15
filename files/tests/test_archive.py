"""test_archive.py — the knowledge SSOT, and the one property that makes it safe.

The archive is the only teaching channel this project has that is not the corpus, and the
corpus is spent. So the pins are, in order of what matters:

    1  NOTHING ROUTES UNTIL A PERSON RATIFIES IT. An unratified entry describes and never
       permits — otherwise a sentence grants authority, which is the courtesy defect one
       layer up
    2  keyed by the WORD, never the phrase — the ledger paid for that rule already
    3  a NEGATIVE entry is a real answer, not an absent one
    4  supersession keeps the old fact; the store must be auditable backwards, because the
       real risk is one misspoken answer becoming permanent and silent
    5  an assertive DECLINES far more than it accepts, and each refusal is a case where a
       guess would file a wrong fact permanently
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.seam import archive as A

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_nothing_routes_until_a_person_says_so():
    """⇒⇒ THE SAFETY PROPERTY, AND IT IS THE WHOLE REASON THIS IS A TWO-STEP STORE.

    If a proposal routed, then *"a grubnash is a vm"* typed by anyone — or imported from a
    lexicon — would silently teach the lab what a word means. That is a sentence granting
    authority, the same shape as a courtesy deciding the intent rung.
    """
    a = A.Archive()
    a.propose("jumpbox", "a vm", kind="vm", said="a jumpbox is a vm")
    check("a proposed entry is not known", a.known("jumpbox") is None)
    check("and it resolves no kind", a.kind_of("jumpbox") is None)
    check("but it IS visible to a person", [e.word for e in a.pending()] == ["jumpbox"])

    a.ratify("jumpbox", who="operator")
    check("once ratified it is known", a.known("jumpbox") is not None)
    check("and it resolves its kind", a.kind_of("jumpbox") == "vm")
    check("and it is no longer pending", not a.pending())


def test_an_imported_entry_never_routes_even_ratified():
    """⇒ TOLD vs IMPORTED. A poisoned source must produce a bad SUGGESTION, never a bad
    program — containment by construction rather than by trusting the source."""
    a = A.Archive()
    a.propose("router", "a network device", kind="network", source=A.IMPORTED)
    a.ratify("router")
    check("an imported entry does not route even after ratification",
          a.known("router") is None)


def test_a_negative_entry_is_an_answer():
    """*"routers are not a thing this lab keeps"* — 7 of 20 measured words were this case.

    The value is that the question stops being asked, which only works if the store can say
    NO rather than only failing to say YES.
    """
    a = A.Archive()
    a.propose("router", "not a thing this lab keeps", holds=False)
    a.ratify("router")
    check("a negative entry is known", a.known("router") is not None)
    check("and it settles no kind — the answer is no, not silence",
          a.kind_of("router") is None and a.known("router").holds is False)


def test_supersession_keeps_the_old_fact():
    """⇒ APPEND-ONLY. The real risk is one misspoken answer becoming permanent and silent, so
    the store has to be readable backwards. Nothing is deleted; the old row is marked."""
    a = A.Archive()
    a.propose("box", "a vm", kind="vm")
    a.ratify("box")
    a.propose("box", "a network", kind="network")
    a.ratify("box")
    check("the newest ratified entry wins", a.kind_of("box") == "network")
    check("the old one is kept, marked superseded",
          any(e.status == A.SUPERSEDED and e.kind == "vm" for e in a.rows()))
    check("and exactly one entry routes at a time",
          len([e for e in a.rows() if e.routes]) == 1)


def test_a_word_never_a_phrase():
    """The ledger's own rule, carried over: *'a grubnash named alpha'* once filed an answer
    under a phrase and bound it to nothing."""
    check("`a jumpbox is a vm` teaches the WORD",
          [p["word"] for p in A.taught_by("a jumpbox is a vm")] == ["jumpbox"])
    check("`n1 is the jumpbox` teaches `n1`, one token and not two",
          [p["word"] for p in A.taught_by("n1 is the jumpbox")] == ["n1"])
    check("a SET definition is declined — it defines no word",
          not A.taught_by("the red vms are the ones on mesh0"))


def test_it_declines_far_more_than_it_accepts():
    """Every refusal here is a case where a guess would file a wrong fact permanently."""
    for said, why in [
            ("yes, it's a label", "a pronoun subject would key an entry on `it`"),
            ("no, n1 is not a vm", "an ANSWER — reading_answers owns those"),
            ("snapshots are never to be deleted without asking me",
             "a RULE, not a description — it belongs to the referendum"),
            ("create a vm named alpha", "an order teaches nothing"),
            ("how many vms are there", "a question teaches nothing"),
            ("don't start any changes", "a conversation control teaches nothing")]:
        check(f"declined — {why}", not A.taught_by(said))


def test_the_kind_binds_when_the_lab_has_one():
    """⇒ `a jumpbox is a VM` binds a new word to a manifest kind, which is what will let an
    entry settle a reading. When the predicate names no kind the entry still describes."""
    bound = A.taught_by("a jumpbox is a vm")
    check("a predicate naming a manifest kind binds it", bound and bound[0]["kind"] == "vm")
    loose = A.taught_by("n1 is the jumpbox")
    check("and one that does not still teaches a description",
          loose and loose[0]["kind"] is None and loose[0]["description"] == "the jumpbox")


def test_it_survives_a_round_trip():
    """A store that cannot be reloaded is a cache."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "archive.json")
        a = A.Archive(path)
        a.propose("jumpbox", "a vm", kind="vm")
        a.ratify("jumpbox")
        a.save()
        b = A.Archive(path)
        check("a ratified entry survives save/load", b.kind_of("jumpbox") == "vm")
        check("and so does its provenance",
              b.known("jumpbox").source == A.TOLD)


def test_the_ratification_door_exists_and_is_reachable():
    """⇒⇒ **A RULE WITH NO DOOR IS A STORE THAT FILLS WITH THINGS NOBODY CAN ACT ON.**

    `known()` returning ratified entries only is the archive's whole safety property — and it
    is worth nothing if a person has no way to sign one. That is the same family as
    [[gorgon-built-and-never-called]]: a mechanism that cannot be exercised.

    The design names this surface and says why: *"it needs an audit surface — a `words`
    shortcut beside `books` — because the real risk is one misspoken answer becoming permanent
    and silent."*
    """
    from orchestrator.ai.chat.shortcuts.base import ALL_SHORTCUTS
    names = {c.__name__ for c in ALL_SHORTCUTS}
    check("the `words` shortcut is registered with the REPL", "Words" in names)

    from orchestrator.ai.chat.shortcuts.words import Words
    w = Words()
    for said in ("words", "words ratify jumpbox", "words reject jumpbox"):
        check(f"it matches {said!r}", w.matches(said))
    check("and does not swallow unrelated input", not w.matches("wordsmith the request"))

    from orchestrator.seam import archive as _A
    check("the process-wide archive exists, beside books.LEDGER",
          isinstance(_A.ARCHIVE, _A.Archive))


def test_a_ratified_entry_settles_a_row_the_world_could_not():
    """⇒⇒ **THE PAYOFF, AND THE REASON A STORE WITH NO READER IS HALF A FEATURE.**

    A kindless row is what makes gate 2 ask *"the request does not say what 'grubnash' is"*.
    Once the operator has taught the word and signed it, the same request settles silently —
    **capability bought by adding a FACT, with no prompt change and no re-fit.** That is the
    operator's *"without more corpus"* in one test.
    """
    from orchestrator.seam import pass1, schema as S
    from planner.formula.legal import Board

    board = Board()
    # ⇒⇒ **A PHRASE-NAMED ROW, BECAUSE THAT IS WHAT PASS 1 ACTUALLY PRODUCES.** The real
    #   reading of *"create a grubnash named alpha"* declares `a grubnash named alpha` — and
    #   the first cut of `settle_from_archive` looked THAT up in a store keyed by the word, so
    #   a ratified entry matched nothing and the teach-then-settle loop silently never closed.
    #   Testing a bare-word row passed and proved nothing; this is the case that bites.
    row = S.declare_from("a grubnash named alpha", S.UNKNOWN_KIND, {}, S.NEW, board,
                         span="a grubnash named alpha")

    empty = A.Archive()
    check("with an empty archive the row stays kindless",
          pass1.settle_from_archive([row], board, archive=empty)[0].object_type
          == S.UNKNOWN_KIND)

    taught = A.Archive()
    taught.propose("grubnash", "a vm", kind="vm")
    check("a PROPOSED entry settles nothing — it does not route",
          pass1.settle_from_archive([row], board, archive=taught)[0].object_type
          == S.UNKNOWN_KIND)

    taught.ratify("grubnash", who="operator")
    check("a RATIFIED entry settles it",
          pass1.settle_from_archive([row], board, archive=taught)[0].object_type == "vm")

    # ⇒ AND THE WORLD OUTRANKS THE STORE. A row the manifest or the lab already typed is not
    #   touched, however confidently the archive disagrees — a stale memory must never win.
    live = S.declare_from("grubnash", "network", {}, S.EXISTING, board, span="a grubnash")
    check("a row the world already settled is left alone",
          pass1.settle_from_archive([live], board, archive=taught)[0].object_type == "network")


def test_reject_refuses_without_deleting():
    """Refused, not erased — *who told it that, and when did we say no* has to be answerable."""
    a = A.Archive()
    a.propose("grubnash", "a vm", kind="vm")
    check("reject drops the proposal", a.reject("grubnash") == 1)
    check("nothing pending survives", not a.pending())
    check("and it never routed", a.known("grubnash") is None)
    check("but the row is still on record", any(e.word == "grubnash" for e in a.rows()))


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "archive")


if __name__ == "__main__":
    sys.exit(main())
