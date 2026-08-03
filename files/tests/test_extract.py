"""test_extract.py — the extractor's REPAIRS, with no model in the loop.

EVERY REPAIR IN `to_goals` WAS VERIFIED BY RUNNING THE MODEL and nothing else. That is a
40-minute, non-deterministic check of a pure function over a dict, and it meant a repair
could be broken by an edit and only noticed on the next ladder run — if the number happened
to move enough to be believed.

The repairs are the interesting half of the extractor, because they are the line the project
draws: A SLOT ERROR IS REPAIRED, A WRONG MEANING NEVER IS. Both sides of that line are
asserted here, and the DECLINES matter more than the repairs — a repair that fires when it
should not is how an extractor starts inventing requests.
"""
import os
import sys

# THE REPO ROOT FIRST, and it is not boilerplate. Run as a script, `tests/` becomes
# sys.path[0] — where `tests/shared.py` shadows the real `shared` PACKAGE, so the first
# import that reaches `shared.display` dies with "not a package". The suite was green under
# `-m` and NO-RESULT under run_all, which is the shape of a suite that quietly stops running.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.extract import to_goals

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def g(**kw):
    return {"goals": [kw]}


def test_the_number_is_read_from_either_slot():
    """The schema offers `amount`; the model routinely uses `value`."""
    print("[repair] a count arrives in whichever field the model chose")
    check("from amount", to_goals(g(goal="count", select={"kind": "vm"}, amount=3))[0]["eq"] == 3)
    check("from value", to_goals(g(goal="count", select={"kind": "vm"}, value="3"))[0]["eq"] == 3)
    check("as a word, because operators write words",
          to_goals(g(goal="count", select={"kind": "vm"}, value="three"))[0]["eq"] == 3)
    check("missing means one — the reading the sentence already had",
          to_goals(g(goal="count", select={"kind": "vm"}))[0]["eq"] == 1)


def test_a_number_that_is_not_a_number_does_not_crash():
    """`int("One")` raises, and a raising extractor loses the whole request."""
    print("[repair] an unparseable amount degrades, it does not explode")
    out = to_goals(g(goal="count", select={"kind": "vm"}, amount="lots"))
    check("the goal survives", len(out) == 1 and out[0]["eq"] == 1)


def test_a_bare_value_on_a_count_of_one_is_an_identity():
    """"create a vm named beta" came back as a count with `value: "beta"` and no attribute —
    the name was dropped and the writer built `vm1`."""
    print("[repair] naming one thing IS a count of one")
    out = to_goals(g(goal="count", select={"kind": "vm"}, value="beta"))
    check("the name reaches the selector", out[0]["select"].get("name") == "beta")
    check("and the count is one", out[0]["eq"] == 1)


def test_a_total_the_identities_account_for_is_dropped():
    """THE WORST THING FOUND ALL DAY, against the real lab.

    "create a machine named probe1" came back as TWO goals — a count of one over ALL
    machines, and the name — because the model said "a machine" and "named probe1"
    separately. Read literally over a nine-machine lab the first means DELETE EIGHT, and the
    program did exactly that: a benign creation request that would have emptied the lab.
    """
    print("[decline] a bare total the identities already explain")
    both = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "value": "One"},
        {"goal": "every", "select": {"kind": "vm"}, "attr": "name", "value": "probe1"}]})
    check("only the identity survives", len(both) == 1)
    check("and it is the named one", both[0]["select"].get("name") == "probe1")

    # IT FIRES ONLY WHERE THE TOTAL IS FULLY EXPLAINED. A label goal is not an identity and
    # accounts for nothing, so the total stands.
    kept = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 3},
        {"goal": "every", "select": {"kind": "vm"}, "attr": "label", "value": "prod"}]})
    check("a real total is not dropped", any(
        gg.get("shape") == "count" and gg.get("eq") == 3 for gg in kept))
    check("and a lone destructive ask is untouched — the operator meant it",
          to_goals(g(goal="count", select={"kind": "vm"}, amount=2))[0]["eq"] == 2)


