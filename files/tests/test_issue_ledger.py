"""test_issue_ledger.py — B1 AND B2 ARE ONE OBJECT, AND THIS IS THE ROUND TRIP.

The operator, 2026-08-13: *"let's do the issue ledger, that dissolves B1 and B2 together."*

    B2 was  "nothing consumes an operator reply"
    B1 was  "an answered ASK should be kept globally, clarified ONCE, model-independent"

An ASK that is RECORDED, stays open until somebody answers, and is REMEMBERED afterwards is
both. Built as two items they would have been two stores.

⇒ THE TESTS BELOW ARE THE LIFECYCLE, plus the two refusals that make the store safe: the world
  still outranks it, and a WORLD answer is never replayed.
"""
import pathlib
import tempfile

from tests.bench.twopass import asking, issues

_FAIL = 0


def check(label, ok):
    global _FAIL
    if not ok:
        _FAIL += 1
    print(f"    {'ok  ' if ok else 'FAIL'}  {label}")


def test_the_round_trip_open_answered_remembered():
    print("\n[issues] a question is raised, answered once, and known thereafter")
    led = issues.Issues()
    led.raise_("kind-not-settled", "jumpbox", "what is a jumpbox?")
    check("it starts open", [i.word for i in led.open()] == ["jumpbox"])
    check("and has no answer to give yet", led.answers() == {})

    led.answer("jumpbox", "a jumpbox is a vm")
    check("answering closes it", led.open() == [])
    check("and it is now known", led.answers() == {"jumpbox": "a jumpbox is a vm"})


def test_the_same_question_twice_is_not_asked_twice():
    """*Clarified ONCE* is the whole point — the second sighting must not reopen it."""
    print("\n[issues] asking again does not lose the answer")
    led = issues.Issues()
    led.raise_("kind-not-settled", "jumpbox", "what is a jumpbox?")
    led.answer("jumpbox", "a vm")
    again = led.raise_("kind-not-settled", "jumpbox", "what is a jumpbox?")
    check("it stays answered", again.status == issues.ANSWERED)
    check("and counts that it came up again", again.seen == 2)
    check("and still answers", led.answers() == {"jumpbox": "a vm"})


def test_a_world_answer_is_never_replayed():
    """THE SAFETY PROPERTY OF A PERSISTENT STORE.

    *"A jumpbox is a vm"* is a fact about the LANGUAGE — true tomorrow, true for a different
    model, true in a different lab, which is exactly what *"clarified once"* means. *"Yes, create
    it"* is a fact about ONE REQUEST'S WORLD, and replaying it would build machines on a decision
    made about a different sentence last week.

    They are told apart by the RULE that asked — a lookup, not a judgement about the words.
    """
    print("\n[issues] language answers persist; world answers do not")
    led = issues.Issues()
    led.raise_("kind-not-settled", "jumpbox", "what is it?")
    led.raise_("not-there", "jumpbox", "should it be created?")
    led.answer("kind-not-settled:jumpbox", "a vm")
    led.answer("not-there:jumpbox", "yes, create them")
    check("the language answer is remembered", led.answers().get("jumpbox") == "a vm")
    check("the world answer is NOT replayed",
          "yes, create them" not in led.answers().values())


def test_it_survives_a_restart():
    """A store that forgets on restart is a cache, and B1 asked for memory."""
    print("\n[issues] answered once means answered after a restart")
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "issues.json"
        led = issues.Issues(p)
        led.raise_("kind-not-settled", "jumpbox", "what is it?")
        led.answer("jumpbox", "a vm")
        led.save()
        check("a fresh ledger reads it back",
              issues.Issues(p).answers() == {"jumpbox": "a vm"})


def test_the_ledger_files_the_WORD_not_the_phrase():
    """THE BUG THAT MADE THE FIRST LEDGER USELESS, caught by its own round trip.

    An issue was filed under `'a jumpbox named bastion'`, so answering *"a jumpbox is a vm"*
    matched nothing and the next request — *"launch every jumpbox"* — learned nothing. **A phrase
    is an artefact of one sentence; the word is what recurs**, and recurrence is the entire value
    of a store whose promise is *clarified once, globally, model-independent*.

    ⇒ FOUND BY SUBTRACTION FROM CLOSED CLASSES ONLY — the determiners, enumerators, naming cues
      and linking words `scan` already owns, plus the manifest's own operation words. No new
      list, and no content words: the third time today the word/phrase distinction has decided a
      design.
    """
    print("\n[issues] every phrasing of the same word files under one key")
    from tests.bench.formula.legal import Board
    from tests.bench.twopass.issues import word_of
    b = Board()
    for phrase in ("a jumpbox named bastion", "every jumpbox", "launch every jumpbox"):
        check(f"{phrase!r} -> jumpbox", word_of(phrase, b) == "jumpbox")
    check("'a network called core' -> core", word_of("a network called core", b) == "core")


def test_only_addressable_questions_are_filed():
    """An issue nobody can close is worse than none — it makes the real ones unreadable."""
    print("\n[issues] a question with no key is not filed as an open item")
    led = issues.Issues()

    class _Run:
        questions = [asking.Ask("kind-not-settled", "jumpbox", "what is it?"),
                     asking.Ask("", "", "something gate 4 said in prose")]

    issues.raise_from(led, _Run())
    check("the addressable one is filed", [i.word for i in led.open()] == ["jumpbox"])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{_FAIL} failed")
