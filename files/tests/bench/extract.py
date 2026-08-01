"""extract.py — English into goal components. THE ONLY PLACE A MODEL IS CALLED.

The translation half of the operator's design (#60). The ghost writer proved that code alone
can write every rung once the goal is expressed as components; this is the question that was
left open — whether a model can produce those components from a sentence.

WHY THIS SHOULD BE EASIER THAN AUTHORING. Every field is a CLOSED SET drawn from the
manifest: seven kinds of goal, three kinds, the attributes of each, the legal values of the
enumerated ones. There is no program to get wrong, no ordering to remember, no grounding to
add, no `$reference` to bind. A wrong answer here is DETECTABLE — it names a kind or an
attribute that does not exist — where a wrong program merely fails later, for one of two
reasons nobody could tell apart.

THE SCHEMA IS BUILT FROM THE MANIFEST, never written out. A kind added to `ir.defaults.json`
is extractable the same day, and a schema that listed the kinds by hand would be the second
authority this codebase keeps deleting.

AND IT CARRIES NO `pattern`. On 2026-07-31 a single `pattern: "^\\$"` silently disabled
constrained decoding for the whole authoring path — ollama returned 200 and generated free
text. There is nothing here that needs one: the fields are enums, integers and plain
strings. `assert_enforced` proves the grammar actually applies before any number from this
module is believed.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from orchestrator.ai.chat.ollama_client import OLLAMA_URL
from orchestrator.ai.planner.ir import config

from . import pinned
from .ladder import BENCH_MODEL


def _kinds() -> List[str]:
    return sorted((config.KINDS or {}).keys())


def _attrs(kind: str = None) -> List[str]:
    """Every queryable attribute, aliases included — the operator's words, not ours."""
    out = set()
    for k, spec in (config.KINDS or {}).items():
        if kind and k != kind:
            continue
        out |= set(spec.get("attrs") or ())
        out |= set((spec.get("aliases") or {}).keys())
        out |= set((spec.get("observed") or {}).keys())
    return sorted(out)


def _facts() -> List[str]:
    out = set()
    for spec in (config.KINDS or {}).values():
        out |= set((spec.get("observed") or {}).keys())
    return sorted(out) or ["alive"]


