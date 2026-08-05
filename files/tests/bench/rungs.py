"""The complexity ladder: goals of strictly increasing reasoning load, each with an
objective checker read off the SimWorld.

The ladder exists to locate the CLIFF — the rung where the weak local model stops coping —
so the harness work has a measurement instead of an impression. Rungs 1-3 are the control
(they should stay green; a regression there means a fix broke something that worked).
Rungs 4+ are the frontier.

Each rung names the reasoning load it ADDS over the one below:

  1  one action, fully specified
  2  two ordered actions on one entity
  3  an action whose prerequisite must exist first
  4  an unnamed set, distributive ops over it, and an assurance clause
  5  a FILTERED collective — act on the subset matching a condition, not on everything
  6  a PARTITION — two groups, treated differently, kept apart
  7  CONVERGENCE to a spec — diff current against desired and both add and remove
  8  a general rule with an EXCEPTION — "all of them, except this one"
  9  DIAGNOSIS — the goal states an end-state; find which member is wrong and fix it
 10  a derived set — clone from a source, then act on the results
 11  RESULT-DEPENDENT action — the condition is a call's ANSWER, not a queryable attribute
 12  a SECOND RESOURCE KIND — the manifest's extensibility claim, measured
 13  IDEMPOTENT RE-ENTRY — the goal is already satisfied; doing it again must not duplicate

RUNGS 11-13 WERE ADDED 2026-07-26 TO MEASURE THE LANGUAGE, NOT THE MODEL. The first ten
escalate on structure and the procedure language carries them to rung 7. These three test
things no earlier rung asks for, and two of them the four-node IR provably CANNOT express
— there is no conditional and no way to bind a call's result. They are expected to fail
by construction, and that is their value: a rung that fails because the NODE SET is short
tells you something a rung that fails because the model is weak does not.

A rung may seed starting state (`setup`); a goal about existing VMs needs VMs to exist.
The seeded state is part of the problem: rung 5 is only a filter if something is already
running, and rung 7 is only a convergence if some labels are already right.

STANDING PRINCIPLE (the user's, explicit): this is a BENCHMARK OF PROGRESS, NOT A TARGET.
Never game it — no scripting the loop, no seeding sub_goals, no swapping in a bigger model
to make a rung go green. Improve the system genuinely and let the ladder measure.
"""
from typing import Callable, List, NamedTuple, Optional

from .sim_world import SimWorld


class Rung(NamedTuple):
    n: int
    name: str
    goal: str
    check: Callable[[SimWorld], bool]     # objective pass/fail, read off world state
    why: str                              # what reasoning load this rung adds
    setup: Optional[Callable[[SimWorld], None]] = None    # starting state, if any
    # SAME capability, deliberately DIFFERENT wording. A rung passes on one phrasing and
    # fails on another when the thing that made it pass was a PATTERN rather than an
    # ability — not hypothetical: rung 6 passed while "set up three machines tagged alpha"
    # created nothing, because `set up` was missing from one regex. `--paraphrase` grades
    # the capability instead of the sentence.
    paraphrase: Optional[str] = None
    # COST BASELINES. `minimum` = the tool calls the goal logically requires; `best` = the
    # lowest we have actually MEASURED. The checker grades world state only, so without
    # these a run can double its cost and still print PASS — which is exactly what
    # happened: rung 4 was measured at 17/done on 5813493 and had silently become 35/partial
    # by the next day, because nothing compared the number to anything. The day's own lesson
    # was that the biggest wins came from measuring COST, not pass/fail; this records it.
    #
    # These are a REGRESSION TRIPWIRE, never a target. Per the standing principle above:
    # do not tune the harness to make a number go down. A rung that gets cheaper because
    # the system genuinely got better is progress; a rung that gets cheaper because
    # something was special-cased for it is the benchmark being gamed. Cost is reported
    # separately from pass/fail for exactly that reason.
    minimum: Optional[int] = None
    best: Optional[int] = None
    # VERIFIED — the calls the GHOST WRITER actually makes, on every rung, checked by that
    # rung's own function. Not an estimate and not a target: a number produced by running
    # deterministic code and grading the result.
    #
    # IT IS A SEPARATE FIELD FROM `best` ON PURPOSE. `best` prices a MODEL'S program, and it
    # is deliberately loose because a model may spend calls VERIFYING its own work — rung 4's
    # own comment says so, and setting best=16 there would flag every program that checks
    # itself. The writer grounds with ENSUREs, which cost no calls, so its number is not
    # comparable and overwriting `best` with it would buy cheapness by punishing
    # verification. That is the pricing-versus-gating mistake this file already warns about,
    # one field over.
    #
    # WHAT IT IS FOR: a regression tripwire on the PLANNER. The writer is deterministic, so
    # any change to these numbers is a change in what the planner does, and
    # `test_verified_costs_still_hold` says which rung moved and in which direction.
    verified: Optional[int] = None
    # WHAT THE GOAL ASKS FOR, clause by clause — the [clause ledger]'s record, opened
    # before the author writes anything. Each is {"text", "anchors"}: `text` restates one
    # demand in the goal's own terms, `anchors` are literal tokens the plan must mention.
    #
    # THIS IS NOT A SECOND DEFINITION OF THE GOAL, and the guard is mechanical rather than
    # a promise: `open_ledger` DROPS any anchor that does not appear in the goal text being
    # asked, so the ledger can only ever point at words the operator actually used. It says
    # WHAT IS MISSING, never what to write. `test_rung_demands_are_honest` holds the line.
    #
    # WHY THEY EXIST, measured 2026-07-29: three rungs were answered by dropping a clause
    # outright — rung 8 lost `except db`, rung 10 lost `and launch all of them`, rung 11
    # lost `stop the ones that do not answer` — while the validator objected about
    # something else entirely and both repair rounds went there. The operator: *"if clauses
    # are gone, that's a LEDGER issue not a decomp issue."*
    #
    # A rung with none declared is not policed, which is deliberate: an empty list must
    # mean "not asked", never "nothing was missing". Same three-valued rule as `alive`.
    demands: Optional[List[dict]] = None


