"""door_key.py — WHERE EACH REQUEST SHOULD GO, WRITTEN DOWN BEFORE ANYTHING CAN ROUTE IT.

    PYTHONPATH=. python3 -m tests.bench.door_key           # print the key
    PYTHONPATH=. python3 -m tests.bench.door_key --check   # the key still describes the world

# ⇒⇒ WHY THIS FILE EXISTS AND WHY IT IS EMPTY OF LOGIC

N1 is about to gain a DOOR — the thing that decides which regime a request wants before any
of them runs. **A key written after the router is not a key, it is a description of the
router.** So this is committed first, imports nothing it grades, and is allowed to be wrong: a
disagreement between this file and the door is a conversation, not a bug report, and which
file gets edited is decided case by case rather than by whichever came second. That is
`sentence_key`'s rule, and writing that one first killed a rule before a line of the reader
existed ([[gorgon-handover-2026-08-16]]).

⇒ **THE DOOR PICKS *WHERE*, NEVER *WHETHER*.** Legality belongs to gate 3, destruction to the
  consent seam, meaning to the gates. A request keyed `TOOL` here is not thereby approved —
  it is merely being sent to the place that will decide. Keying `delete the vm called n3` as
  `TOOL` says nothing about whether it should be carried out.

⇒ **AND THE PROVENANCE OF EVERY ROW IS NAMED, BECAUSE A1 IS SEALED.** These come from the
  fourteen rungs, `sentence_key`'s controls, `route_holdout`'s traps, the ladder memory's own
  worked example, `plan.py`'s measured docstrings and the manifest itself. `heldout_a1.py` was
  NOT OPENED while writing this. Any overlap is two files describing one lab, not fitting.

# ⇒⇒ THE DESTINATIONS, NAMED BY WHO VERIFIED THE ARTIFACT

The open list is explicit that N1 is [[gorgon-vague-request-ladder]] promoted, not a new idea —
*build it as the ladder or the two designs will disagree at the door.* The ladder's order is
not difficulty, it is **who verified the thing you are about to run**, descending, so the
operator's attention is spent last:

    ── OFF THE LADDER ENTIRELY. Not the lab, so no lab regime can be right ──
    SELF        Gorgon's own session, configuration, model and credentials. Nothing in the
                lab changes. `clear session`, `verbose on`, `switch models`, the password
    GOVERNANCE  the operator's own artifacts — contracts, missions, taught words, standing
                rules. Every one of them GOVERNS future acts, which is why none of them may
                be enacted by a sentence ([[gorgon-courtesy-escalates-intent]], one layer up)
    CHAT        not a request about the lab or about Gorgon at all. A greeting, a thank-you,
                a question about the world. **The model is the right answer here and only here**

    ── THE LADDER. The lab, ordered by who verified the artifact ──
    TOOL        one manifest operation, and its output or effect IS the answer.
                Verified by whoever wrote the tool, and it has a dry run
    PROCEDURE   a stored program already covers it. Verified by having been written and used —
                *"we trust already written code than newly generated one"*
    PROGRAM     assembled now, therefore UNVERIFIED — the one destination that ends in the
                operator's confirmation. A set, an ordering, a filter, a count, a postcondition
    ASK         the request does not settle which of the above it is. The operator's turn

⇒ **RUNGS 1 AND 2 ARE ONE TEST ASKED TWICE** — *does a verified artifact already cover this?* —
  differing only in where you look. Keyed as two destinations because they route to different
  code, and the ladder memory's own note says to collapse them if the door ever grows a third
  place to look.

# ⇒⇒ THE ONE RULE THIS KEY LEANS ON — TOOL vs PROGRAM, AND IT IS BORROWED ON PURPOSE

    one call, and its output or effect is the answer          -> TOOL
    a SET · an ORDERING · a FILTER · a COUNT · a POSTCONDITION -> PROGRAM

**This is `regime_probe.py`'s own three-way judgement, moved from the node to the door** — the
engine already makes exactly this choice at every node (`engine_core.py:798`) and scores 10/10
on it. Reusing it means the two designs cannot disagree; inventing a second rule at the door is
how a term drifts.

⇒ ⚠ **AND IT PUTS COUNTING ON THE PROGRAM SIDE, WHICH IS THE KEY'S MOST ARGUABLE CALL.** *"how
  many vms are there"* is one `list_vms` and some arithmetic. Both readings are written into
  the rows that carry it, marked `hard`, because this is exactly the decision worth having
  before a rule exists rather than after:

      FOR PROGRAM   arithmetic done by the model is verified by NOBODY, and the whole ladder
                    is ordered by who verified the artifact. `QUERY COUNT(SELECT …)` is
                    computed, gated and cheap — a query program is not a tree
      FOR TOOL      the open list's own complaint is that *"assembling a program, grading it
                    whole and inert, and gating it is an absurd treatment of a question"*

  The rows say PROGRAM. If the operator says TOOL, the rows move and the door follows them.

# ⇒⇒ WHAT WRITING THIS FIRST ALREADY CAUGHT — before a line of the door existed

⇒⇒ **`profile` AND `template` ARE MANIFEST KINDS, AND THE BRIEF HAD BOTH ON THE WRONG SIDE.**
  The operator's own framing lists the tiers as *"quick requests (profiles, list), operator
  level (forge contract, create mission), gorgon level (operator password, switch models)"* —
  and `profiles` is in the same breath as `list`, which reads as REPL furniture. It is not:
  `config.KINDS` declares `profile` with `create_profile`, `list_profiles` and
  `delete_profile`, and `template` with `mark_as_template`, `list_templates` and
  `remove_template`. **`show me the profiles` is a lab read, not a settings screen.** A door
  built from the tier list would have sent two whole kinds to the wrong side of itself.
  ⇒ `check()` asserts this premise against the manifest, so if a kind is ever added or removed
    the key says so instead of quietly meaning something else.

⇒⇒ **AND THE THING THE TIER LIST IS ACTUALLY DESCRIBING IS AN EXACT-STRING TABLE.** `list all
  vms` is handled today because that literal string is in `config.json`'s `shortcut_commands`;
  `list all the vms` is not in it and falls through to the model. So the operator's example —
  *"list all vms should be handled by a tool call"* — is already true **for nine spellings**
  and false for every other. That is not a routing decision, it is a phrase book, and it is
  the strongest single argument that the door has to compute something.

⇒ **RUNG 1 IS NOT A PROGRAM REQUEST.** `create a vm named alpha` is one `create_vm` call, so
  the door would not send the ladder's own first rung to the regime the ladder measures. That
  is a control the ladder cannot see about itself, and it is keyed below.

# ⇒⇒ THE SCORING RULES, WRITTEN BEFORE THE RUN — NEVER ONE NUMBER

**Report the confusion BY DIRECTION.** An accuracy figure over these rows would average a
question against a destruction, and the whole point of the ladder's ordering is that those are
not commensurable.

    ⚠ CRITICAL   any lab row -> CHAT          the model answers from memory with NO gate in
                                              front of it. The one cell with no downstream
                                              check at all
    ⚠ CRITICAL   PROGRAM -> TOOL              a set request served by one call. Partial
                                              execution, reported as done
    ⚠ CRITICAL   TOOL -> PROGRAM              **and this one is measured, not feared.**
                                              `create a vm` lowers to an unfiltered
                                              `count(vm) = 1`, which against a nine-machine
                                              lab is satisfied by DELETING EIGHT — including
                                              vm-orchestrator and vm-executor (`plan.py`,
                                              2026-08-02). Routing UP the ladder is merely
                                              slow in most systems. In this one it has a
                                              destructive path, caught today only by a
                                              question the door exists to avoid needing
    ⚠ CRITICAL   GOVERNANCE -> any lab        a rule, a contract or a taught word ENACTED
                                              instead of proposed. A sentence must never
                                              grant authority
      CHEAP      anything -> ASK              a false avoid costs a question. **Except where
                                              the row is obvious** — the operator's own
                                              definition of a bad route is *"asked when it
                                              was obvious"*, so an ASK on a keyed TOOL row
                                              is counted and named, just not counted as
                                              critical
      RECORDED   any `hard` row               a miss here is a recorded decision, not a
                                              surprise. It still prints

⇒ **A DECLINE IS AN ANSWER.** The door returning ASK because the facts did not settle it is
  the designed behaviour, and it is what `verb_kind`'s UNKNOWN and `speech_act`'s `None`
  already do. What must never happen is a confident wrong destination.

⇒ ⚠ **AND THE STANDING CEILING APPLIES HERE AS EVERYWHERE.** These are MY rows. A perfect
  score is a claim about the rules and never about English or about real traffic. A1 —
  held-out, the operator's own, sealed and unopened — is still the only thing that changes
  that ([[gorgon-handover-2026-08-16]]).
"""
from typing import Dict, List, NamedTuple, Tuple