# ONE BRANCH PER SHAPE OF GOAL, and the set is closed. A request that fits none of these is
# one the writer could not build anyway, so the honest outcome is a refusal at this step
# rather than a program nobody can trust.
def schema(kinds=None) -> Dict[str, Any]:
    """The grammar the model is decoded against — BUILT FROM THE MANIFEST IN FORCE.

    IT USED TO BE A MODULE CONSTANT, frozen at import from the default manifest, and that
    made a package half-mounted: its kinds joined what the system could DO and never what it
    could be ASKED for. Loading the Camoufox package let the writer plan a search and left
    the model unable to say the word — "search the web for the diameter of the earth" came
    back with zero goals, and the request closed UNTRANSLATED with nothing wrong anywhere
    the ledger could point at.

    A CAPABILITY THAT CANNOT BE REQUESTED IS NOT MOUNTED. Rebuilding costs microseconds and
    is done per call, so `config.use_kinds` — which every engine operation already runs
    inside — reaches the front seam the same way it reaches the writer.

    EVERY PIECE THAT READS THE MANIFEST IS BUILT HERE. A first attempt moved only the outer
    literal and left `_SELECT` at module level, so the KIND ENUM — the one part that decides
    whether a package's kinds can be named at all — stayed frozen. It appeared to work only
    because a test imported this module from inside the context.
    """
    _WHERE = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "attr": {"type": "string", "enum": _attrs(),
                         "description": "which property to match on"},
                "value": {"type": "string",
                          "description": "the value it must have, as written by the operator"},
            },
            "required": ["attr", "value"],
            "additionalProperties": False,
        },
    }

    _SELECT = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": _kinds()},
            "where": _WHERE,
            "except": {**_WHERE,
                       "description": "members to EXCLUDE — 'every vm except db' puts db here"},
        },
        "required": ["kind"],
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "properties": {
            # DECLINING MUST BE LEGAL, or the model routes around the check. This carried
            # `minItems: 1` and `required: ["goals"]`, which means the GRAMMAR MADE REFUSAL
            # IMPOSSIBLE — asked to translate "asdkjh qwe ;;; 42" the model could not answer
            # "that is not a request", so it invented one ("make every vm running") and the
            # writer built it and the orchestrator reported DONE. Found by the prompt matrix
            # 2026-08-01, which is exactly what a matrix of six PROMPT KINDS is for: thirteen
            # valid rungs could never have shown it.
            #
            # A schema that forbids the honest answer does not get honesty. It gets a
            # confident answer to a question nobody asked.
            "cannot": {
                "type": "string",
                "description": ("say WHY, if this is not a request you can express as goals — "
                                "it is noise, it is ambiguous, or it asks for something these "
                                "goals cannot say. Leave `goals` empty when you set this."),
            },
            "goals": {
                "type": "array",
                "minItems": 0,
                "items": {
                    "type": "object",
                    "properties": {
                        "goal": {
                            "type": "string",
                            "enum": ["count", "reach", "every", "per", "observe"],
                            "description": (
                                "count: how many members must match. "
                                "reach: these must be able to reach each other. "
                                "every: every member of a set must get a property. "
                                "per: make one new thing for each member of a set. "
                                "observe: ask each member something, without requiring an answer"
                            ),
                        },
                        "select": _SELECT,
                        "amount": {"type": "integer",
                                   "description": "for count: how many. for reach: how few is too few"},
                        "attr": {"type": "string", "enum": _attrs(),
                                 "description": "for every: which property to give them"},
                        "value": {"type": "string",
                                  "description": "for every: what to set that property to"},
                        "make": {"type": "string", "enum": _kinds(),
                                 "description": "for per: what kind of thing to make"},
                        "link": {"type": "string", "enum": _attrs(),
                                 "description": "for per: the property tying the new thing to the member"},
                        "fact": {"type": "string", "enum": _facts(),
                                 "description": "for observe: what to ask"},
                    },
                    "required": ["goal", "select"],
                    "additionalProperties": False,
                },
            }
        },
        # NOTHING IS REQUIRED. Either answer is a complete one: goals, or a reason there are
        # none. Requiring `goals` is what made refusal unsayable in the first place.
        "additionalProperties": False,
    }


# The default-manifest instance, for callers that only ever wanted that one.
SCHEMA = schema()

def prompt(kinds=None) -> str:
    """The system prompt, with the DOMAIN named from the manifest in force.

    IT ASSERTED "virtual machines" UNCONDITIONALLY, and that is a false statement the moment
    a package is loaded. Asked to translate "search the web for the diameter of the earth"
    with the Camoufox package mounted — its kinds in the schema, the writer able to plan the
    whole chain — the model answered `cannot: too vague` and was RIGHT TO: it had been told
    the subject was machines, and a web search is not one.

    ONLY THE DOMAIN CLAIM IS BUILT, and deliberately nothing else. Every other line of this
    prompt has been measured, several of them expensively; changing more while chasing a
    package would mix an unmeasured edit into a measured artifact. The nouns come from the
    manifest, which is where the operator's words already live.
    """
    nouns = []
    for kind, spec in (config.KINDS or {}).items():
        nouns.append((spec.get("nouns") or [kind])[0])
    subject = ", ".join(sorted(nouns)) or "virtual machines"
    return PROMPT.replace("about virtual machines", f"about {subject}")


