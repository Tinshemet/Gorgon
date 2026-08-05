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
    """`int("One")` raises, and a raising extractor loses the whole request.

    THE ASSERTION CHANGED ON 2026-08-05 AND THE PURPOSE DID NOT. This used to require the
    goal to SURVIVE with `eq: 1`, which is the same "said and unreadable becomes said and
    ignored" collapse that let `amount: -1` become `eq: 1` and turned a deletion into a
    creation — see `test_a_count_is_a_total_and_never_a_change`. `lots` is a quantity the
    operator stated and this reader cannot read, so defaulting it to ONE answers a request
    nobody made, silently. What this test was actually written to protect is that the
    extractor DEGRADES rather than raises, and that is asserted below unchanged.
    """
    print("[repair] an unparseable amount degrades, it does not explode")
    dropped = []
    out = to_goals(g(goal="count", select={"kind": "vm"}, amount="lots"), "make lots of vms",
                   dropped)
    check("it does not raise", isinstance(out, list))
    check("the unreadable quantity is refused rather than invented", out == [])
    check("and the request is not half-read in silence",
          len(dropped) == 1 and "lots" in dropped[0])


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
    """A rule nothing applies is a rule that does not exist.

    THE REQUEST NOW CONTAINS THE NAME IT EXPECTS TO SURVIVE, and that is a fixture fix rather
    than a change of subject. It read `"launch all of them"` while asserting that a goal about
    a machine called `web` came through — a pairing no real extraction produces, because the
    operator cannot be asking about `web` in a sentence that never says it. The
    invented-identifier guard flagged it correctly on the day it was added
    (`test_a_name_the_request_never_says_is_not_a_name`). What this test is FOR — that
    `unusable` is actually applied by `to_goals` and not merely defined — is unchanged.
    """
    from engines.extract import to_goals

    raw = {"goals": [
        {"goal": "count", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "all"}]}},
        {"goal": "count", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "web"}]}}]}
    got = to_goals(raw, "launch all of them, especially web")
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


def test_a_value_the_answer_calls_a_property_is_not_also_a_name():
    """THE COMMONEST TRANSLATION FAILURE, and the model hands over the evidence itself.

    `name` is REQUIRED on a count goal — measured necessary, because offered as optional it
    went unfilled and `box1` was lost — and most requests name no member. So the model must
    answer, the only free string in the branch is `name`, and it repeats whatever qualifier
    is nearby. A name is an IDENTITY, so `count(vm WHERE name=prod) = 3` asks for three
    members sharing one, which no world can reach: the writer refuses, and refuses THE WHOLE
    REQUEST including the goals it could have served.

    NOTHING IS GUESSED HERE. The same answer states the fact correctly in its own `every`
    goal, so a value the model called a `label` is not a name BECAUSE THE MODEL SAID SO.
    """
    print("[repair] a value this answer called a property is not also a name")

    got = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 3, "name": "prod"},
        {"goal": "every", "select": {"kind": "vm"}, "attr": "label", "value": "prod"},
    ]}, "make sure exactly 3 vms carry the prod label")
    counts = [g for g in got if g.get("shape") == "count"]
    check("the impossible identity is gone", counts and "name" not in counts[0]["select"])
    check("the count survives", counts and counts[0]["eq"] == 3)
    check("and the property the model stated is kept",
          any(g.get("must") == {"label": "prod"} for g in got))

    # A REAL NAME IS UNTOUCHED — used as a value of the KEY, which is agreement, not
    # contradiction.
    kept = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 1, "name": "box1"},
        {"goal": "every", "select": {"kind": "vm", "where": [{"attr": "name",
                                                              "value": "box1"}]},
         "attr": "os_type", "value": "linux"},
    ]}, "a vm called box1 running linux")
    check("a name the answer only ever uses AS a name survives",
          any(g.get("select", {}).get("name") == "box1" for g in kept))

    # SCOPED TO THE KIND THAT SAID IT. Read globally this cost rung 3: "put web on lab" makes
    # `web` a value of a NETWORK property, which says nothing about what a MACHINE is called.
    both = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "network"}, "amount": 1, "name": "lab"},
        {"goal": "count", "select": {"kind": "vm"}, "amount": 1, "name": "web"},
        {"goal": "every", "select": {"kind": "network", "where": [{"attr": "name",
                                                                   "value": "lab"}]},
         "attr": "members", "value": "web"},
    ]}, "create a network called lab and a vm named web, then put web on lab")
    check("a network's member does not disqualify a machine's NAME",
          any(g.get("select", {}).get("name") == "web" for g in both))
    check("and the network keeps its own name",
          any(g.get("select", {}).get("net_name") == "lab" for g in both))

    # NO EVIDENCE, NO REPAIR — this rule declines rather than guessing. Asserted at a count
    # of ONE, because above one the arithmetic rule below catches it first for a different
    # and stronger reason.
    alone = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 1, "name": "golden"},
    ]}, "clone golden")
    check("a stray name the answer never explains is left alone",
          any(g.get("select", {}).get("name") == "golden" for g in alone))


