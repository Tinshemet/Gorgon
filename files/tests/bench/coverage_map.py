"""coverage_map.py — EVERY KIND OF THING A PERSON CAN SAY TO GORGON, AND WHAT READS IT TODAY.

    PYTHONPATH=. python3 -m tests.bench.coverage_map          # the map, with live verdicts
    PYTHONPATH=. python3 -m tests.bench.coverage_map --holes  # only what nothing reads

# ⇒⇒ WHY THIS IS AN INSTRUMENT AND NOT A DOCUMENT

The operator, 2026-08-16: *"lets cover all, because what we dont cover will remain a hole, so
lets cover everything… we went over statements, question, actionable, etc — we also need to
cover everything else."*

**A hole nobody has named is a hole nobody can close**, and a prose list of them rots the day
after it is written. So every row here carries an EXAMPLE, and `--run` puts that example
through the door and prints what actually happens. The map cannot claim coverage the code does
not have.

⇒ **AND THE DOOR IS FREE TO ASK.** `door.facts` costs no model call, so the whole map can be
  re-run in a second. The seam costs three model calls per row and is NOT run here — where a
  row's real answer needs the seam, the note says so.

# ⇒⇒ THE AXIS: WHAT DOES THE TURN ACT ON?

Six groups, and they are exhaustive over what a turn in this conversation can be ABOUT. A turn
addresses the WORLD we manage, the POLICY that governs us, the CONVERSATION itself, the
SPEAKER, GORGON's own state, or nothing of ours.

    WORLD         the lab: change it, ask about it, tell us about it
    POLICY        what may be done, ever or in this request
    CONVERSATION  the exchange itself: hold, retract, repair, answer, audit
    SPEAKER       what the speaker will do, and how they feel
    GORGON        the session, the model, the credentials, the artifacts
    NOT-OURS      unrelated, noise, unknown vocabulary

⇒ Within a group the kinds are distinguished by WHAT COULD BE BUILT from them, which is the
  producer test this project has used since the sentence types were written.

# ⇒ HOW TO READ A ROW

    reads_it   the code that turns this kind into something, TODAY. Empty means a HOLE.
    goes       where the door sends it, or "" when the door has no destination for it
    ⚠          a hole whose failure mode is a WRONG ACTION rather than a lost answer
"""
from typing import List, NamedTuple, Optional

WORLD, POLICY, CONVERSATION, SPEAKER, GORGON, NOT_OURS = (
    "WORLD", "POLICY", "CONVERSATION", "SPEAKER", "GORGON", "NOT-OURS")


class Turn(NamedTuple):
    group: str
    kind: str
    example: str
    reads_it: str          # the module that reads it today; "" is a hole
    goes: str              # the door destination, or "" when there is none
    note: str = ""
    danger: bool = False   # a hole whose failure is a wrong ACTION, not a lost answer

    @property
    def hole(self) -> bool:
        return not self.reads_it