PROMPT = """You read an operator's request about virtual machines and say WHAT MUST BE TRUE
when it is done. You do NOT write any program, choose any tool, or decide any order —
something else does all of that.

Break the request into goals. Each goal is one thing that must be true at the end.
MOST REQUESTS CONTAIN SEVERAL. "Create a vm named beta and then launch it" is TWO goals —
beta exists, and beta is running. Return one goal for every thing the operator asked for.

  count    HOW MANY members must exist at    "create a vm named alpha" -> count 1,
           the end. Naming one thing is a      select vm where name=alpha
           count of one.                       "3 vms labelled prod"     -> count 3
  every    every member of a set GAINS A       "put them all on network lab"
           PROPERTY it may not have yet.        -> every, attr network, value lab
           Never to name a thing: a name is
           what a thing IS, not something
           it is given.
  reach    members must reach each other      "make sure they can all ping each other"
  per      one new thing per member           "snapshot every running vm"
                                               -> per, make snapshot, link vm
  observe  ask each member something          "ping every vm" -> observe, fact alive

`select` names the members a goal is about. `where` narrows it; `except` carves members out.
Say what the operator asked for and nothing more.

IF IT IS NOT A REQUEST YOU CAN EXPRESS THIS WAY — it is noise, it is too vague to act on, or
it asks for something these goals cannot say — return NO goals and set `cannot` to the
reason. That is a correct answer. Inventing a goal nobody asked for is not."""


def _to_select(raw: Dict[str, Any]) -> Dict[str, Any]:
    """The extractor's `select` into the writer's — flat filters, alias-resolved.

    `where`/`except` lists exist because a LIST OF PAIRS constrains cleanly and an object
    with arbitrary keys does not. The writer wants flat filters, so the conversion happens
    here, once, at the boundary where the two shapes meet.
    """
    kind = raw.get("kind")
    alias = ((config.KINDS or {}).get(kind) or {}).get("aliases") or {}
    out: Dict[str, Any] = {"kind": kind}
    for pair in raw.get("where") or []:
        out[alias.get(pair["attr"], pair["attr"])] = _coerce(pair["value"])
    carve = {}
    for pair in raw.get("except") or []:
        carve[alias.get(pair["attr"], pair["attr"])] = _coerce(pair["value"])
    if carve:
        out["not"] = carve
    return out


_RESIDUE = __import__("re").compile(r"^\$\{?([A-Za-z0-9._-]+)\}?$")


def _unwrap(v: Any) -> Any:
    """`${lab}` -> `lab`. Template residue stripped, because there is nothing for it to name.

    MEASURED ON RUNG 13 AGAINST THE REAL PATH, and it is the failure that rung exists to
    catch. The world already satisfied the request; the model returned `value: "${lab}"` and
    `value: "${fleet}"`, so the writer planned against a network that does not exist and a
    label nobody asked for — SIXTEEN CALLS on a goal that already held, a junk network and a
    junk label. The rung's own checker still passed, because the original state survived
    underneath, which is exactly how this hides.

    THE ARGUMENT THAT MAKES THIS SAFE IS SCOPE. Inside a Medusa program `$item` is a real
    reference and stripping it would be vandalism. A GOAL HAS NO BINDINGS — there is no
    scope, nothing has been bound, and nothing can be — so at this layer anything shaped
    like a variable is notation the model reached for and not a reference to anything. The
    value inside is what the operator wrote; only the wrapper is invented.

    This is the sanitiser's rule one layer up: residue that cannot mean anything is removed,
    and the shape is counted rather than guessed at.
    """
    if not isinstance(v, str):
        return v
    hit = _RESIDUE.match(v.strip())
    return hit.group(1) if hit else v


def placeholder(v: Any) -> bool:
    """Is this the prompt's own placeholder handed back as an answer?"""
    return bool(_PLACEHOLDER.match(str(_unwrap(v)).strip()))


def _coerce(v: str) -> Any:
    """`"false"` is not `False`, and an observed attribute compared against a string never
    matches. The extractor emits strings because a grammar cannot type a free value."""
    v = _unwrap(v)
    low = str(v).strip().lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    return v