def test_a_word_the_model_was_shown_is_not_a_name():
    """A GOAL SHAPE HANDED BACK AS AN IDENTITY. `reach` is an enum value the model is shown,
    and it returns it the same way it returns a field name — `_echoed` named the field names
    and the kind nouns and not the shapes, so "spin up five machines… confirm each can reach
    the others" built a machine called `reach`.

    AND THE RULE THAT WAS WITHDRAWN, recorded so it is not re-derived. "A count above one
    cannot pin an identity, so strip the name and keep the count" is ARITHMETICALLY SOUND —
    the key is the identity — and measured 6 -> 12 DONE_BUT_FALSE on the literal arm:

        "make sure exactly 3 vms carry the 'prod' label"
          name=prod stripped  ->  count(vm) = 3     satisfiable, and NOT the request

    The impossible goal was refused by the writer and reported UNMET, which is honest.
    Stripped, it can be MET — three machines, no label — so the run builds them and closes
    DONE over a world the checker disagrees with. Stripping is only safe when what remains
    is still the whole truth, and there the name carried the only copy of `prod`.
    """
    print("[repair] a word the model was shown is not a name")
    got = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 5, "name": "reach"}]}, "")
    check("a goal shape handed back as a name is stripped",
          got and "name" not in got[0]["select"])
    check("and the count survives it", got and got[0]["eq"] == 5)

    # AN UNEXPLAINED NAME BESIDE A COUNT ABOVE ONE IS REFUSED — and refusing is NOT the
    # withdrawn rule above, which is the distinction the whole docstring turns on.
    #
    #   STRIP the name  -> `count(vm) = 3`, SATISFIABLE and not the request. The run builds
    #                      three machines and closes DONE. That is the 6 -> 12 disaster.
    #   KEEP  the name  -> impossible goal, writer says `Unsolvable: nothing reaches`,
    #                      run closes UNMET. Honest, and it blames the ENGINE.
    #   REFUSE the goal -> the front seam says WHY, and closes UNTRANSLATED. Honest, and it
    #                      blames the layer that actually got it wrong.
    #
    # Nothing about whether the request works changes between the last two; what changes is
    # which half a reader is sent to debug. `engine_probe` is explicit that this matters —
    # "confusing it with an engine failure is how a day gets spent debugging the wrong half"
    # — and the rule is `coverage_probe.judge`'s own, which has flagged it as FORCED since
    # the corpus was written while production had no equivalent.
    dropped = []
    kept = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 3, "name": "prod"}]}, "",
        dropped)
    check("several members cannot share one identity, so the goal is refused", kept == [])
    check("and the refusal says so in the operator's terms, not the writer's",
          len(dropped) == 1 and "no world has that" in dropped[0])
    check("the name is never STRIPPED to leave a satisfiable count — the withdrawn rule",
          not any(g.get("eq") == 3 and "name" not in g.get("select", {}) for g in kept))

    # A MEMBERSHIP LIST IS NOT THIS. Three names for three members is an ordinary request.
    trio = to_goals({"goals": [{"goal": "count", "select": {"kind": "vm", "where": [
        {"attr": "name", "value": "n1"}, {"attr": "name", "value": "n2"},
        {"attr": "name", "value": "n3"}]}, "amount": 3, "name": ""}]},
        "make sure n1, n2 and n3 exist")
    check("three members with three names is untouched",
          trio and trio[0]["eq"] == 3 and isinstance(
              trio[0]["select"].get("name"), dict))

    one = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "vm"}, "amount": 1, "name": "box1"}]}, "")
    check("a count of ONE still names its member", one[0]["select"].get("name") == "box1")


