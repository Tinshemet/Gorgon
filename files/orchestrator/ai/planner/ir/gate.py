"""
gate.py — the SCHEMA GATE: should this authored program be allowed to run?

THE SPLIT, and it is structural rather than a matter of taste. The schema master decides
what MAY be emitted; the gate decides whether what WAS emitted should run. A schema can
constrain the FORM of a statement and cannot compel that a program SAYS something — there
is no JSON-Schema for "every identifier the operator named appears somewhere" — so a rule
of that kind has to be judged after authoring, and everything that CAN be a constraint
belongs to the master instead. That direction is enforced, not just intended: see
`test_no_constrainable_rule_lives_only_in_the_gate`.

MECHANICALLY THIS IS THE CONTRACT'S RISK FORMULA AGAIN — weighted factors, a score,
threshold bands — and the operator spotted the similarity before it was built. One
correction matters: the contract scores DECLARED facts about a tool (someone wrote down
that `delete_vm` is irreversible), while the gate scores COMPUTED facts about a program.
Every factor here is read off the IR. **No factor asks a model whether a program looks
right.** That is the same firewall the reason gate drew around p_self, for the same
reason: a gate that consults the author it is judging has judged nothing.

WHY A SCORE AND NOT A VERDICT. A boolean cannot tell an improving correction from a
degrading one, and "getting worse" is one of the four ways the clarify loop ends. Three
bands:

    PROCEED   run it.
    CLARIFY   coherent, but something the operator asked for is missing or unstated.
              Re-ask, with the reasons, and TELL the operator it happened.
    REFUSE    too many things are wrong at once for re-asking to fix.

REFUSE IS REACHED BY ACCUMULATION, NEVER BY A SINGLE FACTOR, and that took a correction to
get right. The design called the refuse band "the compiler case — illogical, refused
outright", which is true and is already `validate.py`'s job: everything illogical on its
own is rejected before a program ever reaches here. So a gate that refused on one factor
would either duplicate a judgement upstream had already made, or make a new one on thinner
evidence. The first factor drafted here — an ACHIEVE on a predicate declaring
`derivable: false` — was exactly that mistake: `derive()` returning None is a DOCUMENTED
FALLBACK to asking the author, not a dead end, so `ACHIEVE ALL(...)` is a legitimate goal
that reaches its answer another way, and refusing it would have deleted a working
capability for a reason no rewording could ever satisfy. No weight in the manifest reaches
the refuse threshold alone.

INTENT IS CONSUMED, NEVER SNIFFED (decision 5). The gate never guesses whether the
operator wanted a check or a command; it is told, and it scores the program against what
it was told. Under `achieve`, a program with no ACHIEVE scores badly — that is the whole
of the inference it performs.

WHAT THE OPERATOR SEES is in `MESSAGES` below, phrased by the operator themselves. A
suppressed program is reported, not swallowed: a gate that silently re-asks would make a
harness that quietly disagreed with you indistinguishable from one that understood you.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from . import config, consent as _consent, intent as _intent, master, refs

PROCEED, CLARIFY, REFUSE = "proceed", "clarify", "refuse"

# The operator's own wording. Kept verbatim: these are the three things a person needs to
# be able to tell apart — it said no, it is having another go, it had another go and still
# says no — and the third is the one a silent implementation would lose.
MESSAGES = {
    REFUSE:  "Gate refused the schema: {reason} (score {score:.2f})!",
    CLARIFY: "Gate suppressed the proposed schema {reason} (score {score:.2f}), reclarifying....",
    "gave_up": "Gate refused the suppressed schema {reason} (score {score:.2f}), Please clarify",
}

# The four ways a clarify loop ends without ever reaching PROCEED. Written down together
# because "it stopped improving" and "it ran out of tries" are different facts about the
# request, and collapsing them would lose the more useful one.
STALE, WORSE, ATTEMPTS, TIMEOUT = "stale", "worse", "attempts", "timeout"


# ── the factors, each computed from the IR and each in [0, 1] ─────────────────────────

def _no_verdict(program: Any) -> float:
    """Medusa's one soundness rule, scored instead of asserted.

    `consent.unsound()` already computes this and already asks the operator a y/n about
    it. The gate does not replace that — it folds the same fact into a score, so a program
    that is unsound AND ignores the intent AND does nothing lands in refuse rather than
    presenting three separate small questions.
    """
    return 1.0 if _consent.unsound(program) is not None else 0.0


def _intent_unmet(comp: Dict[str, int], want: Optional[str]) -> float:
    """Did the program produce the KIND of answer that was asked for?

    Not "is it a good program" — whether it answers in the right currency. An `achieve`
    with no ACHIEVE never states what done means; an `ensure` with no ENSURE returns no
    verdict; a `fetch` that reads nothing returns no data. Zero when no intent was
    supplied, because an unsupplied fact is not a failing.
    """
    if want == _intent.ACHIEVE:
        return 0.0 if comp["achieve"] else 1.0
    if want == _intent.ENSURE:
        return 0.0 if comp["ensure"] else 1.0
    if want == _intent.FETCH:
        return 0.0 if comp["fetch"] else 1.0
    return 0.0


def _inert(comp: Dict[str, int], want: Optional[str]) -> float:
    """An `achieve` that only looks.

    Distinct from `intent_unmet`, and the pair is worth keeping apart: a program can carry
    a perfectly good ACHIEVE and no way to reach it, which is the declarative form and is
    LEGAL — `derive` computes the calls. So this is not fatal on its own. It scores because
    a declarative achieve depends entirely on the deriver being able to close that shape,
    and a program that also fails elsewhere is more likely to be one nobody can close.
    """
    if want != _intent.ACHIEVE:
        return 0.0
    return 0.0 if comp["acts"] else 1.0


def _goal_unnamed(program: Any, goal: str) -> float:
    """The fraction of the operator's own identifiers the program never mentions.

    THE REASON THE GATE EXISTS SEPARATELY FROM THE MASTER. There is no schema for "say
    this word": an enum can stop `core_net` being written where the operator said `core`,
    and cannot make a program mention `core` at all. A program that quietly operates on
    something else entirely is well-formed, decodable, and wrong.

    Deliberately a FRACTION rather than a flag. One unmentioned name out of four is often
    a paraphrase; four out of four is a program about a different request. Weighted so
    that even all-missing sits in clarify rather than refuse, because the honest response
    to "you did not mention what I asked about" is to ask again, not to decide.

    READS `master.named()`, NOT `master.identifiers()`, and the distinction is load-bearing
    rather than tidy. `identifiers()` is the permissive union that feeds enums, where an
    extra name widens what may be said and costs nothing. Here an extra name is a false
    accusation: it was scoring `fine`, out of "make sure it is all fine", as a name the
    program had forgotten — one word away from suppressing a correct program for failing to
    mention an adjective.
    """
    wanted = master.named(goal)
    if not wanted:
        return 0.0
    blob = json.dumps(program, default=str).lower()
    missing = [w for w in wanted if w.lower() not in blob]
    return len(missing) / len(wanted)


def _dead_binding(stmts: List[dict]) -> float:
    """Names bound and never read back.

    A smell, not a fault, and weighted below the clarify threshold on its own for exactly
    that reason — a program may legitimately bind something it does not use. It earns its
    place because it is the fingerprint of a specific failure that has happened: rung 6
    bound `red-net`, could not pronounce `$red-net`, and carried on as though it had. The
    binding-name pattern in the schema stops the unpronounceable case; this catches the
    general one, where a program builds something and then forgets it.
    """
    bound, read = [], set()

    def visit(value: Any):
        if isinstance(value, str):
            read.update(refs.names(value))
        elif isinstance(value, list):
            for v in value:
                visit(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                if k in ("var", "graft") and isinstance(v, str):
                    bound.append(v.lstrip(config.SIGIL))
                    continue
                visit(v)

    for st in stmts:
        visit(st)
    if not bound:
        return 0.0
    return len([b for b in bound if b not in read]) / len(bound)


# ── the score ─────────────────────────────────────────────────────────────────────────

def score(program: Any, goal: str = "", want: Optional[str] = None) -> Dict[str, Any]:
    """Every factor, the weighted total, the band, and why — in one object.

    Returns the FULL breakdown rather than a verdict, because two callers need different
    parts of it: the operator sees the reasons, and the clarify loop compares the score
    against the previous round to notice a correction that is making things worse.
    """
    from .validate import coerce_body
    stmts = _consent._walk(coerce_body(program) or [])
    comp = _consent.composition(program)

    factors = {
        "no_verdict":   _no_verdict(program),
        "intent_unmet": _intent_unmet(comp, want),
        "inert":        _inert(comp, want),
        "goal_unnamed": _goal_unnamed(program, goal),
        "dead_binding": _dead_binding(stmts),
    }
    weights = config.GATE["weights"]
    total = sum(weights[name] * value for name, value in factors.items())

    thresholds = config.GATE["thresholds"]
    band = (REFUSE if total >= thresholds["refuse"]
            else CLARIFY if total >= thresholds["clarify"]
            else PROCEED)

    return {"score": round(total, 4), "band": band, "factors": factors,
            "reasons": _reasons(factors, program, want)}


def _article(want: Optional[str]) -> str:
    """`an ensure`, `an achieve`, `a fetch` — the operator reads these sentences."""
    return f"{'an' if str(want)[:1] in 'aeiou' else 'a'} {want}"


def _reasons(factors: Dict[str, float], program: Any, want: Optional[str]) -> List[str]:
    """What to tell the operator, and what to hand back to the author.

    ONE LIST FOR BOTH, on purpose. If the sentence shown to the person is not the sentence
    the model is asked to fix, the operator is watching a different conversation from the
    one taking place — and the whole point of announcing a suppression is that they can
    see what the harness objected to.
    """
    out = []
    docs = config.GATE["factors"]
    for name, value in sorted(factors.items(), key=lambda kv: -kv[1]):
        if value <= 0:
            continue
        if name == "no_verdict":
            out.append(_consent.unsound(program) or docs[name]["doc"])
        elif name == "intent_unmet":
            out.append(f"the operator asked for {_article(want)}, and no {str(want).upper()} "
                       f"statement says what that answer is")
        elif name == "goal_unnamed":
            out.append(f"{round(value * 100)}% of the names the operator wrote appear "
                       f"nowhere in this program")
        else:
            out.append(docs[name]["doc"])
    return out


def verdict(program: Any, goal: str = "", want: Optional[str] = None) -> str:
    """Just the band, for a caller that does not need the breakdown."""
    return score(program, goal, want)["band"]


# ── the clarify loop ──────────────────────────────────────────────────────────────────

def clarify(program: Any, goal: str, want: Optional[str],
            reauthor: Callable[[Any, List[str]], Any],
            say: Optional[Callable[[str], None]] = None,
            elapsed: Optional[Callable[[], float]] = None,
            budget: Optional[float] = None) -> Dict[str, Any]:
    """Score, and if it lands in CLARIFY, re-ask until it proceeds or one of four ends.

    ONE GATE, AND THE CONVERSATION IS INJECTED. `reauthor` re-asks whoever wrote the
    program, `say` tells the operator — the same pattern `consent` and `referendum`
    already use for their `ask`. That is what lets the planner and the chat share this
    gate and differ only in where the clarification happens: in `emit_program` for a
    program the planner authored, in the chat for one the operator asked for there. A gate
    that owned its own surface would be two gates within a week.

    THE FOUR TERMINATIONS, and each is a different fact about the request:

      ATTEMPTS   it has been re-asked as often as the manifest allows.
      STALE      the author returned the SAME program. Re-asking a deterministic author
                 the same question gets the same answer; the loop is not going anywhere.
      WORSE      the score went UP. This is the one a boolean verdict cannot see, and the
                 strongest argument for scoring at all — a correction that is degrading is
                 not one more round away from working.
      TIMEOUT    the clarification has taken longer than it was given.

    REFUSE never enters the loop. An illogical program is not unclear, and asking the
    author to reword something that cannot converge would be theatre.
    """
    result = score(program, goal, want)
    if result["band"] == PROCEED:
        return {**result, "program": program, "attempts": 0}

    reason = "; ".join(result["reasons"]) or "no reason recorded"
    if result["band"] == REFUSE:
        _tell(say, MESSAGES[REFUSE].format(reason=reason, score=result["score"]))
        return {**result, "program": program, "attempts": 0, "ended": REFUSE}

    limit = int(config.GATE.get("attempts", 3))
    seen = {json.dumps(program, sort_keys=True, default=str)}
    attempts, ended = 0, None
    best = result

    while attempts < limit:
        if elapsed is not None and budget is not None and elapsed() >= budget:
            ended = TIMEOUT
            break
        _tell(say, MESSAGES[CLARIFY].format(reason="; ".join(best["reasons"]),
                                            score=best["score"]))
        attempts += 1
        nxt = reauthor(program, best["reasons"])
        if nxt is None:
            ended = STALE
            break
        fingerprint = json.dumps(nxt, sort_keys=True, default=str)
        if fingerprint in seen:
            # A DETERMINISTIC AUTHOR ASKED THE SAME QUESTION ANSWERS THE SAME WAY. Note
            # this checks against EVERY program seen, not just the last one — a loop that
            # alternates between two programs is as stuck as one that repeats a single
            # one, and comparing only with the previous round would never notice.
            ended = STALE
            break
        seen.add(fingerprint)

        scored = score(nxt, goal, want)
        if scored["band"] == PROCEED:
            return {**scored, "program": nxt, "attempts": attempts}
        if scored["band"] == REFUSE or scored["score"] > best["score"]:
            # Worse is worse whichever direction it came from: a correction that crossed
            # into refuse and one that merely regressed are both moving away from an
            # answer. Keep the BEST program seen rather than the last, so what the
            # operator is finally shown is the closest the author ever got.
            ended = WORSE
            break
        program, best = nxt, scored
    else:
        ended = ATTEMPTS

    _tell(say, MESSAGES["gave_up"].format(
        reason="; ".join(best["reasons"]) + f" [{ended}]", score=best["score"]))
    return {**best, "program": program, "attempts": attempts, "ended": ended}


def _tell(say: Optional[Callable[[str], None]], message: str) -> None:
    """Say it if there is anybody to say it to. Never raises — a gate that fell over
    because nobody was listening would refuse programs for the wrong reason."""
    if say is None:
        return
    try:
        say(message)
    except Exception:                                          # pragma: no cover
        pass