_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                 "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _as_count(v: Any) -> Optional[int]:
    """`v` read as a number, or None if it is not one. Words included, because the model
    writes what the operator wrote and operators write "two".

    RESIDUE IS STRIPPED FIRST, and skipping that here cost rung 13 a machine called "5".
    `${5}` is the number five wrapped in notation; read literally it is not a number, so it
    fell past this, defaulted the count to one, and was then taken as an IDENTITY — the
    request for five machines became a request for one machine NAMED five. Residue has to be
    removed before ANY interpretation, not before some of them.
    """
    if v is None:
        return None
    text = str(_unwrap(v)).strip().lower()
    if text.isdigit():
        return int(text)
    if text in _WORD_NUMBERS:
        return _WORD_NUMBERS[text]

    # A NUMBER INSIDE A SENTENCE IS STILL THE NUMBER. `value: "There must be exactly 3 vms"`
    # was dropped whole — not parseable, not name-shaped — and the request to create THREE
    # MACHINES vanished with it, leaving goals quantified over an empty world that were
    # vacuously true. The model answered the question; it just answered in prose.
    #
    # ONLY FROM A PHRASE, AND ONLY WHEN THERE IS EXACTLY ONE. A single token like `vm1` is a
    # NAME that happens to contain a digit, and reading it as the count would turn "the
    # machine vm1" into "one machine". Two numbers ("3 of the 5 machines") is a sentence this
    # cannot read, and declining beats picking one — the rule this module keeps: compute
    # where the answer is determined, decline where it is not.
    if " " in text:
        found = __import__("re").findall(r"\b\d+\b", text)
        words = [w for w in _WORD_NUMBERS if __import__("re").search(rf"\b{w}\b", text)]
        if len(found) == 1 and not words:
            return int(found[0])
        if len(found) == 0 and len(words) == 1:
            return _WORD_NUMBERS[words[0]]
    return None


def _name_shaped(v: Any, kind: str = None) -> bool:
    """Could this string be a member's NAME at all? A shape question, never a meaning one.

    SOME KINDS ARE NAMED BY A PHRASE, and the manifest says which. A machine is called
    `bench-red-1`; a SEARCH is named by its query — "diameter of the earth" — and rejecting
    it for containing spaces killed the whole Camoufox path at the first goal. `key_freetext`
    lets a kind declare that its key is prose, which is a fact about the kind and not a
    loosening of the rule for everyone: a value still cannot be empty, cannot be residue,
    and cannot be longer than a name plausibly is.

    THE REPAIR NEEDED A FLOOR AND THIS IS IT. Reading a bare value on a count of one as an
    identity is right when the value is a name and wrong when it is the model shrugging:
    `value: "Not specified"` became a machine CALLED "Not specified", and the writer produced
    an invalid program from it. `value: "${5}"` is template residue and did the same.

    THE RULE IS THE SYSTEM'S OWN. `_fresh_names` mints `vm1`, `network2`; every machine in
    the real lab is `bench-red-1`, `vm-orchestrator`, `work-laptop`. A name is ONE token of
    word characters, hyphens and dots — so a value with a space, a brace or a dollar is not a
    name under any reading, and saying so requires no opinion about what the model meant.

    IT IS DELIBERATELY NOT A STOP-LIST. "unknown", "none", "n/a" and every other way a model
    can shrug are NOT enumerated here, because that is the arms race this project has
    refused twice. `fleetsize` passes this test and becomes a name, which is a genuine
    ambiguity the model created — and a wrong answer that came from the model is a different
    thing to fix than one this module invented.
    """
    text = str(_unwrap(v)).strip()
    if not text or len(text) > 200:
        return False
    if _PLACEHOLDER.match(text):
        return False
    if kind and ((config.KINDS or {}).get(kind) or {}).get("key_freetext"):
        # A PHRASE, BUT STILL NOT A SHRUG. Residue and shell syntax are refused for a
        # free-text key exactly as they are for a token one; what is allowed is spaces.
        return not any(c in text for c in "${}|;&<>`\n")
    return len(text) <= 64 and _NAME_OK.match(text) is not None


