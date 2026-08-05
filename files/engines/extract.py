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
    """Every queryable attribute — ONE SPELLING EACH, plus what can be observed.

    ALIASES WERE OFFERED HERE AND ARE NOT ANY MORE — "the operator's words, not ours" was
    the reasoning, and it is the right instinct in the wrong place. The model does not read
    the operator's sentence out of this enum; it picks a slot from it under a CONSTRAINED
    GRAMMAR, so every alias is one more indistinguishable choice at the moment of picking
    and buys nothing at the moment of reading — `_to_select` resolves whatever arrives, and
    a canonical name needs no resolving.

    IT WAS 25 CHOICES FOR 14 ATTRIBUTES, five concepts spelled three ways each:

        cores · cpu · cpu_cores          memory · memory_mb · ram
        net · net_name · network         label · labels · tag          os · os_type

    A WIDE OPEN SLOT SURFACE IS THE ONE THING EVERY MEASUREMENT IN THIS FILE SAYS THIS MODEL
    IS BAD AT — it is the whole argument for giving each goal shape its own closed branch
    ("the model chose a slot from a wide open surface on every goal it wrote"), and the
    `where` clause was still carrying the old shape inside the new one.

    `observed` STAYS, and it is not an alias. `alive` is a fact the world can be ASKED for
    rather than a second name for a stored one, and it is exactly the attribute rung 11's
    missing clause selects on — dropping it would make that clause unrepresentable while
    trying to make it findable.

    `_to_select` STILL RESOLVES ALIASES and that is deliberate, not leftover: the grammar
    covers the model's path into this enum, and nothing covers a hand-built dict, a package
    manifest, or a differently-served model.
    """
    out = set()
    for k, spec in (config.KINDS or {}).items():
        if kind and k != kind:
            continue
        out |= set(spec.get("attrs") or ())
        out |= set((spec.get("observed") or {}).keys())
    return sorted(out)


def _can_reach() -> List[str]:
    """The kinds that can be asked to reach each other — DERIVED, never listed.

    `ghost_writer` needs exactly two things to plan a reach: a PROBE that asks whether a
    member is alive, and a CONNECTIVE setter whose value `refs` another kind, so members can
    be put somewhere together. A kind with neither cannot be made to reach anything, ever.

    ONLY `vm` HAS BOTH, and every other kind has NEITHER — no probe and no connector. So a
    reach over a network is not a hard goal, it is an unplannable one, and the schema was
    offering it: rung 9's paraphrase came back `reach(network WHERE net_name IN [n1,n2,n3])`
    for a request about machines, the writer looked for networks by those names, found none,
    and planned ZERO calls. UNMET 3/3.

    THE LITERAL ARM PROVES THE REST OF THE READING IS FINE. It answers the same request with
    the same pairwise decomposition and the same `min: 1`, differing only in the KIND, and it
    passes — so the kind is the whole of the failure.

    DERIVED FROM THE MANIFEST RATHER THAN NAMED, because a package that mounts a kind with a
    probe and a connector should get `reach` without an edit here, and one without them
    should never be offered it. Same rule as `asks_reach` one layer up: a shape a request
    cannot mean is not offered to it — here, a shape a KIND cannot satisfy.
    """
    from planner.ir import effects as _effects
    out = []
    for kind, spec in (config.KINDS or {}).items():
        probe = _effects.probe_for(kind, "alive", config.KINDS)
        link = next((s for s in (spec.get("setters") or {}).values() if s.get("refs")), None)
        if probe and link:
            out.append(kind)
    return sorted(out) or _kinds()


def _settable() -> List[str]:
    """The attributes an `every … must` may name — everything EXCEPT what is merely OBSERVED.

    A FINDING IS NOT A STATE YOU BRING ABOUT. `alive` and `exists` are answers the world
    GIVES; nothing sets them, and no plan can make a machine answer a ping. Asking for
    `every vm must alive=true` is asking the world to become something no tool can make it —
    it is not a hard goal, it is an unsatisfiable one.

    AND THE MODEL EMITS IT INSTEAD OF THE THING THAT WORKS. Rung 11 — "ping every vm and stop
    the ones that do not answer" — comes back as TWO independent assertions:

        every vm[] must alive  = true      <- unsatisfiable, and the condition in disguise
        every vm[] must status = stopped   <- right pair, EMPTY selector

    The condition belongs in the SELECTOR: `every vm[alive=false] must status=stopped`, which
    the language already accepts and the writer already plans (verified end to end — it emits
    `guest_ping` for each member, then `stop_vm` for the ones that did not answer). Blinded to
    the `every` shape the model produces `status=stopped` correctly and leaves the selector
    empty, so the pair is not the difficulty; the CONDITION having a legal home elsewhere is.

    SO THE WRONG HOME IS CLOSED. Four attempts to TEACH the construction failed on 2026-08-05
    — a filtered example, a second example, its own table row, and the whole provenance family
    — and this is the move that has worked instead every time: make the wrong shape
    unrepresentable and leave the right one as the only place the clause can go.

    OBSERVED ONLY, AND NOT `setters`. Restricting to what a setter can write would take
    `memory_mb`, `cpu_cores` and `os_type` with it — the coverage corpus asks "give the
    machine called burner 8192 MB of memory" and means it. Those are attributes the world
    HOLDS and a creator or an act can establish; they are simply not findings. The line is
    between what the world is TOLD and what the world is ASKED.
    """
    observed = set()
    for spec in (config.KINDS or {}).values():
        observed |= set((spec.get("observed") or {}).keys())
    return [a for a in _attrs() if a not in observed]


def _facts() -> List[str]:
    out = set()
    for spec in (config.KINDS or {}).values():
        out |= set((spec.get("observed") or {}).keys())
    return sorted(out) or ["alive"]


