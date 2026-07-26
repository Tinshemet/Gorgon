"""
translator.py — restate a goal in the vocabulary the harness already understands.

THE PROBLEM, MEASURED. The planner reads goals with patterns: 33 hand-maintained
vocabularies in this package, `vms` appearing in seven separate constants. They never
failed at REASONING — they fail on unfamiliar SURFACE FORMS. Run the complexity ladder
twice, once with each rung's literal wording and once with a paraphrase of the same
capability, and it scores 7/10 literal against 2/10 paraphrase. "set up three machines
tagged alpha" creates zero VMs where "provision 3 vms labelled alpha" works, because
`set up` is not in `_CARDINAL_CREATE_RE`.

THE MOVE. The model is good at rephrasing and bad at execution, so use it as a
TRANSLATOR: normalise the goal once into canonical vocabulary, then let the existing
machinery — cardinal creation, the collective expander, the state reader — recognise it
again. This is a FRONT-END THAT RESCUES what is already there, not a replacement for it.

THE LINE THAT MATTERS, AND IT IS NOT NEGOTIABLE. This module may change how a goal is
WORDED. It may never change how a goal is BROKEN DOWN. The clauses it returns are
re-joined into one canonical goal string and handed to the ordinary planner, which does
all the decomposition exactly as before. Feeding the clauses in as sub-goals would seed
the decomposition, which is precisely the benchmark-gaming the standing principle in
bench/rungs.py forbids — and it would make the ladder measure this module's sentence
splitting rather than the system's reasoning. If the rungs improve, it must be because
normalisation made the EXISTING vocabularies fire.

WHY CLAUSES RATHER THAN ONE SENTENCE. Three reasons, in order of weight: a dropped
clause is only detectable if clauses are countable (that check is the after-pass, the
next increment); flat lists are what this model class reliably emits, where nesting is
not; and a clause list is the direct on-ramp to IR statements when the procedure
language lands — same call, different output schema, nothing downstream changes.

WHERE THE VOCABULARY COMES FROM. The command catalog, and nowhere else. Twenty-eight of
its thirty-five commands carry an `ai_example` — "create a Ubuntu VM called dev with 4GB
RAM", "attach dev to the isolated network" — which are canonical phrasings authored
beside the tools they describe. Building a separate list here would make this the 34th
vocabulary and it would drift, which is the whole thing we are trying to stop.

FAILURE IS ALWAYS BACKWARDS-COMPATIBLE. A missing model, malformed arguments, an empty
result, an exception — every path returns the goal unchanged. The worst case of this
module is exactly today's behaviour.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from .score import _first_tool_call as _default_first_tool_call

# The catalog is the SSOT for canonical phrasing. Guarded so an orchestrator-only
# checkout (no executor/) degrades to no examples rather than failing to import — the
# same posture context_assistant takes for TOOL_TRIGGERS.
try:
    from executor.command_catalog import COMMAND_CATALOG as _CATALOG
except ImportError:                                        # pragma: no cover
    _CATALOG: List[Dict[str, Any]] = []


# The model answers by CALLING this, so its output arrives as validated JSON arguments.
# No parser, no grammar, no format for it to get wrong — the same discipline
# DECOMPOSE_TOOL uses, and the reason translation costs one schema rather than a lexer.
RESTATE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "restate_goal",
        "description": (
            "Restate the operator's goal in this system's standard wording. Keep the "
            "MEANING identical — same actions, same counts, same names, same conditions. "
            "Do NOT plan, do NOT add steps the operator did not ask for, do NOT remove "
            "any part of the request, and do NOT invent names or numbers. If the goal is "
            "already in standard wording, return it unchanged."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "clauses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One entry per distinct thing the operator asked for, in the "
                        "SAME order, each restated in standard wording. Split only where "
                        "the operator already asked for separate things — do not break a "
                        "single action into smaller steps. Example: 'set up three "
                        "machines tagged alpha and make sure they can reach each other' "
                        "becomes ['create 3 vms labelled alpha', 'make sure they all "
                        "ping each other']."
                    ),
                },
            },
            "required": ["clauses"],
        },
    },
}


# How many catalog examples to put in front of the model. A context budget, not a
# preference: a weak model's attention is finite and the examples compete with the goal
# itself. 24 covers every command that carries one today (28 of 35) minus the tail; if
# this ever needs per-deployment tuning it graduates to a planner config folder rather
# than growing more literals here.
_MAX_EXAMPLES = 24


def canonical_examples(limit: int = _MAX_EXAMPLES) -> List[str]:
    """The catalog's own canonical phrasings — its `ai_example` strings.

    These are the shape the harness's patterns were written against, authored next to
    the tools they exercise. Derived, never copied: adding a tool with an example
    teaches the translator that phrasing for free, and there is no second list to drift.
    """
    out = []
    for entry in _CATALOG:
        ex = (entry or {}).get("ai_example")
        if ex:
            out.append(ex)
        if len(out) >= limit:
            break
    return out


def _system_prompt() -> str:
    """The translator's instructions: the job, the standard wording, and the limits."""
    lines = [
        "You restate an operator's request in this system's standard wording.",
        "",
        "You are NOT planning. You are NOT choosing tools. You are rewording, and "
        "nothing else. The meaning must survive exactly: same actions, same counts, "
        "same names, same conditions, same order.",
        "",
        "COUNT THE ACTIONS FIRST. Read the request and count how many separate things "
        "the operator asked you to DO. Return exactly that many clauses, in that order. "
        "If the request asks for three things, return three clauses — never two.",
        "",
        "Rules:",
        "  - Never drop an action. Creating a thing and then using it are TWO actions: "
        "'set up a network called lab and connect web to it' is 'create a network "
        "called lab' AND 'attach web to the network called lab'.",
        "  - Never merge two actions into one clause.",
        "  - Never add an action the operator did not ask for.",
        "  - Keep every detail: counts, names, labels, and qualifiers. 'one private "
        "network' keeps 'one' and 'private'; 'five machines' keeps 'five'. Dropping a "
        "qualifier changes the request.",
        "  - Never invent a name, a number or a label. If the operator did not name "
        "something, leave it unnamed — do not make one up.",
        "  - Keep the operator's own names and labels verbatim.",
        "  - If a phrase is already standard, leave it alone.",
    ]
    ex = canonical_examples()
    if ex:
        lines += ["", "STANDARD WORDING — these are how requests are normally phrased here:"]
        lines += [f"  - {e}" for e in ex]
    return "\n".join(lines)