def test_a_link_the_manifest_does_not_have_is_not_a_link():
    """`per` took the model's `link` on trust, and the model supplies nonsense.

    "launch every vm that is currently stopped" came back as `per vm make=vm link=status` —
    one machine created per machine, tied by a STATUS. The manifest answers this exactly, so
    a link it cannot derive is not a link the world has, whoever wrote it down.
    """
    print("[repair] a link is derived from the manifest, never taken on trust")
    junk = to_goals({"goals": [
        {"goal": "per", "select": {"kind": "vm"}, "make": "vm", "link": "status"}]}, "")
    check("a link the manifest cannot derive is refused", junk == [])

    good = to_goals({"goals": [
        {"goal": "per", "select": {"kind": "vm"}, "make": "snapshot"}]}, "")
    check("and one it CAN derive is supplied without being asked",
          good and good[0].get("link") == "vm")


def test_the_same_goal_twice_is_one_goal():
    """Repairs converge, so duplicates arrive with neither half wrong."""
    print("[repair] the same goal twice is one goal")
    got = to_goals({"goals": [
        {"goal": "count", "select": {"kind": "network"}, "amount": 1, "name": "lab"},
        {"goal": "every", "select": {"kind": "network"}, "attr": "name", "value": "lab"},
    ]}, "set up a network named lab")
    check("two goals that repaired to the same shape become one", len(got) == 1)


# THE ENTRY POINT BELONGS AT THE BOTTOM, and this is not style. It sat in the MIDDLE of this
# file, and `main()` ends in `sys.exit` — so when the suite was run directly every test
# defined below it was never even defined, let alone called. Two were:
# `test_a_value_slot_filled_with_prose_is_refused`, which guards the worst outcome the
# production probe measures, and the drop-reporting test above. Found 2026-08-03 by adding a
# test and watching the total not move — the exact symptom `_suite.py`'s own docstring names
# as the only one this failure mode has.


def test_a_value_outside_a_closed_set_matches_nothing_and_is_refused():
    """THE WORST SHAPE A BAD FILTER TAKES, measured on rung 12's paraphrase 3 of 3.

    *"make a restore point for each machine that is currently up"* — the model answers
    `status = 'up'`. But `attr_values` declares the states a machine can be IN, and `up` is
    not one, so the filter matches NOTHING for ever. A goal about nothing is VACUOUSLY TRUE:
    the run plans zero snapshots, closes DONE, and the world disagrees. DONE_BUT_FALSE, which
    is the only outcome the production probe calls unacceptable.

    REFUSED RATHER THAN TRANSLATED. `up` plainly means `running` to a person, and mapping it
    would be this module guessing what the operator meant — the job it exists not to have. A
    declared synonym is a manifest row and the operator's call; an inferred one is how a
    vocabulary starts.

    AND NOT REPAIRED BY STRIPPING IT, which is the trap next door: dropping the filter turns
    "snapshot the RUNNING ones" into "snapshot every machine", a request that CAN be met and
    is a different one. Measured 2026-08-03 at 6 -> 12 false successes.
    """
    print("[extract] a value the world cannot hold is not a filter")
    from engines.extract import unusable
    check("a state outside the declared set is refused",
          "not one of" in (unusable({"kind": "vm", "status": "up"}) or ""))
    check("and a declared one is not",
          unusable({"kind": "vm", "status": "running"}) is None)
    # A REFERENCE IS NOT A VALUE YET. `$state` resolves at run time, so judging it here would
    # refuse every procedure that takes its own filter as a parameter.
    check("a $reference is left alone", unusable({"kind": "vm", "status": "$state"}) is None)
    # AN OPEN ATTRIBUTE IS STILL OPEN. Only an attribute the manifest CLOSES is judged.
    check("a label may be any word, including that one",
          unusable({"kind": "vm", "label": "up"}) is None)

    # `per` WAS NEVER JUDGED AT ALL, which is why this reached the writer. It carries a set of
    # members exactly as `every` does.
    # THE FIXTURE MOVED OFF `up` ON 2026-08-05 AND THE TEST DID NOT CHANGE. `up` WAS the
    # impossible value here — rung 12's paraphrase, refused 3 of 3 — until the operator
    # DECLARED it as a synonym for `running` (`value_aliases` on the vm kind), at which point
    # it resolves before this guard ever sees it and the goal rightly survives. What is being
    # asserted is that a `per` over a filter the world cannot hold is dropped WHOLE, so the
    # fixture needs a value that is still undeclared, not the one that stopped being.
    dropped = []
    raw = {"goals": [{"goal": "per",
                      "select": {"kind": "vm",
                                 "where": [{"attr": "status", "value": "hibernating"}]},
                      "make": "snapshot"}]}
    goals = to_goals(raw, "make a restore point for each machine that is hibernating",
                     dropped)
    check("a `per` over an impossible filter is dropped, whole", goals == [])
    check("and the drop is reported, so the request is not half-read",
          len(dropped) == 1 and "matches nothing" in dropped[0])

    # A DECLARED SYNONYM RESOLVES BEFORE THIS GUARD RUNS, which is the whole difference
    # between a manifest row and this module guessing. `unusable`'s own comment drew the
    # line: "`up` plainly means `running` to a person, and mapping it here would be this
    # module guessing what the operator meant… a declared synonym is a manifest row and the
    # operator's call." That row exists now, so rung 12's paraphrase translates.
    kept = []
    up = to_goals({"goals": [{"goal": "per",
                              "select": {"kind": "vm",
                                         "where": [{"attr": "status", "value": "up"}]},
                              "make": "snapshot"}]},
                  "make a restore point for each machine that is currently up", kept)
    check("a DECLARED synonym resolves to the value the world stores",
          up and up[0]["per"].get("status") == "running")
    check("and nothing is reported lost for it", kept == [])

    from planner.ir.config import canonical_value
    check("the counterpart is declared too — `down` is `stopped`",
          canonical_value("vm", "status", "down") == "stopped")
    check("a value the world does hold is left alone",
          canonical_value("vm", "status", "running") == "running")
    check("and an undeclared one is NOT invented into a legal state",
          canonical_value("vm", "status", "hibernating") == "hibernating")

    # IT MAPS A VALUE, NOT A WORD IN THE REQUEST — the table is consulted only where a
    # `where` clause already holds a value for a declared attribute. Rung 11's paraphrase
    # says "shut DOWN whichever ones don't" and nothing here touches it.
    said = []
    to_goals({"goals": [{"goal": "observe", "select": {"kind": "vm", "where": []},
                         "fact": "alive"}]},
             "check which machines respond and shut down whichever ones don't", said)
    check("a request that merely says the word is untouched", said == [])