# ONE BRANCH PER SHAPE OF GOAL, and the set is closed. A request that fits none of these is
# one the writer could not build anyway, so the honest outcome is a refusal at this step
# rather than a program nobody can trust.
def schema(kinds=None, request: str = "") -> Dict[str, Any]:
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
        # EVERY GOAL MUST SAY WHICH MEMBERS IT IS ABOUT, in the one shape that cannot be
        # abused: a list of (attr, value) where `attr` is an ENUM — the closed type this
        # model is measurably good at. EMPTY IS LEGAL and means "all of them", so requiring
        # the FIELD is not requiring a filter; it is requiring that a filter was CONSIDERED.
        #
        # MEASURED TWICE. On `count` it is what stopped every qualifier falling into `name`
        # (see that branch). On `per` it is what recovers a filter that was being dropped in
        # silence — "take a snapshot of every RUNNING vm" came back as `per vm make=snapshot`
        # over ALL of them, so the stopped machine was snapshotted too and the run reported
        # success. With the field required: `per vm[status=running] make=snapshot`.
        # `except` IS NOT REQUIRED, AND THAT WAS MEASURED RATHER THAN ASSUMED. The evidence
        # for requiring it looked overwhelming — offered as optional the model emitted it
        # ZERO times in 28 runs, and required it immediately produced rung 8's carve-out for
        # the first time: `every vm[] !{name=db} network=core`. It is still a NET LOSS:
        # literal 29 -> 27/42 with DONE_BUT_FALSE 3 -> 9, paraphrase false 5 -> 8, breaking
        # rungs 2 and 11 on the literal arm and 3 on the paraphrase — and rung 8 STILL failed,
        # because the second clause ("db goes on dmz") came back carved out too.
        #
        # A REQUIRED FIELD GETS FILLED WHETHER OR NOT IT IS MEANT. That is what makes
        # requiring `where` and `name` work — every request HAS members and most name one —
        # and it is exactly what makes requiring an EXCEPTION wrong: most requests carve out
        # nothing, so the model invents one to have something to say.
        "required": ["kind", "where"],
        "additionalProperties": False,
    }

    out = {
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
            # REFUSAL IS UNGUIDED AND TWO FIXES HAVE NOW BEEN MEASURED AND WITHDRAWN. The
            # field is a FREE STRING: legal to fill, never chosen, and its description says
            # to use it when the request "asks for something these goals cannot say" — which
            # names nothing. 0 of 8 unstateable requests are declined (`coverage_probe`).
            # The model is shown every shape the goals HAVE and never what they lack, and a
            # model cannot decline against an absence.
            #
            # ATTEMPT 1, ENUMERATE THE REASONS (2026-08-04). A closed `refusals` table —
            # order, branch, over_time, compare, cause, unclear — bought 0/8 -> 4/8 honest
            # refusals and cost 2 of 14 ordinary requests, then deterministically refused `a
            # vm named param_name with os param_os_name` as `order`, 3 of 3, which is the
            # request the whole parameterised-procedure feature rests on. SIX WORDS TO
            # CHOOSE BETWEEN IS LESS WORK THAN COMPOSING A GOAL.
            #
            # ATTEMPT 2, MAKE REFUSING COST SOMETHING (2026-08-05). `cannot` became an
            # object requiring `words` — a verbatim span of the request — beside `why`, with
            # a deterministic check dropping any refusal whose span was not in the text, and
            # a prompt paragraph telling the model to quote before it refuses. Measured
            # n=3 against a re-run baseline:
            #
            #     baseline    10 TRANSLATED · 0 DECLINED · 10 FORCED · 2 BROKE    0/8 declined
            #     span         7 TRANSLATED · 3 DECLINED ·  9 FORCED · 3 BROKE    2/8 declined
            #
            # WORSE THAN THE ENUM ON EVERY AXIS — half the refusals for 3 broken ordinary
            # requests instead of 2 — and the bisect is the part worth keeping. Reverting
            # ONLY the prompt paragraph and leaving the object schema recovered all three
            # regressions AND lost both declines: 3/3 stateable, 0/3 unstateable. So the
            # PROMPT TEXT caused the gain and the damage alike, and the schema shape on its
            # own is inert. There is no version of that idea that keeps the refusals without
            # the regressions, which is why the object is not here.
            #
            # WHAT BOTH ATTEMPTS SHARE: they tell the model MORE ABOUT REFUSING, and a model
            # told more about refusing refuses more — correct requests included. The lever
            # is not a better description of when to decline.
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
                                # A COUNT IS NEVER NEGATIVE, AND SAYING SO IN THE GRAMMAR IS
                                # THE WHOLE FIX FOR THE WORST BUG THIS SEAM HAS HAD. Asked to
                                # "delete every machine labelled scratch" the model answered
                                # `amount: -1` — a DELTA, not a count — and `_as_count`
                                # stripped the sign and returned 1. So a request to remove
                                # every scratch machine became `count(vm WHERE label=scratch)
                                # = 1`, and the writer planned it faithfully:
                                #
                                #   3 scratch machines exist -> remove the LABEL from 2 of
                                #                               them, delete nothing, DONE
                                #   0 scratch machines exist -> CREATE a machine and label it
                                #                               `scratch`, DONE
                                #
                                # A DELETION REQUEST THAT CREATES A MACHINE, silently: nothing
                                # reached `dropped`, and `coverage_probe` judges shapes and
                                # names so it read the row as merely the wrong shape. Found
                                # 2026-08-05 by dumping RAW beside GOALS on the rows that
                                # fail, which is the audit this codebase keeps being paid by.
                                #
                                # `minimum` REACHES THE DECODER — verified against ollama, not
                                # assumed: asked point blank for -1 under this constraint the
                                # model returns 0. So the wrong answer is unrepresentable
                                # rather than repaired, which is the move that has worked
                                # every time here. `_as_count` refuses a signed token as well,
                                # because a hand-built dict and a differently-served model are
                                # both paths the grammar does not cover.
                                "amount": {"type": "integer", "minimum": 0,
                                           "description": ("HOW MANY there must be, as a TOTAL "
                                                           "and never as a change. Zero means "
                                                           "none may remain — that is how you "
                                                           "say delete")},
                                "name": {"type": "string",
                                         "description": (
                                             "the NAME of the member, when the operator gave "
                                             "one — 'a vm called box1' puts box1 here. A "
                                             "LABEL, A GROUP OR A DESCRIPTION IS NOT A NAME: "
                                             "those belong in select.where. Empty string when "
                                             "no member is named")},
                                # `where` IS REQUIRED BESIDE THIS ONE, and the pair is the
                                # whole fix. `name` alone was REQUIRED and `where` optional,
                                # so this was the only free string in the branch and every
                                # qualifier fell into it:
                                #
                                #   "exactly 3 vms carry the 'prod' label"  -> name=prod
                                #   "3 vms labelled 'red'"                  -> name=red
                                #   "spin up five machines…"                -> name=reach
                                #
                                # A NAME IS AN IDENTITY, so `count(vm WHERE name=prod) = 3`
                                # asks for three members sharing one — a world that cannot
                                # exist — and the writer honestly refuses the WHOLE request.
                                # It was the commonest translation failure measured.
                                #
                                # REMOVING IT WAS TRIED AND IS WORSE: with nowhere to put an
                                # identity the model left `where` EMPTY and the names went
                                # with it — "create a network called lab and a vm named web"
                                # came back as two unfiltered counts, and the writer minted
                                # `network1` and `vm1`. That is the exact failure this field
                                # was added for, and rung 3 — a CONTROL rung — went OK to
                                # UNMET on it.
                                #
                                # SO BOTH ARE REQUIRED. Given a home for the qualifier the
                                # model USES it — `attr` is an enum, which this model is
                                # measurably good at — and what lands here instead is PROSE
                                # ("prod label on exactly 3 vms", "exactly two vms"), which
                                # `unusable` already strips on whitespace. What survives as a
                                # single junk word is a value the answer used as a property
                                # elsewhere, which `_not_an_identity` already strips on the
                                # model's own evidence. Every guard needed was already built.
                                #
                                # MEASURED: rungs 6 and 7 translate correctly for the first
                                # time — count vm[label=red] = 3 beside count vm[label=blue]
                                # = 2 — while rungs 1 and 3 keep their names.
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
                                # A KIND THAT CANNOT REACH IS NOT OFFERED ONE. Only a kind
                                # with a probe AND a connective setter can be planned into a
                                # reach; every other kind has neither. See `_can_reach`.
                                "select": {**_SELECT, "properties": {
                                    **_SELECT["properties"],
                                    "kind": {"type": "string", "enum": _can_reach()}}},
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
                                # WITHDRAWN AFTER MEASUREMENT, and recorded so it is not
                                # tried a third time. "A VERB IS USUALLY A PROPERTY:
                                # starting or stopping something is `status`" was put here
                                # as the CHEAP carrier for a hint that works — written into
                                # the prompt's goal table the same sentence moved rungs 2
                                # and 4 to passing on the paraphrase arm. In a field
                                # description it did NOTHING: 17/42 and 9/42, byte-identical
                                # to the run without it, not one rung changed at n=3.
                                #
                                # THE MODEL READS THE TABLE AND NOT THE FIELD DESCRIPTIONS,
                                # which is the same finding as the `procedure` field it
                                # filled 0 times in 2. A description is not a place to teach
                                # from.
                                # A FINDING IS NOT A STATE YOU BRING ABOUT — see
                                # `_settable`. `alive` is an answer the world gives, so
                                # `every vm must alive=true` is unsatisfiable, and it is
                                # exactly what the model reaches for instead of putting the
                                # condition in the SELECTOR where rung 11 needs it.
                                "attr": {"type": "string", "enum": _settable(),
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

    # ## DECLARED CLAUSE PROVENANCE — BUILT TWICE, MEASURED TWICE, WITHDRAWN 2026-08-05
    #
    # THE DEFECT IT WAS FOR is the only one nothing in this system can see: a clause NOBODY
    # TRANSLATED. Rung 11 — "ping every vm AND STOP THE ONES THAT DO NOT ANSWER" — comes back
    # as a single `observe` and the second half is simply absent, so no goal is wrong, none is
    # dropped, every guard downstream passes, and the run closes DONE over half a request.
    # `clause_ledger`'s own docstring asked for exactly this fix on 2026-08-01: have each goal
    # SAY which clause it came from, and reconciliation becomes an exact set difference with
    # no matching at all.
    #
    # ATTEMPT 1 — A FREE-TEXT SPAN, quote the words you came from. The model answered with
    # THIS SCHEMA back: `fact alive`, `link vm`, `every`, `per vm`, `except`, and twice the
    # bare word `and`. That is `_echoed`'s failure one field over, and asking for a verbatim
    # quotation is the hardest free string there is. **9 false positives on 12 passing rungs.**
    #
    # ATTEMPT 2 — A CLOSED ENUM built by `clause_ledger.enumerate_clauses`, so a goal could
    # only ever name a real piece of the request. It fixed the echoing completely — every span
    # came back a genuine clause — and the model then PICKED ONE CLAUSE AND REPEATED IT: all
    # four of rung 4's goals claimed "and make sure they all ping each other", leaving three
    # correctly-translated clauses looking uncovered. **6 false positives on 12 passing rungs.**
    #
    # AND IT MISSED THE ONE CASE IT WAS BUILT FOR, which is what settled it. Rung 11 reported
    # CLEAN on both arms: two spans came back, one per raw goal, but only ONE goal survived
    # `to_goals` — the second span belonged to the invented `per` that was thrown away. The
    # detector was reading provenance from goals that do not exist in the output, and rung 12's
    # paraphrase reported clean with ZERO surviving goals. Scoring it on survivors instead
    # fixes that and can only RAISE the false-positive count, because it removes covering
    # spans and adds no new ones.
    #
    # THE STANDING CONCLUSION: THE FRONT SEAM CANNOT SELF-REPORT WHAT IT FAILED TO TRANSLATE.
    # Four mechanisms have now been measured on this one problem — `clause_ledger.reconcile`
    # against a plan (24 of 26 complete plans called incomplete), its pigeonhole detector
    # against the goals (unsound in principle: clauses and goals are not in bijection), a
    # quoted span, and a closed enum. A fifth variant of "ask the model where each goal came
    # from" is not the move. What is left is STRUCTURAL detection that asks the model nothing,
    # and it has no design yet.

    # `reach` IS NOT OFFERED TO A REQUEST THAT NEVER MENTIONS REACHING, which moves a guard
    # that already existed from AFTER generation to BEFORE it. `to_goals` has always dropped
    # such a goal — twenty of twenty-three extraction failures on 2026-08-01 were one — and a
    # grammar that permits what the reader is guaranteed to throw away is a grammar that
    # invites the answer nobody can use.
    #
    # WHAT IT COSTS THE MODEL IS A PLACE TO PUT A CLAUSE IT CANNOT SHAPE, and that is the
    # point. "create a vm named beta AND THEN LAUNCH IT" and "put web on lab" both came back
    # as `reach`, on both arms, every run: a clause that ACTS ON A NAMED MEMBER has no shape
    # the model reliably reaches for, so it grabs the one that takes a bare set. Both are
    # expressible — `every vm[name=beta] must status=running` — and with `reach` gone the
    # model has to find it. MAKE THE WRONG ANSWER UNREPRESENTABLE RATHER THAN REJECT IT
    # AFTERWARDS, which is `master.ops`' move and the one that has worked twice today.
    #
    # ONLY WHEN A REQUEST WAS GIVEN. Called bare — `SCHEMA`, the probes, `assert_enforced` —
    # the full grammar is returned, because "no request" is not "a request about nothing".
    if request and not asks_reach(request):
        branches = out["properties"]["goals"]["items"]["oneOf"]
        out["properties"]["goals"]["items"]["oneOf"] = [
            b for b in branches if b["properties"]["goal"]["enum"] != ["reach"]]

    # ## `per` IS NOT NARROWED THE SAME WAY, AND THE REASON IS MEASURED — 2026-08-05
    #
    # THE HALLUCINATION DID MOVE HERE when `reach` was closed. Four of six extractions on
    # rungs 10 and 11 came back with a `per` MAKING A SNAPSHOT nobody asked for, on requests
    # about pinging and cloning — the model still reaches for an unguarded shape "when it has
    # nothing else to say", and `per` is now the unguarded one.
    #
    # AND GATING IT — offer `per` only where a linkable kind is mentioned — WAS BUILT, RAN
    # CLEAN, AND WAS WITHDRAWN. It did exactly what it promised at the schema (`per` gone from
    # rungs 1, 10 and 11, kept for rung 12 and the mixed-kind rows) and it made the ladder
    # WORSE where it counts:
    #
    #     rung 11, literal, before   UNTRANSLATED 3/3   — refused, honestly
    #     rung 11, literal, after    DONE_BUT_FALSE 3/3 — pinged, reported success, stopped nothing
    #
    # THE INVENTED GOAL WAS ACCIDENTALLY LOAD-BEARING, and that is the finding. "Ping every vm
    # and stop the ones that do not answer" has a second clause the model cannot express
    # (`every vm[alive=false] must status=stopped`, which no model size has ever produced).
    # The spurious `per` was DROPPED by `to_goals`, and `orchestrator` closes UNTRANSLATED the
    # moment anything is dropped — the operator's half-a-request ruling. So the hallucination
    # was tripping the safety net that the MISSING clause never trips. Remove it and the run
    # serves half the request in silence.
    #
    # WHAT THIS ACTUALLY SAYS TO FIX. Not the `per` gate — the fact that a clause NOBODY
    # TRANSLATED has no detector at all. `planner/clause_ledger` is precisely that mechanism
    # and it has NO PRODUCTION CALLER (`built and never called`, again). Wire that first,
    # measure it, and only then take away the accident that is standing in for it.
    #
    # ## THE GATE WAS RETRIED WITH VACUITY BEHIND IT, AND IT FAILED AGAIN — 2026-08-05
    #
    # The withdrawal note above says to build the detector first and then take away the
    # accident standing in for it. `intent.vacuous` was built, and the gate was retried on
    # exactly that reasoning. **Rung 11 went DONE_BUT_FALSE 3/3 a second time**, and the
    # cause is worth more than the gate was:
    #
    #     with `per` offered   observe + an invented `per` -> per DROPPED -> UNTRANSLATED
    #     with `per` gated     observe + count(vm WHERE name='unresponsive') = 0 -> DONE
    #
    # THE MODEL MOVED THE CLAUSE IT CANNOT EXPRESS INTO A THIRD SHAPE. `unresponsive` appears
    # NOWHERE in "ping every vm and stop the ones that do not answer" — it is an invented
    # identifier — and a `count` with a name in it is neither VACUOUS (it asserts something)
    # nor DROPPED (no rule refuses it), so both new guards stay silent and the writer plans
    # four calls for it.
    #
    # THE HALLUCINATION IS CONSERVED, and that is the finding. `reach` was closed on
    # 2026-08-04, the pressure moved to `per`; close `per` and it moves to `count`. Each hop
    # lands somewhere HARDER to detect — a spurious `reach` and a spurious `per` were both
    # droppable, and an invented name is not. CLOSING SHAPES ONE AT A TIME IS A LOSING GAME
    # while the clause has nowhere legitimate to go: rung 11's second half is `every
    # vm[alive=false] must status=stopped`, which no model size has ever produced.
    #
    # WHAT WOULD ACTUALLY MAKE THIS SAFE is a guard on the INVENTED IDENTIFIER — a `name` a
    # selector commits to that does not appear in the request is not a name the operator
    # gave. `coverage_probe.judge` already counts exactly that as FORCED, and production has
    # no equivalent. Build and measure that FIRST; the gate is not the thing in the way.

    # ## THIRD ATTEMPT, WITH `invented` BEHIND IT — the guard now exists
    #
    # The clause moved to `count(vm WHERE name='unresponsive') = 0`, and `extract.invented`
    # drops exactly that: a well-formed name the request never says. So rung 11 with `per`
    # gated should now DROP a goal and close UNTRANSLATED honestly, rather than assert a
    # thing about a machine nobody mentioned.
    if request:
        mentioned = [k for k, spec in (config.KINDS or {}).items()
                     if _relevant(spec or {}, request, k)]
        makeable = [k for k in mentioned
                    if any(s != k and _link_between(s, k) for s in (config.KINDS or {}))]
        if len(mentioned) < 2:
            makeable = []
        branches = out["properties"]["goals"]["items"]["oneOf"]
        if makeable:
            for b in branches:
                if b["properties"]["goal"]["enum"] == ["per"]:
                    b["properties"]["make"]["enum"] = makeable
        else:
            out["properties"]["goals"]["items"]["oneOf"] = [
                b for b in branches if b["properties"]["goal"]["enum"] != ["per"]]
    return out




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

def _relevant(spec: Dict[str, Any], request: str, kind: str = None) -> bool:
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
    said = str(request or "").lower()
    words = {w.strip(".,!?;:'\"") for w in said.split()}
    nouns = {str(n).lower() for n in (spec.get("nouns") or ())}
    # THE KIND'S OWN NAME COUNTS. `nouns` is the list of OTHER words for a thing — snapshot
    # declares `restore point` and `checkpoint` and not `snapshot` — so asking only that list
    # answered NO to "take a SNAPSHOT of every running vm", which is the plainest possible
    # way to mention one.
    if kind:
        nouns.add(str(kind).lower())
    # A NOUN MAY BE TWO WORDS, and `restore point` could never match a set of single ones.
    # Matched as a substring where it contains a space, and as a whole word otherwise, so
    # `net` still does not fire on `network`.
    for n in nouns:
        if " " in n:
            if n in said:
                return True
        elif n in words or (n + "s") in words:
            return True
    return False


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
        if req and goal and _relevant(spec, request, kind):
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
    key = ((config.KINDS or {}).get(kind) or {}).get("key")
    out: Dict[str, Any] = {"kind": kind}
    for pair in raw.get("where") or []:
        attr = alias.get(pair["attr"], pair["attr"])
        # AND THE VALUE IS RESOLVED THE SAME WAY THE ATTRIBUTE IS. `canonical_value` is the
        # value-side twin of the alias table above: what the operator calls a state, mapped
        # to the one the world stores. `up` is `running`.
        #
        # DECLARED, NOT INFERRED, and the distinction is the whole reason this line is safe.
        # `unusable` refuses a value outside `attr_values` — rightly, since a filter the
        # world cannot hold matches nothing for ever and a goal about nothing is VACUOUSLY
        # TRUE — and rung 12's paraphrase, "each machine that is currently up", was refused
        # 3 of 3 on exactly that. This module REFUSED TO MAP IT ON ITS OWN, and its comment
        # in `unusable` says why: an inferred synonym is how a vocabulary starts. A declared
        # one is a manifest row and the operator's call, made 2026-08-05.
        #
        # IT RESOLVES AND DOES NOT JUDGE. Anything undeclared passes through untouched, so
        # `unusable` still sees the real value and still refuses what the world cannot hold.
        value = config.canonical_value(kind, attr, _coerce(pair["value"]))
        # THE KEY SAID TWICE IS A LIST, NOT AN OVERWRITE. "make sure n1, n2 and n3 can all
        # ping each other" comes back as three `where` pairs on `name`, and this line kept
        # the last one — so a request about THREE machines became a goal about ONE, and a
        # `reach` over one member is trivially true. Rung 9, DONE_BUT_FALSE, deterministically.
        #
        # IT IS A DERIVATION, NOT A GUESS, and that is what separates it from the repairs
        # this module has had to withdraw. A member has exactly ONE key, so `name = n1 AND
        # name = n2` is provably EMPTY as a conjunction — there is no world where it holds.
        # Membership is the only reading under which the answer says anything at all, and it
        # PRESERVES what was already being thrown away rather than inventing anything.
        #
        # THE KEY, AND ONLY THE KEY. `label` is multi-valued — a machine may carry `red` AND
        # `blue`, so folding those to "either" would change what was asked. `status` is
        # single-valued but CLOSED, and two states is a contradiction the value guard already
        # reports. Neither is this rule's business.
        if attr == key and attr in out and out[attr] != value:
            held = out[attr]
            members = list(held["in"]) if isinstance(held, dict) and "in" in held else [held]
            if value not in members:
                members.append(value)
            out[attr] = {"in": members}
            continue
        out[attr] = value
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
    #
    # A HYPHEN DISQUALIFIES THE WHOLE TOKEN, and that clause is the difference between an
    # honest failure and the worst program this seam has ever written. Stripping "everything
    # that is not a digit" also strips a MINUS SIGN: `-1` came back as `1`, so "delete every
    # machine labelled scratch" — which the model answers as `amount: -1`, a delta — became
    # "exactly one machine labelled scratch must exist", and the writer then CREATED one
    # against a clean lab. A count has no sign, so a token carrying one is not a count and
    # this must not pretend otherwise.
    #
    # IT DECLINES A RANGE FOR THE SAME REASON AND THAT IS ALSO RIGHT: `3-5` is not the
    # number 35. Declining where the answer is not determined is this module's standing rule,
    # and `/2` — the case the strip exists for — has no hyphen and still reads as two.
    if not any(c.isalpha() for c in text) and "-" not in text:
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


# THE EVIDENCE A SHAPE NEEDS, read from the language manifest rather than written here —
# `config.REQUEST_EVIDENCE`. It is a vocabulary, which is the one thing this module keeps
# deleting, so it lives as DATA beside every other list the language holds and not as a
# literal somebody has to find.


def _mentions(kind: str, request: str) -> bool:
    """Does the REQUEST contain any of the words that make `kind` believable?

    Whole words for single tokens, so `see` does not fire inside `seed`; substrings for the
    multi-word ones, because `apart from` cannot match a set of single words.
    """
    said = str(request or "").lower()
    words = {w.strip(".,!?;:'\"") for w in said.split()}
    for w in (config.REQUEST_EVIDENCE.get(kind) or ()):
        w = str(w).lower()
        if (w in said) if " " in w else (w in words):
            return True
    return False


def asks_reach(request: str) -> bool:
    """Does the REQUEST mention reaching at all? The one authority, asked twice.

    `to_goals` has always dropped a `reach` goal the request gives no evidence for — twenty
    of twenty-three extraction failures on 2026-08-01 were exactly that. `schema()` now asks
    the same question BEFORE generating, so the shape is not offered where it cannot be
    meant. Two readers, one rule; the alternative is a grammar that permits what the reader
    is guaranteed to throw away.
    """
    return _mentions("reach", request)


def declined(raw: Dict[str, Any]) -> Optional[str]:
    """The model's reason for refusing, or None. An answer, not an error.

    A REFUSAL IS BELIEVED WITHOUT EVIDENCE HERE, and that is a known open weakness rather
    than an oversight. Requiring the model to QUOTE the words it could not serve — and
    dropping any refusal whose span was not in the request — was built and measured on
    2026-08-05; see the `cannot` field in `schema` for the numbers and the bisect. It was
    withdrawn because the gain came entirely from the prompt paragraph that came with it,
    and that paragraph cost three ordinary requests to buy two refusals.
    """
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
    # THE GOAL SHAPES TOO — they are an ENUM the model is shown, and it hands them back the
    # same way it hands back a field name. Measured: "spin up five machines, wire them
    # together… confirm each can reach the others" came back as `name: "reach"`, and a
    # machine called `reach` is exactly the echo this function exists to name. `count` was
    # already here by luck, as a field name; the rest were not.
    out |= {str(s).lower() for s in goal_shapes()}
    for kind, spec in (config.KINDS or {}).items():
        out.add(kind)
        for n in (spec.get("nouns") or ()):
            out.add(str(n).lower())
            out.add(str(n).lower() + "s")          # "machines" is the kind, said twice
        out.add(kind + "s")
        out |= {str(a).lower() for a in (spec.get("attrs") or ())}
    return out


def names_members(kind: str, attr: str) -> Optional[str]:
    """Which kind's MEMBERS this attribute holds the names of, or None.

    ONE AUTHORITY FOR A QUESTION FOUR GUARDS WERE EACH ANSWERING THEMSELVES. `unusable`,
    `invented`, `_named_in` and `precondition` all need to know whether a value is a NAME,
    and all of them answered it by the same CONVENTION: an attribute is a reference when its
    name IS a declared kind. That is how `snapshot.vm` is recognised, and it is silent about
    `network.members`, which holds vm names and is not called `vm`.

    MEASURED COST OF THE SILENCE: rung 8's paraphrase came back as `every network[net_name=
    core] must members = 'all machines'` — prose where member names belong — and no guard
    objected, because none of them could see that `members` names anything. The writer had
    nothing to plan and the run reported DONE having made ZERO calls. A false success, from a
    rule that could not express the case in front of it.

    SO THE MANIFEST DECLARES IT and the convention stays as the fallback. `refs` on a kind
    maps an attribute to the kind it names members of; where a kind says nothing, an
    attribute named for a kind still refers to one, so every existing row keeps working
    without an edit. DECLARE, DON'T INFER — with the inference kept for the cases where it
    was already right.
    """
    if not attr:
        return None
    spec = (config.KINDS or {}).get(kind) or {}
    declared = (spec.get("refs") or {}).get(attr)
    if declared:
        return declared
    return attr if attr in (config.KINDS or {}) else None


def _said(text: str) -> str:
    """The request as one comparable token stream — lowercase, punctuation to spaces, padded.

    PADDED ON BOTH SIDES so containment lands on WORD boundaries: a member called `db` must
    not be found inside `dbms`. Punctuation becomes a space rather than vanishing, so
    `bench-red-1` in the request and `bench-red-1` in a selector flatten the same way while
    `n1,` still yields `n1`.
    """
    words = "".join(c if c.isalnum() or c.isspace() else " " for c in (text or "").lower())
    return f" {' '.join(words.split())} "


def invented(sel: Dict[str, Any], request: str) -> Optional[str]:
    """An identity this selector commits to that the operator never said, or None.

    ## THE DEFECT THAT SURVIVES EVERY SHAPE GATE

    A clause the model cannot express does not disappear — it moves. `reach` was narrowed on
    2026-08-04 and the pressure went to `per`; gating `per` sent it to `count`, as
    `count(vm WHERE name='unresponsive') = 0` for *"stop the ones that do not answer"*.
    THREE SHAPES, ONE CLAUSE, and each hop landed somewhere quieter: a spurious `reach` and a
    spurious `per` were both DROPPED by rules that already existed, and an invented name is
    neither dropped nor vacuous — it asserts something, so the writer plans for it.

    THIS GUARD DOES NOT CARE WHICH SHAPE THE CLAUSE LANDS IN, which is the property every
    shape gate lacks. A name is an IDENTITY: it is the same word in the request and in the
    goal, which is exactly the argument `clause_ledger.open_ledger` makes for its anchors. So
    a name that appears nowhere in the request was not given by the operator, whatever branch
    of the schema it arrived in.

    ASKED OF THE KEY AND OF EVERY REFERENCE — the convention `unusable`, `precondition` and
    `_named_in` already share: a kind's key IS the member's name, and an attribute named for
    a declared kind refers to a member of it.

    ## WHAT IT DELIBERATELY DOES NOT JUDGE

    A `$reference` is a parameter or a stand-in, minted by the harness and substituted INTO
    the request, so it is not the model's invention to answer for. A non-string value is not
    an identity. And an ATTRIBUTE VALUE is not a name — a label is free text and `prod` need
    never appear as a word for `label = 'prod'` to be exactly what was meant.
    """
    if not request:
        return None                      # nothing to check against; never guess
    kind = sel.get("kind")
    key = ((config.KINDS or {}).get(kind) or {}).get("key")
    said = _said(request)

    def _absent(v: Any) -> bool:
        if not isinstance(v, str) or not v.strip():
            return False
        if v.strip().startswith(config.SIGIL):
            return False                 # a stand-in or a declared parameter
        return _said(v) not in said

    for attr, value in sel.items():
        if attr != key and not names_members(kind, attr):
            continue
        # A MEMBERSHIP LIST NAMES SEVERAL, and one invented member is enough: `name IN
        # [n1, n2, ghost]` is a claim about a set the operator did not describe.
        members = value["in"] if isinstance(value, dict) and isinstance(
            value.get("in"), list) else [value]
        bad = [m for m in members if _absent(m)]
        if bad:
            return (f"it is about {attr} {', '.join(repr(b) for b in bad)}, which the "
                    f"request never names")
    return None


def unusable(sel: Dict[str, Any]) -> Optional[str]:
    """Why this selector names something that cannot exist, or None.

    ASKED OF THE KEY AND OF EVERY REFERENCE, because both become names in the world: a
    kind's key IS the member's name, and an attribute whose name is a declared kind refers
    to a member of it — the convention `precondition` and `_named_in` already use.
    """
    kind = sel.get("kind")
    key = ((config.KINDS or {}).get(kind) or {}).get("key")
    # A VALUE OUTSIDE A CLOSED SET IS NOT A VALUE, and this is the worst shape it takes.
    # `attr_values` declares the states an attribute can be IN — a machine's status is
    # running or stopped — so a filter for `status = 'up'` matches nothing, for ever. And a
    # goal about NOTHING is vacuously true: "a snapshot per machine that is up" plans zero
    # snapshots, closes DONE, and the world disagrees. Measured on rung 12's paraphrase,
    # deterministically, 3 of 3 — *"each machine that is currently up"*.
    #
    # REFUSED RATHER THAN TRANSLATED. `up` plainly means `running` to a person, and mapping
    # it here would be this module guessing what the operator meant, which is the job it
    # exists not to have. A declared synonym is a manifest row and the operator's call; an
    # inferred one is how a vocabulary starts.
    for attr, allowed in (((config.KINDS or {}).get(kind) or {})
                          .get("attr_values") or {}).items():
        value = sel.get(attr)
        # A REFERENCE IS NOT A VALUE YET — `$state` is resolved at run time, so judging it
        # here would refuse every procedure that takes its filter as a parameter.
        if not isinstance(value, str) or value.startswith(config.SIGIL):
            continue
        if allowed and value.strip().lower() not in {str(a).lower() for a in allowed}:
            return (f"{attr} = {value!r} is not one of "
                    f"{', '.join(sorted(str(a) for a in allowed))}, so it matches nothing")
    for attr, value in (sel or {}).items():
        if attr in ("kind", "not") or not isinstance(value, str):
            continue
        names_a_member = attr == key or bool(names_members(kind, attr))
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
        owner = kind if attr == key else names_members(kind, attr)
        if ((config.KINDS or {}).get(owner) or {}).get("key_freetext"):
            continue
        if any(c.isspace() for c in value.strip()):
            return (f"{attr} = {value!r} reads as a description rather than a name")
    return None


def _not_an_identity(raw: Dict[str, Any]) -> set:
    """Values this answer ITSELF used as a non-key property. Those are not names.

    THE MODEL CONTRADICTS ITSELF AND ONE SIDE IS EVIDENCE. `name` is REQUIRED on a count
    goal — measured necessary, because offered as optional it went unfilled and box1 was
    lost — and most requests name no member at all. So the model must answer, the only free
    string in the branch is `name`, and it repeats whatever qualifier is nearby:

        "make sure exactly 3 vms carry the 'prod' label"
          -> count  vm  amount 3  name "prod"          <- forced, and impossible
          -> every  vm  attr label  value "prod"       <- correct, in the same reply

    A NAME IS AN IDENTITY, so the first goal asks for three members sharing one — a world
    that cannot exist, which the writer honestly refuses. But the second goal is the model
    SAYING what `prod` is. Nothing has to be guessed: a value the answer uses as a `label`
    is not a name, because the answer said so.

    THE KEY IS THE EXCEPTION, and it is what keeps real names. "a vm called box1 running
    linux" comes back with `name: box1` AND `where: [{attr: name, value: box1}]` — box1 is
    used as a value of the KEY attribute, which is agreement rather than contradiction.

    DETERMINISTIC, AND IT DECLINES WHEN THERE IS NO EVIDENCE. A request whose stray name
    appears nowhere else — "clone golden into 3 new vms" — is untouched, and fails as it did
    before. This rule only ever fires on an answer that already told us the answer.
    """
    out: Dict[str, set] = {}

    def _pairs(node):
        if isinstance(node, list):
            for kid in node:
                yield from _pairs(kid)
        elif isinstance(node, dict):
            if node.get("attr") is not None and node.get("value") is not None:
                yield node["attr"], node["value"]
            for val in node.values():
                if isinstance(val, (dict, list)):
                    yield from _pairs(val)

    for g in (raw or {}).get("goals") or []:
        kind = ((g.get("select") or {}).get("kind"))
        spec = (config.KINDS or {}).get(kind) or {}
        key = spec.get("key")
        alias = spec.get("aliases") or {}
        for attr, value in _pairs(g):
            if alias.get(attr, attr) != key and isinstance(value, str) and value.strip():
                out.setdefault(kind, set()).add(value.strip())
    return out


def _born_with(kind: str, must: Dict[str, Any]) -> bool:
    """May EVERY attribute in `must` only be had by being CREATED with it?

    THE FOLD IS FOR ATTRIBUTES NOTHING CAN CHANGE AFTERWARDS, and that is the whole of it.
    `os_type` has no setter and is a creation default: a machine is born linux or born
    windows, so "a vm named X" and "X runs windows" MUST become one creation or the second
    goal is unreachable by construction — which is the failure the fold was written for.

    EVERYTHING ELSE MUST STAY TWO GOALS, and folding it is actively worse:

      A SETTABLE ATTRIBUTE ALREADY HAS A PLAN — create, then `add_label`. Folding it asks
      the creator for something it cannot take, so the writer would have to claim it at
      birth instead of doing the two steps that work.

      AN ATTRIBUTE NOTHING WRITES AT ALL MUST FAIL HONESTLY. Measured 2026-08-03 on rung 3,
      a CONTROL rung: the model read "put web on lab" as a property of the NETWORK —
      `every network[name=lab] -> members=web` — and `network` has no setters and no
      creation arguments, so nothing in the world can make that true. Folded, it became
      `count(network WHERE net_name=lab AND members=web) = 1`, the writer created a network
      that CLAIMED those members, and the run closed DONE over a machine that was on no
      network. Unfolded, the goal simply cannot be met and says so.

    DETERMINISTIC AND MANIFEST-ONLY: setters, creation arguments and creation defaults are
    all declared, so nothing here is a judgement about meaning.
    """
    spec = (config.KINDS or {}).get(kind) or {}
    settable = {s.get("attr") for s in (spec.get("setters") or {}).values()}
    at_birth = set(spec.get("create_defaults") or {}) | set(spec.get("create_args") or ())
    return bool(must) and all(a not in settable and a in at_birth for a in must)


# ── WHAT A SELECTOR MUST SURVIVE, IN ORDER, AS DATA ───────────────────────────────────────
#
# THE ORDER IS THE RULE, AND IT USED TO BE A SEQUENCE OF STATEMENTS NOBODY COULD SEE.
# `_keep` ran one repair and three refusals in whatever order they had been added, and the
# ordering was LOAD-BEARING and written down nowhere. On 2026-08-05 a refusal was added
# BEFORE the repair and cost four rungs — 4, 7, 13 and 14 went DONE -> UNTRANSLATED, every
# one of them for a name the repair was about to fix. The mistake was invisible in review and
# took a full ladder arm to find.
#
# SO THE TWO PHASES ARE DECLARED RATHER THAN IMPLIED:
#
#     REPAIRS   may CHANGE the selector. A slot error is repaired.
#     REFUSALS  may only reject, and they judge WHAT THE REPAIRS LEFT.
#
# That is this module's oldest stated line — A SLOT ERROR IS REPAIRED, A WRONG MEANING NEVER
# IS — turned from a comment into the shape of the code. A refusal placed among the repairs
# is now a category error a reader can see, not an ordering accident.
#
# EVERY RULE HAS ONE SIGNATURE, `(goal, sel, request) -> (goal, sel, why)`, so each is
# testable on its own and the pipeline below is a loop rather than a cliff of `if`s. A
# refusal returns the goal and selector unchanged; that it CAN return them is what lets a
# repair refuse when nothing usable survives it.


def _repair_unusable(goal: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """STRIP WHAT CANNOT EXIST, KEEP THE GOAL. The one repair, and it runs first.

    Dropping the whole component threw away a perfectly good count because the model had
    echoed `machines` into the name slot — the request survived as nothing rather than as
    most of itself.

    THE KIND IS THE EXCEPTION: a selector whose KIND is unusable describes nothing at all,
    and there is no smaller true statement left inside it. That is the case where a repair
    ends in a refusal, which is why repairs are allowed to.
    """
    why = unusable(sel)
    if not why:
        return goal, sel, None
    kind = sel.get("kind")
    key = ((config.KINDS or {}).get(kind) or {}).get("key")
    trimmed = {k: v for k, v in sel.items()
               if not (k == key or k in (config.KINDS or {}))
               or not unusable({"kind": kind, k: v})}
    if not trimmed.get("kind") or unusable(trimmed):
        return goal, sel, f"it names something that cannot exist ({why})"
    holder = ("select" if "select" in goal else "every" if "every" in goal
              else "observe" if "observe" in goal else "per")
    return {**goal, holder: trimmed}, trimmed, None


def _refuse_invented(goal: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """A NAME THE REQUEST NEVER SAYS. Judged on what the repairs LEFT, never before them.

    PUT FIRST, IT COST FOUR RUNGS — every one for a name `_repair_unusable` was about to fix:
    `name: 'every'` (a schema word `_echoed` knows), `'exactly two vms'` and `'prod label on
    exactly 3 vms'` (prose the whitespace rule knows). Those are SLOT ERRORS.

    WHAT SURVIVES THE REPAIRS IS THE REAL THING: well-formed, not echoed, not prose, and
    still absent from the request — `name: 'unresponsive'` for "stop the ones that do not
    answer", which nothing upstream objects to and which reached the writer and closed DONE
    over four calls.

    IT DROPS RATHER THAN STRIPS. Stripping an echoed word leaves `count(vm) = 5`, still what
    the operator asked; stripping an invented identity leaves `count(vm) = 0` — DELETE EVERY
    MACHINE. Stripping is only safe when what remains is still the whole truth.
    """
    return goal, sel, invented(sel, request)


def _refuse_shared_identity(goal: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """SEVERAL MEMBERS CANNOT SHARE ONE IDENTITY, refused at the seam that owns the error.

    A kind has one member per key, so `count(vm WHERE name='golden') = 3` describes no world
    — rung 10's answer to "clone golden into 3 new vms", where the clone relation is lost.

    IT WAS ALREADY CAUGHT, IN THE WRONG PLACE. `ghost_writer.cover` raises `Unsolvable`, so
    the run is honest — and closes UNMET, which BLAMES THE ENGINE for a front-seam mistake.
    `engine_probe` is explicit that UNTRANSLATED exists so that cannot happen. Nothing about
    whether the request works changes; which layer is told to look does. The rule is
    `coverage_probe.judge`'s, which has counted this as FORCED since the corpus was written
    while production had no equivalent.

    A MEMBERSHIP LIST IS NOT THIS: `name IN [n1, n2, n3]` with a count of three is three
    members with three names. Only a SCALAR key beside a count above one is impossible.
    """
    key = ((config.KINDS or {}).get(sel.get("kind")) or {}).get("key")
    pinned = sel.get(key) if key else None
    if (isinstance(goal.get("eq"), int) and goal["eq"] > 1
            and isinstance(pinned, (str, int, float))):
        return goal, sel, (f"it asks for {goal['eq']} {sel.get('kind')}s all called "
                           f"{pinned!r}, and a {sel.get('kind')} is identified by its "
                           f"{key} — no world has that")
    return goal, sel, None


# REPAIRS FIRST, THEN REFUSALS. Adding a rule means putting it in the right tuple, which is
# the whole point: the phase is a declaration rather than a line number.
_REPAIRS = (_repair_unusable,)
_REFUSALS = (_refuse_invented, _refuse_shared_identity)


# ── ONE BUILDER PER SHAPE, SO THE DISPATCH IS A TABLE ─────────────────────────────────────
#
# `to_goals`' loop was a 250-line `elif` chain, and the four shapes below were buried in the
# middle of it. Each is now a named function with one signature — `(g, sel, request)` ->
# `(goal, reason)` — so it can be read and tested without the loop around it.
#
# THREE ANSWERS, NOT TWO, and the third is what preserves the old behaviour exactly:
#
#     (goal, None)   admit this, subject to `_keep`'s repairs and refusals
#     (None, reason) refuse it, and say why
#     (None, None)   THIS BRANCH DOES NOT APPLY — fall through to "not a shape this
#                    translator can express", which is where `every` with no attribute and
#                    `per` with no `make` already landed.
#
# `count` IS DELIBERATELY NOT HERE. It is 160 lines carrying its own repair stack — the
# either-slot number, the identity repair, the shape floor, the pigeonhole against
# `_not_an_identity` — and lifting it would be a rewrite of the most sensitive code in the
# system rather than a move. It stays inline until there is a reason beyond tidiness.


def _build_reach(g: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """REACH IS NOT INVENTED. Twenty of twenty-three extraction failures on 2026-08-01 were a
    `reach` goal the request never asked for, over a set too small to satisfy it. The evidence
    is IN THE REQUEST, so it is checked there rather than argued with in a prompt.

    THE GUARD IS RIGHT AND THE SILENCE WAS NOT: the model reaches for `reach` when a clause
    has no shape (rung 2's "and then launch it"), the goal is correctly refused, and the
    clause it stood for goes with it — which is why the refusal is reported.
    """
    if request and not asks_reach(request):
        return None, "the model asked for reachability and the request never mentions it"
    return {"shape": "reach", "select": sel, "min": int(g.get("amount") or 2)}, None


def _build_every(g: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """A property every member of a set must gain.

    AN IDENTITY IS NOT A PROPERTY, and it is REPAIRED rather than argued with. "Create a vm
    named alpha" came back as `every vm must be named alpha` — four of ten failures on
    2026-08-01 — and giving every member of a set one name is not a state any world reaches.
    The reading meant is a COUNT OF ONE.

    A GOAL THAT ASKS FOR WHAT IT ALREADY SELECTS IS VACUOUS, so it cannot be what was meant —
    it is a LOST NEGATION. Rung 5's paraphrase, "start up any machine that ISN'T already
    running", came back as `every vm[status=running] must status=running`: nothing planned,
    nothing run, and the goal true the moment it is asked. `effects.complement` knows the
    opposite because the manifest enumerates the values, and DECLINES where a third value
    exists, because then the sentence genuinely did not say which.
    """
    if not (g.get("attr") and g.get("value") is not None and not placeholder(g["value"])):
        return None, None
    spec = (config.KINDS or {}).get(sel["kind"]) or {}
    attr = (spec.get("aliases") or {}).get(g["attr"], g["attr"])
    if attr == spec.get("key"):
        return {"shape": "count", "select": {**sel, attr: _coerce(g["value"])}, "eq": 1}, None
    # NOTHING CAN BE ASKED OF A KIND NOTHING CAN CHANGE. An `every … must` says members
    # GAIN a property, so it needs something able to confer one — a setter, or an act. A
    # `network` has NEITHER: it can be created and deleted and that is all, so `every
    # network[net_name=core] must members = 'web'` is not a hard goal, it is an unplannable
    # one.
    #
    # AND IT IS RUNG 8'S PARAPHRASE, DONE_BUT_FALSE. "Connect all the machines to a network
    # named core, apart from db" came back with the RECEIVER INVERTED — asking the network to
    # gain members, where the language wants `every vm[…] must network=core` — the writer had
    # nothing to plan, made ZERO calls, and the run reported success.
    #
    # THE WHOLE KIND, NOT THE ATTRIBUTE, and that is deliberate. Matching an attribute against
    # what a setter writes would take `memory_mb` and `cpu_cores` with it — those are changed
    # by ACTS, which promise nothing and so declare no attribute. A kind with no setters AND
    # no acts cannot be changed by anything, whatever the attribute, so the coarse test is the
    # sound one and the fine one would be a guess.
    #
    # THE IDENTITY REPAIR RUNS FIRST and is untouched: `every network must net_name=lab` is
    # already a COUNT by the time this is reached, which is what keeps rung 3 working.
    spec_changeable = bool(spec.get("setters")) or bool(spec.get("acts"))
    if not spec_changeable:
        return None, (f"it asks every {sel['kind']} to gain {attr}, and nothing in the lab "
                      f"can change a {sel['kind']} at all")
    want = _coerce(g["value"])
    if sel.get(attr) == want:
        from planner.ir import effects as _fx
        other = _fx.complement(sel["kind"], attr, want)
        if other is None:
            return None, (f"it asks every {sel['kind']} with {attr}={want} to have "
                          f"{attr}={want}, which is already so")
        sel = {**sel, attr: other}
    return {"every": sel, "must": {attr: want}}, None


def _build_per(g: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """One new thing per member of a set.

    A KIND THE REQUEST NEVER MENTIONS IS NOT BEING ASKED FOR — same rule as `reach`, same
    reason. Rung 11's paraphrase came back `per vm make=snapshot` for a request naming no
    snapshot, restore point or checkpoint: the model reached for `per` because "shut down
    whichever ones don't" has no shape, and the run MADE SNAPSHOTS and reported success.
    `_relevant` answers "could this request be about this kind" from the manifest's own
    nouns, which is what keeps rung 12 working — that request does name one.

    THE LINK IS DERIVED, NEVER TAKEN ON TRUST. "Launch every vm that is currently stopped"
    came back as `per vm make=vm link=status` — one machine per machine, tied by a STATUS.
    """
    if not g.get("make"):
        return None, None
    if request and not _relevant((config.KINDS or {}).get(g["make"]) or {},
                                 request, g["make"]):
        return None, f"it makes a {g['make']}, which the request never mentions"
    link = _link_between(sel.get("kind"), g["make"])
    if not link:
        return None, f"nothing links a {sel.get('kind')} to a {g['make']}"
    return {"per": sel, "make": g["make"], "link": link}, None


def _build_observe(g: Dict[str, Any], sel: Dict[str, Any], request: str) -> tuple:
    """Ask each member something, requiring nothing of the answer."""
    return {"observe": sel, "fact": g.get("fact") or "alive"}, None


_BUILDERS = {"reach": _build_reach, "every": _build_every,
             "per": _build_per, "observe": _build_observe}


def to_goals(raw: Dict[str, Any], request: str = "",
             dropped: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """The model's answer, in the shape `ghost_writer.cover` takes.

    `dropped` IS AN OUT-LIST, AND IT IS WHY A HALF-READ REQUEST STOPS BEING SILENT. Every
    rule below that refuses a component is right to refuse it — but the caller was told
    nothing, so a request whose second clause never survived translation went on to be
    planned, run, and closed DONE over the half that did. Measured 2026-08-03 on rung 2, a
    CONTROL rung: "create a vm named beta and then launch it" returns two goals every time,
    the second arrives as a bogus `reach`, the reach guard correctly drops it, and the run
    creates beta, never launches it, and reports success. DONE_BUT_FALSE, deterministically,
    on the sentence the prompt uses as its own worked example.

    IT REPORTS DROPS, NOT MERGES. `_scoped` folding two goals about one member into one is
    not a loss and must not read as one, or the signal is noise on every request that
    triggers the fold. Left `None`, nothing is collected and this behaves exactly as before.

    Anything malformed is DROPPED rather than repaired. A goal missing the field its own
    shape requires is a goal the model did not actually state, and inventing the missing
    half here would put this module back in the business of deciding what the operator
    meant — which is the job it exists to not have.

    AND A GOAL NAMING SOMETHING THAT CANNOT EXIST IS DROPPED TOO. See `unusable`: a value
    slot filled with prose is not a smaller mistake than a missing field, it is a larger
    one, because the writer plans faithfully for it and the run closes DONE.
    """
    out: List[Dict[str, Any]] = []

    def _lost(why: str, g: Dict[str, Any] = None, whole: bool = False) -> None:
        """Record that a component the model DID return did not survive translation.

        `whole=True` for a rule that discards the ENTIRE reading rather than one component.
        The per-goal prefix is a goal's shape, and a translation-wide drop has none — it was
        printing `?:`, which reads as a missing value rather than as the deliberate scope it
        is.
        """
        if dropped is None:
            return
        if whole:
            dropped.append(f"whole reading: {why}")
            return
        shape = str((g or {}).get("goal") or "?")
        dropped.append(f"{shape}: {why}")

    def _keep(goal: Dict[str, Any]) -> None:
        """Admit a finished component, once it has survived the repairs and the refusals.

        ONE PLACE, AT THE END. Every branch below builds a selector its own way and several
        REPAIR one — moving a value out of the wrong slot, reading a bare value as an
        identity — so the only selector worth judging is the one that comes out.

        THE PIPELINE IS `_REPAIRS` THEN `_REFUSALS`, declared above this function. It was a
        run of `if`s whose ORDER was load-bearing and unwritten, and putting one refusal in
        the wrong place cost four rungs; the order is now data, and a rule in the wrong phase
        is a category error rather than an accident.
        """
        # `per` WAS NEVER JUDGED, and it is a selector like any other. "a snapshot per
        # machine that is running" carries a set of members exactly as `every` does, so a
        # selector this branch could not read was the one shape that reached the writer
        # unexamined — which is why rung 12's `status = 'up'` had nothing to stop it.
        sel = (goal.get("select") or goal.get("every") or goal.get("observe")
               or goal.get("per") or {})
        if not isinstance(sel, dict):
            _lost("its selector is not a set of members")
            return
        for rule in _REPAIRS + _REFUSALS:
            goal, sel, why = rule(goal, sel, request)
            if why:
                _lost(why)
                return
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
            if isinstance(want, dict) and must and _born_with(want.get("kind"), must):
                host = next((h for h in goals
                             if h is not g and h.get("eq") == 1
                             and isinstance(h.get("select"), dict)
                             and h["select"] == want), None)
                if host is not None:
                    host["select"] = {**host["select"], **must}
                    continue
            merged.append(g)
        goals = merged

        # A NAMED MEMBER BESIDE AN EXCEPTION IS THE CARVE-OUT, NOT THE RECEIVER — and the
        # fold below cannot tell those apart, so where the request says so it must not fold.
        #
        # MEASURED ON RUNG 8, and it produced the exact opposite of the request:
        #
        #   "put every vm on a network called core, EXCEPT db — db goes on dmz instead"
        #     -> every vm network=core   +   count vm[name=db] = 1
        #     -> folded: count vm[name=db AND network=core] = 1
        #
        # db is the one machine that must NOT be on core, and the fold put it there — then
        # the run closed DONE over it. The rule reads a named member as the receiver of a
        # property that escaped one, which is right for "a machine called box1 running
        # linux" and inverted for a carve-out.
        #
        # THE EVIDENCE IS IN THE REQUEST, so it is read there — the same move `asks_reach`
        # makes, and for the same reason: the goals cannot express the exception (the model
        # has never once emitted the `except` the schema offers), so the only place the
        # exception still exists is the sentence. Declining to fold is not a repair; it
        # leaves the request UNMET, which is the honest outcome for something no goal shape
        # currently says.
        low = str(request or "").lower()
        if _mentions("except", request):
            return goals

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

    # COMPUTED ONCE OVER THE WHOLE ANSWER, before any goal is read, because the evidence for
    # one goal lives in a DIFFERENT goal — the label statement that proves `prod` is a label
    # may come after the count that misnames it.
    _said_property = _not_an_identity(raw)

    for g in (raw or {}).get("goals") or []:
        shape, sel = g.get("goal"), _to_select(g.get("select") or {})
        if not sel.get("kind"):
            _lost("it says nothing about what kind of thing it is about", g)
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
            #
            # BUT A NUMBER THAT WAS SAID AND COULD NOT BE READ IS NOT A MISSING NUMBER, and
            # collapsing the two is what let `amount: -1` become `eq: 1`. NOT SAID means the
            # sentence already implied one; SAID AND UNREADABLE means the model stated a
            # quantity this reader does not understand, and inventing one there is exactly
            # the "wrong meaning" the module refuses to repair everywhere else. The request
            # is returned as untranslated, with the value that defeated it named.
            if eq is None:
                stated = g.get("amount")
                if stated is not None and str(stated).strip() != "":
                    _lost(f"it asks for {stated!r} of them, which is not a number of "
                          f"things — a count is a total, never a change", g)
                    continue
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
            # A VALUE THIS ANSWER CALLED A PROPERTY IS NOT ALSO A NAME — see
            # `_not_an_identity`. Dropped rather than moved: the model has already stated the
            # property in its own goal, so the fact is not lost, and MOVING it would be
            # inventing a second copy of a statement that is already there.
            # SCOPED TO THIS KIND, and the first version was not — measured at n=3, it cost
            # rung 3. "put web on lab" comes back as `every network -> attr members, value
            # web`, so `web` is a value of a NETWORK property; read globally that disqualified
            # `web` as the name of the MACHINE the same request creates, and the vm was never
            # made. A value being a network's member says nothing about what a vm is called.
            if named is not None and str(named).strip() in _said_property.get(sel.get("kind"), ()):
                named = None
            # MANY MEMBERS CANNOT SHARE ONE IDENTITY, so a name beside a count above one is
            # not a name — the key IS the identity. THE NAME IS STRIPPED AND THE COUNT IS
            # KEPT, which is `_keep`'s own rule for an unusable name and NOT the refusal
            # tried earlier the same day: refusing the component cost rungs 4, 13 and 14,
            # because the stray name sits beside a count that is perfectly good and the rest
            # of the request depends on it.
            #
            # IT CATCHES WHAT THE WORD LISTS CANNOT. `unusable` knows quantifiers and kind
            # nouns; these were all measured surviving as machine names:
            #
            #   "spin up five machines…"          -> NAME=reach   (the schema's own word)
            #   "cut the lab down to two"         -> NAME=lab
            #   "clone golden into 3 new vms"     -> NAME=golden
            #
            # and none of them is a quantifier or a noun. What they share is arithmetic: a
            # count of five machines all called `reach` is not a world, whatever the word is.
            # WITHDRAWN AFTER MEASUREMENT — the rule was "a count above one cannot pin an
            # identity, so strip the name and keep the count", and the arithmetic is sound.
            # It still made things WORSE, 6 -> 12 DONE_BUT_FALSE on the literal arm:
            #
            #   "make sure exactly 3 vms carry the 'prod' label"
            #     name=prod stripped  ->  count(vm) = 3   <- satisfiable, and NOT the request
            #
            # The impossible goal was refused by the writer and reported UNMET, which is
            # honest. Stripped, it becomes a goal that CAN be met — three machines, no label
            # — so the run builds them and closes DONE over a world the checker disagrees
            # with. STRIPPING IS ONLY SAFE WHEN WHAT REMAINS IS STILL THE WHOLE TRUTH, and
            # here the name was the only thing carrying `prod`.
            #
            # SO IT IS LEFT TO THE TWO RULES THAT HAVE EVIDENCE: `_not_an_identity`, which
            # fires when the answer ITSELF calls the value a property, and `_echoed`, which
            # names a word the model was shown. Where neither applies, the name stands and
            # the goal fails honestly.
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
                _lost("it states no number and its value names nothing", g)
                continue
            _keep({"shape": "count", "select": sel, "eq": eq})
        else:
            # ONE BUILDER PER SHAPE — see `_BUILDERS`. A builder answering `(None, None)`
            # means its branch does not apply (an `every` with no attribute, a `per` with no
            # `make`), which is exactly where the old chain fell through to the message
            # below.
            build = _BUILDERS.get(shape)
            made, why = build(g, sel, request) if build else (None, None)
            if why:
                _lost(why, g)
                continue
            if made is None:
                # NO BRANCH MATCHED, which until now was the quietest exit of all: a shape
                # this module does not implement, or one whose required field the model
                # omitted, left the loop having produced nothing and said nothing.
                _lost("it is not a shape this translator can express", g)
                continue
            _keep(made)
    # THE SAME GOAL TWICE IS ONE GOAL. Repairs converge — an `every` whose property was
    # unusable is stripped back to the count it was built on, and a request that states a
    # thing two ways lands on one shape — so duplicates arrive without either half being
    # wrong. Measured on rung 3's paraphrase, which produced `count network[net_name=lab]
    # = 1` twice, and on "a vm with the name and os based on user input", where stripping a
    # prose name left two identical unfiltered counts. Harmless to the writer, which dedupes
    # its own tiles, and noise to every reader of the ledger and every rule below that counts
    # goals — `_one_statement_not_two` decides by comparing a total against the number of
    # identity goals, and a duplicate is a miscount.
    seen, unique = [], []
    for g in out:
        if g not in seen:
            seen.append(g)
            unique.append(g)
    out = _partitioned(_scoped(unique), request)
    before = _one_statement_not_two(out)
    kept = _subject_survived(before, request)
    # THE ONE GUARD THAT THREW AWAY A WHOLE TRANSLATION IN SILENCE. Every other rule in this
    # function reports what it dropped — that is what `dropped` is for, and `to_goals`' own
    # docstring calls a half-read request the failure it exists to prevent — but this one
    # returned `[]` and said nothing, so `rig` reported the generic "no usable goal" for a
    # translation that was discarded for a specific, nameable reason. Found 2026-08-05 on
    # `clone-fleet`: "make four copies of the golden IMAGE" names a template, every goal was
    # about machines, the subject guard fired correctly and the operator was told nothing.
    #
    # A CORRECT RULE THAT CANNOT SAY WHY IT FIRED IS STILL A DEBUGGING DEAD END, and this
    # codebase has now paid for that twice in one file.
    if before and not kept:
        missing = ", ".join(sorted(_subject_gap(before, request))) or "something else"
        _lost(f"the request is about a {missing} and not one goal is — discarded rather "
              f"than run against the wrong subject", whole=True)
    return kept


def _partitioned(goals: List[Dict[str, Any]], request: str = "") -> List[Dict[str, Any]]:
    """Two counts over one kind, one attribute, DIFFERENT values — they name different members.

    THE WRITER ALREADY KNOWS HOW TO HONOUR THIS and was never told. `_lower`'s candidate
    search respects `sel["not"]` and its comment names this exact rung: *"two blue ones that
    are not red may not be satisfied by relabelling a red one… without this,
    `count(vm label=blue)=2` cheerfully paints two of the three machines the previous goal
    made red."* The guard is there; the goals carry no carve-out for it to read.

    MEASURED, on the now-correct translation of rung 6:

        count vm[label=red] = 3   +   count vm[label=blue] = 2
          -> add_label(vm1, red) … add_label(vm1, blue) …

    Three machines wearing both colours, on both networks, and the run closes DONE. The
    counts are each satisfied; what nobody said is that they are about different machines.

    IT IS A READING OF ENGLISH, AND THAT MAKES IT DIFFERENT FROM EVERY OTHER RULE HERE. The
    rest compute from the manifest, the schema, or the model's own answer. `label` and
    `network` are MULTI-VALUED — a machine legitimately carries several — so "3 red and 2
    blue" permitting three double-labelled machines is not a contradiction, it is a
    perfectly good second reading. This takes the first: "3 of X and 2 of Y" means five
    things. Ruled by the operator 2026-08-03.

    NARROW, AND IT DECLINES WHEN UNSURE — the deterministic-rules pattern:

        exactly one filter each        two filters do not name one group; leave it
        the same attribute             different attributes are not a partition
        exactly one other value        three groups cannot be carved out pairwise here
        never the identity key         a key already names one member, uniquely
        no carve-out already present   the goal said its own exclusion; do not overwrite it
    """
    counts = [g for g in goals
              if g.get("shape") == "count" and isinstance(g.get("select"), dict)]

    def _one_filter(sel):
        got = {k: v for k, v in sel.items() if k not in ("kind", "not")}
        return next(iter(got.items())) if len(got) == 1 else (None, None)

    # AN UNFILTERED `every` BESIDE A MEMBER-SPECIFIC ONE, ON THE SAME ATTRIBUTE, WITH THE
    # REQUEST SAYING "EXCEPT". Rung 8 is the case and it needs all three signals:
    #
    #   "put every vm on a network called core, EXCEPT db — db goes on dmz instead"
    #     -> every vm         must network=core     <- includes db
    #        every vm[name=db] must network=dmz
    #
    # Both are kept, so db is put on core AND dmz and the run closes DONE. Neither goal is
    # wrong on its own; what is missing is that the first does not mean db.
    #
    # THE THIRD SIGNAL IS WHY THIS IS NOT A GUESS. `network` is multi-valued — a machine may
    # legitimately sit on two — so a collision alone proves nothing. The word `except` in the
    # REQUEST is what says the operator meant one and not both, and it is read from
    # `request_evidence` like every other piece of sentence evidence.
    for g in goals:
        want = g.get("every")
        if not isinstance(want, dict) or not g.get("must") or want.get("not"):
            continue
        kind = want.get("kind")
        key = ((config.KINDS or {}).get(kind) or {}).get("key")
        if not key or len(want) != 1 or not _mentions("except", request):
            continue
        for other in goals:
            o_sel, o_must = other.get("every"), other.get("must")
            if other is g and True:
                continue
            if not isinstance(o_sel, dict) or not o_must or o_sel.get("kind") != kind:
                continue
            named = o_sel.get(key)
            if not named:
                continue
            clash = [a for a, v in o_must.items() if a in g["must"] and g["must"][a] != v]
            if clash:
                g["every"] = {**want, "not": {key: named}}
                break

    for a in counts:
        if a["select"].get("not"):
            continue
        attr, val = _one_filter(a["select"])
        kind = a["select"].get("kind")
        key = ((config.KINDS or {}).get(kind) or {}).get("key")
        if attr is None or attr == key:
            continue
        others = set()
        for b in counts:
            if b is a or b["select"].get("kind") != kind:
                continue
            b_attr, b_val = _one_filter(b["select"])
            if b_attr == attr and b_val != val:
                others.add(b_val)
        if len(others) == 1:
            a["select"] = {**a["select"], "not": {attr: next(iter(others))}}
    return goals


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
    return goals if not _subject_gap(goals, request) else []


def _subject_gap(goals: List[Dict[str, Any]], request: str) -> set:
    """The kinds the REQUEST names and no goal is about. Empty means the subject survived.

    SPLIT OUT SO THE VERDICT AND THE REASON COME FROM ONE PLACE. `_subject_survived` used to
    compute this inline and return a bare `[]`, which made the drop unexplainable without
    recomputing the rule somewhere else — and a second copy of a rule is how the two readers
    of `reach` nearly diverged. One authority, asked twice: once for the decision, once for
    the sentence the operator reads.
    """
    if not request or not goals:
        return set()
    words = {w.strip(".,!?;:'\"").lower() for w in request.split()}
    mentioned = set()
    for kind, spec in (config.KINDS or {}).items():
        nouns = {kind, *(spec.get("nouns") or ())}
        if nouns & words or {n + "s" for n in nouns} & words:
            mentioned.add(kind)
    if not mentioned:
        return set()
    covered = set()
    for g in goals:
        for holder in ("select", "every", "observe", "per"):
            sel = g.get(holder)
            if isinstance(sel, dict) and sel.get("kind"):
                covered.add(sel["kind"])
        if isinstance(g.get("make"), str):
            covered.add(g["make"])
    return set() if mentioned & covered else mentioned


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
    return constrained(prompt(request=request), request,
                       schema(request=request),
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
