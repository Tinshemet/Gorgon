"""A HELD-OUT corpus for new-vs-call, written BEFORE the rule that will be scored on it.

`route_menu_probe.CELLS` is seven cells, and a rule keyed on the leading verb scores 7/7 on
it immediately — which is why it cannot be the evidence. These fourteen were written first
and committed first, and are not to be edited to accommodate a rule that fails them.

THE DISTINCTION, from the manifest's own definitions:

    new    the statement BRINGS AN OBJECT INTO EXISTENCE. `NEW` supplies the name and calls
           the creator; the object did not exist before this statement.
    call   the statement INVOKES A TOOL ON SOMETHING ALREADY THERE — including something an
           earlier sibling created a moment ago.

FIVE ARE BUILT TO BREAK A LEADING-VERB RULE, because that is the rule anyone writes first
and it is the one the tuning corpus rewards:

  * "add a second disk to web"     — ADD sounds like creation, and `disk` is not a kind.
  * "take a copy of golden"        — TAKE, but it brings a new vm into existence.
  * "set up a network called dmz"  — SET UP is a creation verb the tuning corpus never uses,
                                     and 'set up' missing from one regex already cost this
                                     project a rung (see rungs.py on --paraphrase).
  * "build the lab network"        — BUILD, creation, phrased as though the thing is known.

ONE KEY WAS CORRECTED AFTER SCORING, 2026-07-30, and it is recorded here rather than
quietly changed. I committed "create a snapshot of web" as `call`, on the stated reasoning
that snapshotting is a tool call on an existing vm. THE MANIFEST DECLARES `snapshot` A KIND
— config.KINDS is ['vm', 'network', 'snapshot'] — so `NEW snapshot(...)` brings an instance
of a declared kind into existence and `new` is correct. I asserted a manifest fact without
reading the manifest, which is the same habit that produced two other corrections today.

The clause STAYS, with the right answer. The rule scored 13/14 against the key as
committed and 14/14 against the corrected one; both numbers are reported in the commit,
because a key edited after seeing a result has to justify itself independently — and this
one does: anyone reading config.KINDS would key it `new` without knowing a rule exists.

The rest are ordinary cases in both directions so a constant answer cannot score: always
`call` gets 7/14, always `new` gets 7/14.

Each cell carries the same shape as the tuning corpus — (goal, want, parent, done) — because
the earlier-siblings context is the other half of the question: a goal naming something an
earlier step created is a `call` however it is phrased.
"""
from typing import List, Tuple

# (goal, want, parent goal, what earlier steps already did)
HOLDOUT: List[Tuple[str, str, str, List[str]]] = [
    # ── call: acting on something already there ────────────────────────────────────────
    ("add a second disk to web", "call",
     "give web more storage", ["create a vm named web"]),
    ("start it", "call",
     "make a box called beta, then start it up", ["create a vm named beta"]),
    ("put the red ones on the red network", "call",
     "put the red ones together on their own network",
     ["create a network called red"]),
    ("give vm1 the 'prod' label", "call",
     "tag three machines 'prod'", ["create a vm named vm1"]),
    ("shut down the last machine", "call",
     "stop everything that is running", ["create a vm named vm3"]),
    ("wire the machines together on one network", "call",
     "take 5 vms and wire them together", ["create a network called fleet"]),

    # CORRECTED KEY — see the note above: `snapshot` is a declared kind, so this is a NEW.
    ("create a snapshot of web", "new",
     "snapshot every vm in the lab", ["create a vm named web"]),

    # ── new: bringing an object into existence ─────────────────────────────────────────
    ("take a copy of golden", "new",
     "take a copy of golden three times over and boot them", []),
    ("set up a network called dmz", "new",
     "put db on its own network", []),
    ("build the lab network", "new",
     "create an isolated network named lab", []),
    ("provision another machine", "new",
     "spin up five machines", ["create a vm named vm1"]),
    ("make a box called beta", "new",
     "make a box called beta, then start it up", []),
    ("clone golden once more", "new",
     "clone golden into 3 new vms", ["clone golden into a new vm"]),
    ("spin up a machine and call it alpha", "new",
     "spin up a machine and call it alpha", []),
]

BY_WANT = {k: sum(1 for _g, w, _p, _d in HOLDOUT if w == k) for k in ("new", "call")}
FLOOR = max(BY_WANT.values())  # a constant answer scores 7/14