def _clean(clauses: Any) -> List[str]:
    """Strings only, stripped, empties dropped, order preserved."""
    if not isinstance(clauses, (list, tuple)):
        return []
    return [c.strip() for c in clauses if isinstance(c, str) and c.strip()]


def join_clauses(clauses: List[str]) -> str:
    """Clauses back into ONE goal string for the ordinary planner.

    Joining rather than returning the list is the mechanism that enforces this module's
    limit: the planner receives a goal, decomposes it itself, and never sees a pre-made
    step list.

    The SHAPE of the join matters. Commas between, `and` only before the last — the way
    the benchmark's own hand-written goals read ("create 5 vms, put them all in a
    network, and give them all the 'fleet' label"). A bare ` and ` is deliberately NOT
    split by the compound splitter (it must not tear a shared-verb conjunction), so the
    commas are what make a translated goal splittable at all; and putting `and` before
    every clause instead of just the last would hand the splitter N-1 clauses beginning
    with a stray conjunction rather than one.
    """
    if len(clauses) < 2:
        return "".join(clauses)
    return ", ".join(clauses[:-1]) + ", and " + clauses[-1]


def normalize_goal(
    goal: str,
    call_model: Callable[[List[Dict], List[Dict]], Dict],
    *,
    first_tool_call: Optional[Callable[[Any], Tuple]] = None,
) -> Tuple[str, Optional[List[str]]]:
    """Restate `goal` in canonical vocabulary. Returns (goal_to_plan, clauses_or_None).

    ONE model call per goal — not per node. A per-node pass would cost N calls (rung 6
    spends 22 today), re-invent phrasing on every pass, and could not detect a dropped
    clause at all, since only the whole goal compared against the whole plan can see
    that something went missing.

    `clauses` is returned for the after-pass to check coverage against; it is NOT a plan
    and must not be used as one. None means translation did not happen and the caller
    got its original goal back — every failure path lands here.
    """
    text = (goal or "").strip()
    if not text:
        return goal, None
    # Injectable so a test can drive the parse without a model; defaults to the same
    # extractor every other planning call uses, so a translated answer is read exactly
    # the way a decompose answer is.
    first_tool_call = first_tool_call or _default_first_tool_call
    messages = [{"role": "system", "content": _system_prompt()},
                {"role": "user", "content": text}]
    try:
        name, args = first_tool_call(call_model(messages, [RESTATE_TOOL]))
    except Exception:
        return goal, None                     # model down / transport error → unchanged
    if name != "restate_goal":
        return goal, None                     # answered with prose or the wrong tool
    clauses = _clean((args or {}).get("clauses"))
    if not clauses:
        return goal, None
    restated = join_clauses(clauses)
    if not restated or restated.lower() == text.lower():
        return goal, None                     # already canonical — say so by returning None
    return restated, clauses
