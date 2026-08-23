"""A LATER MENTION BINDS BY NUMBER AGREEMENT (operator ruling 08-23, ledger #18).

"'those' is plural, and the only plural here is '3 vms' — it should be paired based on the
plurality." Model-free; pass 1 is code.
"""
import engines.channel as channel
from planner.formula.legal import Board
from orchestrator.languages.english.seam import pass1 as P1, proforms as PF

B = Board()


def _rows(s):
    was = channel.constrained
    channel.constrained = lambda *a, **k: {}
    try:
        return P1.run_scanned(s, board=B)
    finally:
        channel.constrained = was


def _bindings(s):
    return {m["text"]: (r.span, m["bound"])
            for r in _rows(s) for m in (r.mentions or ())}


def test_nl_0004_those_pairs_with_the_only_plural_and_it_with_the_only_singular():
    b = _bindings("create 3 vms named after musicians and a network called the stadium "
                  "and add those vms to it")
    assert b["those vms"] == ("3 vms", True)
    assert b["it"] == ("a network", True)


def test_agreement_beats_recency():
    # recency would bind `them` to the network (the last thing); number says the vms
    b = _bindings("create 3 vms and a network, then stop them")
    assert b["them"] == ("3 vms", True)


def test_a_tie_binds_nothing_and_is_carried_with_its_hint():
    rows = _rows("create a vm and a network, then stop it")
    assert all(not m["bound"] for r in rows for m in (r.mentions or ()))
    asks = PF.unbound(rows)
    assert len(asks) == 1 and "'it' could be a vm or a network" in asks[0]


def test_the_noun_breaks_a_tie_among_plurals():
    b = _bindings("create 3 vms and 2 networks, then stop those vms")
    assert b["those vms"] == ("3 vms", True)


def test_a_phrases_own_head_is_not_a_mention():
    # `the blue ones` is its own certified span; its `ones` is not a reference to the red vms
    assert _bindings("label the red vms 'ready' and launch the blue ones") == {}


def test_a_mention_that_is_already_a_row_is_left_to_its_rule():
    rows = _rows("ping every vm and stop the ones that do not answer")
    assert [r.span for r in rows if r.kind != "value"] == ["every vm", "the ones that do not answer"]
    assert all(not (r.mentions or ()) for r in rows)


def test_a_full_phrase_mention_is_reported_as_a_span_and_a_bare_pronoun_is_not():
    from tests.bench.read_eval.runner import read_case
    was = channel.constrained
    channel.constrained = lambda *a, **k: {}
    try:
        r = read_case("create 3 vms named after musicians and a network called the stadium "
                      "and add those vms to it", board=B)
    finally:
        channel.constrained = was
    spans = [(x["span"], x["start"], x["end"]) for x in r["rows"]]
    assert ("those vms", 76, 85) in spans
    assert not any(x["span"] == "it" for x in r["rows"])


def test_the_tie_reaches_the_operator():
    from orchestrator.languages.english.seam import pipeline as PL
    was = channel.constrained
    channel.constrained = lambda *a, **k: {}
    try:
        r = PL.run("create a vm and a network, then stop it", board=B)
    finally:
        channel.constrained = was
    assert any("'it' could be" in a for a in r.asks), r.asks