def test_a_count_is_a_total_and_never_a_change():
    """THE WORST PROGRAM THIS SEAM HAS WRITTEN, and it was three characters of arithmetic.

    Asked to *"delete every machine labelled scratch"* the model answers `amount: -1` — a
    DELTA. `_as_count` stripped everything that was not a digit, which strips a MINUS SIGN,
    so -1 came back as 1 and the goal became `count(vm WHERE label=scratch) = 1`. Run
    against a real world by `ghost_writer.cover`:

        3 scratch machines exist  ->  remove the LABEL from 2, delete nothing, report DONE
        0 scratch machines exist  ->  CREATE a machine and label it `scratch`, report DONE

    A DELETION REQUEST THAT CREATES A MACHINE. Nothing reached `dropped`, so no layer below
    could know, and `coverage_probe` judges shapes and names so it read the row as merely
    the wrong shape.

    THE DEFECT UNDERNEATH IS THE GENERAL ONE: a value that was SAID AND NOT UNDERSTOOD was
    treated as a value that was NOT SAID. The `amount is None -> 1` default is correct and
    stays — "create a vm named alpha" really is a count of one — but it must not swallow a
    quantity the model stated and this reader could not read.
    """
    print("\n[count] a count is a total, never a change")

    from engines.extract import _as_count

    check("a signed token is not a count", _as_count("-1") is None)
    check("nor is a negative integer", _as_count(-3) is None)
    # A RANGE IS DECLINED BY THE SAME CLAUSE AND THAT IS ALSO RIGHT: `3-5` is not 35.
    check("nor is a range", _as_count("3-5") is None)
    # AND THE CASE THE DIGIT-STRIP EXISTS FOR STILL WORKS — `/2` is how this model writes
    # "exactly two", and it carries no sign.
    check("`/2` is still two", _as_count("/2") == 2)
    check("zero is a number, not an absence", _as_count(0) == 0)
    check("and an ordinary count is untouched", _as_count("3") == 3)

    def one(amount, request="delete every machine labelled scratch"):
        g = {"goal": "count", "select": {"kind": "vm",
                                         "where": [{"attr": "label", "value": "scratch"}]},
             "name": ""}
        if amount is not None:
            g["amount"] = amount
        lost = []
        return to_goals({"goals": [g]}, request, lost), lost

    goals, lost = one(-1)
    check("a goal asking for -1 of something is refused, not rounded", goals == [])
    check("and the refusal names the value that defeated it",
          len(lost) == 1 and "-1" in lost[0])

    # ZERO IS THE SHAPE THE GRAMMAR NOW FORCES, and it is the correct reading of a deletion.
    goals, lost = one(0)
    check("zero survives, because that is how deletion is said",
          goals == [{"shape": "count", "select": {"kind": "vm", "label": "scratch"},
                     "eq": 0}])

    # THE DEFAULT IS NOT COLLATERAL DAMAGE. An ABSENT amount still means one.
    goals, lost = one(None, "create a vm labelled scratch")
    check("an amount nobody stated still defaults to one",
          len(goals) == 1 and goals[0]["eq"] == 1 and lost == [])


