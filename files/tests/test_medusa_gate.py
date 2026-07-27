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

from orchestrator.ai.planner.ir import config, gate

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

NO_VERDICT = {"body": [
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
        ("no_verdict", NO_VERDICT, GOAL, "achieve"),
        ("goal_unnamed", ABOUT_SOMETHING_ELSE, GOAL, "achieve"),
        ("inert", DECLARATIVE, GOAL, "achieve"),
        ("intent_unmet", SOUND, "ensure: is there a vm called core labelled prod", "ensure"),
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


def test_intent_is_consumed_and_never_sniffed():
    """The same program scores differently under different intents, and the difference
    comes ENTIRELY from what the operator said — decision 5, made mechanical."""
    for want, expect_unmet in (("achieve", 0.0), ("ensure", 1.0), ("fetch", 1.0)):
        r = gate.score(SOUND, GOAL, want)
        check(f"under {want}: intent_unmet={expect_unmet}",
              r["factors"]["intent_unmet"] == expect_unmet)
    check("with no intent supplied, nothing is held against the program",
          gate.score(SOUND, GOAL, None)["factors"]["intent_unmet"] == 0.0)


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

    # WORSE — a correction that scores higher than what it replaced.
    worse = {"body": [{"op": "call", "tool": "create_vm",
                       "args": {"name": "web", "os_type": "linux"}}]}
    out, said = _loop(ABOUT_SOMETHING_ELSE, [worse])
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
                           (gate.WORSE, [{"body": [{"op": "call", "tool": "create_vm",
                                                    "args": {"name": "web",
                                                             "os_type": "linux"}}]}])):
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
    out = gate.clarify(NO_VERDICT, GOAL, "achieve", reauthor, say=said.append)
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

    examples = {"no_verdict": NO_VERDICT, "intent_unmet": SOUND,
                "inert": DECLARATIVE, "goal_unnamed": ABOUT_SOMETHING_ELSE,
                "dead_binding": DEAD_BINDING}
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


def main():
    for fn in (test_a_good_program_is_not_touched,
               test_no_single_factor_can_refuse,
               test_an_underivable_achieve_is_a_legitimate_goal,
               test_each_factor_moves_the_score_and_says_why,
               test_intent_is_consumed_and_never_sniffed,
               test_an_unnamed_goal_is_a_fraction_not_a_flag,
               test_a_proceeding_program_never_enters_the_loop,
               test_a_clarified_program_is_run_and_the_operator_hears_about_it,
               test_the_loop_ends_four_distinguishable_ways,
               test_every_termination_tells_the_operator_which_one_it_was,
               test_a_refusal_is_announced_and_never_re_asked,
               test_the_gate_survives_having_nobody_to_talk_to,
               test_the_gate_never_asks_a_model_anything,
               test_no_constrainable_rule_lives_only_in_the_gate):
        print(f"\n── {fn.__name__}")
        fn()
    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