_NAME_OK = __import__("re").compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# `<n>`, `<name>` — a placeholder handed back as an answer. The same argument as `${lab}`:
# notation the model reached for, never a value the operator wrote.
#
# THE GUARD SURVIVED AN EXPERIMENT THE PROMPT CHANGE DID NOT. Replacing the examples' concrete
# values with `<n>` placeholders was meant to stop the model COPYING them — measured, and it
# only changed WHAT it copied: the crawler request came back with `value: "<n>"` three times
# out of three, and rung 4, which had been clean, started leaking placeholders too. Trading
# plausible contamination for placeholder contamination is not an improvement, so the prompt
# went back. This stays: it costs nothing and catches the shape if it ever appears.
_PLACEHOLDER = __import__("re").compile(r"^<[^>]*>$")


def _enumerated(kind: str) -> set:
    """Every value the manifest already CLAIMS for this kind, from wherever it claims it.

    Used to decline rather than to decide: a bare value the manifest names — `running`,
    `linux` — is ambiguous between an identity and a state, and an extractor that guessed
    there would be inventing meaning rather than moving a field.

    TWO PLACES DECLARE VALUES AND BOTH COUNT. `attr_values` enumerates a closed set
    (`status`), and `create_defaults` names one the world will use if nobody says otherwise
    (`os_type: linux`). Reading only the first left `linux` looking like an unclaimed word,
    so "one linux machine" would have become a machine NAMED linux — the manifest knew and
    was not asked.
    """
    spec = (config.KINDS or {}).get(kind) or {}
    out = set()
    for values in (spec.get("attr_values") or {}).values():
        out |= {str(x).lower() for x in (values or ())}
    out |= {str(v).lower() for v in (spec.get("create_defaults") or {}).values()}
    return out


_REACH_WORDS = {"ping", "reach", "reachable", "connect", "connected", "communicate",
                "talk", "see", "mesh", "each"}


def declined(raw: Dict[str, Any]) -> Optional[str]:
    """The model's reason for refusing, or None. An answer, not an error."""
    said = ((raw or {}).get("cannot") or "").strip()
    return said or None