def test_the_grammar_forbids_a_negative_count():
    """MAKE THE WRONG ANSWER UNREPRESENTABLE, which is the half a repair cannot do.

    `minimum: 0` is asserted on the schema the model is actually sent. It was verified to
    REACH the decoder rather than assumed — asked point blank for -1 under this constraint,
    ollama returns 0 — and that check matters here more than usual, because this file's own
    history is a `pattern` that ollama accepted and ignored for a month.
    """
    from engines.extract import schema

    sc = schema(request="delete every machine labelled scratch")
    branches = ((sc.get("properties") or {}).get("goals") or {}).get("items") or {}
    counts = [b for b in (branches.get("oneOf") or ())
              if "count" in (((b.get("properties") or {}).get("goal") or {}).get("enum") or ())]
    check("the count branch is offered", len(counts) == 1)
    amount = (counts[0].get("properties") or {}).get("amount") or {}
    check("and its amount cannot be negative", amount.get("minimum") == 0)
    check("and it is still an integer", amount.get("type") == "integer")


def test_a_name_the_request_never_says_is_not_a_name():
    """THE DEFECT THAT SURVIVES EVERY SHAPE GATE, measured 2026-08-05.

    A clause the model cannot express does not disappear — it MOVES. `reach` was narrowed on
    08-04 and the pressure went to `per`; gating `per` sent it to `count`, arriving as
    `count(vm WHERE name='unresponsive') = 0` for *"stop the ones that do not answer"*.
    THREE SHAPES, ONE CLAUSE, and each hop landed somewhere quieter: a spurious `reach` and a
    spurious `per` were both dropped by rules that already existed, while an invented name is
    neither dropped nor vacuous — it ASSERTS something, so the writer plans four calls for it
    and the run closes DONE.

    THIS GUARD DOES NOT CARE WHICH SHAPE THE CLAUSE LANDS IN, which is the property every
    shape gate lacks. A name is an IDENTITY — the same word in the request and in the goal —
    which is exactly `clause_ledger.open_ledger`'s argument for its anchors.

    IT DROPS RATHER THAN STRIPS, and that is decided by the measured hazard already recorded
    in this module: stripping would leave `count(vm WHERE name='unresponsive') = 0` as
    `count(vm) = 0`, which is DELETE EVERY MACHINE. Stripping is only safe when what remains
    is still the whole truth, and here the name was the whole subject.
    """
    print("\n[decline] a name the request never says is not a name")

    from engines.extract import invented

    R = "ping every vm and stop the ones that do not answer"
    check("a minted identity is refused", bool(invented({"kind": "vm",
                                                         "name": "unresponsive"}, R)))
    check("and the reason names the value",
          "unresponsive" in (invented({"kind": "vm", "name": "unresponsive"}, R) or ""))

    # THE WHOLE GOAL GOES, because the smaller statement left behind is a catastrophe.
    dropped = []
    goals = to_goals({"goals": [{"goal": "count", "select": {"kind": "vm", "where": []},
                                 "amount": 0, "name": "unresponsive"}]}, R, dropped)
    check("the goal is dropped whole, never stripped down to a bare count", goals == [])
    check("and the drop is reported so the request is not half-read", len(dropped) == 1)

    # ── THE CONTROLS. This must not start refusing names the operator DID give. ───────────
    check("a name the request states survives",
          invented({"kind": "vm", "name": "web"}, "shut down web and db") is None)
    check("case is not the test",
          invented({"kind": "vm", "name": "WEB"}, "shut down web and db") is None)
    check("nor is punctuation — a hyphenated machine is one word in both",
          invented({"kind": "vm", "name": "payload-test"},
                   "take payload-test off every network") is None)
    check("a reference the request names survives",
          invented({"kind": "vm", "network": "lab"}, "put web on lab") is None)
    check("every member of a stated list survives",
          invented({"kind": "vm", "name": {"in": ["n1", "n2", "n3"]}},
                   "n1, n2 and n3 must reach each other") is None)
    check("but one ghost in the list condemns it",
          bool(invented({"kind": "vm", "name": {"in": ["n1", "ghost"]}},
                        "n1, n2 and n3 must reach each other")))

    # AN ATTRIBUTE VALUE IS NOT AN IDENTITY. A label is free text and need never appear as a
    # word — "tag every windows machine as target" means `label = 'target'` whatever the
    # sentence looks like.
    check("a label is not judged", invented({"kind": "vm", "label": "prod"},
                                            "tag every windows machine") is None)
    check("and neither is a state", invented({"kind": "vm", "status": "running"},
                                             "launch everything") is None)

    # A `$reference` IS THE HARNESS' OWN, substituted INTO the request by `stand_in`, so it
    # is not the model's invention to answer for.
    check("a stand-in is not an invention",
          invented({"kind": "vm", "name": "$box"}, "a vm named $box") is None)

    # NO REQUEST MEANS NO OPINION. Callers that pass goals with no sentence behind them —
    # every test fixture and every direct caller — must not have their names refused.
    check("with no request it declines to judge",
          invented({"kind": "vm", "name": "anything"}, "") is None)