# ── the destinations ─────────────────────────────────────────────────────────────────
SELF = "self"
GOVERNANCE = "governance"
CHAT = "chat"
TOOL = "tool"
PROCEDURE = "procedure"
PROGRAM = "program"
ASK = "ask"

DESTINATIONS = (SELF, GOVERNANCE, CHAT, TOOL, PROCEDURE, PROGRAM, ASK)

# ⇒ THE LAB LADDER, IN ORDER, so a miss can be given a DIRECTION rather than a tick. The three
#   off-ladder destinations are deliberately absent: there is no "one rung up" from SELF.
LADDER: Tuple[str, ...] = (TOOL, PROCEDURE, PROGRAM, ASK)

# ⇒ THE CELLS THAT ARE NOT MERELY WRONG. Named here so the probe cannot report them as one
#   accuracy figure, and each one has its reason in the header above.
CRITICAL_MISSES = (
    ("*lab*", CHAT),        # answered from memory, with no gate in front of it
    (PROGRAM, TOOL),        # a set request served by one call — partial execution
    (TOOL, PROGRAM),        # the unfiltered-count destruction, measured 2026-08-02
    (GOVERNANCE, "*lab*"),  # a rule enacted instead of proposed
)


class Keyed(NamedTuple):
    """One request and where it should GO. `why` is the argument, not a restatement."""
    text: str
    goes: str
    why: str = ""
    hard: bool = False      # a known-hard case; a miss here is recorded, not a surprise
    needs: str = ""         # a stored procedure this row assumes — the probe SKIPS without it