def to_goals(raw: Dict[str, Any], request: str = "") -> List[Dict[str, Any]]:
    """The model's answer, in the shape `ghost_writer.cover` takes.

    Anything malformed is DROPPED rather than repaired. A goal missing the field its own
    shape requires is a goal the model did not actually state, and inventing the missing
    half here would put this module back in the business of deciding what the operator
    meant — which is the job it exists to not have.
    """
    out: List[Dict[str, Any]] = []
    for g in (raw or {}).get("goals") or []:
        shape, sel = g.get("goal"), _to_select(g.get("select") or {})
        if not sel.get("kind"):
            continue
        if shape == "count":
            # A MISSING NUMBER MEANS ONE. "Create a vm named alpha" is a count of one and the
            # prompt now says so in those words, so the model omits `amount` as obvious —
            # and the goal was being DISCARDED over it. Defaulting is not a guess about
            # meaning; it is the reading the sentence already had.
            # THE NUMBER MAY ARRIVE IN EITHER SLOT. The schema offers `amount`, and the
            # model routinely puts the count in `value` instead — "create a vm named alpha"
            # came back as `value: "1"`, which was DISCARDED and then defaulted back to 1 by
            # luck. A field the schema offers and the reader ignores is not a model failure.
            eq = _as_count(g.get("amount"))
            if eq is None:
                eq = _as_count(g.get("value"))
            # A MISSING NUMBER MEANS ONE. "Create a vm named alpha" is a count of one and the
            # prompt says so in those words, so the model omits it as obvious — and the goal
            # was being DISCARDED over it. Defaulting is not a guess about meaning; it is the
            # reading the sentence already had.
            if eq is None:
                eq = 1
            # THE CONSTRAINT IN THE WRONG SLOT. It came back as `value: "name=alpha"` at the
            # goal level rather than in `select.where` — the right MEANING in the wrong
            # FIELD, which is a slot error and repairable. What is never repaired is a wrong
            # meaning: that goes back as a failure.
            # WAS THE VALUE USED BY ANYTHING? Tracked rather than assumed, because the
            # hedge check below must only fire on a value NO repair claimed. An earlier
            # version ran it first and swallowed `value: "name=alpha"` — a measured repair,
            # broken by a guard placed one branch too early.
            used = False
            stray = g.get("value")
            if stray and "=" in str(stray) and len(sel) == 1:
                a, _, v = str(stray).partition("=")
                spec = (config.KINDS or {}).get(sel.get("kind")) or {}
                a = (spec.get("aliases") or {}).get(a.strip(), a.strip())
                if a in set(spec.get("attrs") or ()):
                    sel = {**sel, a: _coerce(v.strip())}
                    used = True
            elif g.get("attr") and g.get("value") is not None and len(sel) == 1:
                spec = (config.KINDS or {}).get(sel.get("kind")) or {}
                a = (spec.get("aliases") or {}).get(g["attr"], g["attr"])
                if a in set(spec.get("attrs") or ()):
                    sel = {**sel, a: _coerce(g["value"])}
                    used = True
            elif (g.get("value") is not None and _as_count(g["value"]) is None
                  and eq == 1 and len(sel) == 1):
                # A BARE VALUE ON A COUNT OF ONE IS AN IDENTITY. "create a vm named beta and
                # then launch it" came back as `count vm, value: "beta"` — no attribute, so
                # the value was dropped and the writer built `vm1`. Naming ONE thing is a
                # count of one, which is already how this module reads `every x must be
                # named y`; the same reading, reached through the other slot.
                #
                # IT DECLINES RATHER THAN GUESSES in the one place it could be wrong: a
                # value the manifest already claims as a legal state (`running`, `linux`) is
                # ambiguous between an identity and a property, and moving it would be
                # deciding what the operator meant. Only a count of ONE qualifies, because
                # "two machines called prod" is not an identity under any reading.
                spec = (config.KINDS or {}).get(sel.get("kind")) or {}
                key = spec.get("key")
                if (key and _name_shaped(g["value"], sel.get("kind"))
                        and str(_unwrap(g["value"])).strip().lower()
                        not in _enumerated(sel["kind"])):
                    sel = {**sel, key: str(_unwrap(g["value"])).strip()}
                    used = True
            if (not used and not g.get("attr") and g.get("amount") is None
                    and g.get("value") is not None
                    and _as_count(g["value"]) is None
                    and not _name_shaped(g["value"])):
                # THE MODEL HEDGED AND NOTHING COULD USE WHAT IT GAVE. `value: "Not
                # specified (2)"` is a hedge, not an omission, and the two must not read the
                # same: an ABSENT number means one, because that is the reading the sentence
                # already had, while a PRESENT unusable one means the model did not know.
                # Defaulting a hedge to 1 over a nine-machine lab means DELETE EIGHT.
                #
                # FOUR CONDITIONS, AND EVERY ONE OF THEM EARNED. A first version dropped on
                # "not a number and unused", which killed `value: "prod", amount: 2` — the
                # model HAD given the count and only the stray value was unusable — and
                # `value: "running"`, where the value is a plausible token this module
                # merely declined to read as an identity. What is left is the narrow case:
                # no count anywhere, and a value that is not even a plausible token.
                continue
            out.append({"shape": "count", "select": sel, "eq": eq})
        elif shape == "reach":
            # REACH IS NOT INVENTED. Twenty of twenty-three extraction failures on
            # 2026-08-01 were a `reach` goal the request never asked for, over a set too
            # small to satisfy it — "create a vm named beta and then launch it" came back
            # demanding two machines reach each other. The evidence for a reach goal is IN
            # THE REQUEST, so it is checked there rather than argued with in a prompt. A
            # slot-level guard, not a judgement about meaning: a request that does mention
            # reaching keeps its goal untouched.
            if request and not (_REACH_WORDS & {w.strip(".,!?;:'\"").lower()
                                                for w in request.split()}):
                continue
            out.append({"shape": "reach", "select": sel,
                        "min": int(g.get("amount") or 2)})
        elif (shape == "every" and g.get("attr") and g.get("value") is not None
                and not placeholder(g["value"])):
            spec = (config.KINDS or {}).get(sel["kind"]) or {}
            attr = (spec.get("aliases") or {}).get(g["attr"], g["attr"])
            if attr == spec.get("key"):
                # AN IDENTITY IS NOT A PROPERTY, and this is REPAIRED rather than asked for.
                # "create a vm named alpha" came back as `every vm must be named alpha` —
                # four of ten failures on 2026-08-01, all the same mistake. A name is what a
                # thing IS; giving every member of a set one name is not a state any world
                # can reach. The reading the operator meant is a COUNT OF ONE, and deriving
                # it costs a line where teaching it costs prompt budget measured to have none.
                out.append({"shape": "count",
                            "select": {**sel, attr: _coerce(g["value"])}, "eq": 1})
            else:
                out.append({"every": sel, "must": {attr: _coerce(g["value"])}})
        elif shape == "per" and g.get("make"):
            link = g.get("link") or _link_between(sel.get("kind"), g["make"])
            if link:
                out.append({"per": sel, "make": g["make"], "link": link})
        elif shape == "observe":
            out.append({"observe": sel, "fact": g.get("fact") or "alive"})
    return _subject_survived(_one_statement_not_two(out), request)


