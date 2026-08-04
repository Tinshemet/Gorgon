"""Fetch, ensure, or achieve? The one thing the author cannot know.

The operator's framing, and the neat part is that the three intents ARE the three words —
there is no separate vocabulary sitting above the language, describing it:

  FETCH     "how many are there? list them." Retrieval. It reads and reports VALUES, and
            answers with data.
  ENSURE    "verify this. ground me." A truth check. It reads and reports a VERDICT, and
            answers true or false. Nothing changes.
  ACHIEVE   "do this, and make sure it is done." A command, and the only autonomous one.
            The harness may create, attach, launch, delete — and must say what done
            means.

They nest. A verification may need to fetch; a command may need to do both. So authority
is a ladder — fetch ⊆ ensure ⊆ achieve — and a program is refused when it reaches above
the rung it was given.

That is why `ENSURE` and `ACHIEVE` could not be told apart by a better prompt. *"Make
sure exactly three carry the prod label"* is a verification if the operator wants to KNOW
and a command if the operator wants it TRUE, and nothing in the sentence, the world, or the
model decides which. The fact lives in a person's head and was never written down. A
model asked to infer it will infer confidently, and a wrong inference does not merely
pick the wrong keyword — it either acts on a lab that was only meant to be inspected, or
inspects a lab that was meant to be changed. Those are not symmetrical mistakes.

So intent is SUPPLIED, the same way consent is, and it is ENFORCED rather than suggested:
a program that reaches above the rung it was given is refused, because the operator did
not authorise that much. Three ways to supply it, cheapest first:

  1. A PREFIX — `fetch: how many carry prod` / `achieve: 3 vms carry prod`. Unambiguous,
     free, and the right form for a saved mission or a script.
  2. WORDS THE OPERATOR ALREADY USED. "how many" and "list" are a person asking for data;
     "verify" and "confirm" for a verdict; "spin up" and "bring" for a change. These live
     in the MANIFEST, not here, and are deliberately few — a marker set, not a vocabulary
     trying to parse English. A sentence using none of them is not guessed at. A sentence
     using SEVERAL is not a conflict: it takes the highest rung, because that is the
     authority the program needs and the lower words describe parts of it.
  3. ONE QUESTION, before anything runs.

With nobody to ask, the answer is FETCH — the bottom rung. Reading a lab you meant to
change wastes a run; changing a lab you meant to read cannot be undone.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config

FETCH, ENSURE, ACHIEVE = "fetch", "ensure", "achieve"

_PREFIXES = {"achieve:": ACHIEVE, "command:": ACHIEVE, "do:": ACHIEVE,
             "ensure:": ENSURE, "verify:": ENSURE, "check:": ENSURE,
             "fetch:": FETCH, "list:": FETCH, "count:": FETCH}

# The ladder. Each intent permits its own ops and everything below it; `if` rides along
# everywhere because a branch is only as consequential as the block it runs, and that
# block's own statements are checked when the walk reaches them.
#
# `publish` RIDES ALONG FOR A DIFFERENT REASON, and the manifest already said so before this
# table was updated to agree: it is "the only statement whose effect is on the CONVERSATION
# rather than on the world — so it needs no authority and is legal under FETCH". A rung that
# reads the world and may not REPORT what it read is not a rung, and the writer closes every
# program with one, so its absence here refused every fetch ever written.
#
# `call` AND `foreach` ARE LISTED AT EVERY RUNG, AND THE TOOL DECIDES THE REST. Whether a
# call acts is not a property of the word: `CALL guest_ping` asks a question and `CALL
# create_vm` changes the lab, and every observation the writer makes is spelled the first
# way. So the OP is permitted everywhere and `violations` refuses the INSTANCE, using the
# acting-tool set a caller with a manifest supplies. A `foreach` is judged by its body for
# the same reason — decision 6's canonical read is a loop of probes.
#
# THE ALTERNATIVE WAS LEAVING THEM OUT, and that is what shipped for a day: the two lower
# rungs of the ladder could not run a single program the writer produces, because a probe
# was a trespass. A rung that may not read is not a rung.
#
# THE OFFER AND THE ENFORCEMENT MUST AGREE, which is a live invariant rather than a wish
# (`test_medusa_invariants`, both directions). Narrowing further belongs at the TOOL level —
# offering a fetch only the tools that ask — and that is a schema change nobody has measured,
# so it is not made here on the strength of it sounding right.
_PERMITS = {
    # `break` SITS AT EVERY RUNG, like `if`. It reaches nothing, changes nothing and asserts
    # nothing — it only shortens the loop it is inside — so withholding it from a FETCH would
    # forbid a retrieval from stopping early, which is a restriction with no rung behind it.
    FETCH:   {"fetch", "publish", "call", "foreach", "if", "break"},
    ENSURE:  {"fetch", "ensure", "publish", "call", "foreach", "if", "break"},
    ACHIEVE: None,                # the whole language
}

# Height on the ladder, for picking the authority a sentence actually needs.
_RUNG = {FETCH: 0, ENSURE: 1, ACHIEVE: 2}


def _markers() -> Dict[str, list]:
    """The operator's own words, from the manifest, so they stay data."""
    return (getattr(config, "INTENT", None) or {}).get("markers") or {}