def _vm(w: SimWorld, name: str, status: str = "stopped", labels=(), nets=()):
    w.vms[name] = w.blank_vm(status=status, labels=labels, nets=nets)
    for n in nets:
        w.nets.add(n)


# ── 1-4: the original ladder ──────────────────────────────────────────────────
def _r1(w): return "alpha" in w.vms
def _r2(w): return w.vms.get("beta", {}).get("status") == "running"
def _r3(w): return "lab" in w.nets and "lab" in w.vms.get("web", {}).get("nets", set())


def _r4(w):
    """The TIGHTENED checker: the world's own reach predicate, not two independent counts.
    ≥5 VMs carrying 'fleet' AND all of them on one COMMON network. The loose version
    (count netted, count labelled) passed 5-on-netA + 5-on-netB — zero reachable pairs."""
    return w.reach("fleet", minimum=5)


# ── 5: filtered collective ────────────────────────────────────────────────────
def _s5(w):
    _vm(w, "web", "stopped"); _vm(w, "db", "running"); _vm(w, "cache", "stopped")


def _r5(w):
    """Every VM running. The filter is the point: `db` was ALREADY running, so a model
    that launches everything indiscriminately still passes — but one that launches
    nothing, or only the first, does not."""
    return len(w.vms) >= 3 and all(v["status"] == "running" for v in w.vms.values())


# ── 6: partition ──────────────────────────────────────────────────────────────
def _r6(w):
    """Two groups, each internally reachable, and SEPARATE from each other. The
    separation is what makes this more than two rung-4s: putting all five on one network
    satisfies both reach checks and must still fail."""
    if not (w.reach("red", 3) and w.reach("blue", 2)):
        return False
    return not w.common_networks(w.members("red") + w.members("blue"))


# ── 14: destruction, and the restraint that goes with it ──────────────────────
def _s14(w):
    """FIVE MACHINES, TWO OF THEM RUNNING, AND THREE HAVE TO GO.

    THE REQUEST IS THE ONE THE COVERAGE NOTE CITED: *"make sure there are exactly two
    machines"* against the real lab plans SEVEN deletions including vm-orchestrator. Nothing
    in the measured set resembled it until now.

    RUNNING ON PURPOSE. `delete_requires` declares that a machine must be stopped before it
    can go, and a bare deleter emits a call that can never succeed — measured on the lab,
    where the machine a program minted for its own use survived every run. A rung whose
    machines were all already stopped would never exercise the derived precondition.
    """
    _vm(w, "alpha")
    _vm(w, "beta", status="running")
    _vm(w, "delta")
    _vm(w, "epsilon", status="running")
    _vm(w, "gamma")


def _r14(w):
    """Two left, AND THE RIGHT TWO. Deleting the whole lab satisfies a count of two never;
    deleting four and creating one satisfies it dishonestly, so the survivors are named.

    THE SURVIVORS ARE THE DETERMINISTIC SLICE — the writer removes off the end of a SORTED
    list, so the same request against the same world always removes the same machines. That
    is what makes a destructive program reviewable before it runs, and it is the property
    worth pinning: a checker that only counted would pass a writer that chose at random.
    """
    return set(w.vms) == {"alpha", "beta"}