def test_the_identity_repair_declines_where_it_could_be_wrong():
    """THE HALF THAT MATTERS. A repair that fires when it should not invents a request."""
    print("[decline] ambiguous is left alone, not guessed at")
    two = to_goals(g(goal="count", select={"kind": "vm"}, value="prod", amount=2))
    check("two things are not one thing's name", "name" not in two[0]["select"])
    state = to_goals(g(goal="count", select={"kind": "vm"}, value="running"))
    check("a value the manifest already claims is not an identity",
          "name" not in state[0]["select"])
    check("nor is a declared os", "name" not in
          to_goals(g(goal="count", select={"kind": "vm"}, value="linux"))[0]["select"])
    named = to_goals(g(goal="count", select={"kind": "vm"}, attr="label", value="prod"))
    check("an attributed value stays on its attribute",
          named[0]["select"].get("label") == "prod" and "name" not in named[0]["select"])


def test_the_identity_repair_has_a_shape_floor():
    """A/B-FOUND REGRESSION. `value: "Not specified"` became a machine CALLED "Not
    specified", and the writer produced an invalid program from it.

    The floor is the system's OWN notion of a name: `_fresh_names` mints `vm1`, and the real
    lab holds `bench-red-1` and `vm-orchestrator`. One token of word characters, hyphens and
    dots. A shape question, never a meaning one.
    """
    print("[decline] a value that cannot be a name is not one")
    def name_of(v):
        out = to_goals(g(goal="count", select={"kind": "vm"}, value=v))
        return out[0]["select"].get("name") if out else None
    check("a name is taken", name_of("beta") == "beta")
    check("a hyphenated one too, because real machines are named that way",
          name_of("bench-red-1") == "bench-red-1")
    # A SHRUG IS NOT A GOAL AT ALL, which is stronger than "not a name". An ABSENT number
    # means one — that is the reading the sentence already had — but a PRESENT unparseable
    # one means the model TRIED and did not know, and defaulting that to 1 over a
    # nine-machine lab means DELETE EIGHT.
    check("a shrug is dropped, not defaulted",
          to_goals(g(goal="count", select={"kind": "vm"}, value="Not specified")) == [])
    check("while an absent number still means one",
          to_goals(g(goal="count", select={"kind": "vm"}))[0]["eq"] == 1)
    # TEMPLATE RESIDUE IS STRIPPED BEFORE ANYTHING IS READ. `${5}` is the number five in
    # notation: read literally it fell past `_as_count`, defaulted to 1, and was then taken
    # as an IDENTITY — rung 13's request for five machines became one machine NAMED five.
    check("residue unwraps to the number it was hiding",
          to_goals(g(goal="count", select={"kind": "vm"}, value="${5}"))[0]["eq"] == 5)
    check("and a residue-wrapped name unwraps to the name",
          name_of("${probe1}") == "probe1")
    check("nor is anything with a space", name_of("two machines") is None)
    check("nor is nothing at all", name_of("") is None)
    # NOT A STOP-LIST, and that is deliberate. "unknown", "none", "n/a" and every other way
    # a model can shrug are NOT enumerated — that is the arms race refused twice already.
    # `fleetsize` looks like a name and becomes one; a wrong answer that came from the model
    # is a different thing to fix than one this module invented.
    check("a plausible token is still taken, ambiguity and all",
          name_of("fleetsize") == "fleetsize")


def test_an_identity_is_not_a_property():
    """`every vm must be named alpha` is not a state any world can reach."""
    print("[repair] `every ... must be named x` is a count of one")
    out = to_goals(g(goal="every", select={"kind": "vm"}, attr="name", value="alpha"))
    check("it becomes a count", out[0].get("shape") == "count" and out[0]["eq"] == 1)
    check("carrying the name", out[0]["select"].get("name") == "alpha")
    other = to_goals(g(goal="every", select={"kind": "vm"}, attr="status", value="running"))
    check("a real property stays an `every`", "every" in other[0])


def test_the_constraint_in_the_wrong_field():
    """`value: "name=alpha"` at goal level is the right meaning in the wrong slot."""
    print("[repair] a packed filter is unpacked into the selector")
    out = to_goals(g(goal="count", select={"kind": "vm"}, value="name=alpha"))
    check("unpacked", out[0]["select"].get("name") == "alpha")
    # A FILTER ON AN ATTRIBUTE THE KIND DOES NOT HAVE TAKES THE GOAL WITH IT. Keeping the
    # count and dropping only the filter would turn "one vm with colour=blue" into "exactly
    # one vm" — which over a nine-machine lab means DELETE EIGHT. The unusable half is not
    # separable from the half that would act on it.
    check("an unusable filter takes the goal with it, rather than acting without it",
          to_goals(g(goal="count", select={"kind": "vm"}, value="colour=blue")) == [])


