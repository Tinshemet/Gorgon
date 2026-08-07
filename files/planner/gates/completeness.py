"""completeness.py — GATE 1. Is the pattern the AI produced WHOLE?

    inspect(request, goals) -> Report(holes, dropped, mutated, invented)

## THE FOUR QUESTIONS, AND WHY THEY ARE ONE GATE

The operator, 2026-08-07: gate 1 *"FILLS information"*, and then — *"add another thing to the
gate one legality question: did the AI DROP or MUTATE something?"* Those are the same question
asked in two directions, which is why they belong together:

    HOLE      a slot the pattern requires, with no value and no declared way to fill it
    DROPPED   a QUOTED value the REQUEST carries that no goal carries
    MUTATED   an identity in the goals that is a NEAR-MISS of a request token
              ("5" -> "fives", "fleet" -> "fleetsize")
    INVENTED  an identity in the goals with no counterpart in the request at all

`HOLE` looks at what the pattern needs and the request never said. The other three look at
what the request said and the pattern failed to carry faithfully.

## ⇒ IT CLASSIFIES. IT NEVER STRIPS, AND THAT IS NOT A STYLE CHOICE

**A GATE 1 THAT STRIPS AN INVENTED NAME IS MEASURED-DEAD, TWICE OVER.**

1. `engines/extract.py:2424-2436` — the rule *"a count above one cannot pin an identity, so
   strip the name and keep the count"* was implemented, measured, and WITHDRAWN: **6 -> 12
   DONE_BUT_FALSE on the literal arm.** The comment's conclusion is the standing law here —
   *"STRIPPING IS ONLY SAFE WHEN WHAT REMAINS IS STILL THE WHOLE TRUTH."*

2. **AND STRIPPING THAT SLOT IS DESTRUCTIVE.** `count(vm WHERE name='fives') = 10` is a claim
   about one machine; strip the name and it becomes `count(vm) = 10`, an UNFILTERED total.
   Against a lab holding twelve, `ghost_writer.py:302-318` covers that by DELETING TWO. The
   apparent backstop cannot fire: `_refuse_unasked_teardown` returns early unless `eq == 0`
   (`engines/extract.py:1622`), and `eq=10` walks straight past it.

So this module ADDS NO PASS-THROUGH. Every goal that reaches it leaves it unchanged. It
answers "is this pattern whole?" and hands the answer up; deciding what to do about a hole is
the caller's, and turning a refusal into an acceptance is nobody's.

## WHAT IT NEEDS, AND WHY IT ASKS THE MODEL NOTHING

The request text and the goals. Both are already in hand at the front seam. No prompt, no
schema, no vocabulary, no world — the world belongs to gate 2, and keeping it out is what
stops this gate from re-deriving gate 2 badly.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

# ── WHAT COUNTS AS A THING THE REQUEST NAMED ──────────────────────────────────────────────
#
# QUOTED STRINGS ONLY, and the narrowness is deliberate — twice over. A general "which words
# are identifiers" test needs a stopword list, and this project has measured that road:
# `clause_ledger`'s anchor detector cannot see `set`, `isolated`, `named`, `provision` or
# `connect`, and its `anchors[:3]` cap drops a real one. A number and a quoted string are
# unambiguous in any phrasing, which is exactly the property a gate needs — it must survive
# the operator saying the same thing differently.
#
# ⇒ AND A BARE NUMBER WAS TRIED AND REMOVED. "clone golden into 3 NEW vms" is correctly served
#   by `count(vm) = 4` — a count is a TOTAL and the request stated a DELTA — so the number rule
#   accused a hand-written CORRECT reading. Whether a cardinality is the right one needs the
#   world, which makes it gate 2's.
_QUOTED = re.compile(r"['\"`]([^'\"`]{1,40})['\"`]")


# ── TYPE ENFORCEMENT, BY SLOT MEANING ─────────────────────────────────────────────────────
#
# The operator, 2026-08-07: *"we should do type enforcement: count and amount should only have
# ints, name must be string."* These two sets are that rule, and they are keyed on the SLOT
# rather than the branch so a schema rename cannot silently switch the check off.
#
# A CARDINALITY IS A WHOLE NUMBER. `amount: "fives"`, `value: "Yeah, 5"`, `eq: "All 5 vms"` are
# illegal on sight — no request needed, no world needed, no model asked.
# ⇒ `value` IS **NOT** IN THIS SET, AND THE MEASUREMENT IS THE REASON. On the count branch
#   `value` carries the IDENTITY, not the number — "create a vm named alpha" is recorded as
#   `{"goal":"count","select":{"kind":"vm"},"value":"alpha"}`. Typing it as a cardinality
#   accused 21 of 21 passing readings. It is the `name` SINK under another spelling, which is
#   exactly the slot [[gorgon-rung-2-is-the-prompts-own-example]] describes as absorbing every
#   clause the model cannot shape.
_CARDINALITY = {"amount", "eq", "gte", "lte", "min", "max"}
# AN IDENTITY IS TEXT.
_IDENTITY = {"name", "net_name", "vm_name", "new_name", "source_name", "template", "path"}
# THE SINK ITSELF. Typed as text, because that is all that is ever true of it.
_IDENTITY |= {"value"}


class Report:
    """What gate 1 found. Four lists, and `legal` is the whole verdict.

    NOT A VERDICT OBJECT WITH A REASON STRING. The caller needs to know WHICH KIND of
    incompleteness it is looking at, because the four have different remedies: a HOLE can be
    filled from a declared default, a MUTATION should be re-read, and an INVENTION is the one
    the operator has to answer. Collapsing them into one "incomplete" was how the single gate
    ended up with rules that collided.
    """

    def __init__(self, holes=None, dropped=None, mutated=None, invented=None):
        self.holes: List[Dict[str, Any]] = list(holes or ())
        self.dropped: List[Dict[str, Any]] = list(dropped or ())
        self.mutated: List[Dict[str, Any]] = list(mutated or ())
        self.invented: List[Dict[str, Any]] = list(invented or ())

    @property
    def legal(self) -> bool:
        return not (self.holes or self.dropped or self.mutated or self.invented)

    def findings(self) -> List[str]:
        """One sentence per problem, in the operator's terms — never the model's."""
        out = []
        for h in self.holes:
            out.append(h.get("why")
                       or f"{h['shape']} says nothing: it has no {h['slot']} and names nothing")
        for d in self.dropped:
            out.append(f"the request says {d['token']!r} and no goal carries it")
        for m in self.mutated:
            out.append(f"the request says {m['said']!r} and the reading says {m['became']!r} "
                       f"— data was {m['change']}")
        for i in self.invented:
            out.append(f"it is about {i['slot']} {i['value']!r}, which the request never names")
        return out

    # ── THE RESOLVE ARM ──────────────────────────────────────────────────────────────────
    #
    # THE STANDING BAR: *"every gate must say what it RESOLVES, not only what it rejects."* A
    # gate 1 that only classifies is half a gate — but the four findings do NOT resolve alike,
    # and pretending they do is how a repair turns an honest refusal into a false success.
    #
    #     HOLE      a numeral written as text — RESOLVABLE by coercion, and by nothing else
    #     MUTATED   RESTORABLE: the operator's own word is known, so put it back
    #     INVENTED  nothing to restore FROM. Only the operator can answer.
    #     DROPPED   nothing to restore INTO. Only the operator can answer.
    #
    # ⇒ AND NOTE WHAT IS ABSENT: filling `os_type` or minting a name. Those CANNOT move here
    #   and it is measured rather than argued — `_fresh_names(kind, n, taken)` needs the names
    #   THE WORLD ALREADY HOLDS (`ghost_writer.py:380`), and `create_defaults` fills the
    #   REQUIRED_FIELDS of a creator that has not been CHOSEN yet (`vm` declares three). A
    #   gate-1 minter would collide with real machines. The writer keeps that job.

    def repairs(self) -> List[Dict[str, Any]]:
        """The fixes gate 1 can make WITHOUT GUESSING. Proposed, never applied.

        TWO KINDS ONLY, and both restore something already known rather than inventing one:

        COERCION — `"5"` becomes `5`. The value is unchanged; only its type is corrected, so
        nothing about the claim moves. `"five"` and `"Yeah, 5"` are NOT coerced: reading a
        number out of prose is guessing, and a guess here is indistinguishable from the
        PhantomFill that put a machine called `Not specified` on a lab.

        RESTORATION — `fleetsize` becomes `fleet`, because the request says `fleet` and the
        gate already knows which token was mangled. THIS IS NOT THE WITHDRAWN REPAIR. That one
        STRIPPED a filter — turning `count(vm WHERE name=X) = 10` into an unfiltered
        `count(vm) = 10`, which deletes machines — and its lesson was *"stripping is only safe
        when what remains is still the whole truth."* Restoration removes nothing; it puts the
        operator's own word back where the model mangled it.
        """
        out: List[Dict[str, Any]] = []
        for h in self.holes:
            value = h.get("value")
            if isinstance(value, str) and value.strip().lstrip("-").isdigit():
                out.append({"kind": "coerce", "slot": h["slot"],
                            "from": value, "to": int(value.strip()),
                            "why": "a cardinality written as text"})
        for m in self.mutated:
            out.append({"kind": "restore", "slot": m["slot"],
                        "from": m["became"], "to": m["said"],
                        "why": f"the request says {m['said']!r}"})
        return out

    def question(self) -> Optional[str]:
        """ONE message naming EVERY gap at once, or None if the operator is not needed.

        ONE MESSAGE, NOT ONE PER GAP. An operator answering four questions in sequence
        re-answers the first three every time the fourth changes, and a refusal that arrives
        in pieces reads as a system that cannot make up its mind.

        ONLY WHAT NOTHING ELSE CAN CLOSE. A hole that coerces and a mutation that restores are
        not questions — asking about a thing you could have fixed is how a consent prompt
        becomes noise, which is the failure `consent.py` was written to avoid.
        """
        asks = [f"{i['value']!r} — the request never names it" for i in self.invented]
        asks += [f"{d['token']!r} — you said it and no part of the reading carries it"
                 for d in self.dropped]
        if not asks:
            return None
        return ("part of this reading does not match what you asked. "
                + "; ".join(asks)
                + ". Say that part again in terms of what must be TRUE when it is finished.")

    def __repr__(self) -> str:
        return (f"<Report {'legal' if self.legal else 'ILLEGAL'} holes={len(self.holes)} "
                f"dropped={len(self.dropped)} mutated={len(self.mutated)} "
                f"invented={len(self.invented)}>")


def _flat(text: str) -> str:
    """Punctuation to spaces, lowercased — so `web-server` and `web server` are one token
    stream and `db` does not match inside `dbms`."""
    return " " + re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip() + " "


def said(request: str, value: Any) -> bool:
    """Did the operator's sentence contain this value?

    WORD-BOUNDARY, PUNCTUATION-FLATTENED. `web-server` matches "web server" because a person
    writing either meant the same thing, and `db` does NOT match inside `dbms` because they
    did not.
    """
    token = _flat(value).strip()
    return bool(token) and token in _flat(request)


def _near(value: str, request: str) -> Optional[Tuple[str, str]]:
    """(the request token this value mangles, which DIRECTION the data moved) — or None.

    ## ⇒ THERE ARE TWO KINDS OF MUTATION AND ONLY ONE OF THEM IS GATE 1'S

    The operator, 2026-08-07: *"gate 1 catches a mutation that DROPS OR ADDS DATA. gate 2
    catches mutation that CHANGES THE NATURE OF THE OUTCOME, ie that goes against the world."*

        GATE 1   the token itself changed —   `fleet` -> `fleetsize`   (data ADDED)
                 information was gained or    `work-laptop` -> `work`  (data DROPPED)
                 lost in the copy             ⇒ decidable from the SENTENCE alone

        GATE 2   the token is intact and      `db` -> `database`, both well-formed, but the
                 well-formed, and it now      world holds no `database`
                 MEANS something else         ⇒ needs the WORLD, so it is not asked here

    So this function reports only the first, and it reports the DIRECTION, because that is the
    distinction the operator drew: data added and data dropped are different mistakes. Whether
    a faithful-looking value still refers to the right thing is gate 2's question, and
    answering it here would make gate 1 a worse copy of gate 2.

    ⇒ THE TEST IS CONTAINMENT, NOT AN EDIT DISTANCE, and that narrowness is deliberate.
    `fleetsize` contains `fleet`; `work` is contained by `work-laptop`. `database` contains
    neither `db` nor anything else the sentence said, so it stays INVENTED and the operator is
    asked. An edit-distance threshold would have to be TUNED, and a tuned constant inside a
    legality check is a false-alarm generator with a dial on it.
    """
    v = _flat(value).strip()
    if not v or len(v) < 3:
        return None
    words = set(v.split())
    for token in _flat(request).split():
        if len(token) < 3:
            continue
        if token == v:
            return None                                    # said outright, not mutated
        # ⇒ A COMPOUND THAT *CONTAINS THE WORD* IS A MINT, NOT A MANGLING — and this
        #   distinction was worth 12 of gate 1's false alarms against the fresh corpus.
        #
        #       fleet -> fleetsize      `fleet` is buried INSIDE a word.  MANGLED.
        #       red   -> lab-red        `red` is a WHOLE WORD of a compound. MINTED.
        #
        #   Rung 6 says *"put the red ones together on their own network"* — the network is
        #   NEVER NAMED, so the model must supply one, and `lab-red` is a reasonable supply
        #   built from the operator's own word. That is gate 1's FILLS arm working, and the
        #   first draft accused it: `lab-red`, `lab-blue`, `private-red`, `private-blue`,
        #   `vms labelled prod`, `exactly two vms` — every one on a reading that PASSED.
        #
        #   THE TEST NEEDS NO THRESHOLD, which is why it is this one and not an edit
        #   distance: a tuned constant inside a legality check is a false-alarm generator
        #   with a dial on it.
        if token in words:
            # A COMPOUND BUILT FROM THE OPERATOR'S OWN WORDS. Neither mangled nor invented —
            # its own answer, because returning None here routed it to INVENTED and simply
            # moved the same 12 false alarms from one column to another.
            return token, "compound"
        if token in v:
            return token, "added"                          # the reading gained data
        if v in token:
            return token, "dropped"                        # the reading lost data
    return None


def _identities(goals: List[dict], kinds=None) -> List[Tuple[str, str, Any]]:
    """(shape, slot, value) for every IDENTITY the goals pin.

    AN IDENTITY IS THE KIND'S OWN KEY, read from the manifest. A goal saying
    `network: core` REFERS to a network and does not name a vm, so it is gate 2's business —
    checking it here would make gate 1 report the same thing twice under a worse name.
    """
    from planner.ir import config as _config
    table = kinds if kinds is not None else (_config.KINDS or {})
    out = []
    for goal in goals or ():
        shape = ("every" if "every" in goal else
                 "per" if "per" in goal else
                 "observe" if "observe" in goal else
                 str(goal.get("shape") or "?"))
        for sel in _selectors(goal):
            kind = sel.get("kind")
            key = ((table.get(kind) or {}).get("key")) if kind else None
            if key and isinstance(sel.get(key), (str, int)):
                out.append((shape, key, sel[key]))
    return out


def _selectors(node) -> List[dict]:
    """Every selector in a goal, however nested — `not`/`except` carve-outs included."""
    found = []
    if isinstance(node, list):
        for kid in node:
            found += _selectors(kid)
    elif isinstance(node, dict):
        if "kind" in node:
            found.append(node)
        for field, val in node.items():
            if field in ("must",) or not isinstance(val, (dict, list)):
                continue
            if val is not node:
                found += _selectors(val)
    return found


def _numbers(goals: List[dict]) -> Set[str]:
    """Every cardinality the goals assert, as strings."""
    out: Set[str] = set()
    for goal in goals or ():
        for field in ("eq", "gte", "lte", "min", "max"):
            if isinstance(goal.get(field), int):
                out.add(str(goal[field]))
    return out


# SLOTS THE SCHEMA CONTROLS. A model filling one of these is choosing from a closed list, so
# the value cannot be an invention — it is a branch name, not data. Everything else the model
# writes is FREE TEXT, and free text is the only thing that can be dropped or mutated.
#
# `link` IS ONE OF THEM AND IT COST NINE FALSE ALARMS BEFORE IT WAS LISTED. It holds a KIND
# NAME — "per vm, make a snapshot, LINKED BY network" — so the model is picking from the
# manifest's kinds, not writing data. Every slot here was decided by asking what the schema
# lets the model put in it, never by watching which ones happened to misfire.
_SCHEMA_SLOTS = {"goal", "shape", "kind", "attr", "fact", "make", "of", "min", "max",
                 "eq", "gte", "lte", "amount", "link", "per", "every", "observe"}


def _declared_value(attr: str, value: Any, kinds=None) -> bool:
    """Is this a value the MANIFEST declares for that attribute?

    `status: running` is not an invention even though the operator never typed "running" —
    "launch every vm that is currently stopped" legitimately becomes `status = running`. The
    enum is the schema speaking, and a gate that cannot tell a declared value from a fabricated
    one would accuse every correct reading that used one.
    """
    from planner.ir import config as _config
    table = kinds if kinds is not None else (_config.KINDS or {})
    for spec in table.values():
        if not isinstance(spec, dict):
            continue
        values = (spec.get("attr_values") or {}).get(attr)
        if values and str(value) in {str(v) for v in values}:
            return True
    return False


def _free_text(node, kinds=None, attr: Optional[str] = None) -> List[Tuple[str, Any]]:
    """(slot, value) for every string the model WROTE rather than CHOSE.

    Walks the answer in whatever shape it arrives — the raw schema form (`goal`/`attr`/`value`)
    and the goal form (`shape`/`must`/`select`) both, because the distinction that matters is
    schema-slot versus free-text and neither shape changes it.
    """
    out: List[Tuple[str, Any]] = []
    if isinstance(node, list):
        for kid in node:
            out += _free_text(kid, kinds, attr)
    elif isinstance(node, dict):
        here = node.get("attr") or attr
        for slot, val in node.items():
            if isinstance(val, (dict, list)):
                out += _free_text(val, kinds, here if slot != "must" else None)
            elif isinstance(val, str) and slot not in _SCHEMA_SLOTS:
                # A `must` maps attr -> value directly, so the SLOT is the attribute there.
                enum_attr = slot if slot not in ("value", "name") else here
                if not _declared_value(enum_attr or slot, val, kinds):
                    out.append((slot, val))
    return out


def _branches(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """goal-name -> its declared branch. The schema IS the legality specification."""
    out = {}
    items = (((schema or {}).get("properties") or {}).get("goals") or {}).get("items") or {}
    for branch in items.get("oneOf") or items.get("anyOf") or ():
        names = ((branch.get("properties") or {}).get("goal") or {})
        for name in (names.get("enum") or ([names["const"]] if "const" in names else ())):
            out[str(name)] = branch
    return out


def typed(raw: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """IS EACH GOAL WELL-FORMED FOR THE BRANCH IT CLAIMS? No request, no world, no model.

    ## ⇒ THE OPERATOR'S RULE, GENERALISED: *"count's value should only return ints"*

    It is stronger than it looks, because the schema already says so and says more. The count
    branch declares `amount: integer` and `name: string`, BOTH REQUIRED — and no `value` slot
    at all. So a recorded reading like

        {"goal": "count", "select": {"kind": "vm"}, "value": "fives"}

    is illegal THREE times over: `value` is not a slot of this branch, `amount` is required and
    missing, `name` is required and missing. **None of that needs the sentence.** A gate that
    can say "malformed" without reading the request is the cheapest true thing in the system,
    and it is what "the gates catch if the pattern the AI translated is LEGAL" means literally.

    ⇒ THE SCHEMA IS PASSED IN, NOT IMPORTED. `planner` is layer 0 and may not reach up into
    `engines` (`tests/test_layering.py`), and the caller has the schema anyway — it built it.
    It also makes the rule mockable, which is the standing bar for new code here.

    ⇒ WHY THIS FINDS ANYTHING AT ALL, given constrained decoding is supposed to make it
    impossible: it evidently does not, on this corpus. Whether the grammar is enforced on the
    live path is a separate question worth asking ([[gorgon-grammar-was-never-enforced]]) — but
    a check that is free when the grammar holds and load-bearing when it does not is worth
    keeping either way.
    """
    faults = []
    spec = _branches(schema)
    for goal in (raw or {}).get("goals") or ():
        if not isinstance(goal, dict):
            faults.append({"slot": "goal", "why": "not an object"})
            continue
        name = str(goal.get("goal") or "")
        branch = spec.get(name)
        if not branch:
            faults.append({"slot": "goal", "value": name,
                           "why": "not a shape this translator declares"})
            continue
        props = branch.get("properties") or {}
        # ⇒ REQUIRED-NESS IS *NOT* CHECKED, AND THE MEASUREMENT SAYS WHY. The schema marks
        #   `amount` required on the count branch; `to_goals` declares that an ABSENT amount
        #   MEANS ONE (`engines/extract.py:2353-2366`). They disagree, and the reader is the
        #   one that ships — 15 of the 21 recorded readings that PASSED omit `amount`, so
        #   enforcing the schema's word here accused correct answers three times out of four.
        #
        #   THAT IS GATE 1'S OWN "FILLS" ARM GIVING THE ANSWER: a slot missing with a DECLARED
        #   DEFAULT is SUPPLIED, not a hole. A slot missing with nothing to fill it from would
        #   be a hole — but every currently-required slot has a filler behind it (`amount` ->
        #   one, `name` -> `_fresh_names`), so there is nothing left here to refuse.
        #
        #   WHAT REMAINS IS THE PART NOTHING CAN FILL: a slot the branch does NOT HAVE, and a
        #   value of the WRONG TYPE. Neither has a default, because neither is a gap — they are
        #   malformations.
        for slot, value in goal.items():
            # ⇒ TYPE BY WHAT THE SLOT *MEANS*, NOT BY WHAT THE BRANCH DECLARES, because the
            #   two have drifted and the reader is the one that ships. A count's cardinality
            #   arrives as `amount` OR as `value` (`engines/extract.py:995,2346` accepts both)
            #   while the schema declares only `amount` — so "this branch has no `value`"
            #   accused 15 of the 21 recorded readings that PASSED. The DISAGREEMENT is worth
            #   reporting to a human; it is not worth refusing a correct reading over.
            #
            #   WHAT IS ALWAYS TRUE, whichever spelling arrives: A CARDINALITY IS A WHOLE
            #   NUMBER AND AN IDENTITY IS TEXT. The operator, 2026-08-07: *"count and amount
            #   should only have ints, name must be string."* That holds under any rename.
            if slot in _CARDINALITY and not isinstance(value, bool):
                if not isinstance(value, int):
                    faults.append({"slot": slot, "shape": name, "value": value,
                                   "why": f"{name}.{slot} must be a whole number, "
                                          f"and it is {value!r}"})
                continue
            if slot in _IDENTITY and not isinstance(value, str):
                faults.append({"slot": slot, "shape": name, "value": value,
                               "why": f"{name}.{slot} must be text, and it is {value!r}"})
                continue
            declared = props.get(slot)
            if declared is None:
                continue                      # unknown slot: schema/reader drift, not a fault
            want = declared.get("type")
            if want == "integer" and not isinstance(value, int):
                faults.append({"slot": slot, "shape": name, "value": value,
                               "why": f"{name}.{slot} must be a whole number"})
            elif want == "string" and not isinstance(value, str):
                faults.append({"slot": slot, "shape": name, "value": value,
                               "why": f"{name}.{slot} must be text"})
            elif declared.get("enum") and value not in declared["enum"]:
                faults.append({"slot": slot, "shape": name, "value": value,
                               "why": f"{value!r} is not one of {name}.{slot}"})
    return faults


def inspect_raw(request: str, raw: Dict[str, Any], kinds=None,
                schema: Optional[Dict[str, Any]] = None) -> Report:
    """GATE 1 ON WHAT THE MODEL ACTUALLY EMITTED — which is the only place it can work.

    ⇒ MEASURED, AND IT IS WHY THIS FUNCTION EXISTS. Run against the goals that come OUT of
    `to_goals`, gate 1 found 0 mutations and 0 inventions across all 78 recorded readings —
    while the corpus visibly contains `'fives'` and `'fleetsize'`. It was inspecting the
    SURVIVORS: `to_goals` had already moved every invented value into `lost` and thrown the
    goal away. The gate was auditing a room the evidence had been removed from.

    ⇒ AND IT IS THE OPERATOR'S QUESTION, EXACTLY. *"Did the AI drop or mutate something?"* is
    a question about THE AI'S ANSWER. Asking it of a filtered version of that answer is asking
    something else.

    A `value` a model writes is free text; a `kind` or an `attr` is a branch it chose from a
    closed list. Only the first can be dropped or mutated, which is what makes this decidable
    without a vocabulary.
    """
    report = Report()
    # ⇒ THE GRAMMAR'S OWN WORDS ARE NOT INVENTIONS. A model that writes `name: "every"` or
    #   `name: "per"` is ECHOING THE SCHEMA into the free-text slot, not naming a thing — the
    #   `name` sink absorbing a word it could not shape. `extract` already strips these
    #   (`_echoed`), and gate 1 flagged them 12 times on readings that PASSED because it runs
    #   BEFORE that repair. Naming the class here is cheaper than teaching the gate to predict
    #   which repairs downstream will succeed.
    echoes = {"count", "every", "per", "observe", "reach", "goal", "select", "value",
              "name", "attr", "amount", "must", "all", "any", "none"}
    echoes |= {str(k).lower() for k in (kinds if kinds is not None else {})}
    # THE TYPE CHECK FIRST, because it needs nothing and settles the most. A goal that is not
    # well-formed for its own branch is illegal whatever the sentence said.
    if schema:
        for fault in typed(raw, schema):
            report.holes.append({"shape": fault.get("shape", "?"),
                                 "slot": fault["slot"], "why": fault["why"],
                                 "value": fault.get("value")})
    for slot, value in _free_text(raw, kinds):
        if said(request, value):
            continue
        # ⇒ A BARE NUMBER IS A CARDINALITY, AND CARDINALITIES ARE GATE 2'S. "create a vm named
        #   alpha" legitimately carries `1` that the sentence never types — the count branch
        #   declares that absent-means-one (`extract.py:2353`) — and "3 new" legitimately
        #   becomes a total of 4. Whether a number is the RIGHT one needs the world, which is
        #   the operator's line between the gates: gate 1 catches data dropped or added, gate 2
        #   catches an outcome that goes against the world. Measured: 3 false alarms without
        #   this, all of them a defaulted `1`.
        if str(value).strip().isdigit():
            continue
        if str(value).strip().lower() in echoes:
            continue
        origin = _near(value, request)
        if origin and origin[1] == "compound":
            # ⇒ THE MODEL MINTED A NAME OUT OF WHAT THE OPERATOR SAID, AND THAT IS THE JOB.
            #   "put the red ones together on their own network" never names the network, so
            #   one has to be supplied, and `lab-red` is built from the operator's own word.
            #   Flagging it accused six PASSING readings — it is gate 1's FILLS arm working.
            continue
        if origin:
            token, direction = origin
            report.mutated.append({"shape": "raw", "slot": slot, "said": token,
                                   "became": value, "change": direction})
        else:
            report.invented.append({"shape": "raw", "slot": slot, "value": value})
    return report


def inspect(request: str, goals: List[dict], kinds=None) -> Report:
    """Gate 1 over one reading. Deterministic, no model call, no world.

    THE GOALS ARE NOT MODIFIED. See the module docstring for why that is load-bearing rather
    than tidy.
    """
    holes, dropped, mutated, invented = [], [], [], []

    # ── 1 · HOLES. A pattern that pins nothing and counts nothing says nothing. ───────────
    #
    # `count(vm)` with no cardinality is not a small claim, it is NO claim — and this is the
    # one the corpus reports most often ("count: it states no number and its value names
    # nothing"). Read as a legality question rather than a semantic one: a count is a
    # cardinality assertion, so a count without a cardinality is malformed.
    for goal in goals or ():
        if str(goal.get("shape") or "") != "count":
            continue
        has_number = any(isinstance(goal.get(f), int) for f in ("eq", "gte", "lte"))
        pins = [v for _s, _k, v in _identities([goal], kinds)]
        if not has_number and not pins:
            holes.append({"shape": "count", "slot": "number", "goal": goal})

    # ── 2 · MUTATED and INVENTED — from the GOALS back to the REQUEST. ───────────────────
    #
    # THIS DIRECTION IS THE SOUND ONE. Starting from the request means deciding which of its
    # words were meant as identifiers, which needs a stopword list nobody can make correct.
    # Starting from the GOALS gives a small closed set of values the AI actually committed
    # to, and each one either appears in the sentence or does not.
    for shape, slot, value in _identities(goals, kinds):
        if not isinstance(value, str) or said(request, value):
            continue
        origin = _near(value, request)
        if origin:
            token, direction = origin
            mutated.append({"shape": shape, "slot": slot, "said": token,
                            "became": value, "change": direction})
        else:
            invented.append({"shape": shape, "slot": slot, "value": value})

    # ── 3 · DROPPED — the one check that must run the other way, kept to what is certain. ─
    #
    # A QUOTED STRING, AND DELIBERATELY NOT A NUMBER. Both survive rephrasing, so both looked
    # like good evidence, and the numbers had to go:
    #
    # ⇒ A CARDINALITY IN THE REQUEST NEED NOT APPEAR IN THE GOALS, AND THE CORRECT READING IS
    #   THE PROOF. "clone golden into 3 NEW vms" is served by `count(vm) = 4` — three clones
    #   plus the `golden` already there — because A COUNT IS A TOTAL AND THE REQUEST STATED A
    #   DELTA ([[gorgon-count-is-a-total]]). Measured: the number rule accused that reading,
    #   which is a hand-written CORRECT answer, and it was the gate's only false alarm across
    #   all fourteen.
    #
    # ⇒ AND GATE 1 CANNOT FIX IT, BECAUSE THE ARITHMETIC NEEDS THE WORLD. Whether 4 is the
    #   right total for "3 new" depends on how many exist now. That is precisely the operator's
    #   line between the two gates — gate 1 catches a mutation that DROPS OR ADDS DATA, gate 2
    #   catches one that CHANGES THE NATURE OF THE OUTCOME, ie that goes against the world. A
    #   delta read as a total is the second kind. It belongs to gate 2 and is left for it.
    #
    # A quoted string carries no arithmetic, so it has no such reading: if the operator wrote
    # 'fleet' and no goal mentions `fleet`, the label was dropped, whatever the world holds.
    #
    # "take 5 vms" vs "use five machines" is a case this MISSES rather than guesses at, and
    # missing it is the right trade — a gate that fires on the wrong word teaches the operator
    # to ignore it.
    carried = _numbers(goals) | {str(v).lower() for _s, _k, v in _identities(goals, kinds)}
    flat_goals = _flat(repr(goals))
    for token in set(_QUOTED.findall(request or "")):
        if token.lower() not in carried and _flat(token).strip() not in flat_goals:
            dropped.append({"token": token, "why": "a value the request quotes"})

    return Report(holes=holes, dropped=dropped, mutated=mutated, invented=invented)
