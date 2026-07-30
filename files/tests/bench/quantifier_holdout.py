"""A HELD-OUT corpus for the quantifier, written BEFORE the rule that will be scored on it.

WHY THIS FILE EXISTS SEPARATELY. `CLAUSES` in `quantifier_probe` is the corpus the
attribute-modifier rule (E7) was PROTOTYPED against, and a pattern tuned until it scores
full marks on the sixteen clauses that produced it demonstrates nothing — that is the
benchmark-gaming line the operator drew on 2026-07-25. These ten were written first,
committed first, and are not to be edited to accommodate a rule that fails them. If a rule
fails one of these, the rule is wrong or the TAXONOMY is wrong; the clause stays.

THE KEY IS ASSIGNED BY THE SAME FOUR DEFINITIONS `quantifier_probe` uses, and nothing else:

    all     the whole kind, with no filter of any shape
    any     a condition picks the members, and a NEGATIVE condition is still a condition
    single  one identified object, however much else the goal mentions
    not     a whole is NAMED and a member is subtracted from it

TWO OF THESE ARE EXPECTED TO BE HARD, and they are here on purpose rather than in spite of
it. A held-out set assembled from cases the rule will pass is a stacked deck:

  * `archive every red vm` — a LABEL filter. The manifest's entire closed vocabulary is
    ['false', 'running', 'stopped', 'true', 'unknown'], so a value-driven rule cannot see
    `red` at all and will answer `all`. This is the ceiling of the whole approach, and it
    is rung 6's own shape — "put the red ones together" — so it is the case that decides
    whether E7 is worth wiring.
  * `tag all of them with 'prod'` — the mirror. A vocabulary value appears, but as the
    OBJECT of the action rather than a modifier of the quantified set, so the answer is
    `all`. A rule that fires on any recognised value anywhere in the clause breaks here.

The lab vocabulary is the ladder's own: vms and networks, `status` running/stopped, labels
like red/prod/fleet/derived, and the named machines golden, db, web, alpha.
"""
from typing import List, Tuple

# (clause, quantifier) — balanced 3 all / 3 any / 2 not / 2 single so that no constant
# answer can score well. Always-`all` scores 3/10 here; always-`any` scores 3/10.
HOLDOUT: List[Tuple[str, str]] = [
    # ── all: the whole kind, unfiltered ────────────────────────────────────────────────
    ("connect each vm to the management network", "all"),
    ("give every machine the 'audited' label", "all"),
    # The vocabulary value is the OBJECT, not a filter on the set being quantified.
    ("tag all of them with 'prod'", "all"),

    # ── any: a condition picks the members ─────────────────────────────────────────────
    # The E7 target shape: the filter is an ADJECTIVE on the head noun.
    ("restart every stopped machine", "any"),
    # The same filter written as a relative clause, which the model already handles.
    ("shut down all vms that are running", "any"),
    # A LABEL filter — outside the manifest's declared vocabulary. Expected to be hard.
    ("archive every red vm", "any"),

    # ── not: a whole is named, a member subtracted ─────────────────────────────────────
    ("every vm apart from golden gets the 'derived' label", "not"),
    ("reboot all machines other than db", "not"),

    # ── single: one identified object ──────────────────────────────────────────────────
    ("start the vm called alpha", "single"),
    ("move web onto the dmz network", "single"),
]

BY_KIND = {k: sum(1 for _t, q in HOLDOUT if q == k)
           for k in ("all", "any", "single", "not")}
FLOOR = max(BY_KIND.values())  # what a constant answer scores: 3/10