# ⇒ THE PROCEDURES THE `PROCEDURE` ROWS ASSUME. Rung 2 of the ladder cannot be measured against
#   an empty library, and a row that silently passes because nothing was stored is worse than
#   no row. Declared, so the probe reports SKIPPED and says which one is missing.
FIXTURE_PROCEDURES = ("nightly_snapshot",)


# ── THE FOURTEEN RUNGS, KEYED — the corpus that already exists ───────────────────────
#
# ⇒⇒ **AND THE FIRST ONE IS THE FINDING.** Twelve of these serve today through the program
#   regime, and the door would send rung 1 somewhere else entirely. That is not a defect in
#   either — it is the ladder measuring the program regime on a request that did not need it,
#   which no number the ladder produces can show.
RUNG_DESTINATION: Dict[int, str] = {
    1:  TOOL,      # create a vm named alpha — ONE create_vm call, and the effect is the answer
    2:  PROGRAM,   # …and then launch it — two calls with an ORDERING between them
    3:  PROGRAM,   # a network, a vm, then a join — three calls and a dependency
    4:  PROGRAM,   # 5 vms, a network, a label, and a postcondition
    5:  PROGRAM,   # every vm that is currently stopped — a FILTER over a set
    6:  PROGRAM,   # two labelled groups on two networks
    7:  PROGRAM,   # exactly 3 carry the label — a POSTCONDITION
    8:  PROGRAM,   # every vm except db — a set with an exclusion
    9:  PROGRAM,   # n1, n2 and n3 can all ping each other — an ACHIEVE over kindless names
    10: PROGRAM,   # clone golden into 3 — a repetition
    11: PROGRAM,   # ping every vm and stop the ones that do not answer — a derived filter
    12: PROGRAM,   # a snapshot of every running vm — filter, then act on each
    13: PROGRAM,   # rung 4 in the operator's own English
    14: PROGRAM,   # exactly two machines left — the destructive postcondition
}