def test_reach_is_not_invented():
    """Twenty of twenty-three failures were a reach goal the request never asked for."""
    print("[decline] a goal with no evidence in the request is dropped")
    asked = to_goals(g(goal="reach", select={"kind": "vm"}, amount=2),
                     "make sure the machines can ping each other")
    check("a request that asks for it keeps it", asked and asked[0].get("shape") == "reach")
    unasked = to_goals(g(goal="reach", select={"kind": "vm"}, amount=2),
                       "create a vm named beta and then launch it")
    check("a request that does not is dropped", not unasked)
    check("with no request given, nothing is assumed either way",
          to_goals(g(goal="reach", select={"kind": "vm"}, amount=2))[0]["shape"] == "reach")


def test_a_goal_the_model_did_not_state_is_dropped_not_completed():
    """The job this module exists to NOT have: deciding what the operator meant."""
    print("[decline] malformed is dropped, never filled in")
    check("no kind, no goal", not to_goals(g(goal="count", select={})))
    check("an `every` with no property is not a goal",
          not to_goals(g(goal="every", select={"kind": "vm"})))
    check("a `per` with nothing to make is not a goal",
          not to_goals(g(goal="per", select={"kind": "vm"})))
    check("an empty answer is an empty list, not a crash", to_goals({}) == [])
    check("and so is None", to_goals(None) == [])


def test_a_value_slot_filled_with_prose_is_refused():
    """THE WORST OUTCOME THE PRODUCTION PROBE MEASURES, and its cause.

    A prose value does not crash. The writer plans faithfully for it, the program grounds
    itself against that goal, and the run closes DONE while the world disagrees — 16 of 39
    literal and 21 of 39 paraphrase runs came back `DONE_BUT_FALSE`, which the probe calls
    the only unacceptable outcome on that path.

    EVERY EXAMPLE HERE WAS OBSERVED. "put the red ones on their own network" names no
    network and came back `network: "Not specified"`, so the writer created one CALLED
    `Not specified`; "launch all of them" came back as a machine named `all`; "clone golden
    into 3" as one named `clone of golden`.
    """
    from engines.extract import unusable

    for sel, why in (
            ({"kind": "vm", "name": "all"}, "a quantifier is not a name"),
            ({"kind": "vm", "name": "All"}, "and case does not launder it"),
            ({"kind": "vm", "network": "Not specified"}, "nor does a placeholder"),
            ({"kind": "vm", "name": "clone of golden"}, "nor a description")):
        assert unusable(sel), why

    # DECLINING WHEN UNSURE, which is the half that keeps this from becoming a vocabulary.
    # Two signals only — a listed word, and whitespace inside a value that NAMES a member —
    # because a false accusation refuses a correct request.
    for sel in ({"kind": "vm", "name": "web"},
                {"kind": "vm", "name": "vm-orchestrator"},
                {"kind": "network", "net_name": "core"},
                {"kind": "vm", "label": "red team"},      # a LABEL may be prose
                {"kind": "vm", "status": "running"}):
        assert not unusable(sel), f"{sel} is a request somebody could mean"


def test_the_refusal_reaches_to_goals():
    """A rule nothing applies is a rule that does not exist."""
    from engines.extract import to_goals

    raw = {"goals": [
        {"goal": "count", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "all"}]}},
        {"goal": "count", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "web"}]}}]}
    got = to_goals(raw, "launch all of them")
    assert len(got) == 1, "the unusable goal is dropped and the real one survives"
    assert got[0]["select"]["name"] == "web"


