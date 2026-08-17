"""test_write_back.py — B2: AN ANSWER FINDS THE ROW THAT ASKED FOR IT.

Until 2026-08-13 the chain could ask *"what is a grubnash?"* and had nowhere to put the reply.
`gates12.report` ends `"asks": [f.says for f in found …]` — the finding knows its gate, its rule
and WHAT IT IS ABOUT, and all three were discarded the moment it became a question. `run()` took
no `answers` for the same reason: there was no key to accept one against.

**That, and not storage, is what blocked the Encyclopedia.** B1 is a place to keep answers; there
were no answers to keep.

⇒ THE FOUR PROPERTIES BELOW ARE THE ONES THAT MAKE AN OPERATOR OVERRIDE SAFE. Three of them
  REFUSE to act, which is the point: this is the one authority allowed to settle a row by saying
  so, and an authority that always says yes is not an authority.
"""
import engines.channel as channel

from planner.formula.legal import Board
from orchestrator.seam import asking, pass1, pass2, pipeline as PL
from tests.bench.twopass.metrics import Lab

_FAIL = 0
REQUEST = "create a grubnash named alpha"


def check(label, ok):
    global _FAIL
    if not ok:
        _FAIL += 1
    print(f"    {'ok  ' if ok else 'FAIL'}  {label}")


def _canned(handle):
    was = channel.constrained
    channel.constrained = (lambda p, pl, s, **k:
                           {"operations": [{"operator": "create_vm", "on": handle}]}
                           if "operations" in (s.get("properties") or {}) else {})
    return was


def _rows(answers=None):
    board = Board()
    rows = pass1.settle_with_world(pass1.run_scanned(REQUEST, board=board), Lab(), board)
    settled, clashes = pass1.settle_with_answers(rows, answers or {}, board)
    return settled, board, clashes


def test_an_unknown_noun_refuses_until_it_is_answered():
    """The whole point, end to end: the same request, before and after a person answers."""
    print("\n[b2] the answer turns a refusal into a program")
    was = _canned("a_grubnash_named_alpha")
    try:
        cold = PL.run(REQUEST, board=Board(), world=Lab())
        warm = PL.run(REQUEST, board=Board(), world=Lab(),
                      answers={"grubnash": "a grubnash is a vm"})
        check(f"unanswered it refuses ({cold.outcome})", cold.outcome == PL.REFUSE)
        check(f"answered it serves ({warm.outcome})", warm.outcome == PL.SERVE)
        check("and the row is typed by what the operator said",
              all(r.object_type == "vm" for r in warm.declarations))
    finally:
        channel.constrained = was


def test_an_answer_naming_no_kind_settles_nothing():
    """*"A grubnash is a wombat"* is an answer, and it is not usable.

    Declining is the honest outcome — the same three-valued honesty a kindless row already has.
    Typing a row from a word nothing can act on would turn a clarification into a silent
    mis-settlement, which is worse than asking twice.
    """
    print("\n[b2] an answer that names no kind is declined, never guessed at")
    rows, board, clashes = _rows(
        {"a grubnash named alpha": ("kind-not-settled", "a grubnash is a wombat")})
    check("the row stays unsettled", all(r.object_type == "?" for r in rows))
    # ⇒ AND THE OPERATOR IS TOLD WHY. We cannot ground an answer — nothing here can check
    #   whether what a person said is TRUE — but we can see that it names no kind, and a
    #   clarification that vanishes silently is worse than one refused out loud.
    check(f"and told why it did not take ({clashes})",
          any("names no kind" in c for c in clashes))


def test_an_answer_never_overrides_a_lookup():
    """THE ORDERING IS THE SAFETY PROPERTY. The settler runs LAST, after the manifest, the lab
    and affordance — so it only ever fills a row nothing else could settle.

    An operator answer that could overwrite a lookup would make a stale Encyclopedia entry
    stronger than the live world, which is the wrong way round for a store whose whole value is
    that it is remembered across sessions.
    """
    print("\n[b2] a row the world already settled is not re-typed by an answer")
    board = Board()
    rows = pass1.settle_with_world(pass1.run_scanned("launch db", board=board), Lab(), board)
    before = [(r.name, r.object_type) for r in rows]
    # ⇒ KEYED BY THE ROW, NOT BY THE WORD. `asking.answered` does the word -> row translation
    #   and hands this settler keys that already name rows; calling it with a bare word (as this
    #   test first did) silently matches nothing. The two halves have different contracts on
    #   purpose — one resolves WHICH question an answer is for, the other applies it.
    settled, clashes = pass1.settle_with_answers(
        # ⇒ the row is named `db` since the 2026-08-18 span fix — the verb is the ACT and no
        #   longer part of the row's name. The old key "launch db" matched nothing, silently.
        rows, {"db": ("kind-not-settled", "db is a network")}, board)
    after = [(r.name, r.object_type) for r in settled]
    check(f"the lab's answer stands ({before} -> {after})", before == after)
    check(f"and the disagreement is reported, not swallowed ({clashes})",
          any("already settled" in c for c in clashes))


def test_an_answer_to_a_question_nobody_asked_is_ignored():
    """The Encyclopedia will hold answers for words this request never mentions.

    Applying those would settle rows on evidence the request never produced — which is
    indistinguishable from guessing, and is exactly what the anchor-and-scan design refuses.
    """
    print("\n[b2] a standing answer does not leak into an unrelated request")
    asks = [asking.Ask("kind-not-settled", "a grubnash named alpha", "what is it?")]
    check("an answer for an unmentioned word binds to nothing",
          asking.answered(asks, {"wibble": "a wibble is a vm"}) == {})
    # ⇒ THE RULE TRAVELS WITH THE ANSWER, because what an answer MEANS depends on what was
    #   asked: "yes" to *should it be created?* sets an existence, "a vm" to *what is it?* sets
    #   a kind. Inferring which from the text would be a guess where a person was explicit.
    check("and the one that WAS asked about binds, carrying its rule",
          asking.answered(asks, {"grubnash": "a vm"}) ==
          {"a grubnash named alpha": ("kind-not-settled", "a vm")})


def test_a_word_matches_on_boundaries_not_substrings():
    """`db` must not answer a question about `dbf`.

    The operator answers about a WORD and a row is named by a PHRASE — measured the moment this
    was wired, when an exactly-correct answer filed under `grubnash` bound to nothing because the
    question was about `'a grubnash named alpha'`. Matching had to widen; widening to substrings
    would have let `db` settle `dbf`.
    """
    print("\n[b2] the word, not any substring of it")
    asks = [asking.Ask("kind-not-settled", "the dbf server", "what is it?")]
    check("a shorter word inside another does not answer it",
          asking.answered(asks, {"db": "a vm"}) == {})
    check("the actual word does", asking.answered(asks, {"dbf": "a vm"}) ==
          {"the dbf server": ("kind-not-settled", "a vm")})


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{_FAIL} failed")
