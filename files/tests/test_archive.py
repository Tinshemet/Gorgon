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


def test_a_signed_entry_can_be_changed_and_withdrawn():
    """⇒⇒ **THE OPERATOR ASKED HOW YOU REMOVE A WORD AND THE ANSWER WAS: YOU CANNOT.**

    `ratify` supersedes an old entry when a NEW one replaces it, and `reject` drops a PENDING
    proposal — so a wrong fact could be overwritten and never simply withdrawn. That is the
    exact risk this store was designed around: *"the real risk is one misspoken answer becoming
    permanent and silent."* An archive is meant to be the REPAIRABLE SSOT — the one whose wrong
    entries are fixable by teaching — and an unwithdrawable entry would make it the other kind.
    """
    a = A.Archive()
    a.propose("jumpbox", "a vm", kind="vm")
    a.ratify("jumpbox")
    check("it routes", a.kind_of("jumpbox") == "vm")

    # CHANGE — say the new thing and sign it. No special verb needed.
    a.propose("jumpbox", "a network", kind="network")
    a.ratify("jumpbox")
    check("changed by stating the new fact", a.kind_of("jumpbox") == "network")

    # REMOVE — withdraw what is in force.
    gone = a.retract("jumpbox")
    check("withdrawn", gone is not None and a.known("jumpbox") is None)
    check("and it settles nothing now", a.kind_of("jumpbox") is None)
    check("but every version is still on record",
          len([e for e in a.rows() if e.word == "jumpbox"]) == 2)
    check("withdrawing what is not in force says so",
          a.retract("jumpbox") is None)


def test_a_question_about_a_word_is_answered_from_the_archive():
    """*"what is kaya?"* — the one question shape that needs no QUERY.

    ⇒⇒ **A QUESTION ABOUT A WORD IS NOT A SELECT.** *"how many vms are running"* becomes a
      program the engine runs against the lab; `kaya` is not a thing the lab keeps, it is a
      WORD the lab was taught, so the answer is a lookup and nothing else. Without this the
      question read correctly, produced a goal with an empty selector, and was answerable by
      nothing at all.

    ⇒ THE DISCRIMINATOR IS THE MANIFEST, as everywhere else: *"what is on the LAB NETWORK"*
      names a kind and stays a select.
    """
    from orchestrator.seam import speech_act as SA
    from planner.formula.legal import Board
    board = Board()

    st = A.Archive()
    st.propose("kaya", "a vm", kind="vm")
    st.ratify("kaya")
    st.propose("router", "", holds=False)
    st.ratify("router")

    check("a question about a word wants a MEANING",
          SA.answer_shape("what is kaya", board) == SA.MEANING)
    check("a question about a KIND still wants a select",
          SA.answer_shape("what is on the lab network", board) == SA.MEMBERS)

    said = A.asked_about("what is kaya now?", board, store=st)
    check(f"and it is answered from the store — {said}",
          said and "kaya" in said[0] and "a vm" in said[0])
    check("a negative entry answers NO rather than nothing",
          "not a thing this lab keeps" in (A.asked_about("what is router", board,
                                                         store=st) or [""])[0])
    check("an unknown word says so, and says what to do about it",
          "nothing on file" in (A.asked_about("what is a jumpbox", board,
                                              store=st) or [""])[0])

    # ⇒ AND A PENDING ENTRY DOES NOT ANSWER. A question must not be answered with something
    #   nobody signed — the same rule that stops it settling a reading.
    st2 = A.Archive()
    st2.propose("kaya", "a vm", kind="vm")
    check("a proposal answers nothing",
          "nothing on file" in (A.asked_about("what is kaya", board, store=st2) or [""])[0])


def test_an_entry_can_name_a_class_that_is_another_entry():
    """*"kaya is a printer"* has to mean something — the operator, 2026-08-16.

    ⇒⇒ **A STORE THAT RESOLVES ONLY WHEN THE PREDICATE NAMES A MANIFEST KIND CAN LEARN
      *"kaya is a vm"* AND NOTHING ELSE.** The design is *a manifest-shaped row for a noun the
      manifest does not have*, so an entry may name a CLASS and the class may be another entry:

          kaya    -> classes ('printer',)
          printer -> kind 'vm'
          ⇒ kaya resolves to vm, and what the lab can do to a vm it can do to kaya
    """
    check("a predicate naming no manifest kind becomes a CLASS",
          A.taught_by("kaya is a printer")[0]["classes"] == ("printer",))
    check("and one that DOES name a kind still binds it directly",
          A.taught_by("kaya is a vm")[0]["kind"] == "vm")

    a = A.Archive()
    a.propose("kaya", "a printer", classes=("printer",))
    a.ratify("kaya")
    check("an unresolved class settles nothing yet", a.kind_of("kaya") is None)

    a.propose("printer", "a vm", kind="vm")
    a.ratify("printer")
    check("teaching the CLASS resolves everything under it", a.kind_of("kaya") == "vm")
    check("and the chain is readable", a.classes_of("kaya") == ("printer",))

    # ⇒ ⚠ TWO TRUE-SOUNDING SENTENCES MUST NOT HANG THE SEAM.
    cyc = A.Archive()
    cyc.propose("a", "a b", classes=("b",)); cyc.ratify("a")
    cyc.propose("b", "an a", classes=("a",)); cyc.ratify("b")
    check("a cycle says nothing rather than hanging", cyc.kind_of("a") is None)