# ── THE CONTROLS — WHERE THE DESIGN IS ACTUALLY TESTED ───────────────────────────────
#
# ⇒ GROUPED BY WHAT THEY DEFEAT, so a failure names its own cause.
CONTROLS: List[Keyed] = [

    # ⇒⇒ ONE CALL, AND THE OUTPUT OR EFFECT IS THE ANSWER. The rung the whole item was raised
    #   about: *"list all vms should be handled by a tool call so the AI needs to know to
    #   route it."*
    Keyed("list all vms", TOOL,
          "THE OPERATOR'S OWN EXAMPLE. `list_vms` returns rows and the rows ARE the answer"),
    Keyed("list all the vms", TOOL,
          "THE SAME REQUEST, ONE WORD LONGER, AND TODAY IT FALLS TO THE MODEL — the literal "
          "string is not in `shortcut_commands`. The phrase book's whole failure in one row"),
    Keyed("show me the networks", TOOL,
          "an EMBEDDED question — the speaker is the recipient, so it asks — and one "
          "`list_networks` answers it whole"),
    Keyed("what profiles are there", TOOL,
          "⚠ `profile` IS A MANIFEST KIND with its own enumerator. The tier list reads "
          "`profiles` as REPL furniture and it is a lab read"),
    Keyed("list the templates", TOOL,
          "`template` is a kind too — a thing with its own list, by the operator's own rule"),
    Keyed("stop alpha", TOOL,
          "one named target, one setter. The floor of the ladder"),
    Keyed("launch db", TOOL,
          "same shape, the other direction"),
    Keyed("delete the vm called n3", TOOL,
          "DESTRUCTIVE AND STILL ONE CALL. The door picks where, never whether — consent is "
          "gate 3's and the seam's, and routing it elsewhere to be safe would be a lie about "
          "what the request is"),
    Keyed("create a vm called alpha", TOOL,
          "⚠⚠ THE ROW WITH THE MEASUREMENT BEHIND IT. One `create_vm` — and the program "
          "regime lowers it to an unfiltered `count(vm) = 1`, satisfied against a real lab by "
          "DELETING EIGHT MACHINES (`plan.py`, 2026-08-02). Routing up the ladder is not free"),
    Keyed("take a snapshot of db", TOOL,
          "`snapshot_create` takes both names; one call, and no procedure is stored for it"),
    Keyed("set up a network called dmz", TOOL,
          "`SET UP` IS A CREATION VERB THE TUNING CORPUS NEVER USES — `route_holdout`'s own "
          "trap, and `set up` missing from one regex already cost this project a rung"),
    Keyed("is alpha running?", TOOL,
          "`vm_status(alpha)` — one read whose output is the answer verbatim. Keyed "
          "DIRECTIVE_INFORM by `sentence_key` and still a tool call, which is the point: the "
          "speech act says what was said, the door says where it goes"),

    # ⇒⇒ A SET · AN ORDERING · A FILTER · A COUNT · A POSTCONDITION. Structure is the signal,
    #   and none of these can be one call however the sentence is phrased.
    Keyed("stop all the vms", PROGRAM,
          "ONE WORD FROM `stop alpha` AND A DIFFERENT REGIME. A set, enumerated then acted on"),
    Keyed("stop every vm that has over 6gb of ram", PROGRAM,
          "a FILTER over the population. ⚠ Part 2 discards the qualifier today and the DOOR'S "
          "answer is unaffected — which is the honest split: READ fails, ROUTE holds"),
    Keyed("make sure there are exactly two machines", PROGRAM,
          "a POSTCONDITION — rung 14, the shape no tool call has"),
    Keyed("create a vm and put it on the lab network", PROGRAM,
          "two calls with a DEPENDENCY: the second needs what the first minted"),
    Keyed("put every stopped vm on the lab network", PROGRAM,
          "filter, then act on each member"),
    Keyed("clone golden into three new machines", PROGRAM,
          "a repetition — three calls the request states once"),
    Keyed("label all the ubuntu vms as fleet", PROGRAM,
          "a filter on an attribute, then a setter per member"),
    Keyed("delete all the snapshots of db", PROGRAM,
          "a set, and a destructive one. Structure decides the regime; the destruction is "
          "still gate 3's"),

    # ⇒⇒ THE LEADING VERB LIES — the rows that defeat a keyword table, which is the door
    #   anybody writes first and the one `context_assistant.proactive_prep` already is.
    Keyed("list all vms over 6gb and stop them", PROGRAM,
          "OPENS ON `list` AND ENDS IN AN ACT. A trigger-word table routes this to a read"),
    Keyed("show me which vms are stopped and start them", PROGRAM,
          "the same trap with the politest possible opener"),
    Keyed("just stop everything", PROGRAM,
          "no kind named, no target named, and it is a population act. `stop` is one call's "
          "verb and this is not one call"),
    Keyed("create a snapshot of web", TOOL,
          "`route_holdout`'s row, at the door: CREATE, and it is one `snapshot_create`"),
    Keyed("list the vms and remove the fleet label from them", PROGRAM,
          "THE SENTENCE GATE 4'S GUARD MOST HAD TO CATCH (2026-08-16). It reads as a question "
          "and ends in a state change"),

    # ⇒⇒ NOT THE LAB — THE OBJECT TEST. *A contract, a mission, a model, a password are not
    #   manifest kinds*, and that is the same discriminator used everywhere else in the seam.
    Keyed("clear the session", SELF,
          "conversation state. Nothing in the lab is touched"),
    Keyed("forget everything we said", SELF,
          "⚠ `forget` IS TWO OPS. `clear session`'s own phrase set holds it, and `words forget "
          "<x>` withdraws a signed archive entry. The object settles it — `everything we said` "
          "is the session — but a door that reads the verb alone gets this wrong",
          hard=True),
    Keyed("turn verbose on", SELF,
          "a display toggle"),
    Keyed("set the loop limit to 5", SELF,
          "a harness knob, and it names a number the way a lab request names a count"),
    Keyed("check drift", SELF,
          "a report about the conversation, not about the lab"),
    Keyed("what model are you running", SELF,
          "gorgon level. `model` is not a kind and no manifest verb applies"),
    Keyed("switch to the bigger model", SELF,
          "`gorgon load model`'s territory — and the A2 axis. Reads exactly like a lab "
          "instruction and touches nothing in the lab"),
    Keyed("change the operator password", SELF,
          "credentials. `change` is an act and `password` is not a kind"),
    Keyed("show system info", SELF,
          "the HOST Gorgon runs on, which is not a member of any declared kind"),

    # ⇒⇒ GOVERNANCE — the operator's artifacts. **Every one of these governs future acts, so
    #   none may be ENACTED by a sentence.** The archive's own safety property, one layer up.
    Keyed("forge a contract", GOVERNANCE,
          "operator level, and `cli.py` already intercepts it ahead of the model"),
    Keyed("sign the contract", GOVERNANCE,
          "a signature is the one act that must never be automatic"),
    Keyed("create a mission to keep the lab clean", GOVERNANCE,
          "⚠ `create` IS THE MANIFEST'S OWN CREATION VERB and `mission` is not a kind. The "
          "object test alone separates this from `create a vm`"),
    Keyed("a jumpbox is a vm", GOVERNANCE,
          "TEACHING — the archive, pending a signature. **This BUILT A MACHINE until "
          "2026-08-16**: telling the system what a word means produced `create_vm(jumpbox)`"),
    Keyed("never delete a vm without asking me first", GOVERNANCE,
          "⚠ THE BEST TRAP IN THE GROUP. `delete` and `vm` are both lab words and this is "
          "LEGISLATION — a rule quantified over time, not an instruction about now"),
    Keyed("treat prod as read-only", GOVERNANCE,
          "a DECLARATION -> the referendum. S2 is unbuilt and the DESTINATION is still knowable"),
    Keyed("what words have i taught you", GOVERNANCE,
          "D7. The archive as a whole is not queryable in a sentence yet; where it belongs is "
          "not in doubt",
          hard=True),
    Keyed("what procedures do you have", GOVERNANCE,
          "the library the operator authored. Not a kind, not a setting",
          hard=True),

    # ⇒⇒ THE PROCEDURE RUNG — *"we trust already written code than newly generated one."*
    #   These are the only rows with a fixture, and they SKIP rather than lie without it.
    Keyed("run the nightly snapshot", PROCEDURE,
          "names the stored program outright", needs="nightly_snapshot"),
    Keyed("do the nightly snapshots", PROCEDURE,
          "PHRASED AS A GOAL, not as a call — the rung only pays for itself if it is reached "
          "without the operator knowing the procedure's name", needs="nightly_snapshot"),
    Keyed("take a snapshot of every running vm", PROGRAM,
          "RUNG 12, AND THE CONTROL FOR THE RUNG ABOVE: no stored procedure covers it, so rung "
          "2 must not swallow it. A procedure store that matches loosely is a false avoid "
          "wearing a verified artifact's clothes"),

    # ⇒⇒ ASK — the request does not settle it. The ladder's own default, and rungs 1-3 are
    #   attempts to avoid spending the operator's attention.
    Keyed("scan the network for security issues", ASK,
          "THE LADDER'S FOUNDING EXAMPLE. `network` is unfiltered and `security issues` "
          "matches no manifest noun — and `scan_network()` would dry-run beautifully, which "
          "is the soft spot: a dry run closes a LEGALITY gap, never a MEANING one"),
    Keyed("grubnash the vms", ASK,
          "the words mean nothing. VAGUE IS NOT JUNK and this is junk — it can only be asked "
          "about or rejected, never guessed at"),
    Keyed("sort out n1", ASK,
          "RUNG 9'S OWN CASE: `n1` is genuinely kindless, and `sort out` names no operation. "
          "The ask is the correct next step, which is not the same as the ticket closing"),
    Keyed("clean up the lab", ASK,
          "a real intent with no kind, no operation and no target. The honest answer is a "
          "question"),
    Keyed("make it faster", ASK,
          "an anaphor with no previous turn (Part 3) over an attribute nothing declares"),
    Keyed("fix vm2", ASK,
          "⚠ D1 WOULD MOVE THIS TO PROGRAM — an ACHIEVE whose target is implicit (*it should "
          "work*). Keyed ASK because that reading does not exist yet, and keyed HARD so the "
          "day it does, this row moves as a decision rather than a drift. Justified by rung 9 "
          "and E5, which predate the held-out set",
          hard=True),

    # ⇒⇒ CHAT — not a request about the lab or about Gorgon. **The only place the model is
    #   the right answer**, which is why the current door having it as the fall-through is
    #   the whole complaint.
    Keyed("good morning doorman", CHAT,
          "EXPRESSIVE. Names no manifest verb, no kind and no known word — the producer test "
          "settles it with nothing added"),
    Keyed("thanks, that worked", CHAT,
          "and `that` is deliberately not in ANAPHORA: counting it as a named object read a "
          "pleasantry as an order to act"),
    Keyed("who are you", CHAT,
          "a question about the system, answerable in words, touching nothing"),
    Keyed("what's a hypervisor?", CHAT,
          "GENERAL KNOWLEDGE IN LAB VOCABULARY. `hypervisor` is not a kind and the model "
          "genuinely knows this better than the manifest does"),
    Keyed("why is qemu slow on windows guests", CHAT,
          "⚠ `guest` IS A DECLARED NOUN FOR `vm`, so a noun-membership test alone routes this "
          "into the lab. Nothing is being asked OF the lab",
          hard=True),

    # ⇒⇒ THE DANGEROUS DIRECTION — a lab question that must never reach chat, because there
    #   the model answers it from memory and no gate is in front of the answer.
    Keyed("how many vms are running", PROGRAM,
          "⚠ TODAY THIS FALLS TO THE MODEL. A filter and a count — the arguable call the "
          "header states both sides of, and the direction that matters is that it is not CHAT",
          hard=True),
    Keyed("how many machines carry the 'fleet' label", PROGRAM,
          "READ AS `add_label` ON 2026-08-14 — the false serve the interrogative reader was "
          "built to stop, keyed here for where it goes once it is read right",
          hard=True),
    Keyed("is there a machine called alpha", PROGRAM,
          "A MEMBERSHIP TEST, not a status read: `list_vms` returns rows and somebody has to "
          "decide. Sits one word from `is alpha running?`, which IS one call, and the pair is "
          "the sharpest statement of the TOOL/PROGRAM line in the file",
          hard=True),

    # ⇒⇒ THE SHAPE THE DOOR HAS NO ANSWER FOR — raised once, deliberately, rather than three
    #   times. One request, two destinations, and a door whose contract is ONE destination.
    Keyed("clear the session and then list the vms", ASK,
          "SELF AND TOOL IN ONE STRING. Keyed ASK because a door that silently drops half a "
          "request is the worst available answer — and the alternative (split the clauses and "
          "route each) changes the door's contract, so it is recorded here and NOT keyed",
          hard=True),
]