def declared(goal: str) -> Optional[str]:
    """What the operator already said, or None if they did not say.

    None rather than a nearest match. A marker set that reaches is a vocabulary, and
    vocabularies are the thing this language exists to delete.
    """
    if not isinstance(goal, str) or not goal.strip():
        return None
    text = goal.strip().lower()

    for prefix, meaning in _PREFIXES.items():
        if text.startswith(prefix):
            return meaning

    hits = {meaning for meaning, words in _markers().items()
            for w in words if text.startswith(w + " ") or f" {w} " in f" {text} "}
    if not hits:
        return None
    # SEVERAL MARKERS IS NOT AMBIGUITY. "check golden exists, then spin up two" wants a
    # verification AND a command, and the ladder already says a command may contain both.
    # So the answer is the HIGHEST rung named — the authority the program needs — and the
    # lower words describe parts of it rather than competing with it. This is the three
    # working together rather than three choices to pick between.
    return max(hits, key=_RUNG.__getitem__)


def strip_prefix(goal: str) -> str:
    """The goal without its prefix — what the author should actually read."""
    if not isinstance(goal, str):
        return goal
    for prefix in _PREFIXES:
        if goal.strip().lower().startswith(prefix):
            return goal.strip()[len(prefix):].strip()
    return goal


def question(goal: str) -> Optional[str]:
    """The one question, or None when the operator has already answered it."""
    if declared(goal) is not None:
        return None
    return (f'"{goal}" — what do you want back?\n'
            f"  fetch    the numbers or the names. I read and report, nothing changes.\n"
            f"  ensure   a yes or no. I check whether it is so, nothing changes.\n"
            f"  achieve  it done. I do whatever is missing to make it true.")


def resolve(goal: str, asked: Any = None) -> str:
    """The operator's intent: declared, answered, or defaulted to FETCH — the bottom
    rung, which can do no harm."""
    said = declared(goal)
    if said is not None:
        return said
    if asked in _PERMITS:
        return asked
    if callable(asked):
        answer = asked(question(goal))
        if answer in _PERMITS:
            return answer
    return FETCH


def permits(intent: str) -> bool:
    """May a program written under this intent CHANGE anything?"""
    return _PERMITS.get(intent, _PERMITS[FETCH]) is None