def test_reject_refuses_without_deleting():
    """Refused, not erased — *who told it that, and when did we say no* has to be answerable."""
    a = A.Archive()
    a.propose("grubnash", "a vm", kind="vm")
    check("reject drops the proposal", a.reject("grubnash") == 1)
    check("nothing pending survives", not a.pending())
    check("and it never routed", a.known("grubnash") is None)
    check("but the row is still on record", any(e.word == "grubnash" for e in a.rows()))


def test_every_words_command_is_reachable_in_sentence_form():
    """The operator's spec, 2026-08-16: *"in a statement sentence you can do all the commands
    `words` do … all `words` commands are reachable in sentence form."*

    ⇒⇒ **AND IT IS SIGNED IMMEDIATELY, WHICH CORRECTS A POSITION I ARGUED.** I said
      ratification must never be automatic. The danger was never a PERSON stating a fact — it
      was an IMPORTED or INFERRED entry routing with nobody answering for it, and `source`
      already draws that line. **The signature is not the ceremony, it is who spoke.**

    ⇒ **THE ASK MOVES FROM ASSERTION TO CONTRADICTION.** Do not interrupt someone teaching you
      something new; interrupt them when the new fact disagrees with one already on file.
    """
    from planner.formula.legal import Board
    board = Board()

    def taught():
        st = A.Archive()
        A.apply_effects(A.effect_of("kaya is a vm", board, store=st), store=st)
        return st

    st = taught()
    check("a statement TEACHES and is signed on the spot — no ratify step",
          st.kind_of("kaya") == "vm")

    st = taught()
    A.apply_effects(A.effect_of("kaya is now a network", board, store=st), store=st)
    check("a second statement CHANGES the fact", st.kind_of("kaya") == "network")

    st = taught()
    eff = A.effect_of("kaya isnt a vm", board, store=st)
    check("a denial that NAMES A KIND contradicts what is on file",
          [e["op"] for e in eff] == [A.CONTRADICTS])
    check("and contradicting is never performed — it is a question",
          "which stands?" in A.apply_effects(eff, store=st)[0]
          and st.kind_of("kaya") == "vm")

    st = taught()
    A.apply_effects(A.effect_of("kaya doesn't exist", board, store=st), store=st)
    check("a denial that names NOTHING withdraws the word", st.known("kaya") is None)

    # ⇒ THE ARCHIVE'S OWN VERBS WITHDRAW A WORD. Declared at the operation, scoped to this
    #   store, and unambiguous because no lab operation shares them.
    for said in ("forget kaya", "unlearn kaya", "discard kaya"):
        st = taught()
        A.apply_effects(A.effect_of(said, board, store=st), store=st)
        check(f"{said!r} withdraws it", st.known("kaya") is None)

    # ⇒⇒ **AND A LAB DELETER OVER A WORD WE WERE ONLY TAUGHT IS A QUESTION, NEVER A GUESS.**
    #   The operator: *"erase is a deleting verb not a forgetting one … we can also use context
    #   to understand what the user is demanding but we can also ASK."* `delete kaya` is one
    #   sentence and two operations, and only one of them can be undone.
    for said in ("delete kaya", "remove kaya"):
        st = taught()
        eff = A.effect_of(said, board, store=st)
        check(f"{said!r} asks rather than guessing",
              [e["op"] for e in eff] == [A.AMBIGUOUS_REMOVAL])
        A.apply_effects(eff, store=st)
        check(f"and {said!r} changed nothing while it asks", st.kind_of("kaya") == "vm")

    # ⇒ AND A PROHIBITION ABOUT THE LAB IS NOT A STATEMENT ABOUT THE WORD.
    st = taught()
    check("`don't delete kaya` touches the archive not at all",
          not A.effect_of("don't delete kaya", board, store=st))

    # ⇒ A DENIAL ABOUT A WORD NOBODY TAUGHT IS NOISE, NOT A CORRECTION.
    check("a denial with nothing on file does nothing",
          not A.effect_of("zzz isnt a vm", board, store=A.Archive()))

    # ⇒⇒ **AND A CONDITION IS NOT AN ASSERTION.** *"if kaya is a vm, launch it"* predicates
    #   exactly like a statement and asserts nothing — filing it would teach a permanent fact
    #   from a sentence that named a CASE. It was already safe by accident (the conjunction
    #   survived the determiner strip and made the subject two words); a guard that holds
    #   because of an unrelated rule vanishes the first time that rule changes.
    for said in ("if kaya is a vm, launch it",
                 "if the vm is stopped, launch it",
                 "unless db is running, stop it"):
        check(f"a conditional teaches nothing — {said[:34]!r}",
              not A.effect_of(said, board, store=A.Archive()))