# ── checks ───────────────────────────────────────────────────────────────────────────

# ⇒ THE PREMISE THIS KEY RESTS ON, ASSERTED AGAINST THE MANIFEST RATHER THAN BELIEVED.
#   The whole SELF/GOVERNANCE side of the key is the object test — *these words are not
#   manifest kinds* — and it was WRONG about two of them when the brief was written.
KIND_WORDS = ("vm", "network", "profile", "snapshot", "template", "file",
              "machine", "guest", "net")
NOT_KIND_WORDS = ("contract", "mission", "model", "password", "session",
                  "procedure", "drift")


def check() -> List[str]:
    """The key still describes the corpus and the world. Returns the faults, empty if well."""
    from planner.ir import config
    from .rungs import RUNGS

    faults: List[str] = []
    kinds = set(config.KINDS)
    nouns = {n.lower() for k in config.KINDS.values() for n in (k.get("nouns") or ())}
    known = kinds | nouns

    for w in KIND_WORDS:
        if w not in known:
            faults.append(f"premise broken: {w!r} is keyed as a lab noun and the manifest "
                          f"no longer declares it")
    for w in NOT_KIND_WORDS:
        if w in known:
            faults.append(f"premise broken: {w!r} is keyed as NOT a lab noun and the manifest "
                          f"now declares it — the object test moved under the key")

    seen = set()
    for k in CONTROLS:
        if k.goes not in DESTINATIONS:
            faults.append(f"control {k.text!r}: unknown destination {k.goes!r}")
        if not k.why:
            faults.append(f"control {k.text!r}: keyed with no argument")
        if k.text in seen:
            faults.append(f"control {k.text!r}: keyed twice")
        seen.add(k.text)
        if k.needs and k.needs not in FIXTURE_PROCEDURES:
            faults.append(f"control {k.text!r}: needs {k.needs!r}, which is not a declared "
                          f"fixture")
        if k.goes == PROCEDURE and not k.needs:
            faults.append(f"control {k.text!r}: keyed PROCEDURE and names no procedure, so it "
                          f"would pass against an empty library")

    rung_ns = {r.n for r in RUNGS}
    for n in RUNG_DESTINATION:
        if n not in rung_ns:
            faults.append(f"rung {n} is keyed and no longer exists in rungs.py")
    for n in rung_ns:
        if n not in RUNG_DESTINATION:
            faults.append(f"rung {n} exists and is not keyed")

    for d in DESTINATIONS:
        if counts()[d] == 0:
            faults.append(f"destination {d!r} has no controls at all")

    return faults


