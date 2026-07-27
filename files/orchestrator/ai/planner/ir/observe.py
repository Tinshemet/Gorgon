"""
observe.py — reading an OBSERVED attribute, and the one rule that governs it.

Decision 6, settled 2026-07-27. The question was what may escape a `foreach` iteration,
so that a fleet-wide judgement can be built out of per-member call results — *"ping every
machine, and if any of them failed to answer, stop the whole rollout."* The answer chosen
was that **nothing escapes**: the loop probes, the findings ledger remembers, and a later
`SELECT` reads it back. So the language gained no accumulator, no new op and no second
data type; its one data type is still a set of names.

The precedent was already load-bearing rather than invented for this. The `reach`
predicate reads the findings ledger and not the registry, precisely because reachability
is DISCOVERED by asking and is never inferred from a tool reporting success. An observed
attribute is that one predicate generalised into the query form.

THE RULE, and it is the whole reason this module exists rather than a line in each
`select`: an observed attribute is **three-valued** — `true`, `false`, `unknown` — and
**unknown matches neither of the others**. A machine nobody probed is not alive and is not
dead. It is unasked.

Collapsing unknown into false is the tempting shortcut and it is the false-success class
wearing a query for a disguise: `SELECT vm WHERE alive = 'false'` would come to mean
"everything I never looked at", and a program acting on that set would stop machines it
had no evidence against. Keeping the third value also makes the honest clause SAYABLE,
which is the part that protects a goal:

    ACHIEVE COUNT(SELECT vm WHERE label = 'fleet' AND alive = 'unknown') = 0;

That asserts every member was actually asked. Without it, a program that probes nothing at
all satisfies `COUNT(... AND alive = 'false') = 0` trivially and closes green over a fleet
it never touched — the same shape as a node closing green over a world that is plainly
wrong, which is what this layer exists to refuse.

The ledger is INJECTED, not imported. The bench drives a `Findings` populated through the
production yield schema; the orchestrator will drive the run's real one. Anything with
`has(fact)` and `get(fact)` satisfies it, which keeps this module free of any opinion
about where observations are stored.
"""
from __future__ import annotations

from typing import Any, Optional

from . import config

TRUE, FALSE = "true", "false"


def unknown() -> str:
    """The value meaning nobody has asked. From the manifest, so the spelling is data."""
    return config.OBSERVED_UNKNOWN


def value(ledger: Any, kind: str, attr: str, member: str) -> Optional[str]:
    """One member's observed attribute as `true` / `false` / `unknown`.

    None — distinct from `unknown` — when `attr` is not an observed attribute of `kind` at
    all. The caller needs to tell "this is a registry attribute, go read the registry"
    apart from "this is observed and nothing has asked yet", and one of those is a routing
    question while the other is an answer.
    """
    fact = config.fact_key(kind, attr, member)
    if fact is None:
        return None
    if ledger is None or not ledger.has(fact):
        return unknown()
    return TRUE if ledger.get(fact) else FALSE


def matches(ledger: Any, kind: str, attr: str, member: str, wanted: Any) -> Optional[bool]:
    """Does this member's observed attribute equal `wanted`?

    None when `attr` is not observed for this kind, so a `select` can fall through to its
    registry handling with one check rather than repeating the manifest lookup.

    Equality, deliberately — including against `unknown`, which is what makes "which
    machines has nobody asked about" a query rather than a special form. Because it is
    plain equality over three values, the rule that unknown does not match `true` or
    `false` needs no code of its own: it simply is not equal to them.
    """
    got = value(ledger, kind, attr, member)
    if got is None:
        return None
    return got == str(wanted).lower()


def is_observed(kind: str, attr: str) -> bool:
    """Is this attribute learned by asking rather than stored?"""
    return attr in config.observed(kind)
