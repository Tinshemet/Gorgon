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

THE GATE IS SMALL, AND IT GOT THAT WAY BY MEASUREMENT. It began with six factors and has
two. Four were deleted, every one for the same reason: they were invented from first
principles instead of from what the rest of the system leaves UNCOVERED, so each duplicated
a mechanism that already existed and already had a better answer.

  unclosable     duplicated derive()'s documented fallback to asking the author.
  inert          contradicted the declarative form derive() supports — and was the same
                 error as unclosable, written a second time in this very file.
  no_verdict     duplicated consent.py, which ASKS the operator y/n (decision 2). The gate
                 turned a settled question into a refusal.
  intent_unmet   was no_verdict counted twice. Under `achieve`, a program with no ACHIEVE
                 IS a program with no verdict; at 0.36 + 0.34 = 0.70 one flaw crossed a
                 0.50 threshold designed to need several.

WHAT IT COST, measured on the 13-rung ladder: the literal column went from 10/12 to 0/12
and the paraphrase column from 8/13 to 2/13. It refused every program that worked. No
deterministic suite could have found that, because every fixture in one is a program
written to exercise a factor — a suite built from a factor list can only confirm the
factor list.

`intent_unmet` was also wrong on the language's own terms. The operator's correction, worth
keeping verbatim in substance: ENSURE is the statement a program truly needs; FETCH grounds
the world before it starts; ACHIEVE is a PERMUTATION of ENSURE used to make sure something
is DONE — a barrier saying the run cannot pass this point unless X exists, so the rest of
the program has what it depends on. Plenty of correct programs need no ACHIEVE at all, so
its absence was never a fault to score.

WHAT SURVIVES is only what nothing else in the system checks: whether the program mentions
what the operator NAMED, and whether it bound something it never read. Both scored zero on
all thirteen rungs, with no false alarms. A gate whose failure mode is throwing away
correct work should fire rarely, and this one now does by construction.

REFUSE IS REACHED BY ACCUMULATION, NEVER BY A SINGLE FACTOR — asserted arithmetically over
the manifest, so a retuning cannot quietly hand one factor a veto. That invariant held
through the disaster above and did not save it: two factors that are secretly ONE FAULT
satisfy accumulation on paper while violating it in substance. Independence is the part
that has to be checked by hand.

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

from . import config, consent as _consent, master, refs

# ── #25, THE PROGRAM-REGIME REASON GATE: CLOSED BY TRIAGE, NOT BUILT ────────────────────
#
# The TOOL regime has one (`autonomous.make_reason_gate`): before a call runs, the model
# states WHY, and the stated reason is checked against the action. It exists because a model
# choosing a tool can choose a wrong one for a plausible-sounding reason.
#
# THE PROGRAM REGIME DOES NOT HAVE THAT FAILURE, because it does not choose. The ghost writer
# places a tile only where `effects.invert` says the tile makes the goal true, refuses with
# `Unsolvable` when nothing does, and NEVER IMPROVISES — the reason is the inversion, and it
# is a computation rather than a claim. A gate asking "why did you place this?" would be
# asking a lookup table to justify itself.
#
# WHAT PLAYS THE ROLE INSTEAD, and it is stricter: every goal closes with a WITNESS
# (`as_program` grounds each one), an assertion that ALREADY HOLDS is refused as decorative
# (`MedusaEngine._staged`), and a program that acts while asserting nothing is refused before
# it runs (`consent.survey`). A stated reason is a promise; a witness is a check.
#
# IT WOULD COME BACK if a model ever authored whole programs on the main line again. Staged
# lowering authors LEAVES, and each leaf is graded against one operator's schema and then
# against the assembled artifact — which is the same job at a finer grain.

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

    `want` IS CURRENTLY READ BY NO FACTOR, and that is worth stating rather than quietly
    dropping. It stays because intent is a fact the gate is TOLD (decision 5) and any
    future factor must take it that way rather than sniff it. But both factors that used it
    were deleted for being wrong, and `intent_unmet` was wrong twice over: it demanded an
    ACHIEVE in every program, when ENSURE is the statement a program truly needs and
    ACHIEVE is a permutation of it used as a barrier — "the run cannot pass this point
    unless X exists". Plenty of correct programs have none.
    """
    from .validate import coerce_body
    stmts = _consent._walk(coerce_body(program) or [])

    factors = {
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
        if name == "goal_unnamed":
            out.append(f"{round(value * 100)}% of the names the operator wrote appear "
                       f"nowhere in this program")
        elif name == "dead_binding":
            out.append(f"{round(value * 100)}% of the names this program binds are never "
                       f"read back")
        else:                                                  # pragma: no cover
            # A NEW FACTOR WITH NO SENTENCE FALLS BACK TO ITS MANIFEST DOC, and that is a
            # placeholder, not a design. The manifest doc explains a factor to whoever
            # maintains the gate; it is not addressed to the operator, and printing one
            # produced the line "a smell rather than a fault — deliberately below the
            # clarify threshold on its own" INSIDE A REFUSAL. Unreadable and
            # self-contradicting. Write the operator's sentence above.
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