# ── 7: convergence to a spec ──────────────────────────────────────────────────
def _s7(w):
    _vm(w, "one", labels=["prod"]); _vm(w, "two", labels=["prod"])
    _vm(w, "three"); _vm(w, "four")


def _r7(w):
    """EXACTLY three, from a starting point of two. Requires reading what is already
    true and adding only the difference — over-labelling all four fails."""
    return len(w.members("prod")) == 3


# ── 8: a rule with an exception ───────────────────────────────────────────────
def _s8(w):
    for n in ("app1", "app2", "app3", "db"):
        _vm(w, n)


def _r8(w):
    """Everything on `core` EXCEPT db, which belongs on `dmz` and not on core. The
    exception has to survive the distributive step that handles the rest."""
    others = [n for n in w.vms if n != "db"]
    if not others or not all("core" in w.vms[n]["nets"] for n in others):
        return False
    return "dmz" in w.vms.get("db", {}).get("nets", set()) and "core" not in w.vms["db"]["nets"]


# ── 9: diagnosis ──────────────────────────────────────────────────────────────
def _s9(w):
    w.nets.add("mesh0")
    _vm(w, "n1", nets=["mesh0"]); _vm(w, "n2", nets=["mesh0"]); _vm(w, "n3")


def _r9(w):
    """All three sharing one network. The goal names no culprit: two are already wired
    and the third is not, so the work is finding WHICH one is wrong."""
    return bool(w.common_networks(["n1", "n2", "n3"]))


# ── 10: a derived set ─────────────────────────────────────────────────────────
def _s10(w):
    _vm(w, "golden", "stopped")


def _r10(w):
    """Three clones of golden, all running. The set does not exist until the model makes
    it, and the follow-up action applies to members it chose the names for."""
    clones = [n for n in w.vms if n != "golden"]
    return len(clones) >= 3 and all(w.vms[n]["status"] == "running" for n in clones)


# ── 11: result-dependent action ───────────────────────────────────────────────
def _s11(w):
    for n in ("alpha", "beta", "gamma", "delta"):
        _vm(w, n, "running")
    w.unreachable |= {"beta", "delta"}          # knowable ONLY by pinging


def _r11(w):
    """Exactly the unreachable ones stopped, the reachable ones left alone.

    Which VMs are unreachable is NOT a queryable attribute — the world knows, the
    registry does not, so no SELECT can find them. The program must ping and act on the
    ANSWER. Stopping everything fails, and so does stopping nothing.

    A MISSING MACHINE IS A FAILED RUNG, NOT A CRASH. This indexed `w.vms[n]` directly, so a
    program that DELETED a machine raised KeyError out of the checker and took the whole run
    down with it — 2026-08-01, at cell 64 of 78, destroying a measurement that had been
    running for an hour. It is the same defect `author_probe` records against the executor
    ("a crashing program fails its own rung and nothing else; it used to take the whole
    column with it"), arriving in the one place nobody had hardened: the grader itself. A
    checker that can crash can erase the evidence of what it was grading."""
    def status(n):
        return (w.vms.get(n) or {}).get("status")
    return (all(status(n) == "stopped" for n in ("beta", "delta"))
            and all(status(n) == "running" for n in ("alpha", "gamma")))


# ── 12: a second resource kind ────────────────────────────────────────────────
def _s12(w):
    _vm(w, "web", "running"); _vm(w, "db", "running"); _vm(w, "cache", "stopped")


def _r12(w):
    """A snapshot of every RUNNING vm, and none of the stopped one. Snapshots are a third
    kind — neither vm nor network — so this measures whether a new resource type really is
    one manifest row, or whether it needs language code."""
    snapped = {v["vm"] for v in w.snapshots.values()}
    return snapped == {"web", "db"}


# ── 13: idempotent re-entry ───────────────────────────────────────────────────
def _s13(w):
    """The goal ALREADY HOLDS. Five labelled vms, one shared network, nothing to do."""
    w.nets.add("net1")
    for i in range(1, 6):
        _vm(w, f"vm{i}", "stopped", labels=["fleet"], nets=["net1"])