def test_a_declaration_governs_and_is_only_proposed():
    """The other half of the statement type — *"never delete a vm without asking me"*.

    ⇒⇒ **IT WAS A FALSE SERVE UNTIL 2026-08-16.** *"prod vms must always keep a snapshot"*
      read as `directive-act` and would have TAKEN A SNAPSHOT NOW — carrying out, once, a
      sentence that was legislating forever.

    ⇒ **AND IT IS PROPOSED, NEVER SIGNED, WHICH IS THE OPPOSITE OF THE ARCHIVE ON PURPOSE.** A
      statement that TEACHES is signed on the spot: the operator's own words are the signature,
      and a wrong entry is repairable by teaching. A statement that GOVERNS is not, because a
      rule constrains every future act and the contract already has a formal amendment path.
      `proposals.py`'s own note: *"The AI can propose but never enact."*
    """
    from orchestrator.seam import governing as G, speech_act as SA
    from planner.formula.legal import Board
    board = Board()

    for said in ("never delete a vm without asking me",
                 "prod vms must always keep a snapshot",
                 "snapshots are never to be deleted without asking me"):
        check(f"a rule reads as a DECLARATION — {said[:38]!r}",
              SA.DECLARATION in [a for _, a in SA.read(said, board)])
        check(f"and it is proposed — {said[:38]!r}", G.rules_from(said, board))

    # ⇒ THE SUBJECT IS THE WHOLE DIFFERENCE, exactly as it is for the whimperative: a deontic
    #   over the ADDRESSEE obliges us NOW; over a class it binds forever.
    check("`you should stop the vms` is an ORDER, not a rule",
          SA.verdict("you should stop the vms", board) == SA.ORDER)
    check("and it proposes nothing", not G.rules_from("you should stop the vms", board))

    # ⇒⇒ **AND A UNIVERSAL IN SUBJECT POSITION OVER A NON-COPULA VERB IS A RULE TOO.** *"from
    #   now on every new vm gets the 'fleet' label"* carries no modal and no frequency adverb
    #   and is plainly legislation. Three tests, each load-bearing — see `speech_act` 3a-ii.
    for said in ("from now on every new vm gets the fleet label",
                 "every new vm gets the fleet label"):
        check(f"a class-binding rule is read — {said[:38]!r}", G.rules_from(said, board))
    check("but a FACT about the class is not a rule — 'every vm is running'",
          not G.rules_from("every vm is running", board))
    check("and an ORDER over the class is not either — 'put every vm on a network'",
          not G.rules_from("put every vm on a network called core", board))

    # ⇒⇒ **AND THIS STORE'S OWN FRAME, DECLARED AT THE OPERATION.** *"treat prod as
    #   read-only"* carries no closed-class marker at all — no modal, no frequency adverb, no
    #   universal — and is plainly legislation. `CONTRACT_VERBS` declares that in THIS system
    #   `treat X as Y` names an act of governing, the same move `OPERATION_VERBS` makes for
    #   `forget`. A fact about the system, which the admission test accepts.
    for said in ("treat prod as read-only", "regard prod as read-only",
                 "consider db as critical"):
        check(f"a declared contract frame is read — {said[:34]!r}", G.rules_from(said, board))
    check("the `as` complement is required — 'treat it carefully' assigns nothing",
          not G.rules_from("treat it carefully", board))
    # ⇒ ⚠ AND A DECLARED VERB CAN NEVER SHADOW ONE THE LAB OWNS. Same `X as Y` shape, and
    #   `mark` IS a manifest verb (`mark_as_template`), so it stays an ORDER.
    check("`mark alpha as a template` is still an order, not a rule",
          not G.rules_from("mark alpha as a template", board))

    # ⇒ AND AN ORDINARY ORDER IS UNTOUCHED — no rung carries a modal, so the ladder cannot move.
    for said in ("stop every vm", "create a vm named alpha", "don't delete the vms"):
        check(f"{said!r} proposes no rule", not G.rules_from(said, board))

    from tests.bench.rungs import RUNGS
    noisy = [r.n for r in RUNGS if G.rules_from(r.goal, board)]
    check(f"silent on every literal rung — {noisy or 'all 14'}", not noisy)


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "archive")


if __name__ == "__main__":
    sys.exit(main())