MAP: List[Turn] = [

    # ── WORLD ────────────────────────────────────────────────────────────────────────
    Turn(WORLD, "order", "stop every vm that has over 6gb of ram",
         "speech_act.DIRECTIVE_ACT -> pass1/pass2 -> the writer", "program",
         "the path the whole system was built along"),
    Turn(WORLD, "single call", "stop alpha",
         "speech_act.DIRECTIVE_ACT -> the tool regime", "tool",
         "N1 decides this one rather than the program regime taking it by default"),
    Turn(WORLD, "question", "how many vms are running",
         "speech_act.DIRECTIVE_INFORM -> answer_shape -> a QUERY program", "program",
         "shape read off the wh-word; `None` declines rather than answering another question"),
    Turn(WORLD, "scheduled", "take a snapshot of the vms daily",
         "temporal.clock_in -> the door", "routine",
         "⚠ THE STORE HOLDS A RECURRENCE AND NOT A ONE-OFF — `every` recurs, `when` is a "
         "world predicate, and nothing holds *at 9pm, once*"),
    Turn(WORLD, "event-driven", "whenever a vm stops, take a snapshot of it",
         "temporal.events_in + standing -> the door", "trigger",
         "the rule is the act, the event is what starts it"),
    Turn(WORLD, "teaching", "a jumpbox is a vm",
         "speech_act.ASSERTIVE -> archive.taught_by", "governance",
         "proposed, never filed — nothing routes until a person signs it"),
    Turn(WORLD, "diagnosis", "vm2 isn't working, it boots to a blue screen",
         "", "",
         "⚠⚠ **THE THESIS OF THE PRODUCT AND IT HAS NO READING.** Grammatically a STATEMENT; "
         "nothing turns a symptom into a goal. The machinery exists — rung 9, `derive`, "
         "ACHIEVE — and the READING does not. D1, and justified by rung 9 and E5, which "
         "predate the held-out set",
         danger=True),
    Turn(WORLD, "evidence", "alpha won't boot, the error says 'cannot allocate memory'",
         "", "",
         "⚠ the quoted half is DATA the operator is handing us. It correlates with nothing in "
         "the manifest — the exact profile of UNRELATED — and it is the evidence a diagnosis "
         "would run on. The quotes are structural, so this costs no vocabulary",
         danger=True),

    # ── POLICY ───────────────────────────────────────────────────────────────────────
    Turn(POLICY, "standing rule", "never delete a vm without asking me first",
         "speech_act.DECLARATION -> governing.rules_from", "governance",
         "documentary only: it carries the operator's sentence and enforces nothing until "
         "they type the effect themselves"),
    Turn(POLICY, "scoped red line", "treat prod as read-only",
         "governing.CONTRACT_VERBS -> rules_from", "governance",
         "no closed-class marker at all — `treat X as Y` is declared to name an act of "
         "governing in THIS system"),
    Turn(POLICY, "manner constraint", "stop the vms, one at a time",
         "", "",
         "⚠ **A CONSTRAINT ON HOW, BINDING THIS REQUEST ONLY.** Not a standing rule and not "
         "part of the goal — and dropping it changes what runs. Same shape as the qualifiers "
         "in Part 2 and not on that list",
         danger=True),
    Turn(POLICY, "preference", "i'd rather use the smaller profile for these",
         "", "",
         "SOFT — it should bias a choice and never bind one. Nothing reads it, and unlike a "
         "rule it has no store to go in"),

    # ── CONVERSATION ─────────────────────────────────────────────────────────────────
    Turn(CONVERSATION, "hold", "don't start any changes yet",
         "speech_act.META_CONTROL -> gate4.told_not_to_act", "",
         "the program is held and the operator is asked whether they meant it yet"),
    Turn(CONVERSATION, "answer", "yes, it's a label",
         "reading_answers.settle", "",
         "the operator's reply to a question we asked; the only reader that owns it"),
    Turn(CONVERSATION, "retraction", "actually, never mind — cancel that",
         "", "",
         "⚠⚠ **MEASURED HARM ALREADY:** [[gorgon-confirm-answer-rule]] — the word *cancel* "
         "CREATED A VM. One rule was added for the confirm prompt; a retraction arriving as "
         "an ordinary turn is still unread",
         danger=True),
    Turn(CONVERSATION, "repair", "stop alpha — sorry, i meant beta",
         "", "",
         "⚠⚠ **IT REWRITES THE REQUEST.** `sorry` is APOLOGY's word and `i meant` is shaped "
         "like a hedge, so every flavour rule wants to discard it. Discard it and the wrong "
         "machine dies",
         danger=True),
    Turn(CONVERSATION, "topic shift", "list the vms. anyway, is alpha running?",
         "", "",
         "⚠ IT STARTS A SECOND REQUEST. Merging the two makes a compound nobody asked for",
         danger=True),
    Turn(CONVERSATION, "audit", "what did you just run?",
         "", "",
         "⚠ **A QUESTION ABOUT OUR OWN BEHAVIOUR, NOT ABOUT THE LAB.** `events.log` is the "
         "arbiter and no sentence reaches it. The door would read `run` as a manifest verb "
         "and send it at the lab",
         danger=True),
    Turn(CONVERSATION, "acknowledgement", "ok, got it",
         "", "",
         "a receipt for something we said. Harmless to mis-read and it is still a hole"),
    Turn(CONVERSATION, "resolution", "thanks, that worked",
         "", "",
         "the ticket CLOSES. `Issues.answers()` is the writer that would take one — D3. "
         "Today it is indistinguishable from `sort out n1`: both read EXPRESSIVE"),

    # ── SPEAKER ──────────────────────────────────────────────────────────────────────
    Turn(SPEAKER, "commitment", "i'll add the labels myself tomorrow",
         "", "",
         "⚠ COMMISSIVE — `speech_act` names the type and NOTHING EMITS IT. It says the WORLD "
         "will change without us, which is a planning fact: do not do it, and expect the "
         "change",
         danger=True),
    Turn(SPEAKER, "stance", "if you don't mind, stop the vms please",
         "speech_act.EXPRESSIVE -> pass1.consume_meta_control (partial)", "",
         "⚠ MEASURED: 12 SERVE -> 0 SERVE under politeness, recovered to 4 by the per-chunk "
         "producer rule. The rest needs the stance taxonomy — 16 kinds on 4 axes"),
    Turn(SPEAKER, "greeting", "good morning doorman",
         "speech_act.EXPRESSIVE + pass1.agent_name", "chat",
         "the agent's own name is the only fact separating this from `sort out n1`"),

    # ── GORGON ───────────────────────────────────────────────────────────────────────
    Turn(GORGON, "own state", "switch to the bigger model",
         "door.GORGON_NOUNS -> the tier test", "self",
         "the object test: a model is not a manifest kind"),
    Turn(GORGON, "own artifacts", "forge a contract",
         "door.GORGON_NOUNS -> GOVERNANCE_OWNERS", "governance",
         "a signature is the one act that must never be automatic"),
    Turn(GORGON, "capability", "can you even do snapshots?",
         "", "",
         "⚠ A QUESTION ABOUT WHAT WE CAN DO, answerable from the manifest alone and read by "
         "nothing. The door sends it at the lab as a polar question about snapshots"),

    # ── NOT-OURS ─────────────────────────────────────────────────────────────────────
    Turn(NOT_OURS, "unrelated", "oh its really hot in here",
         "", "",
         "it parses, names things, and not one referent is ours. **The most dangerous of the "
         "three because it has the shape of a request**"),
    Turn(NOT_OURS, "noise", "asdjhasjdbhasd",
         "", "",
         "the only species catchable by FORM — phonotactics, which is structure and not a list"),
    Turn(NOT_OURS, "unknown word", "grubnash the vms",
         "residue.classify -> ASK, by the slot", "ask",
         "**NOT unprocessable — only unread.** The slot decides, and it must always ask"),
]