def test_repairs_run_before_refusals_and_the_order_is_declared():
    """THE ORDERING BUG THAT COST FOUR RUNGS, pinned so it cannot come back quietly.

    `_keep` used to be one repair and three refusals as a run of `if`s, in whatever order
    they had been added. The order was LOAD-BEARING and written down nowhere: on 2026-08-05 a
    refusal was added BEFORE the repair and rungs 4, 7, 13 and 14 went DONE -> UNTRANSLATED,
    every one for a name the repair was about to fix. Invisible in review; it took a full
    ladder arm to find.

    The phases are now DATA — `_REPAIRS` then `_REFUSALS` — so a rule in the wrong tuple is a
    category error a reader can see. This asserts the split, the order, and the behaviour the
    order exists to protect.
    """
    print("\n[pipeline] repairs run before refusals, and the phases are declared")
    from engines.extract import (_REFUSALS, _REPAIRS, _refuse_invented,
                                 _refuse_shared_identity, _repair_unusable)

    check("the repair phase holds the repair", _REPAIRS == (_repair_unusable,))
    check("and the refusals are declared separately",
          _REFUSALS == (_refuse_invented, _refuse_shared_identity))
    check("no rule appears in both phases", not set(_REPAIRS) & set(_REFUSALS))

    # EVERY RULE HAS ONE SIGNATURE, which is what makes them testable alone and the pipeline
    # a loop. Each returns `(goal, sel, why)`; a refusal hands back what it was given.
    g = {"shape": "count", "select": {"kind": "vm"}, "eq": 1}
    for rule in _REPAIRS + _REFUSALS:
        got = rule(dict(g), {"kind": "vm"}, "make a vm")
        check(f"{rule.__name__} returns (goal, sel, why)",
              isinstance(got, tuple) and len(got) == 3)

    # THE BEHAVIOUR THE ORDER PROTECTS. `every` is a schema word `_echoed` knows, so the
    # repair strips it and the count survives — and the invented-name refusal must never see
    # it, because a name absent from the request is exactly what it would object to.
    dropped = []
    got = to_goals({"goals": [{"goal": "count", "select": {"kind": "vm", "where": []},
                               "amount": 5, "name": "every"}]},
                   "create 5 vms and put them all in a network", dropped)
    check("a repairable name is repaired, not refused as invented",
          got and got[0]["eq"] == 5 and "name" not in got[0]["select"])
    check("and nothing is reported lost", dropped == [])

    # AND WHAT SURVIVES THE REPAIR IS STILL REFUSED. `unresponsive` is well-formed, not
    # echoed and not prose, so no repair touches it — and the request never says it.
    lost2 = []
    to_goals({"goals": [{"goal": "count", "select": {"kind": "vm", "where": []},
                         "amount": 0, "name": "unresponsive"}]},
             "ping every vm and stop the ones that do not answer", lost2)
    check("a name no repair explains is still refused", len(lost2) == 1)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "extract repairs"))


if __name__ == "__main__":
    main()