def violations(program: Any, intent: str, actors: Optional[set] = None) -> List[str]:
    """Statements this intent is not authorised to contain.

    Enforced, not advised. The operator asked to be told something; a program that
    quietly creates a machine on the way to telling them has exceeded what it was given,
    and no postcondition makes that acceptable. Empty for an ACHIEVE, which sits at the
    top of the ladder and may use the whole language.

    `None` means NO INTENT WAS SUPPLIED, and nothing is refused. That is one word meaning
    one thing: `resolve()` is the only place absence becomes FETCH, because the safe
    default belongs where the operator is asked, not scattered through every consumer.
    This used to fall back to FETCH's set, which made the offer and the enforcement
    disagree on an unsupplied intent — the schema master offered the whole language while
    this function would have refused five sevenths of it. `run()` never hit it because it
    guards on `is not None`, so the disagreement was latent rather than live; it was found
    by asking the two sides the same question.

    `actors` IS THE SET OF TOOLS THAT CHANGE THE WORLD, and without it the two lower rungs
    of this ladder could not run a single program. `_PERMITS` is a set of OPS, and every
    observation the writer makes is spelled `CALL <probe>` — so `call` being absent from
    FETCH and ENSURE meant *"how many machines are up"* was refused for reaching above a
    fetch, on statement one. MEASURED the day enforcement was switched on: every read-only
    request, every phrasing.

    A rung that may read but not report, or report but not read, is not a rung. So the
    question a CALL is judged by is the one the tool answers, not the one the word does —
    see `master.statement_acts`, and `effects.actors(manifest)` is what to hand it. Absent,
    a call still counts as acting: the caller could not say, and fail-closed is the rule.
    """
    if intent is None:
        return []
    allowed = _PERMITS.get(intent, _PERMITS[FETCH])
    if allowed is None:
        return []
    from . import master
    from .consent import _walk
    from .validate import coerce_body
    out = []
    for i, st in enumerate(_walk(coerce_body(program) or [])):
        op = st.get("op")
        if not op or op in allowed:
            continue
        # AN ACTING OP IS A TRESPASS; A READING ONE IS A QUESTION ABOUT THE ANSWER SHAPE.
        # Different mistakes, so different sentences — the second is not a safety matter at
        # all: a `fetch` that wanted a verdict simply asked for the rung below the one it
        # meant.
        #
        # `achieve` IS COUNTED AS ACTING HERE AND IS NOT MARKED SO IN THE MANIFEST, and the
        # difference is real rather than an oversight. To `consent.survey` an ACHIEVE is an
        # ASSERTION — it is what grounds a program — while to this ladder it is the
        # CORRECTION operator, which closes whatever gap it finds and therefore changes the
        # lab. Both readings are right about their own question; only this one decides
        # authority, and getting it wrong would let a `fetch:` carry the one statement whose
        # entire purpose is to make something so.
        acts = master.statement_acts(st, actors) or op == ACHIEVE
        if acts:
            out.append(f"statement {i + 1}: `{op}` reaches above a {intent} — "
                       f"you asked to be TOLD something, and this changes the lab. "
                       f"Say `achieve:` if you meant to act.")
        elif op in (FETCH, ENSURE):
            out.append(f"statement {i + 1}: `{op}` reaches above a {intent} — "
                       f"a {intent} answers with data, not a verdict. Say `ensure:` "
                       f"if you wanted it checked.")
        # ANYTHING ELSE NEITHER ACTS NOR JUDGES, so there is nothing to refuse it for — a
        # statement whose whole effect is on the conversation is legal at every rung.
    return out


def standing_goal(program: Any) -> Optional[Dict[str, Any]]:
    """The one statement that stands for the whole program, or None.

    ONE AUTHORITY for a rule that had already been written twice — `tree_probe`'s
    `_goal_predicate` and an inline block in `author_probe`, whose own comment admits it is
    "the same rule author_probe arrived at". Both halves of it were learned by being broken,
    and both breakages cost a rung:

      * AN `achieve` OUTRANKS AN `ensure`, because it is the goal rather than a check along
        the way; among ensures the LAST wins, because a precondition at the top of a program
        is not what the program was FOR.
      * LOOP-LOCAL PREDICATES ARE EXCLUDED. Searching only the top level made a program
        whose one verdict sat inside a loop have no standing goal at all, so every revision
        "passed" against nothing (rung 9 reported `goal=HOLDS` while the checker said FAIL).
        Walking nested blocks fixed that and broke rung 11 the other way: an in-loop
        `ENSURE COUNT(SELECT vm WHERE name = '$item') = 1` was taken as the standing goal,
        and outside its loop `$item` resolves to nothing, so no correction could satisfy it.
        The rule that covers both: the standing goal must be re-evaluable in the OUTER
        scope.

    Returns the STATEMENT, not the predicate, because a caller that wants to change the op
    needs the statement — `standing_goal(p)["predicate"]` is the predicate.
    """
    import json as _json

    from .consent import _walk
    from .validate import coerce_body
    member = f"{config.SIGIL}{config.LOOP_VAR}"
    candidates = [st for st in _walk(coerce_body(program) or [])
                  if st.get("predicate") is not None
                  and member not in _json.dumps(st["predicate"])]
    return (next((st for st in candidates if st.get("op") == ACHIEVE), None)
            or next((st for st in reversed(candidates) if st.get("op") == ENSURE), None))