def holes() -> List[Turn]:
    return [t for t in MAP if t.hole]


def dangerous() -> List[Turn]:
    return [t for t in MAP if t.hole and t.danger]


def run_door(t: Turn, world=None):
    """What the door actually does with this example today. No model call."""
    from orchestrator.door import facts, route
    try:
        got = route(facts(t.example, world=world))
        return got.goes, got.rung
    except Exception as e:                                       # pragma: no cover
        return "ERROR", f"{type(e).__name__}: {e}"


def main(argv: Optional[List[str]] = None) -> int:               # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    only_holes = "--holes" in argv
    try:
        from tests.bench.door_probe import FixtureWorld
        from tests.bench import door_key as K
        world = FixtureWorld(K.FIXTURE_MEMBERS)
        world_says = "fixture lab"
    except Exception:                                            # pragma: no cover
        world, world_says = None, "no lab"

    print(f"\n  {len(MAP)} kinds of turn · {len(holes())} holes · "
          f"{len(dangerous())} of them dangerous · {world_says}")
    group = None
    for t in MAP:
        if only_holes and not t.hole:
            continue
        if t.group != group:
            group = t.group
            print(f"\n═══ {group} ═══")
        goes, rung = run_door(t, world)
        mark = "⚠⚠" if (t.hole and t.danger) else ("⚠ " if t.hole else "  ")
        agree = " " if (goes == t.goes or not t.goes) else "!"
        print(f"\n {mark} {t.kind.upper()}   “{t.example}”")
        print(f"      reads it   {t.reads_it or '*** NOTHING ***'}")
        print(f"      door says  {goes}{agree}  ({rung})"
              + (f"   [map says {t.goes}]" if t.goes and goes != t.goes else ""))
        if t.note:
            print(f"      {t.note}")

    print(f"\n{'─' * 96}")
    print(f"  COVERED   {len(MAP) - len(holes()):2} of {len(MAP)}")
    print(f"  HOLES     {len(holes()):2}   and {len(dangerous())} of them fail as a WRONG "
          f"ACTION rather than a lost answer:")
    for t in dangerous():
        print(f"      {t.group:12} {t.kind}")
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
