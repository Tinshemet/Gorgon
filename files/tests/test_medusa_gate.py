#!/usr/bin/env python3
"""
test_medusa_gate.py — the schema gate, held to what it promises.

THE GATE IS THE PART THAT CAN SILENTLY DO HARM. Everything else in this language either
runs a program or refuses one with a message. The gate SUPPRESSES: it takes a program the
author produced, decides it is not good enough, and goes back for another. Done well that
is the difference between a harness that understood you and one that quietly did something
else. Done badly it is a layer that discards correct work, and — because it re-asks
automatically — discards it repeatedly and invisibly.

So the properties worth testing are not "does the score look sensible". They are:

  * REFUSE IS REACHED BY ACCUMULATION ONLY. `validate.py` already refuses everything
    illogical on its own. A gate that refuses on one factor is either repeating an
    upstream judgement or making a new one on thinner evidence — and the first factor
    drafted for this gate did exactly that, scoring `ACHIEVE ALL(...)` as unclosable when
    `derive()` returning None is a documented fallback to asking the author. That would
    have deleted a working capability, permanently, for a reason no rewording could fix.
  * A PROGRAM DOING LESS IS NOT A PROGRAM DOING WORSE. The same mistake was made twice:
    `unclosable` and then `inert`, both penalising the DECLARATIVE form on the grounds
    that derive() might not close it. Rung 13 priced it — in a world already satisfying
    the goal the pure `ACHIEVE REACH(...) >= 5` is the RIGHT answer, and the gate scored
    it CLARIFY at 0.18 while scoring the program that duplicated five machines PROCEED at
    0.00. Exactly backwards, and only visible because the gate was pointed at a rung.
  * A GOOD PROGRAM PASSES UNTOUCHED. The cost of a false suppression is a wasted round
    and an operator watching their harness argue with itself.
  * THE LOOP TERMINATES, four ways, and each is DISTINGUISHABLE. "It ran out of tries"
    and "it stopped improving" are different facts about the request.
  * THE OPERATOR IS TOLD. A suppression nobody hears about is indistinguishable from a
    harness that understood the request.

No model, no world, no network — every factor is computed from the IR.

Run:  PYTHONPATH=. python3 tests/test_medusa_gate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.ir import config, consent, gate

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


# ── programs, each a minimal example of one thing ─────────────────────────────────────

GOAL = "achieve: create a vm called core and label it prod"

SOUND = {"body": [
    {"op": "call", "tool": "create_vm", "args": {"name": "core", "os_type": "linux"}},
    {"op": "call", "tool": "add_label", "args": {"name": "core", "label": "prod"}},
    {"op": "achieve", "predicate": {"shape": "count",
                                    "select": {"kind": "vm", "label": "prod"}, "gte": 1}}]}

# BOTH surviving factors at once — the only route to a refusal now that no single factor
# can reach the threshold. It operates on a machine the operator never mentioned AND binds
# a set it never reads.
BOTH_FAULTS = {"body": [
    {"op": "new", "var": "spare", "kind": "vm", "args": {"os_type": "linux"}},
    {"op": "call", "tool": "create_vm", "args": {"name": "web", "os_type": "linux"}},
    {"op": "achieve", "predicate": {"shape": "count",
                                    "select": {"kind": "vm"}, "gte": 1}}]}

# ACTS AND VOUCHES FOR NOTHING, and the gate no longer has an opinion about it. consent.py
# asks the operator y/n — decision 2 — and a gate that refused the same program would be
# overriding a settled answer with a worse one. It did, and it cost the whole ladder.
UNGROUNDED = {"body": [
    {"op": "call", "tool": "create_vm", "args": {"name": "core", "os_type": "linux"}},
    {"op": "call", "tool": "add_label", "args": {"name": "core", "label": "prod"}}]}

ABOUT_SOMETHING_ELSE = {"body": [
    {"op": "call", "tool": "create_vm", "args": {"name": "web", "os_type": "linux"}},
    {"op": "achieve", "predicate": {"shape": "count", "select": {"kind": "vm"}, "gte": 1}}]}

DECLARATIVE = {"body": [
    {"op": "achieve", "predicate": {"shape": "count",
                                    "select": {"kind": "vm", "label": "prod"}, "gte": 1}}]}

DEAD_BINDING = {"body": [
    {"op": "new", "var": "spare", "kind": "vm", "args": {"os_type": "linux"}},
    {"op": "call", "tool": "create_vm", "args": {"name": "core", "os_type": "linux"}},
    {"op": "call", "tool": "add_label", "args": {"name": "core", "label": "prod"}},
    {"op": "achieve", "predicate": {"shape": "count",
                                    "select": {"kind": "vm", "label": "prod"}, "gte": 1}}]}

UNDERIVABLE_ACHIEVE = {"body": [
    {"op": "call", "tool": "create_vm", "args": {"name": "core", "os_type": "linux"}},
    {"op": "call", "tool": "add_label", "args": {"name": "core", "label": "prod"}},
    {"op": "achieve", "predicate": {"shape": "all", "of": [
        {"shape": "count", "select": {"kind": "vm", "label": "prod"}, "gte": 1},
        {"shape": "count", "select": {"kind": "vm"}, "gte": 1}]}}]}


def test_a_good_program_is_not_touched():
    """The commonest case, and the one a suppressing layer must never get wrong."""
    r = gate.score(SOUND, GOAL, "achieve")
    check("a sound program proceeds", r["band"] == gate.PROCEED)
    check("and carries no complaints", r["reasons"] == [])
    check("and every factor is clean", all(v == 0 for v in r["factors"].values()))


def test_no_single_factor_can_refuse():
    """THE INVARIANT OF THE BAND, asserted against the manifest rather than by example.

    Checked arithmetically over the weights, so it holds for any retuning: someone raising
    a weight to make a factor 'count more' cannot silently give it a veto. That is the
    mistake this gate already made once and caught before shipping."""
    weights = config.GATE["weights"]
    refuse = config.GATE["thresholds"]["refuse"]
    for name, w in weights.items():
        check(f"`{name}` alone ({w}) cannot reach refuse ({refuse})", w < refuse)
    check("but some pair can, or the band is unreachable",
          max(a + b for i, a in enumerate(weights.values())
              for b in list(weights.values())[i + 1:]) >= refuse)
    check("the weights are a distribution", abs(sum(weights.values()) - 1.0) < 1e-9)
    check("clarify sits below refuse",
          config.GATE["thresholds"]["clarify"] < refuse)


def test_a_program_doing_less_is_not_a_program_doing_worse():
    """THE SECOND CORRECTION, and the one that had to be measured to be seen.

    `unclosable` and `inert` were the same error twice: both penalised the DECLARATIVE
    form — an ACHIEVE with nothing before it — because derive() might not close it. Rung
    13 runs rung 4's goal against a world that ALREADY SATISFIES IT, and there the
    declarative form is not merely legal, it is the only right answer: derive computes the
    difference, finds none, and does nothing. The gate scored it CLARIFY while scoring a
    program that duplicated five machines PROCEED.

    Kept as a test rather than a comment because the reasoning that produced it is
    seductive — "surely an achieve should DO something" — and it has now been written into
    this gate twice."""
    goal = ("create 5 vms, put them all in a network, give them all the 'fleet' label, "
            "and make sure they all ping each other")
    declarative = {"body": [{"op": "achieve", "predicate": {
        "shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 5}}]}
    r = gate.score(declarative, goal, "achieve")
    check("the declarative form proceeds untouched", r["band"] == gate.PROCEED)
    check("with nothing held against it", r["reasons"] == [])
    check("no factor punishes a program for acting less",
          "inert" not in r["factors"])


def test_an_underivable_achieve_is_a_legitimate_goal():
    """THE CORRECTION, kept as a test so it cannot come back.

    `ACHIEVE ALL(...)` is stated on a shape the manifest declares underivable, and that is
    NOT a dead end: derive() returning None means "I cannot compute the difference", and
    the documented behaviour is to fall back to asking the author. Scoring it as a fault
    would refuse a capability that works."""
    r = gate.score(UNDERIVABLE_ACHIEVE, GOAL, "achieve")
    check("an ACHIEVE on an underivable shape still proceeds", r["band"] == gate.PROCEED)
    check("the gate has no factor for underivability",
          "unclosable" not in r["factors"])


def test_each_factor_moves_the_score_and_says_why():
    """A factor that never fires is decoration; a factor that fires without a sentence is
    a suppression the operator cannot act on."""
    cases = [
        ("goal_unnamed", ABOUT_SOMETHING_ELSE, GOAL, "achieve"),
    ]
    for factor, prog, goal, want in cases:
        r = gate.score(prog, goal, want)
        check(f"`{factor}` fires on its own example", r["factors"][factor] > 0)
        check(f"`{factor}` puts the program past proceed", r["band"] != gate.PROCEED)
        check(f"`{factor}` produces a reason to show", bool(r["reasons"]))

    # dead_binding is the deliberate exception: it fires and does NOT suppress, because a
    # program may legitimately bind something it never reads.
    r = gate.score(DEAD_BINDING, GOAL, "achieve")
    check("`dead_binding` fires on an unread binding", r["factors"]["dead_binding"] > 0)
    check("`dead_binding` alone does not suppress", r["band"] == gate.PROCEED)


def test_the_gate_has_no_opinion_about_a_missing_verdict():
    """THE FACTOR THAT COST THE WHOLE LADDER, kept as a test so it cannot return.

    A program that acts and vouches for nothing is unsound by the language's own rule —
    and `consent.py` ALREADY computes exactly that and responds by ASKING the operator
    y/n, which is decision 2 and was settled long before this gate existed. Scoring it
    here did not add a second opinion; it overrode a settled one with a worse response.

    It also double-counted. `no_verdict` means "no ensure AND no achieve"; `intent_unmet`
    under an achieve meant "no achieve". For these programs that is ONE fault, and at
    0.36 + 0.34 = 0.70 it cleared a 0.50 refuse threshold built to need SEVERAL. The
    accumulation invariant was satisfied on paper and violated in substance — which is
    why independence is checked by hand and not by arithmetic.

    Measured: the full factor set took the ladder's literal column from 10/12 to 0/12.

    AND IT WAS WRONG ON THE LANGUAGE'S TERMS TOO, per the operator: ENSURE is what a
    program truly needs, FETCH grounds the world before it starts, and ACHIEVE is a
    permutation of ENSURE used as a barrier — the run cannot pass this point unless X
    exists. Plenty of correct programs have no ACHIEVE, so demanding one was never a
    fault to score.
    """
    r = gate.score(UNGROUNDED, GOAL, "achieve")
    check("a program that acts and asserts nothing still proceeds",
          r["band"] == gate.PROCEED)
    check("the gate has no `no_verdict` factor", "no_verdict" not in r["factors"])
    check("the gate has no `intent_unmet` factor", "intent_unmet" not in r["factors"])
    check("consent.py still catches it, which is whose job it is",
          consent.question(UNGROUNDED) is not None)
    # Under EVERY intent, not just achieve — the old factor changed its verdict with the
    # intent, which is how one program scored three different ways for no structural
    # reason.
    for want in ("fetch", "ensure", "achieve", None):
        check(f"…and under {want or 'no intent'} too",
              gate.score(UNGROUNDED, GOAL, want)["band"] == gate.PROCEED)


def test_every_surviving_factor_is_one_nothing_else_checks():
    """THE RULE THAT WOULD HAVE PREVENTED ALL FOUR DELETIONS.

    Four factors were deleted for duplicating a mechanism that already existed and already
    answered better. The surviving two are the ones with no other owner: nothing else in
    the system asks whether a program MENTIONS what the operator named, and nothing else
    notices a binding that is never read.

    Asserted by naming the owners explicitly. A new factor has to survive the same
    question — who else already handles this, and do they answer better? — and writing the
    list down is what makes that question unavoidable rather than remembered.
    """
    owned_elsewhere = {
        "no_verdict":   "consent.py asks the operator y/n (decision 2)",
        "intent_unmet": "the same fault as no_verdict, and not every program needs ACHIEVE",
        "unclosable":   "derive() returning None already falls back to asking the author",
        "inert":        "the declarative form is legal and derive() computes the calls",
    }
    factors = set(gate.score(SOUND, GOAL, "achieve")["factors"])
    for name, owner in sorted(owned_elsewhere.items()):
        check(f"`{name}` is NOT a gate factor — {owner}", name not in factors)
    check("what is left is exactly the uncovered pair",
          factors == {"goal_unnamed", "dead_binding"})


def test_an_unnamed_goal_is_a_fraction_not_a_flag():
    """One name missing out of four is usually a paraphrase; four out of four is a program
    about a different request. Collapsing that to a boolean would suppress both alike."""
    partial = {"body": [
        {"op": "call", "tool": "create_vm", "args": {"name": "core", "os_type": "linux"}},
        {"op": "achieve", "predicate": {"shape": "count", "select": {"kind": "vm"}, "gte": 1}}]}
    some = gate.score(partial, GOAL, "achieve")["factors"]["goal_unnamed"]
    none_ = gate.score(SOUND, GOAL, "achieve")["factors"]["goal_unnamed"]
    all_ = gate.score(ABOUT_SOMETHING_ELSE, GOAL, "achieve")["factors"]["goal_unnamed"]
    check("naming everything scores 0", none_ == 0.0)
    check("naming nothing scores 1", all_ == 1.0)
    check("naming some sits strictly between", 0.0 < some < 1.0)
    # PRECISION, not recall — the property that keeps this factor from suppressing correct
    # programs. Every goal below names nothing, so every one must score zero however
    # ordinary its English. `fine` was being read as a name out of the first of them.
    for goal in ("make sure it is all fine",
                 "stop every vm that is currently running",
                 "check whether anything is still up",
                 "how many machines are there"):
        check(f"no name invented from {goal[:38]!r}",
              gate.score(SOUND, goal, "achieve")["factors"]["goal_unnamed"] == 0.0)
    # ...and a name the operator DID give is still found, in each of the three forms.
    for goal, missing in (("create a vm called core", False),
                          ("create a vm called zebra", True),
                          ("label them 'prod'", False),
                          ("label them 'staging'", True),
                          ("create n1 and n2", True)):
        fired = gate.score(SOUND, goal, "achieve")["factors"]["goal_unnamed"] > 0
        check(f"{goal!r}: {'missed' if missing else 'mentioned'} by the program",
              fired is missing)

    # The intent MARKER is not an identifier. "bring up three vms called n1 n2 n3" was
    # scoring `bring` as a name the program failed to mention.
    marked = {"body": [{"op": "new", "var": "vms", "kind": "vm", "amount": 3,
                        "args": {"os_type": "linux"}},
                       {"op": "foreach", "in": "$vms",
                        "call": {"tool": "add_label",
                                 "args": {"name": "$item", "label": "fleet"}}},
                       {"op": "achieve", "predicate": {"shape": "count",
                                                       "select": {"kind": "vm", "label": "fleet"},
                                                       "gte": 3}}]}
    check("an intent marker is not counted as a name the program forgot",
          gate.score(marked, "bring up 3 vms and label them fleet",
                     "achieve")["factors"]["goal_unnamed"] == 0.0)


# ── the clarify loop ──────────────────────────────────────────────────────────────────

def _loop(program, replies, **kw):
    """Run clarify() against a scripted author, collecting what the operator was told."""
    said = []
    seq = list(replies)

    def reauthor(_prog, _reasons):
        return seq.pop(0) if seq else None

    out = gate.clarify(program, GOAL, "achieve", reauthor, say=said.append, **kw)
    return out, said


def test_a_proceeding_program_never_enters_the_loop():
    out, said = _loop(SOUND, [])
    check("no re-ask for a program that was already fine", out["attempts"] == 0)
    check("and the operator is not told about a suppression that did not happen", said == [])


def test_a_clarified_program_is_run_and_the_operator_hears_about_it():
    out, said = _loop(ABOUT_SOMETHING_ELSE, [SOUND])
    check("the corrected program is what comes back", out["program"] == SOUND)
    check("it proceeds", out["band"] == gate.PROCEED)
    check("it took exactly one re-ask", out["attempts"] == 1)
    check("the operator was told it was suppressed",
          len(said) == 1 and said[0].startswith("Gate suppressed the proposed schema"))
    check("and the message carries the reason and the score",
          "appear nowhere" in said[0] and "score 0." in said[0])


def test_the_loop_ends_four_distinguishable_ways():
    """Each termination is a different fact about the request, so each must be reported
    as itself rather than as a generic failure."""
    # ATTEMPTS — always a fresh but still-inadequate program.
    variants = [{"body": [{"op": "call", "tool": "create_vm",
                           "args": {"name": f"other{i}", "os_type": "linux"}},
                          {"op": "achieve", "predicate": {"shape": "count",
                                                          "select": {"kind": "vm"}, "gte": 1}}]}
                for i in range(9)]
    out, said = _loop(ABOUT_SOMETHING_ELSE, variants)
    check("ATTEMPTS: it stops at the manifest's limit",
          out["ended"] == gate.ATTEMPTS and out["attempts"] == config.GATE["attempts"])

    # STALE — the author returns something already seen.
    out, said = _loop(ABOUT_SOMETHING_ELSE, [ABOUT_SOMETHING_ELSE])
    check("STALE: the same program back means the loop is not going anywhere",
          out["ended"] == gate.STALE)
    out, said = _loop(ABOUT_SOMETHING_ELSE, [])
    check("STALE: an author with no answer ends it too", out["ended"] == gate.STALE)

    # WORSE — a correction that scores HIGHER than what it replaced. Now that the gate
    # has two factors, degrading means picking up the second one while keeping the first:
    # BOTH_FAULTS still operates on a machine nobody named AND adds an unread binding.
    out, said = _loop(ABOUT_SOMETHING_ELSE, [BOTH_FAULTS])
    check("WORSE: a degrading correction stops the loop", out["ended"] == gate.WORSE)
    check("WORSE: and the BEST program seen is what is kept, not the last",
          out["program"] == ABOUT_SOMETHING_ELSE)

    # TIMEOUT — the clock, injected. Checked BEFORE each re-ask rather than after, because
    # the cost being budgeted is the author round itself; noticing afterwards that it was
    # already too late has spent the thing the budget existed to protect.
    ticks = iter([0.0, 99.0, 99.0, 99.0])
    out, said = _loop(ABOUT_SOMETHING_ELSE, variants,
                      elapsed=lambda: next(ticks), budget=10.0)
    check("TIMEOUT: the budget ends it mid-loop", out["ended"] == gate.TIMEOUT)
    check("TIMEOUT: after the rounds it did have time for", out["attempts"] == 1)
    over = iter([99.0])
    out, said = _loop(ABOUT_SOMETHING_ELSE, variants,
                      elapsed=lambda: next(over), budget=10.0)
    check("TIMEOUT: an already-spent budget never starts a round",
          out["ended"] == gate.TIMEOUT and out["attempts"] == 0)


def test_every_termination_tells_the_operator_which_one_it_was():
    """The third message exists because 'it tried and still says no' is a different thing
    to hear than 'it says no'. It must name the termination, or all four look alike."""
    for ended, replies in ((gate.STALE, [ABOUT_SOMETHING_ELSE]),
                           (gate.WORSE, [BOTH_FAULTS])):
        out, said = _loop(ABOUT_SOMETHING_ELSE, replies)
        final = said[-1]
        check(f"{ended}: the last word is the give-up message",
              final.startswith("Gate refused the suppressed schema"))
        check(f"{ended}: and it names which termination it was", f"[{ended}]" in final)
        check(f"{ended}: and ends asking the operator to clarify",
              final.endswith("Please clarify"))


def test_a_refusal_is_announced_and_never_re_asked():
    """An illogical program is not an unclear one. Asking the author to reword something
    that cannot be fixed by rewording is theatre, and it burns rounds."""
    asked = []

    def reauthor(prog, reasons):
        asked.append(prog)
        return SOUND

    said = []
    out = gate.clarify(BOTH_FAULTS, GOAL, "achieve", reauthor, say=said.append)
    check("a refused program scores in the refuse band", out["band"] == gate.REFUSE)
    check("the author is never asked", asked == [])
    check("the operator is told once", len(said) == 1)
    check("with the refusal wording", said[0].startswith("Gate refused the schema:"))
    check("and it ends in the operator's exclamation", said[0].endswith("!"))


def test_the_gate_survives_having_nobody_to_talk_to():
    """`say` is injected, and an unattended run supplies none. A gate that fell over
    because nobody was listening would refuse programs for the wrong reason."""
    out = gate.clarify(ABOUT_SOMETHING_ELSE, GOAL, "achieve", lambda p, r: SOUND)
    check("no `say` is not a failure", out["band"] == gate.PROCEED)

    def explodes(_msg):
        raise RuntimeError("the operator's terminal went away")

    out = gate.clarify(ABOUT_SOMETHING_ELSE, GOAL, "achieve", lambda p, r: SOUND,
                       say=explodes)
    check("a `say` that throws does not change the verdict", out["band"] == gate.PROCEED)


def test_the_gate_never_asks_a_model_anything():
    """THE FIREWALL, asserted structurally. Every factor is computed from the IR; a gate
    that consulted the author it is judging has judged nothing. This is the same line the
    reason gate drew around p_self, and it is worth a test rather than a comment because
    'just ask the model to check it' is the easiest thing in the world to add later."""
    import inspect
    src = inspect.getsource(gate)
    for forbidden in ("ollama", "urllib", "requests", "chat(", "complete(", "_OLLAMA"):
        check(f"no {forbidden!r} anywhere in the gate", forbidden not in src)
    check("and it imports nothing outside the language",
          all(m in ("json", "typing", "__future__",
                    "config", "consent", "intent", "master", "refs", "validate")
              for m in _imported(src)))


def _imported(src):
    out = []
    for line in src.splitlines():
        line = line.strip()
        if line.startswith("from . import"):
            out += [p.split(" as ")[0].strip() for p in line[len("from . import"):].split(",")]
        elif line.startswith("import ") and " " in line:
            out.append(line.split()[1].split(".")[0])
        elif line.startswith("from ") and " import " in line:
            out.append(line.split()[1].lstrip(".").split(".")[0])
    return [m for m in out if m]


def test_no_constrainable_rule_lives_only_in_the_gate():
    """THE INVARIANT THAT KEEPS THE TWO HALVES FROM COLLAPSING INTO ONE.

    A rule a schema COULD enforce belongs to the master, where the decoder cannot violate
    it. Catching it here instead costs a whole authoring round to discover something that
    could have been impossible to write — which is the exact cost step 1 of this build
    existed to remove, and it would come straight back if the gate became the convenient
    place to put every new rule. The gate is for what a schema structurally cannot say.

    Two halves, because the interesting claim is not fully mechanical:

      DECLARED   every factor states why it is not expressible as a constraint. Same
                 declare-or-say-why shape as the tool `verify` coverage: the gap becomes a
                 position somebody took rather than a rule nobody thought about.
      CHECKED    validate() must ACCEPT each factor's own example. A factor whose example
                 is already rejected upstream is repeating a judgement rather than making
                 one, and repeating it later and more expensively.

    It lives beside the fixtures rather than in test_medusa_invariants because the second
    half needs a PROGRAM per factor, and the examples are here.
    """
    from orchestrator.ai.planner.ir import validate

    examples = {"goal_unnamed": ABOUT_SOMETHING_ELSE, "dead_binding": DEAD_BINDING}
    factors = config.GATE["factors"]

    check("every factor the gate scores is declared in the manifest",
          set(factors) == set(gate.score(SOUND, GOAL, "achieve")["factors"]))
    check("every declared factor has an example here", set(factors) == set(examples))

    for name, spec in sorted(factors.items()):
        check(f"`{name}`: says why a schema cannot express it",
              bool(spec.get("why_not_schema")))
        ok, problems = validate(examples[name])
        check(f"`{name}`: its example is WELL-FORMED — the gate is not repeating validate",
              ok or not problems)


def test_the_gate_is_actually_in_the_path_a_program_takes():
    """WIRED, not merely written. Every part of this language that was built and left
    unreached stayed broken for days — `disjoint` had no evaluator for weeks, composites
    never evaluated at all — because nothing exercised the path end to end. So this runs a
    program through `make_run_program`, the seam the planner actually calls, and checks
    the gate is standing in it.

    The other half of the claim is the one that would cost real work if it were wrong: a
    program the gate refuses must NOT reach `call`. A gate that announced a refusal and
    ran the program anyway would be worse than no gate — it would report a safety
    behaviour it does not have.
    """
    from orchestrator.ai.planner.program import make_run_program

    class _Lab:
        vms = {}

        def known_names(self):
            return set()

    executed, said = [], []

    def call(tool, args):
        executed.append(tool)
        return {"success": True}

    run_program = make_run_program(_Lab(), None, known_names=set(), consent=True,
                                   intent="achieve", say=said.append)

    # REFUSED: operates on a machine the operator never named AND leaves a binding unread.
    out = run_program(BOTH_FAULTS, GOAL, call)
    check("a refused program comes back as `invalid`", bool(out.get("invalid")))
    check("a refused program's statements never reach the world", executed == [])
    check("and the operator is told", any("Gate refused" in m for m in said))

    # PROCEEDING: the same seam, a program with nothing against it.
    executed.clear(), said.clear()
    out = run_program(SOUND, GOAL, call)
    check("a sound program is not held back", not out.get("invalid"))
    check("and it actually ran", executed != [])
    check("with nothing said to the operator", said == [])

    # SUPPRESSED WITH NOBODY TO RE-ASK: announce and proceed. Suppressing a program the
    # harness has no way to improve would leave the operator with nothing, in exchange for
    # one that still has to pass its own ENSURE before anything is claimed.
    executed.clear(), said.clear()
    out = run_program(ABOUT_SOMETHING_ELSE, GOAL, call)
    check("a clarify with no author to re-ask still runs", executed != [])
    check("but says so", any("suppressed" in m and "nobody to re-ask" in m for m in said))

    # SUPPRESSED WITH AN AUTHOR: the corrected program is the one that runs.
    executed.clear(), said.clear()
    out = run_program(ABOUT_SOMETHING_ELSE, GOAL, call, lambda p, r: SOUND)
    check("the re-authored program is the one executed", "add_label" in executed)
    check("and the operator saw the suppression", any("suppressed" in m for m in said))


def main():
    for fn in (test_a_good_program_is_not_touched,
               test_no_single_factor_can_refuse,
               test_a_program_doing_less_is_not_a_program_doing_worse,
               test_an_underivable_achieve_is_a_legitimate_goal,
               test_each_factor_moves_the_score_and_says_why,
               test_the_gate_has_no_opinion_about_a_missing_verdict,
               test_every_surviving_factor_is_one_nothing_else_checks,
               test_an_unnamed_goal_is_a_fraction_not_a_flag,
               test_a_proceeding_program_never_enters_the_loop,
               test_a_clarified_program_is_run_and_the_operator_hears_about_it,
               test_the_loop_ends_four_distinguishable_ways,
               test_every_termination_tells_the_operator_which_one_it_was,
               test_a_refusal_is_announced_and_never_re_asked,
               test_the_gate_survives_having_nobody_to_talk_to,
               test_the_gate_never_asks_a_model_anything,
               test_no_constrainable_rule_lives_only_in_the_gate,
               test_the_gate_is_actually_in_the_path_a_program_takes):
        print(f"\n── {fn.__name__}")
        fn()
    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
