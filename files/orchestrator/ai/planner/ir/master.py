"""
master.py — the SCHEMA MASTER: the one authority on what the model is offered.

THE PROPERTY, and everything here follows from it:

    A fact the harness already knows must reach the model as a CONSTRAINT,
    never as a description.

The context assistant DESCRIBES — it computes prose guidance and hopes the model heeds it,
which is advisory, phrasing-sensitive, and a vocabulary. The master CONSTRAINS: the decoder
cannot emit what it is not offered. Same information, different physics, and the difference
is measured. Every time a rule moved from prose to schema, a failure class disappeared:
`status` as free text let the decoder invent `'not running'` (matched nobody, ran zero
calls, reported ok); as an enum it stopped. `NOT`'s operand disagreed between schema and
validator and cost two rungs. Binding names had no pattern and `red-net` could be bound but
never read.

WHY IT HAS TO BE ONE MODULE. Six places build something the model sees, and they all read
`config.OPS` independently — two statement-schema forms, two prompt listings, the per-op
statement tools, and the bench's constrained-decoding schema. Six readers of one table is
how the four-way disagreements happen: a construct offered in one place, withheld in
another, and validated in a third. Anything that narrows what may be said belongs HERE, and
every builder asks.

WHAT THIS MODULE IS NOT: it does not judge a program. Deciding whether an authored program
should RUN is the schema gate's job, and the split is structural rather than stylistic — a
schema can constrain what MAY be emitted and cannot compel that something IS. "Every
identifier the operator named appears somewhere" is a MUST, unexpressible as schema, and so
it belongs to the gate.

THE DISCIPLINE: constrain what is CLOSED, never what is open. A label is open text; a
status is not. Over-constraining caps the system at the harness's imagination — and there is
a measurement against exactly that: narrowing the offered tool set from 46 to 4 made
llama3.1 hallucinate `os_type` in four runs of four, where the full set resolved it
correctly four of four (2026-07-17, recorded in `narrow_tools`). The fuller context anchors
a weak model. When uncertain, offer and validate rather than restrict.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config, intent as _intent


def ops(want: Optional[str] = None) -> List[str]:
    """The ops that may be offered under the operator's intent.

    THE FIRST THING MOVED FROM DESCRIPTION TO CONSTRAINT, and it is a relocation rather
    than a new rule. `intent.violations()` already refuses a program that reaches above its
    rung — but it refuses it AFTER authoring, so a `fetch` intent is handed `new`, the model
    writes a program that creates machines, and the whole thing is thrown away. Offering
    only the permitted ops makes that program unrepresentable instead of rejected.

    The rung is the operator's and is never inferred (decision 5): supplied by prefix, by a
    marker they already used, or by one question, and defaulting to `fetch` when there is
    nobody to ask. `None` here means no intent was supplied, and then nothing is narrowed —
    an absent fact must not become a silent restriction.
    """
    allowed = _intent._PERMITS.get(want) if want else None
    if allowed is None:
        return list(config.OPS)
    return [op for op in config.OPS if op in allowed]


def identifiers(goal: str = "", known: Optional[set] = None,
                minted: Optional[set] = None) -> List[str]:
    """Names a program may legitimately refer to — the UNION, never a restriction.

    Three sources, and all three are needed:
      * tokens literally in the goal      the operator said `core`, so `core` is sayable
      * names already in the lab          it may attach to something that exists
      * names `NEW` will mint             a program refers to what it is about to create

    UNION rather than restrict-to-the-goal, deliberately. If the operator says "call it web"
    and the enum were `[web]`, a program that legitimately needs a second machine would have
    nowhere to go — the harness would have capped what can be built at what it predicted.
    What the union still kills is the case that actually bit: `core_net` is in none of the
    three, so a creator silently renaming the operator's `core` becomes unrepresentable.

    Returns [] when there is nothing to say, which callers must read as "do not constrain"
    rather than "no names are legal".
    """
    out: List[str] = []
    for name in _goal_tokens(goal) + sorted(known or ()) + sorted(minted or ()):
        if name and name not in out:
            out.append(name)
    return out


def _goal_tokens(goal: str) -> List[str]:
    """Identifier-shaped words in the goal, in the order they appear.

    Deliberately crude and deliberately NOT a vocabulary: no trigger words, no slot
    patterns, no attempt to work out which token is a name. It collects what could be an
    identifier and lets the union carry the rest. The moment this starts trying to decide
    "this one is the VM's name" it becomes the thing it replaces — the context assistant
    extracts slots by regex and, until it was fixed, read `os_type=mac` out of the word
    "machine".
    """
    import re
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", goal or "")
    stop = _stopwords()
    return [w for w in words if w.lower() not in stop and len(w) > 1]


def _stopwords() -> set:
    """Ordinary English that is never a resource name, plus the language's own words.

    Kept small on purpose. A big list is a vocabulary that drifts; a small one leaves a few
    harmless extra names in an enum, which costs nothing because the enum is a union.
    """
    lang = {op for op in config.OPS} | {s for s in config.PREDICATES} | {
        str(v).lower() for v in config.SURFACE.values() if isinstance(v, str)}
    return lang | {
        "a", "an", "the", "and", "or", "of", "to", "on", "in", "at", "it", "its", "them",
        "they", "all", "each", "every", "any", "that", "this", "with", "for", "from",
        "make", "made", "create", "creates", "put", "puts", "set", "sets", "give", "gives",
        "then", "so", "up", "out", "into", "one", "two", "three", "four", "five", "is",
        "are", "be", "been", "can", "should", "must", "sure", "please", "want", "need",
        "vm", "vms", "machine", "machines", "box", "boxes", "host", "hosts", "network",
        "networks", "net", "nets", "label", "labels", "tag", "tags", "name", "named",
        "called", "currently", "already", "not", "no", "if", "when", "while", "just",
    }


def sources(known: Optional[set] = None) -> List[str]:
    """What a `NEW ... FROM x` may copy — and this one really is CLOSED.

    Unlike a name in general, a copy source is not open: you cannot copy something that
    does not exist, so the set is exactly what the lab holds. The validator has always
    said so — *"`from` copies an EXISTING vm — there is no vm named 'red'. A label is not
    a source."* — and `from` is the one field naming something the program neither creates
    nor binds, which is why it was the one field that could be checked at all.

    Relocating it is the same move as `ops()`: the rule does not change, only when it
    fires. `NEW vm FROM red`, red being a label rather than a machine, currently costs a
    full authoring round to discover; as an enum the decoder cannot write it.

    MATCHES THE VALIDATOR EXACTLY, including the part that looks like an omission: a name
    minted EARLIER IN THE SAME PROGRAM is not a legal source today, and it is not added
    here. Whether it should be is a separate question with a separate answer; making the
    schema more permissive than the validator would just move the rejection back to where
    it already was, with the decoder and the validator disagreeing in between.

    Empty when the lab is unknown, which callers read as "do not constrain" — a `from`
    checked against a world nobody supplied would forbid every source there is.
    """
    return sorted(known or ())


def constraints(want: Optional[str] = None, goal: str = "",
                known: Optional[set] = None, minted: Optional[set] = None) -> Dict[str, Any]:
    """Everything the master narrows, in one object, for a builder to apply.

    One call so a builder cannot honour half of it. `values` comes straight from the
    manifest via `config.values_for` and is included here so that every constraint arrives
    through one door, even the ones the master did not have to compute.
    """
    return {
        "ops": ops(want),
        "identifiers": identifiers(goal, known, minted),
        "sources": sources(known),
        "values": {kind: {attr: config.values_for(kind, attr)
                          for attr in config.queryable(kind)
                          if config.values_for(kind, attr)}
                   for kind in config.KINDS},
    }
