"""extract.py — English into goal components. THE ONLY PLACE A MODEL IS CALLED.

The translation half of the operator's design (#60). The ghost writer proved that code alone
can write every rung once the goal is expressed as components; this is the question that was
left open — whether a model can produce those components from a sentence.

IT LIVED IN `tests/bench/` UNTIL 2026-08-02, and it is production code: `rig.translator()`
imports it, so the chat path's front seam was a module in the test tree. That is not a
tidiness complaint. A bench module is one nobody is careful about deleting, it is free to
import other bench modules — this one pulled in `pinned` and `BENCH_MODEL`, so PRODUCTION was
silently running under the BENCH'S reproducibility policy, which `pinned` explicitly says is
not production's — and a checkout that ships without `tests/` ships without a front seam.

It sits beside the channel that calls it and the reporter that mirrors it, which is where the
three model seams of the architecture belong: translation in, findings out.

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

from planner.ir import config


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
            # AN AUTHORING REQUEST IS NOT A WORLD REQUEST, and there WAS a `procedure` field
            # here for the model to say so. It is gone, and the reason is measurement: asked
            # outright to "create a reusable medusa procedure called vm_disk_builder" the
            # model answered `procedure: null` twice out of two, and the word blinder that
            # switched the instruction on fired on "save a snapshot of web", "keep the vm
            # running" and "store the iso on disk" — 5 of 7 realistic requests.
            #
            # A field the model never fills is schema surface on every extraction for nothing,
            # and a trigger that fires on ordinary requests is a regression waiting for a
            # ladder run. The operator DECLARES it instead: `procedure build_box: ...`. See
            # `planner/procedures.declared_in`.
            "cannot": {
                "type": "string",
                "description": ("say WHY, if this is not a request you can express as goals — "
                                "it is noise, it is ambiguous, or it asks for something these "
                                "goals cannot say. Leave `goals` empty when you set this."),
            },
            "goals": {
                "type": "array",
                "minItems": 0,
                # ONE BRANCH PER SHAPE, AND EVERY BRANCH IS CLOSED. The goal used to be one
                # flat object offering NINE fields — `amount`, `name`, `attr`, `value`,
                # `make`, `link`, `fact` — of which at most three ever apply, so the model
                # chose a slot from a wide open surface on every goal it wrote. That is the
                # one thing every measurement here says it is bad at.
                #
                # WHAT IT COST, measured on the simplest requests there are: "a machine
                # called box1 running linux" put the NAME in `value`, which a count goal
                # reads as a number first, and box1 was lost; "make 5 vms" put the literal
                # string `name` in `value`, echoing the schema back; and `to_goals` grew a
                # repair path for each wrong slot — a stack of corrections for a choice that
                # should never have been offered.
                #
                # A COUNT GOAL NOW HAS NO `value` FIELD AT ALL, so a name cannot land there:
                # the decoder is constrained, and what is not in the branch cannot be
                # emitted. This is the move `master.ops` already makes for the intent ladder
                # and the quantifier router — MAKE THE WRONG PROGRAM UNREPRESENTABLE RATHER
                # THAN REJECT IT AFTERWARDS — applied to the seam where the wrong thing was
                # actually being written.
                "items": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "goal": {"type": "string", "enum": ["count"],
                                         "description": "how many members must match"},
                                "select": _SELECT,
                                "amount": {"type": "integer",
                                           "description": ("HOW MANY there must be. Zero "
                                                           "means none may remain")},
                                "name": {"type": "string",
                                         "description": ("the NAME of the member, when the "
                                                         "operator gave one — 'a vm called "
                                                         "box1' puts box1 here")},
                            },
                            # `amount` IS REQUIRED, and it is the last slot the model was
                            # skipping. Offered as optional it went unfilled on every counted
                            # request — "create 3 machines" and "make 5 vms" both lost their
                            # number — while `name`, the only string left in the branch,
                            # absorbed whatever was nearby.
                            #
                            # AN INTEGER IS A CLOSED TYPE, which is the thing this model is
                            # measurably good at, and the opposite of the `from` field that
                            # was required and withdrawn an hour ago: THAT asked for a span of
                            # prose, this asks for a number the sentence already contains.
                            # BOTH ARE REQUIRED, because the model fills ONE optional field
                            # and drops the other. With `amount` alone required it found the
                            # counts and lost the names — "a machine called box1 running
                            # linux" came back as COUNT(vm)=1 with box1 nowhere, which is the
                            # request that wrote a lab-wipe. With neither required it lost the
                            # counts instead.
                            #
                            # A NAME IT HAD TO INVENT IS STRIPPED, NOT OBEYED — see `_keep`.
                            # That is what makes requiring it safe: the model must answer, and
                            # an answer that echoes the schema back is removed rather than
                            # built. Requiring a field is only reasonable when a wrong answer
                            # costs nothing.
                            "required": ["goal", "select", "amount", "name"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "goal": {"type": "string", "enum": ["reach"],
                                         "description": "these must be able to reach each other"},
                                "select": _SELECT,
                                "amount": {"type": "integer",
                                           "description": "how few is too few"},
                            },
                            "required": ["goal", "select"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "goal": {"type": "string", "enum": ["every"],
                                         "description": ("every member of a set must get a "
                                                         "property")},
                                "select": _SELECT,
                                "attr": {"type": "string", "enum": _attrs(),
                                         "description": "which property to give them"},
                                "value": {"type": "string",
                                          "description": "what to set that property to"},
                            },
                            "required": ["goal", "select", "attr", "value"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "goal": {"type": "string", "enum": ["per"],
                                         "description": ("make one new thing for each member "
                                                         "of a set")},
                                "select": _SELECT,
                                "make": {"type": "string", "enum": _kinds(),
                                         "description": "what kind of thing to make"},
                                "link": {"type": "string", "enum": _attrs(),
                                         "description": ("the property tying the new thing "
                                                         "to the member")},
                            },
                            "required": ["goal", "select", "make"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "goal": {"type": "string", "enum": ["observe"],
                                         "description": ("ask each member something, without "
                                                         "requiring an answer")},
                                "select": _SELECT,
                                "fact": {"type": "string", "enum": _facts(),
                                         "description": "what to ask"},
                            },
                            "required": ["goal", "select"],
                            "additionalProperties": False,
                        },
                    ],
                },
            }
        },
        # NOTHING IS REQUIRED. Either answer is a complete one: goals, or a reason there are
        # none. Requiring `goals` is what made refusal unsayable in the first place.
        "additionalProperties": False,
    }


# The default-manifest instance, for callers that only ever wanted that one.
SCHEMA = schema()


def goal_shapes(sc: Dict[str, Any] = None) -> List[str]:
    """Which goal shapes the model is offered. ASKED, never reached into.

    FOUR TEST FILES INDEXED THE LITERAL STRUCTURE — `["properties"]["goals"]["items"]
    ["properties"]["goal"]["enum"]` — so giving each shape its own closed branch broke them
    all with `KeyError: 'properties'`, on a change that made the schema strictly better. A
    structure four readers index by hand is one nobody can improve.
    """
    items = (sc or SCHEMA)["properties"]["goals"]["items"]
    branches = items.get("oneOf") or [items]
    return [b["properties"]["goal"]["enum"][0] for b in branches]


def fields_for(shape: str, sc: Dict[str, Any] = None) -> set:
    """What one goal shape may carry — which is the whole point of the closed branches."""
    items = (sc or SCHEMA)["properties"]["goals"]["items"]
    for b in items.get("oneOf") or [items]:
        if shape in b["properties"]["goal"].get("enum", ()):
            return set(b["properties"])
    return set()


def kinds_offered(sc: Dict[str, Any] = None) -> List[str]:
    """The kinds the model may NAME — the manifest in force, seen from the model's side.

    THE ONE THING A PACKAGE'S MOUNT HAS TO REACH. A capability that cannot be requested is
    not mounted, and this is where that is checked.
    """
    items = (sc or schema())["properties"]["goals"]["items"]
    b = (items.get("oneOf") or [items])[0]
    return list(b["properties"]["select"]["properties"]["kind"]["enum"])


def select_attrs(sc: Dict[str, Any] = None) -> List[str]:
    """The attributes a `where` clause may name — the enum the model actually sees."""
    items = (sc or SCHEMA)["properties"]["goals"]["items"]
    b = (items.get("oneOf") or [items])[0]
    return list(b["properties"]["select"]["properties"]["where"]["items"]
                ["properties"]["attr"]["enum"])

def _relevant(spec: Dict[str, Any], request: str) -> bool:
    """Could this request be about this kind at all? A word match on the kind's own nouns.

    BLINDERS, AND THEY ARE NOT AN OPTIMISATION HERE — they are what makes the example safe to
    show at all. Rendering every loaded kind's example unconditionally was MEASURED at n=3 and
    it bought one search for five broken rungs: rung 10 went from four goals to ZERO, rung 6,
    7 and 9 each lost one, rung 13 gained one. Consistent 3/3 in both arms, so not noise. That
    prompt has no headroom; anything added to it is paid for somewhere else.

    So a kind's example appears only when the request could plausibly be about that kind, and
    the test is the nouns the manifest already carries for the operator's benefit. On every
    request that mentions no browser and no search the prompt is BYTE-IDENTICAL to the one
    the ladder was measured on — which is a property that can be proved without spending a
    single model call, rather than a regression that has to be re-measured after every change.

    THE LIMIT, SAID PLAINLY: a request that needs a search and never uses one of its words
    gets no example and will fail the way it failed before. Widening the match would put the
    example back in front of requests that measurably do worse for seeing it.
    """
    words = {w.strip(".,!?;:'\"").lower() for w in str(request or "").split()}
    nouns = {str(n).lower() for n in (spec.get("nouns") or ())}
    return bool(nouns & words) or bool({n + "s" for n in nouns} & words)


def prompt(kinds=None, request: str = "") -> str:
    """The system prompt, with the DOMAIN named from the manifest in force.

    IT ASSERTED "virtual machines" UNCONDITIONALLY, and that is a false statement the moment
    a package is loaded. Asked to translate "search the web for the diameter of the earth"
    with the Camoufox package mounted — its kinds in the schema, the writer able to plan the
    whole chain — the model answered `cannot: too vague` and was RIGHT TO: it had been told
    the subject was machines, and a web search is not one.

    THE DOMAIN CLAIM AND THE WORKED EXAMPLES, and still nothing else. The examples were left
    frozen on the first pass with the reasoning that changing more than the domain line would
    mix an unmeasured edit into a measured artifact. That was right then and wrong now, because
    the frozen examples turned out to BE the failure — measured, on the real request:

        "search the web for the diameter of the earth"
          -> every, select vm, attr network, value lab
             count 3, select vm

    which is the prompt's own two worked examples RETURNED VERBATIM. The model did not
    misread the request; it never read it. Every demonstration it had was about machines, so
    it produced machines. The subject guard threw both goals away and the session closed
    UNTRANSLATED — honest, and still no answer.

    SO A KIND DECLARES ITS OWN EXAMPLE, and this renders whatever the manifest in force holds.
    The alternative was to synthesise one from a kind's key and nouns, which means inventing
    English inside the extractor for a subject it knows nothing about; the package already
    knows what asking for one of its things sounds like. Same rule as the schema, the enums and
    the domain line — declare it where it is known, do not infer it where it is not.

    THE EXAMPLE MUST NOT BE THE REQUEST ANYBODY MEANS TO TEST. A demonstration the model can
    copy into a passing answer measures copying, which is the defect this exists to remove.
    """
    nouns = []
    for kind, spec in (config.KINDS or {}).items():
        nouns.append((spec.get("nouns") or [kind])[0])
    subject = ", ".join(sorted(nouns)) or "virtual machines"
    out = PROMPT.replace("about virtual machines", f"about {subject}")

    # THE AUTHORING INSTRUCTION THAT USED TO BE INJECTED HERE IS GONE, and it is worth
    # recording why rather than leaving a clean file that looks like it was never tried.
    # The prompt was switched on by a word blinder — {procedure, snippet, script, reusable,
    # save, store, keep, reuse} — which fires on "save a snapshot of web" and "keep the vm
    # running", 5 of 7 realistic requests. It bought a schema field the model filled 0 times
    # in 2. Prompt text is paid for on every request that sees it, and unconditional text was
    # measured at five broken rungs to buy one capability, so this was the shape of a
    # regression with nothing on the other side of the trade.
    #
    # The operator says it instead: `procedure build_box: ...`. No prompt, no schema, no
    # inference, and it cannot false-positive.
    shown = []
    for kind, spec in (config.KINDS or {}).items():
        ex = (spec or {}).get("example") or {}
        req, goal = str(ex.get("request") or "").strip(), str(ex.get("goal") or "").strip()
        if req and goal and _relevant(spec, request):
            shown.append(f'  "{req}"\n     -> {goal}')
    if shown:
        # PLACED AFTER THE TABLE, where a reader looks for more of the same. The five shapes
        # are the vocabulary; these say the vocabulary is not only about machines.
        out = out.replace(
            "`select` names the members",
            "THE SAME SHAPES DESCRIBE EVERY SUBJECT NAMED ABOVE, not only machines:\n"
            + "\n".join(shown)
            + "\n\n`select` names the members")
    return out


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
    # A TOKEN WITH DIGITS AND NO LETTERS IS A NUMBER, whatever punctuation is around it.
    # `vm1` is a NAME that happens to contain a digit and must never be read as one — which is
    # why single tokens are declined below — but that rule also threw away `/2`, and `/2` is
    # how this model wrote "exactly two machines". MEASURED 3/3, and the request it lost is
    # the one this codebase's own note calls the dangerous case: against a real lab it plans
    # seven deletions including vm-orchestrator. It came back UNTRANSLATED instead.
    #
    # THE LETTERS ARE WHAT SEPARATE THEM, so the rule is exact rather than a guess: strip
    # everything that is not a digit, and accept only if nothing alphabetic was there to
    # begin with.
    if not any(c.isalpha() for c in text):
        digits = "".join(c for c in text if c.isdigit())
        if digits:
            return int(digits)
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


# WORDS THAT ARE NEVER A NAME, and every one was observed in a translation. The model fills
# a value slot it has nothing for: "put the red ones on their own network" names no network,
# and the extractor answered `network: "Not specified"` — so the writer created a network
# CALLED `Not specified`. "launch all of them" came back as a machine named `all`; "clone
# golden into 3" as one named `clone of golden`.
#
# THE FAILURE MODE THIS PREVENTS IS THE WORST ONE THE PROBE MEASURES. A prose value does not
# crash: the writer plans faithfully for the wrong goal, the program grounds itself against
# that goal, and the run closes DONE while the world disagrees — 16 of 39 literal and 21 of
# 39 paraphrase runs. `DONE_BUT_FALSE` is the only unacceptable outcome on that path, and a
# placeholder reaching the lab is how it happens.
#
# NARROW ON PURPOSE, and this is the deterministic-rules pattern: compute, and DECLINE WHEN
# UNSURE. Two signals only — whitespace inside a value, and a word from this list — because
# neither can fire on `web`, `db` or `vm-orchestrator`, and a false accusation here refuses a
# correct request. Anything cleverer would be a vocabulary, which is what the language exists
# to delete.
_NOT_A_NAME = {
    "all", "any", "every", "each", "none", "some", "both", "them", "they", "it",
    "not specified", "unspecified", "n/a", "na", "null", "none specified", "tbd",
    "default", "unknown", "whatever", "anything",
}


def _echoed() -> set:
    """Words the model was SHOWN, coming back as if they were the operator's.

    DERIVED FROM THE SCHEMA AND THE MANIFEST, never listed, because listing them is how a
    guard goes stale the first time a field is added. Two sources, and both are the model
    reading its own instructions back:

        the FIELD NAMES it was offered   `name`, `value`, `amount`, `attr`, `fact`, `link`
        the NOUNS for the kinds          `vm`, `machine`, `network`, `snapshot`, `file`

    MEASURED: "make 5 vms" came back as `value: "name"`, and the identity repair — which
    takes a bare name-shaped value on a count of one — turned it into A MACHINE CALLED
    `name`, losing the five. The repair is right about the shape and cannot tell an
    identity from an echo, so the echo is what gets named.
    """
    out = {"name", "value", "amount", "attr", "fact", "link", "make", "goal",
           "select", "where", "kind", "count"}
    for kind, spec in (config.KINDS or {}).items():
        out.add(kind)
        for n in (spec.get("nouns") or ()):
            out.add(str(n).lower())
            out.add(str(n).lower() + "s")          # "machines" is the kind, said twice
        out.add(kind + "s")
        out |= {str(a).lower() for a in (spec.get("attrs") or ())}
    return out


def unusable(sel: Dict[str, Any]) -> Optional[str]:
    """Why this selector names something that cannot exist, or None.

    ASKED OF THE KEY AND OF EVERY REFERENCE, because both become names in the world: a
    kind's key IS the member's name, and an attribute whose name is a declared kind refers
    to a member of it — the convention `precondition` and `_named_in` already use.
    """
    kind = sel.get("kind")
    key = ((config.KINDS or {}).get(kind) or {}).get("key")
    for attr, value in (sel or {}).items():
        if attr in ("kind", "not") or not isinstance(value, str):
            continue
        names_a_member = attr == key or attr in (config.KINDS or {})
        if not names_a_member:
            continue
        if value.strip().lower() in _NOT_A_NAME | _echoed():
            return (f"{attr} = {value!r} is a word, not a name — the request named no "
                    f"{attr}, and inventing one puts it in the lab")
        # UNLESS THE KIND SAYS ITS KEY IS PROSE. A `search` is keyed by its QUERY, and a query
        # with no spaces in it is the rare one — so the space rule, which is right for every
        # kind whose key is a handle, is exactly backwards here.
        #
        # `key_freetext` WAS ALREADY DECLARED FOR THIS AND ALREADY READ BY `_name_shaped`.
        # This guard never asked. Two guards answering one question by different standards is
        # the same defect as yesterday's intent gate refusing the writer's own output, and it
        # cost the whole Camoufox path: the model DID capture the question, `to_goals` DID fold
        # it onto the key, and then this line threw it away — leaving `COUNT(search) = 1` with
        # nothing to search for, which `cover()` rightly refused to plan, which made an empty
        # program, which closed DONE.
        #
        # THE REFERENCED KIND'S FLAG, NOT THIS ONE'S: `attr` may name another kind entirely.
        owner = kind if attr == key else attr
        if ((config.KINDS or {}).get(owner) or {}).get("key_freetext"):
            continue
        if any(c.isspace() for c in value.strip()):
            return (f"{attr} = {value!r} reads as a description rather than a name")
    return None


def to_goals(raw: Dict[str, Any], request: str = "") -> List[Dict[str, Any]]:
    """The model's answer, in the shape `ghost_writer.cover` takes.

    Anything malformed is DROPPED rather than repaired. A goal missing the field its own
    shape requires is a goal the model did not actually state, and inventing the missing
    half here would put this module back in the business of deciding what the operator
    meant — which is the job it exists to not have.

    AND A GOAL NAMING SOMETHING THAT CANNOT EXIST IS DROPPED TOO. See `unusable`: a value
    slot filled with prose is not a smaller mistake than a missing field, it is a larger
    one, because the writer plans faithfully for it and the run closes DONE.
    """
    out: List[Dict[str, Any]] = []

    def _keep(goal: Dict[str, Any]) -> None:
        """Admit a finished component, unless its selector names something that cannot exist.

        ONE PLACE, AT THE END. Every branch below builds a selector its own way and several
        REPAIR one — moving a value out of the wrong slot, reading a bare value as an
        identity — so the only selector worth judging is the one that comes out.
        """
        sel = goal.get("select") or goal.get("every") or goal.get("observe") or {}
        if not isinstance(sel, dict):
            return
        why = unusable(sel)
        if why:
            # STRIP THE NAME, KEEP THE GOAL. Dropping the whole component threw away a
            # perfectly good count because the model had echoed `machines` into the name
            # slot — the request survived as nothing rather than as most of itself.
            #
            # THE KIND IS THE EXCEPTION: a selector whose KIND is unusable describes nothing
            # at all, and there is no smaller true statement left inside it.
            kind = sel.get("kind")
            key = ((config.KINDS or {}).get(kind) or {}).get("key")
            trimmed = {k: v for k, v in sel.items()
                       if not (k == key or k in (config.KINDS or {}))
                       or not unusable({"kind": kind, k: v})}
            if not trimmed.get("kind") or unusable(trimmed):
                return
            goal = {**goal, ("select" if "select" in goal else
                             "every" if "every" in goal else "observe"): trimmed}
        out.append(goal)

    def _scoped(goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """An UNFILTERED `every` beside a goal that names ONE member is about that member.

        THE SCOPE ERROR, AND IT IS THE LAST THING BETWEEN THE BUILDER AND WORKING. "a machine
        called box1 running linux" translates to two goals — `count(vm WHERE name=box1) = 1`,
        which is right, and `every vm must be linux`, which is not. The second lowered to a
        goal about `work-laptop`, an existing machine with a different OS, and the writer
        honestly refused. `box1` survived and the words "running linux" ESCAPED THEIR
        RECEIVER and attached to every machine the operator owns.

        THE RECEIVER IS THE FIX AND IT IS THE WHOLE CLASSES ARGUMENT: a property asked of an
        object cannot land on the wrong object, because the scope is the receiver. Until the
        extractor emits receiver-scoped goals this folds them back together afterwards.

        NARROW, AND IT DECLINES WHEN UNSURE — the deterministic-rules pattern:

            the `every` carries a FILTER      -> it names its own set; leave it
            more than one member is named     -> which one? cannot say; leave it
            the kinds differ                  -> unrelated clauses; leave it

        So "create 3 machines and make them all linux" is untouched (no member is named), and
        "create alpha, then launch every stopped vm" is untouched (the `every` is filtered).
        """
        # FIRST, THE UNAMBIGUOUS CASE: an `every` whose selector is IDENTICAL to a count's.
        # Both goals are about THE SAME MEMBER, said twice, so merging them cannot move a
        # property onto anything the operator did not point at — no guess, no decline.
        #
        # THE FOLD BELOW COULD NOT DO IT, AND THE GAP OPENS WHEN TRANSLATION IS RIGHT. It
        # requires the `every` to carry ONLY a kind, because it exists to give a receiver to
        # a property that escaped one. An `every` the extractor already scoped has two keys
        # and matches nothing here — so the better translation got the worse plan.
        #
        # MEASURED 2026-08-03 on `procedure p(STRING name, STRING os_name)`:
        #
        #   count:vm[name=X] == 1                  -> place create_vm(os_type=linux, name=X)
        #   every vm[name=X] must os_type=Y        -> count:vm[name=X os_type=Y] == 1
        #                                          -> create_vm AGAIN -> Unsolvable
        #
        # The writer creates the machine for the first goal, `create_defaults` gives it
        # `os_type: linux`, and NOTHING CHANGES os_type AFTER BIRTH — so the second goal is
        # unreachable by construction and the whole request dies. One `create_vm` carrying
        # both attributes is the only plan that was ever possible, and merging is how the
        # writer gets to see it.
        merged = []
        for g in goals:
            want, must = g.get("every"), g.get("must")
            if isinstance(want, dict) and must:
                host = next((h for h in goals
                             if h is not g and h.get("eq") == 1
                             and isinstance(h.get("select"), dict)
                             and h["select"] == want), None)
                if host is not None:
                    host["select"] = {**host["select"], **must}
                    continue
            merged.append(g)
        goals = merged

        named = [g for g in goals
                 if "select" in g and g.get("eq") == 1
                 and len(g["select"]) == 2 and "kind" in g["select"]]
        if len(named) != 1:
            return goals
        host = named[0]
        kind = host["select"]["kind"]
        out2 = []
        for g in goals:
            sel = g.get("every")
            if (g is not host and isinstance(sel, dict) and sel.get("kind") == kind
                    and len(sel) == 1 and g.get("must")):
                host["select"] = {**host["select"], **g["must"]}
                continue
            out2.append(g)
        return out2

    for g in (raw or {}).get("goals") or []:
        shape, sel = g.get("goal"), _to_select(g.get("select") or {})
        if not sel.get("kind"):
            continue
        # NOTE: the usability check is at the END of this loop, on the FINAL selector — see
        # `_keep`. Checked here it ran BEFORE the repairs that fill the selector in, so a
        # name the repair had just invented was never examined: "make 5 vms" came back as
        # `value: "name"`, the identity repair made it A MACHINE CALLED `name`, and the guard
        # had already passed on a selector that did not yet contain it.
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
            # THE DECLARED NAME FIRST, because it is the one slot that cannot mean anything
            # else. Everything below repairs a name that arrived in the WRONG field; this is
            # the field that was missing, and a request whose name reached it needs no repair
            # at all.
            named = g.get("name")
            # A NAME THAT IS A NUMBER IS THE COUNT, and nothing else it could be. Giving the
            # count branch its own closed shape stopped the model losing names — box1 now
            # survives "a machine called box1 running linux", which it never did — and moved
            # the failure one slot over: `name` is the only string field left, so a count
            # lands in it. "make sure there are exactly two machines" came back as A MACHINE
            # CALLED 2.
            #
            # THE REPAIR IS EXACT rather than a guess: no member is named by a bare number,
            # and `_as_count` already knows what a number looks like — including the `/2` the
            # model writes for "two". A name with a digit IN it (`vm1`) is untouched, because
            # that is not a bare number.
            if named is not None and _as_count(named) is not None \
                    and not any(c.isalpha() for c in str(named)):
                if _as_count(g.get("amount")) is None:
                    eq = _as_count(named)
                named = None
            if named is not None and str(named).strip():
                spec = (config.KINDS or {}).get(sel.get("kind")) or {}
                key = spec.get("key")
                if key and key not in sel:
                    sel = {**sel, key: _coerce(str(named).strip())}
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
            _keep({"shape": "count", "select": sel, "eq": eq})
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
            _keep({"shape": "reach", "select": sel,
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
                _keep({"shape": "count",
                            "select": {**sel, attr: _coerce(g["value"])}, "eq": 1})
            else:
                _keep({"every": sel, "must": {attr: _coerce(g["value"])}})
        elif shape == "per" and g.get("make"):
            link = g.get("link") or _link_between(sel.get("kind"), g["make"])
            if link:
                _keep({"per": sel, "make": g["make"], "link": link})
        elif shape == "observe":
            _keep({"observe": sel, "fact": g.get("fact") or "alive"})
    out = _scoped(out)
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
    from .channel import constrained
    return constrained(prompt(request=request), request, schema(),
                       model=model, temp=temp, timeout=timeout)


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