def _subject_survived(goals: List[Dict[str, Any]], request: str) -> List[Dict[str, Any]]:
    """Drop everything when the request's SUBJECT is missing from the goals.

    THE FAILURE THIS EXISTS FOR, and it is the worst kind. "search the web for the diameter
    of the earth" came back as two goals about MACHINES — put them on a network, make there
    be three — and the whole system then worked perfectly: the writer built that program, it
    ran, its ENSUREs asserted exactly what it had done, grounding passed, and the orchestrator
    reported DONE. Three machines and a network, no search, no answer, and nothing anywhere
    that could tell.

    A PROGRAM VOUCHES FOR ITS OWN GOALS, NEVER FOR THE REQUEST. That is a real hole and this
    is the narrow, non-lexical part of it that can be closed here: if the operator named a
    KIND — by any noun the manifest records for it — then some goal must be about that kind.
    Not the words, not the verbs, not a clause count: the SUBJECT.

    SAME SHAPE AS THE REACH GUARD, which is measured and kept: `reach` is never invented
    because the evidence for it is IN THE REQUEST, so it is checked there. This is the
    mirror — a subject the request DOES name may not vanish.

    IT DROPS EVERYTHING RATHER THAN THE ODD GOAL. A translation that lost the subject is not
    partly right; the goals that remain are about something else entirely, and running them
    is how three machines get made for a question about the earth. UNTRANSLATED is the honest
    close, and it is recoverable — a wrong program is not.
    """
    if not request or not goals:
        return goals
    words = {w.strip(".,!?;:'\"").lower() for w in request.split()}
    mentioned = set()
    for kind, spec in (config.KINDS or {}).items():
        nouns = {kind, *(spec.get("nouns") or ())}
        if nouns & words or {n + "s" for n in nouns} & words:
            mentioned.add(kind)
    if not mentioned:
        return goals
    covered = set()
    for g in goals:
        for holder in ("select", "every", "observe", "per"):
            sel = g.get(holder)
            if isinstance(sel, dict) and sel.get("kind"):
                covered.add(sel["kind"])
        if isinstance(g.get("make"), str):
            covered.add(g["make"])
    return goals if mentioned & covered else []