def _r13(w):
    """Still exactly five. Re-running a satisfied goal must not duplicate the work — the
    measured 5 -> 10 -> 15 cascade is what this rung exists to catch, and no earlier rung
    ever runs against a world where the goal is already true.

    THE WORDING WAS REWRITTEN 2026-07-28, because the rung was scoring the wrong thing.

    It used to carry rung 4's goal VERBATIM — "create 5 vms, ..." — with only the seeded
    world telling the two apart. So one sentence had to mean "make five" on rung 4 and
    "make none" on rung 13, and nothing in the prompt said which. The operator: *"the
    prompt LITERALLY asks it to create another 5 vms, if it's supposed to fetch them you
    need to tell it to fetch, not create."* That is right, and the benchmark undercut
    itself: rung 7 already states an end-state goal ("make sure exactly 3 vms carry the
    'prod' label"), so an idiom existed and this rung did not use it.

    BOTH COLUMNS WERE MEASURING DIFFERENT TASKS, which is how the mistake stayed hidden:

      literal    "create 5 vms"      -> NEW AMOUNT(5), ten machines, FAIL
      paraphrase "spin up five ..."  -> read as launch_vm on vm1..vm5 read out of the
                                        CURRENT STATE block, creates nothing, PASS 3/3

    The paraphrase passed on a VOCABULARY ACCIDENT — "spin up" meaning start-an-existing-
    machine — never once reasoning about re-entry. A column passing for a reason the rung
    does not measure is worse than a column failing.

    "TAKE 5 VMS" RATHER THAN "MAKE SURE THERE ARE EXACTLY 5". The obvious repair is the
    end-state idiom, and it LEAKS: "make sure there are exactly 5" hands over the counting
    that is the thing being tested, which is the same objection mutate.py already raises
    against rung 7's paraphrase. `take` names the set without prescribing how to obtain
    it, so creating five more is visibly not what was asked while nothing hints at
    counting.

    AND IT SURVIVES AN EMPTY LAB, which was my objection to it and was wrong. The
    operator: *"if there weren't, the achieve would catch it and it should fix it by
    creating 5 vms."* The ACHIEVE does catch it — an end-state goal over a lab that lacks
    the machines comes back `unachieved`. The correction is only half automatic, and the
    half that is not is worth knowing: `derive()` closes a count gap by adding or removing
    LABELS and explicitly refuses to create resources ("creating them is a bigger decision
    than closing a gap, so leave it to the model"). So the gap is closed by the REVISION
    round asking the author, not by the harness. Which means the prompt's promise — "a
    program that is nothing but an achieve is a legal way to state a goal and let the
    harness plan it" — holds for labels and not for creation.

    COST OF THE CHANGE, stated because it is real: the two rungs no longer share a
    sentence, so "same words, different world" stops being available as a comparison.
    """
    return len(w.vms) == 5 and w.reach("fleet", minimum=5)