def promote(program: Any, intent: str) -> tuple:
    """Raise a standing goal that sits BELOW the authority it was granted.

    THE MIRROR OF `violations`. That function refuses a program reaching ABOVE its rung;
    this one lifts a program sitting below it, and the second case is not symmetrical with
    the first — reaching above is a trespass, sitting below is a program that cannot finish
    the job it was asked to do.

    WHY IT IS NEEDED, measured 2026-07-30. Granted ACHIEVE, the model writes ENSURE for the
    standing goal: a CHECK where it was licensed to CORRECT. The convergence machinery then
    never runs, because `execute` reports a failed non-achieve as `unsatisfied` and the
    deriver fires only for `unachieved` — deliberately, since `unsatisfied` means the
    program assumed something untrue and a diff would paper over it. So the whole
    correction path is unreachable, and the cell fails every time. Rung 7 shows it cleanly:
    the literal says "make sure", ACHIEVE's own phrase, and passes 3/3; the paraphrase says
    "there should end up being" and fails 3/3 on identical machinery.

    ONLY THE STANDING GOAL. A mid-program `ensure` is a legitimate precondition, and
    promoting every check would license acting on assumptions the author meant only to
    verify — the same mistake as inferring intent from wording, one level down.

    RETURNS A NEW PROGRAM AND A NOTE, and never mutates the argument. The operator chose
    promotion over objection, so what RUNS is not what was authored; the note is how that
    stays auditable instead of silent. A rewrite nobody records is indistinguishable from
    the author having written it, which is the one thing that would make this hard to debug
    later.
    """
    if intent != ACHIEVE:
        return program, None
    st = standing_goal(program)
    if st is None or st.get("op") != ENSURE:
        return program, None
    import copy as _copy
    fresh = _copy.deepcopy(program)
    target = standing_goal(fresh)
    if target is None or target.get("op") != ENSURE:
        return program, None          # the copy disagreed — change nothing
    target["op"] = ACHIEVE
    return fresh, ("standing goal promoted ENSURE -> ACHIEVE: granted authority to "
                   "CORRECT, authored only a CHECK")


def instruction(intent: str) -> str:
    """What to tell the author, once a human has settled it.

    Phrased as the operator's decision rather than as guidance, because it is one — the
    author is being handed a fact it had no way to derive, not steered toward a reading.
    """
    if intent == ACHIEVE:
        # "DO THE WORK" WAS THE OLD READING OF ACHIEVE, and it survived the 62160da
        # decision that replaced it. Once ACHIEVE is a MAKE — "make sure you exist" rather
        # than "certify what I just did" — what the operator wants is the state, not the
        # activity, and those differ precisely when the goal already holds. Rung 13 is that
        # case and the line argued for the wrong side of it: shown five machines already
        # labelled and networked, and told to "do the work", the author built five more.
        # A command is still a command; what it commands is an END, and the harness closes
        # whatever gap remains, so a gap of nothing is closed by doing nothing.
        return ("THIS IS A COMMAND. The operator wants this TRUE — an END STATE, not an "
                "activity. ACHIEVE is a MAKE: say what must be so and the harness closes "
                "whatever gap is left. So act on the DIFFERENCE between the lab you were "
                "shown and what was asked for: a goal that already holds needs no work "
                "doing twice. Open with ENSURE if something must already be true.")
    if intent == ENSURE:
        return ("THIS IS A VERIFICATION, NOT A COMMAND. The operator wants a yes or no. "
                "Use ENSURE, and FETCH if you need to read something first. Do NOT "
                "create, launch, label, attach or delete anything.")
    return ("THIS IS A RETRIEVAL. The operator wants the numbers or the names, nothing "
            "more. Use FETCH only. Do not check, and do not change anything.")