def counts() -> Dict[str, int]:
    """How many controls per destination — so a thin rung is visible rather than assumed."""
    out: Dict[str, int] = {d: 0 for d in DESTINATIONS}
    for k in CONTROLS:
        out[k.goes] += 1
    return out


def direction(keyed: str, got: str) -> str:
    """What KIND of miss this is — never a tick. `same` when there is no miss.

    ⇒ CRITICAL is decided by the named cells, and `*lab*` in one of them means any of the
      four ladder destinations. Everything else on the ladder is UP or DOWN, which is enough
      to say whether the door reached past the verification it had or fell short of it.
    """
    if keyed == got:
        return "same"
    for want, then in CRITICAL_MISSES:
        want_ok = keyed in LADDER if want == "*lab*" else keyed == want
        then_ok = got in LADDER if then == "*lab*" else got == then
        if want_ok and then_ok:
            return "CRITICAL"
    if keyed in LADDER and got in LADDER:
        return "up" if LADDER.index(got) > LADDER.index(keyed) else "down"
    return "off-ladder"


if __name__ == "__main__":                                     # pragma: no cover
    import sys

    if "--check" in sys.argv:
        bad = check()
        print("\n".join(bad) if bad else "the key still describes the world — 0 faults")
        raise SystemExit(1 if bad else 0)

    from .rungs import RUNGS

    print("── THE FOURTEEN RUNGS ──────────────────────────────────────────────")
    for r in RUNGS:
        print(f"  {RUNG_DESTINATION[r.n].upper():10} rung {r.n:2}  {r.goal[:64]}")

    print("\n── THE CONTROLS ────────────────────────────────────────────────────")
    for d in DESTINATIONS:
        rows = [k for k in CONTROLS if k.goes == d]
        print(f"\n  ═══ {d.upper()}  ({len(rows)}) ═══")
        for k in rows:
            mark = " ⚠hard" if k.hard else ""
            need = f"  [needs {k.needs}]" if k.needs else ""
            print(f"    {k.text}{need}{mark}\n      {k.why}")

    print("\n── COVERAGE ────────────────────────────────────────────────────────")
    for d, n in counts().items():
        print(f"  {d:12} {n:2} controls" + ("   ⚠ THIN" if n < 3 else ""))
    print(f"\n  {len(CONTROLS)} controls · {len(RUNG_DESTINATION)} rungs · "
          f"{sum(1 for k in CONTROLS if k.hard)} keyed hard")
    print(f"  critical cells: " + " · ".join(f"{a}->{b}" for a, b in CRITICAL_MISSES))
