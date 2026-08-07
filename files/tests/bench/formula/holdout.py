"""THE HELD-OUT SET — written and committed BEFORE the formula was finished.

The operator, 2026-08-07: *"the real test for the formula is to get a response it's not
familiar with, and see it spew the number."*

The fourteen rungs are the TRAINING SET. Every slot in `slots.py` was chosen by looking at
them, so the formula reconstructing them proves only that it was fitted to them. These
twenty are requests it has never seen, and each one carries a PREDICTION made in advance:

    FITS    the nine slots should express this, and the derived key should be sane
    BREAKS  I expect this to fail, and I am naming the reason NOW so that it cannot be
            rationalised afterwards

A held-out set where everything passes is a badly written held-out set. Ten of these are
here because I think they break it — the ones marked BREAKS are the ones worth the money,
because each names a slot the vocabulary does not have.

RULE: nothing in this file may be edited after it is committed. If the formula fails a row,
the formula changes, or the row is recorded as a known limit. The row does not change.
"""
from typing import NamedTuple, Optional


class Held(NamedTuple):
    n: int
    request: str
    verdict: str            # FITS | BREAKS
    because: str            # the prediction, made in advance
    expect: Optional[dict] = None    # the slots I predict, where I predict any


HELD_OUT = [
    # ── things I expect the vocabulary to carry ────────────────────────────────────────
    Held(1, "delete the vm named scratch", "FITS",
         "destruction is not a slot — it is a COUNT OF ZERO, and the corpus already has "
         "eq:0 at rung 5. If this needs a new slot the count model is wrong.",
         {"subject": "vm", "filter": {"name": "scratch"}, "count": ("eq", 0)}),

    Held(2, "make sure no machine is left running", "FITS",
         "same shape as rung 5 with the filter inverted; a straight subject+filter+count.",
         {"subject": "vm", "filter": {"status": "running"}, "count": ("eq", 0)}),

    Held(3, "give every vm on the dmz network the label 'quarantine'", "FITS",
         "subject+filter+target, the second most common signature in training.",
         {"subject": "vm", "filter": {"network": "dmz"}, "target": {"label": "quarantine"}}),

    Held(4, "there should be at most three machines with the 'test' label", "FITS",
         "a comparator the training set never pairs with this signature. `max` exists in "
         "CMP but subject+filter+count[max] is an UNSEEN KEY — the first real test of "
         "whether the comparator belongs inside the count slot.",
         {"subject": "vm", "filter": {"label": "test"}, "count": ("max", 3)}),

    Held(5, "stop everything except the domain controller", "FITS",
         "subject+except+target. Rung 8 and rung 10 both have it.",
         {"subject": "vm", "except": {"name": "dc"}, "target": {"status": "stopped"}}),

    Held(6, "check whether the gateway answers", "FITS",
         "subject+filter+fact. Rung 11 has subject+fact but never with a filter — an "
         "unseen key built from seen parts, which is exactly what a formula should absorb.",
         {"subject": "vm", "filter": {"name": "gateway"}, "fact": "alive"}),

    Held(7, "clone web into two copies", "FITS",
         "the `source` slot, which EXISTS IN THE VOCABULARY AND NEVER FIRES IN TRAINING — "
         "rung 10 bakes the clone arithmetic into a literal 4 instead. If this works, the "
         "held-out set has found a defect in the TRAINING data, not in the formula.",
         {"subject": "vm", "source": "web", "count": ("eq", 2)}),

    Held(8, "take a snapshot of the db machine", "FITS",
         "rung 12's signature narrowed by a name instead of a status.",
         {"subject": "vm", "filter": {"name": "db"}, "makes": ("snapshot", "vm")}),

    Held(9, "put alpha, beta and gamma all on the same network", "BREAKS",
         "THREE NAMED SUBJECTS AND ONE SHARED UNNAMED TARGET. `filter` is a conjunction, "
         "so it cannot say name IN (a,b,g); and the network is existentially quantified — "
         "'the same one' names no value. Missing: a set-valued filter and a SKOLEM target.",
         None),

    Held(10, "make sure the red group and the blue group cannot reach each other", "BREAKS",
          "`predicate` is positive-only. There is no negation of a relation, and no way to "
          "say a relation holds BETWEEN two named sets rather than within one. Rung 6 keeps "
          "its groups apart only by accident, because rednet and bluenet differ by name.",
          None),

    Held(11, "every network should have at least two machines on it", "BREAKS",
          "A COUNT NESTED UNDER A UNIVERSAL. subject=network, and then a count over a "
          "DIFFERENT kind scoped per member. The vocabulary is flat: one subject, one "
          "count. This needs the count to take a subject of its own.",
          None),

    Held(12, "rename the machine called old to new", "BREAKS",
          "the same attribute appears as both filter and target on one identity — "
          "filter={name:old}, target={name:new} — which the formula will happily encode "
          "and which is a CONTRADICTION under any set reading. Gate 3's job, not the "
          "formula's, but the formula should not be able to spell it.",
          None),

    Held(13, "restore db from its latest snapshot", "BREAKS",
          "`source` is a NAME. 'its latest snapshot' is a derived reference — a selector "
          "over a second kind, ordered by time. No slot holds a query.",
          None),

    Held(14, "create a vm and put it on the same network as web", "BREAKS",
          "a target whose VALUE is a query against another entity, not a literal. The "
          "hallucination memory says the model sinks exactly this into an invented name.",
          None),

    Held(15, "shut down half the machines", "BREAKS",
          "a count RELATIVE to the current population. `count` holds a literal integer; "
          "there is no way to say a proportion, and computing it needs the world.",
          None),

    Held(16, "first take a snapshot of every vm, then upgrade them", "FITS",
          "two moves with an explicit ordering word. The interesting part is whether the "
          "FOLD derives the order without being told — if it needs the word 'first', the "
          "claim that edges recover order is false.",
          None),

    Held(17, "put the three biggest vms on their own network", "BREAKS",
          "'biggest' is a ranking over an attribute nobody declared, and 'the three' is a "
          "count that SELECTS rather than asserts. Selection-by-rank is absent.",
          None),

    Held(18, "make sure db is not on the core network", "FITS",
          "a NEGATIVE target. I expect this to encode as subject+filter+except or as a "
          "count of zero — and I am genuinely unsure which, which makes it worth having.",
          {"subject": "vm", "filter": {"name": "db", "network": "core"}, "count": ("eq", 0)}),

    Held(19, "give each vm its own private network", "BREAKS",
          "a network PER member, so `makes` should carry it — but makes was built for "
          "snapshots, whose link points back at the vm. Here the new thing is a network "
          "and the vm must JOIN it, which is a target on the maker's output.",
          None),

    Held(20, "get the lab back to how it was this morning", "BREAKS",
          "no slot holds a time, a baseline, or a diff. Recorded because a real operator "
          "says this, and because the formula should REFUSE it rather than approximate it.",
          None),
]

FITS = [h for h in HELD_OUT if h.verdict == "FITS"]
BREAKS = [h for h in HELD_OUT if h.verdict == "BREAKS"]