RUNGS: List[Rung] = [
    Rung(1, "single", "create a vm named alpha", _r1,
         "one action, fully specified", None,
         "spin up a machine and call it alpha",
         minimum=1, best=2, verified=1),          # 1 create; the measured run also lists to ground itself
    Rung(2, "sequential", "create a vm named beta and then launch it", _r2,
         "two ordered actions on one entity", None,
         "make a box called beta, then start it up",
         minimum=2, best=2, verified=2),          # create + launch
    Rung(3, "dependency-chain", "create a network called lab and a vm named web, then put web on lab", _r3,
         "an action whose prerequisite must exist first", None,
         "set up an isolated network named lab, provision a machine called web, and connect web to it",
         minimum=3, best=7, verified=3),          # create net + create vm + attach
    Rung(4, "collective-loop",
         "create 5 vms, put them all in a network, give them all the 'fleet' label, "
         "and make sure they all ping each other", _r4,
         "an unnamed set, three distributive ops over it, and an assurance clause", None,
         "spin up five machines, wire them together on one private network, tag every one of "
         "them 'fleet', and confirm each can reach the others",
         # RE-EARNED 2026-07-29 FROM A HAND-VERIFIED PROGRAM, which is the only honest
         # source for a cost baseline — one learned from observed passing runs certifies
         # whatever the model already does (rung 13's earned baseline came out 16, the
         # exact wasteful program, against a verified best of 0-5).
         #
         # The old 17 was 5 creates + 1 net + 5 attaches + 5 labels + ONE ping, and that
         # single ping is incoherent: it establishes reach for nobody. Two hand-written
         # correct programs were priced instead:
         #
         #   16  create + net + label/attach + ACHIEVE REACH        passes the CHECKER
         #   21  the same, plus a probe per member                  passes IN PRODUCTION
         #
         # THE 16-CALL PROGRAM IS PASSING ON A TECHNICALITY. The bench's reach asks only
         # whether the members share a network; production's ALSO requires each to have
         # been probed, so that program would report `reach is unestablished` against the
         # real lab. Setting best=16 would flag every program that verifies its own work
         # as over budget — the cost signal pressuring authors to DROP verification, in a
         # system whose one rule is that unverified is not done.
         #
         # So `best` is the cheapest program correct in BOTH regimes, and `minimum` is the
         # logical floor for the state change alone.
         minimum=16, best=21, verified=21),
    Rung(5, "filtered-collective", "launch every vm that is currently stopped", _r5,
         "act on the SUBSET matching a condition, not on everything", _s5,
         "start up any machine that isn't already running", verified=2),
    Rung(6, "partition",
         "create 3 vms labelled 'red' and 2 vms labelled 'blue', put the red ones together "
         "on their own network, and put the blue ones on a different network", _r6,
         "two groups, treated differently, and kept apart", None,
         "set up three machines tagged 'red' and two tagged 'blue'; the red group must share "
         "one private network, and the blue group a separate one",
         # 5 creates + 2 nets + 5 attaches + 5 labels. 30 was the measured cost at the
         # 07-25 close, with the redundancy (14 attaches where 5 would do) a known problem.
         minimum=17, best=30, verified=22),
    Rung(7, "convergence", "make sure exactly 3 vms carry the 'prod' label", _r7,
         "diff what IS against what is wanted, and change only the difference", _s7,
         "there should end up being precisely three machines tagged prod, no more and no fewer", verified=1),
    Rung(8, "exception",
         "put every vm on a network called core, except db — db goes on a network "
         "called dmz instead", _r8,
         "a general rule with one carve-out that must survive it", _s8,
         "connect all the machines to a network named core, apart from db, which belongs on dmz",
         # THE ONLY RUNG WITH DEMANDS DECLARED, and the scope is deliberate. Clause loss
         # was measured on the AUTHOR path here and only here: para:8's program, 3/3,
         # never mentions `db` at all — it puts EVERY vm on core and then loops over
         # app1/app2/app3 for dmz, which is the carve-out enumerated by hand and inverted.
         # The validator objected `select must name a kind`, the least interesting of its
         # three defects, and both repair rounds went there.
         #
         # The other clause losses seen on 2026-07-29 (rungs 10 and 11 dropping `and
         # launch all of them` / `stop the ones that do not answer`) were measured on the
         # ATOMICITY ROUTER, a different surface, and both rungs currently PASS here. So
         # declaring demands for them would be reasoning by analogy onto a passing cell —
         # the invented-rather-than-earned mistake the sanitiser's own doc refuses, where
         # a wrong demand costs a false objection on a rung that works.
         demands=[
             {"text": "put every vm on a network called core", "anchors": ["core"]},
             {"text": "db goes on a network called dmz", "anchors": ["db", "dmz"]},
         ], verified=6),
    Rung(9, "diagnosis", "make sure n1, n2 and n3 can all ping each other", _r9,
         "the goal names an end-state; find WHICH member breaks it", _s9,
         "n1, n2 and n3 should all be able to reach one another — sort out whatever is stopping that", verified=4),
    Rung(10, "derived-set", "clone golden into 3 new vms and launch all of them", _r10,
         "a set that does not exist until the model makes it, then acted on", _s10,
         "take a copy of golden three times over and boot every copy", verified=6),
    Rung(11, "result-dependent",
         "ping every vm and stop the ones that do not answer", _r11,
         "the condition is a call's ANSWER, not an attribute anything can query", _s11,
         "check which machines respond and shut down whichever ones don't", verified=6),
    Rung(12, "second-kind",
         "take a snapshot of every running vm", _r12,
         "a resource type that is neither vm nor network — the manifest claim, measured",
         _s12,
         "make a restore point for each machine that is currently up", verified=2),
    # NEITHER COLUMN MAY SAY create OR spin up — see _r13. The first forces the wrong
    # answer; the second was silently read as launch_vm and passed without ever meeting
    # the question. Both wordings now NAME the set rather than prescribe how to get it,
    # and neither mentions a count, so the model is told what is wanted and nothing about
    # how to check it.
    Rung(13, "idempotent-reentry",
         "take 5 vms, put them all in a network, give them all the 'fleet' label, "
         "and make sure they all ping each other", _r13,
         "the goal ALREADY holds — doing it again must change nothing", _s13,
         "use five machines, wire them together on one private network, tag every one "
         "of them 'fleet', and confirm each can reach the others", verified=5),
    # ── 14: the irreversible act, which the ladder had never once exercised ────────
    Rung(14, "destruction",
         "make sure there are exactly two machines left", _r14,
         "the one act that cannot be undone, and the one that must not overreach", _s14,
         "cut the lab down to two machines and no more", verified=4),
]