def test_a_DELETION_and_a_CREATION_are_currently_indistinguishable():
    """A NAMED HOLE, LOUD, AND IT FLIPS THE DAY SOMEBODY CLOSES IT.

    `delete the vm called doomed` and `create a vm named doomed` produce BYTE-IDENTICAL
    components: `COUNT(SELECT vm WHERE name = 'doomed') = 1`. The writer reads that as "make
    sure it exists", so a request to REMOVE a machine plans to CREATE one.

    THE CAUSE IS NOT THE MODEL BEING WRONG. It emits no `amount` at all, and `to_goals`
    defaults a missing count to ONE — documented, and correct for the commonest request
    there is. The reader cannot tell the two apart because nothing in the answer
    distinguishes them, and deciding from the English is the line this module exists not to
    cross.

    WHAT WAS TRIED AND WITHDRAWN: telling the `count` field that a removal is a count of
    zero. Measured at n=3, changed nothing, and prompt text is paid for on every request.

    THIS ASSERTION IS THE HOLE, not a wish. It passes while the two are identical and FAILS
    the day they differ — at which point this note is wrong and must be rewritten, which is
    the point of encoding it as a check rather than a comment.
    """
    import os

    if not os.environ.get("GORGON_LIVE_EXTRACT"):
        return                      # needs the model; opt in, like every other live arm

    from engines.extract import extract, to_goals
    remove = to_goals(extract("delete the vm called doomed"), "")
    # ASSERTED ON THE CONTROLLING GOAL, not on the whole list. The deletion also produces a
    # trailing `reach` goal, so the two answers are not byte-identical — and an equality
    # assertion read that as "the hole is closed" while the hazard was completely intact.
    # A test about a dangerous reading must assert THE READING.
    assert remove, "a deletion translated to nothing at all, which is a different hole"
    assert remove[0].get("eq") == 1, (
        "THE HOLE IS CLOSED — a deletion no longer asks for the machine to EXIST. Rewrite "
        f"this test's note.\n  delete -> {remove}")


def test_a_clause_that_did_not_survive_is_reported():
    """A HALF-READ REQUEST MUST NOT BE SILENT — measured on rung 2, a CONTROL rung.

    "create a vm named beta and then launch it" returns two goals every time. The second
    arrives as a bogus `reach`, the reach guard correctly refuses it, and until now the
    clause it stood for vanished without a word: the writer covered "beta exists", every
    layer below was honest about that half, and the run closed DONE having never launched
    anything. DONE_BUT_FALSE, deterministically, on the sentence the prompt uses as its own
    worked example.

    THE GUARD IS RIGHT AND STAYS. What is asserted here is that refusing a component is now
    REPORTABLE — the drop is the front seam's business, and what to DO about it belongs to
    a caller that can see it happened.
    """
    print("[honesty] a component that did not survive translation is reported")

    lost = []
    kept = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 1, "name": "beta"},
        {"goal": "reach", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "beta"}]}},
    ]}, "create a vm named beta and then launch it", dropped=lost)
    check("the goal that could be read survives", len(kept) == 1)
    check("and the one that could not is REPORTED", len(lost) == 1)
    check("the report names the shape that was lost", lost and lost[0].startswith("reach:"))

    # A REQUEST THAT DOES ASK ABOUT REACHING KEEPS ITS GOAL, and reports nothing.
    ok = []
    to_goals({"goals": [{"goal": "reach", "select": {"kind": "vm"}}]},
             "make sure they can all ping each other", dropped=ok)
    check("a reach the request DID ask for is not a drop", ok == [])

    # A MERGE IS NOT A LOSS. `_scoped` folding two goals about one member into one must not
    # read as a dropped clause, or the signal is noise on every request that triggers it.
    merged = []
    out = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 1, "name": "box"},
        {"goal": "every", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "box"}]},
         "attr": "os_type", "value": "linux"},
    ]}, "a vm named box with os linux", dropped=merged)
    check("two goals about one member become one", len(out) == 1)
    check("and a MERGE reports no loss", merged == [])

    # A SHAPE NOTHING IMPLEMENTS WAS THE QUIETEST EXIT OF ALL.
    unknown = []
    to_goals({"goals": [{"goal": "teleport", "select": {"kind": "vm"}}]}, "", dropped=unknown)
    check("an unimplemented shape is reported rather than skipped", len(unknown) == 1)

    # AND NOTHING IS COLLECTED WHEN NOBODY ASKED — the old signature, unchanged.
    check("with no out-list the behaviour is exactly as before",
          len(to_goals({"goals": [{"goal": "reach", "select": {"kind": "vm"}}]}, "x")) == 0)


# THE ENTRY POINT BELONGS AT THE BOTTOM, and this is not style. It sat in the MIDDLE of this
# file, and `main()` ends in `sys.exit` — so when the suite was run directly every test
# defined below it was never even defined, let alone called. Two were:
# `test_a_value_slot_filled_with_prose_is_refused`, which guards the worst outcome the
# production probe measures, and the drop-reporting test above. Found 2026-08-03 by adding a
# test and watching the total not move — the exact symptom `_suite.py`'s own docstring names
# as the only one this failure mode has.
def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "extract repairs"))


if __name__ == "__main__":
    main()
