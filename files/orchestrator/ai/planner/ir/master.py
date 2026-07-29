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


def ops(want: Optional[str] = None, quantifier: Optional[str] = None) -> List[str]:
    """The ops that may be offered under the operator's intent, and how many things the
    clause is about.

    TWO NARROWINGS, SAME MECHANISM, DIFFERENT OWNERS. `want` is the INTENT and belongs to
    the operator (decision 5). `quantifier` is a property of the CLAUSE — all/any/single/
    not — and is answered by a router, measured at 15/16 before this was built
    (`quantifier_probe`). Both make a wrong program unrepresentable instead of rejected;
    neither invents a rule the language did not already have.

    WHY `single` MATTERS MOST, and why it was wired first: a clause about one identified
    object licenses `call` and not `foreach`, so the offered schema contains NO `select` at
    all. Rung 8's `statement 4: select must name a kind` then cannot be written — where
    today it is written, rejected, and handed to a repair loop that turned a nearly-correct
    program into an inverted one. The manifest owns the table; this only reads it.

    Absent means absent: `None` narrows nothing, because an unsupplied fact must never
    become a silent restriction. Two supplied narrowings INTERSECT.

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
    out = list(config.OPS) if allowed is None else [op for op in config.OPS if op in allowed]
    spec = config.QUANTIFIERS.get(quantifier) if quantifier else None
    if spec:
        licensed = set(spec.get("ops") or ())
        out = [op for op in out if op in licensed]
    return out


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

    NOT CURRENTLY WIRED INTO ANY SCHEMA, and that is a conclusion rather than a gap. A
    name turns out not to be a CLOSED set: `NEW AMOUNT(5) vm` mints names nobody can know
    at authoring time, so an enum over the union would forbid legal programs to prevent a
    mistake nobody has measured. The slots it would go in agree — `args` is an untyped
    object with nowhere to put an enum, and a literal `in` list has no validator rule to
    relocate, only a new restriction to invent. `sources()` below is the identifier slot
    that IS closed, and it is enumerated. This stays because the union is the right shape
    for whatever uses it next, and because writing down why it is not used is worth more
    than deleting it and rediscovering the reasoning.

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
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", _intent.strip_prefix(goal or ""))
    stop = _stopwords()
    return [w for w in words if w.lower() not in stop and len(w) > 1]


def _stopwords() -> set:
    """Ordinary English that is never a resource name, plus the language's own words.

    Kept small on purpose. A big list is a vocabulary that drifts; a small one leaves a few
    harmless extra names in an enum, which costs nothing because the enum is a union.

    THE INTENT MARKERS COME FROM THE MANIFEST, so a word that already told the harness
    what the operator WANTS is not then read as something they NAMED. "bring up three vms
    called n1 n2 n3" was yielding `bring` as an identifier — harmless in a union, and not
    harmless at all to the gate, which scores how many of the operator's names the program
    failed to mention. Data, not a list here, so the two uses cannot drift apart.
    """
    markers = {w.split()[0] for words in (config.INTENT.get("markers") or {}).values()
               for w in words if w}
    lang = {op for op in config.OPS} | {s for s in config.PREDICATES} | {
        str(v).lower() for v in config.SURFACE.values() if isinstance(v, str)}
    return lang | markers | {
        "a", "an", "the", "and", "or", "of", "to", "on", "in", "at", "it", "its", "them",
        "they", "all", "each", "every", "any", "that", "this", "with", "for", "from",
        "make", "made", "create", "creates", "put", "puts", "set", "sets", "give", "gives",
        "then", "so", "up", "out", "into", "one", "two", "three", "four", "five", "is",
        "are", "be", "been", "can", "should", "must", "sure", "please", "want", "need",
        "vm", "vms", "machine", "machines", "box", "boxes", "host", "hosts", "network",
        "networks", "net", "nets", "label", "labels", "tag", "tags", "name", "named",
        "called", "currently", "already", "not", "no", "if", "when", "while", "just",
    }


def named(goal: str = "") -> List[str]:
    """Names the operator EXPLICITLY gave — high precision, low recall, on purpose.

    NOT `identifiers()` WITH A TIGHTER FILTER; a different question for a different
    consumer, and the difference is the whole reason both exist. `identifiers()` feeds an
    enum, where an extra name is harmless — it widens what may be said. This feeds the
    gate, where an extra name is a FALSE ACCUSATION: the gate scores how many of the
    operator's names a program failed to mention, so a word wrongly read as a name becomes
    a suppression of a correct program. Same input, opposite cost of being wrong.

    Measured on the crude version: "make sure it is all fine" yielded `fine`, so a perfectly
    good program was one word away from being suppressed for not mentioning an adjective.
    That is the context assistant's own failure — `mac` inside "machine" — arriving by a
    different route, and it is why the two functions are not one function with a flag.

    THREE HIGH-CONFIDENCE FORMS, and nothing else:

      after a naming cue    "a vm called core"      -> core
      quoted                "label them 'fleet'"    -> fleet
      identifier-shaped     n1, web_02, red-net     -> a digit, underscore or hyphen is
                            something English words do not have

    RECALL IS DELIBERATELY SACRIFICED. A name this misses costs nothing — the factor stays
    at zero and the program is judged on everything else. A name it invents costs a
    correct program. Silence is the safe direction, so it takes it.
    """
    import re
    text = _intent.strip_prefix(goal or "")
    out: List[str] = []

    def add(word: str):
        if word and word.lower() not in _stopwords() and word not in out:
            out.append(word)

    cues = (config.GATE.get("naming_cues") or []) if hasattr(config, "GATE") else []
    for cue in cues:
        for m in re.finditer(rf"\b{re.escape(cue)}\b\s+['\"]?([A-Za-z_][A-Za-z0-9_-]*)",
                             text, re.I):
            add(m.group(1))
    for m in re.finditer(r"['\"]([A-Za-z_][A-Za-z0-9_-]*)['\"]", text):
        add(m.group(1))
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_-]*[0-9_-][A-Za-z0-9_-]*)\b", text):
        add(m.group(1))
    return out


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


def cardinality_of(sel) -> str:
    """`singular` or `set` for a select — DERIVED from the manifest, never asked.

    The operator's rule, 2026-07-29: a filter on the kind's KEY can never match two, so it
    is singular BY CONSTRUCTION. Anything else is a set expression, even when it happens to
    hold one member today — *"a label that is filtered might only be singling out one object
    now but it's technically a set with currently 1 member."*

    A COMPLEMENT IS A SET. `not` carves members out of a whole, and the complement of a
    filter is itself a filter, so a select carrying `not` is a set whatever else it says.
    That is what dissolves `NOT ANY`, the case the four-way enum could not answer.

    An unrecognised or absent kind answers `set`, which is the conservative direction: a set
    denies `call`, so the worst case offers a loop where one was not needed, rather than
    denying the loop a real set requires.
    """
    if not isinstance(sel, dict):
        return "set"
    kind = sel.get("kind")
    spec = config.KINDS.get(kind) or {}
    key = spec.get("key")
    if not key or "not" in sel or "any" in sel or "all" in sel:
        return "set"
    aliases = spec.get("aliases") or {}
    named = {aliases.get(k, k) for k in sel if k != "kind"}
    if named != {key}:
        return "set"
    # A KEY FILTER IS NOT AUTOMATICALLY ONE OBJECT. `name = {"in": ["a","b"]}` is membership
    # over the key and names TWO — singular only when the list holds exactly one. Missing
    # this answered `singular` for a two-member select, which would have denied the FOREACH
    # that select requires.
    val = sel.get(key, sel.get(next((k for k in sel if aliases.get(k, k) == key), key)))
    if isinstance(val, dict) and "in" in val:
        # MEMBERSHIP IS A SET CONSTRUCTOR, AT EVERY LENGTH — including one.
        #
        # I first wrote this as `singular if len(members) == 1`, which contradicts the rule
        # the whole module rests on. The operator caught it: *"name in [solo] is technically
        # a set, even if it's singular — that was our issue. It should be treated with a
        # foreach even if it's 1 member."* Right, and it is the same trap in a new costume:
        # `len(...) == 1` IS a member count, and counting is exactly what by-construction
        # replaces. A list of one is still a list; `EXCEPT` narrowing it to one member
        # tomorrow does not change what the expression IS.
        #
        # Only SCALAR equality on the key is singular, because the key is unique by
        # declaration and a scalar match can never yield two.
        return "set"
    return "singular"


def ops_for_cardinality(want=None, cardinality=None):
    """The ops offered once cardinality is known — the SYMMETRIC narrowing.

    singular denies `foreach` (no looping over one object); `set` denies the bare `call`
    (a single invocation cannot address a set). Both directions matter: offering `foreach`
    for one object is rung 8's statement 4, and offering a bare `call` for a set is the
    same error inverted.
    """
    out = ops(want)
    spec = config.CARDINALITY.get(cardinality) if cardinality else None
    if spec:
        denied = set(spec.get("deny") or ())
        out = [op for op in out if op not in denied]
    return out