def _one_statement_not_two(goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop a bare total that the IDENTITY goals beside it already account for.

    MEASURED AGAINST THE REAL LAB, and it is the worst thing found all day. "create a machine
    named probe1" came back as TWO goals — a count of one over ALL machines, and the name —
    because the model said "a machine" and "named probe1" separately. Read literally over a
    nine-machine lab the first means DELETE EIGHT, and the program did exactly that: a benign
    creation request that would have emptied the lab.

    THE RULE FIRES ONLY WHERE THE TOTAL IS FULLY EXPLAINED. One unfiltered count of N over a
    kind, and exactly N identity goals over that same kind — then the total is the same
    statement said as a sum, and dropping it is the reading the sentence had. "Make sure
    there are three machines, and web carries the prod label" keeps its total, because a
    label goal is not an identity and does not account for anything.

    IT DROPS RATHER THAN KEEPS, and that is decided by which mistake is recoverable. The
    ambiguity is real; what is not symmetric is the cost. `clean up the lab` is already
    written down here as the case where AN IRREVERSIBLE READING OF A VAGUE SENTENCE MUST
    NEVER BE CHOSEN CONFIDENTLY, and this is that rule applied where it was measured to
    matter rather than where it was first written.
    """
    by_kind: Dict[str, Dict[str, List]] = {}
    for g in goals:
        if g.get("shape") != "count":
            continue
        sel = g.get("select") or {}
        kind = sel.get("kind")
        spec = (config.KINDS or {}).get(kind) or {}
        key = spec.get("key")
        if not kind or not key:
            continue
        slot = by_kind.setdefault(kind, {"totals": [], "identities": []})
        filters = {k: v for k, v in sel.items() if k != "kind"}
        if not filters:
            slot["totals"].append(g)
        elif set(filters) == {key} and g.get("eq") == 1:
            slot["identities"].append(g)

    drop = []
    for kind, slot in by_kind.items():
        if len(slot["totals"]) != 1 or not slot["identities"]:
            continue
        total = slot["totals"][0]
        if total.get("eq") == len(slot["identities"]):
            drop.append(id(total))
    return [g for g in goals if id(g) not in drop]


def _link_between(source_kind: str, made_kind: str) -> Optional[str]:
    """Which attribute of the NEW kind names a member of the source kind. Derived.

    A snapshot's `vm`, a page's `crawl` — the tie is an attribute of the thing being made,
    named for the thing it belongs to. The model dropped `link` and the entire goal was
    discarded (rung 12, 2026-08-01) when the manifest could have answered it. Ambiguity
    declines rather than guesses.
    """
    spec = (config.KINDS or {}).get(made_kind) or {}
    hits = [a for a in (spec.get("attrs") or ()) if a == source_kind]
    return hits[0] if len(hits) == 1 else None


def extract(request: str, model: str = None, temp: float = 0.0,
            timeout: int = 300) -> Dict[str, Any]:
    """Call the model once. Returns the raw parsed answer (use `to_goals` to convert)."""
    # THE ONE CONSTRAINED CALL, shared with every other AI seam. This built its own for
    # months, which was fine while it was the only one and became #26's defect the moment it
    # was not: two paths deciding what a model call IS, differing on keep_alive and on how a
    # decode failure surfaces.
    from orchestrator.ai.engines.channel import constrained
    return constrained(prompt(), request, schema(), model=model or BENCH_MODEL,
                       temp=temp, timeout=timeout)


def assert_enforced(model: str = None) -> bool:
    """Is the grammar actually applied? Ask something that would never produce JSON.

    THE CHECK THAT WOULD HAVE SAVED A MONTH. `pattern: "^\\$"` made ollama accept a schema,
    return HTTP 200, and generate completely unconstrained — so every result measured on that
    path was really measuring few-shot imitation. A schema that parses is not a schema that
    constrains, and the only way to know is to send a prompt whose answer cannot be JSON and
    see whether JSON comes back anyway.
    """
    try:
        got = extract("Say hello in one word.", model)
    except Exception:
        return False
    # THE SHAPE, NOT A PARTICULAR KEY. This asserted `"goals" in got`, which stopped being
    # true the moment refusal became legal — and the guard then refused to run at all, which
    # is the right failure but the wrong reason. What proves a grammar is applied is that a
    # prompt whose answer CANNOT be JSON came back as an object of exactly this schema's
    # keys; unconstrained generation returns prose, not `{}`.
    return isinstance(got, dict) and set(got) <= {"goals", "cannot"}
