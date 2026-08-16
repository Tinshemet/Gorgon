"""iso_map.py — GORGON'S READING, MAPPED ONTO ISO 24617-2. A TRANSLATION, NEVER A RENAME.

    PYTHONPATH=. python3 -m tests.bench.iso_map            # the mapping, with live checks
    PYTHONPATH=. python3 -m tests.bench.iso_map --holes    # only the ISO cells we do not fill
    PYTHONPATH=. python3 -m tests.bench.iso_map --check    # every one of OUR types is placed

# ⇒⇒ WHY A STANDARD, AND WHY THIS ONE

Every taxonomy in this project so far has been mine: six groups here, eight flavours there, and
each time the operator asked *"really? only eight?"* the answer was no. **ISO 24617-2 (SemAF
part 2) is a published standard for annotating TASK-ORIENTED DIALOGUE** — the exact shape of
this problem — and it enumerates NINE DIMENSIONS and a function hierarchy that somebody else
argued about for years.

⇒ **SO THE GAP LIST STOPS DEPENDING ON MY IMAGINATION.** With an external enumeration, a hole
  is *an ISO cell nothing of ours fills* — which is a fact, not a guess. That is the entire
  value of this file and the reason it is Phase 1.

⇒ **AND IT IS A MAP, NOT A RENAME — the operator's ruling, 2026-08-16:** *"map rather than
  rename."* `DIRECTIVE_ACT`, `mood_of`, the four gates and the door's destinations are embedded
  everywhere and are staying. Two vocabularies coexist and this file is the only place they
  meet, which is what keeps them from drifting apart in a dozen docstrings.

# ⇒⇒ THE THREE AXES ISO SEPARATES, AND WE HAD COLLAPSED TWO OF THEM

    DIMENSION    WHAT the utterance is about — the task, the feedback, the floor, the social
                 obligations. Nine of them, and one utterance may carry SEVERAL AT ONCE
    FUNCTION     WHAT IT DOES in that dimension — question, inform, instruct, promise
    QUALIFIER    HOW it is held — certainty · conditionality · partiality · sentiment

⇒⇒ **AND THE QUALIFIER AXIS IS THE ONE WE DO NOT HAVE AT ALL.** We modelled stance as a
  SPECIES sitting beside order and question; ISO makes it a MODIFIER ON any act. *"maybe stop
  the vms"* is an Instruct with `certainty: uncertain` — not a different kind of sentence.
  ⇒ **AND CONDITIONALITY IS ONE OF THEM**, which is why a conditional can be READ while E5
    stands: it is a flag on the act, not a clause structure the writer must emit.

# ⇒ WHAT IS SOURCED AND WHAT IS INFERRED, SAID PLAINLY

The nine dimensions and the four qualifiers are quoted from the standard's own summaries. The
general-purpose function hierarchy is sourced for the leaves named below; the dimension-specific
functions are partly sourced and partly reconstructed, and every reconstructed one is marked
`⚠ inferred` so nobody mistakes my reading for the standard's text.

    ISO 24617-2:2020        https://www.iso.org/standard/76443.html
    Bunt et al., chapter 6  https://people.ict.usc.edu/~traum/Papers/iso-2017.pdf
"""
from typing import Dict, List, NamedTuple, Optional

# ⇒⇒ **THE VOCABULARY IS PRODUCTION'S, READ AND NEVER RESTATED.** It began here and moved to
#   `orchestrator/seam/iso.py` the moment an EMITTER existed: two copies of a standard's names
#   is exactly the drift this file was written to prevent, and a bench that declares the same
#   strings as the thing it describes has stopped describing it.
from orchestrator.seam.iso import (  # noqa: E402
    ALLO_FB, AUTO_FB, DIMENSIONS, DISCOURSE, OWN_COMM, PARTNER_COMM, PLACED, QUALIFIERS,
    SOCIAL, TASK, TIME, TURN,
)


class Cell(NamedTuple):
    """One ISO function, and what of ours fills it."""
    dimension: str
    function: str
    ours: str                 # the Gorgon type/module that fills it; "" is a hole
    example: str = ""
    note: str = ""
    inferred: bool = False    # the ISO name is my reconstruction, not quoted from the standard

    @property
    def hole(self) -> bool:
        return not self.ours


MAP: List[Cell] = [

    # ── TASK · information-seeking ───────────────────────────────────────────────────
    Cell(TASK, "Set Question", "speech_act.DIRECTIVE_INFORM + answer_shape",
         "which vms are running", "the wh-word names the answer's SHAPE — members · count"),
    Cell(TASK, "Check Question", "speech_act.DIRECTIVE_INFORM (tag/polar branch)",
         "the vms are all stopped, right?", "keyed in sentence_key as tag questions"),
    Cell(TASK, "Choice Question", "", "should i delete db or keep it?",
         "⚠ read as a QUESTION and the DISJUNCTION is not read — `linguistics/"
         "unexpressed-choice` raises it on the DIRECTIVE side only"),

    # ── TASK · information-providing ─────────────────────────────────────────────────
    Cell(TASK, "Inform", "speech_act.ASSERTIVE -> archive.taught_by",
         "a jumpbox is a vm", "teaching, proposed and never filed until signed"),
    Cell(TASK, "Answer", "reading_answers.settle", "yes, it's a label",
         "the one cross-turn reader that exists"),
    Cell(TASK, "Confirm", "reading_answers.AFFIRMATION", "yes, that one"),
    Cell(TASK, "Disconfirm", "reading_answers.NEGATION", "no, not that one"),
    Cell(TASK, "Correction", "", "stop alpha — sorry, i meant beta",
         "⚠⚠ IT REWRITES THE REQUEST and every stance rule wants to discard it. ISO files it "
         "under Own Communication Management too — see there"),

    # ── TASK · action-discussion ─────────────────────────────────────────────────────
    Cell(TASK, "Instruct", "speech_act.DIRECTIVE_ACT -> the whole seam",
         "stop every vm that has over 6gb", "the path the system was built along"),
    Cell(TASK, "Request", "speech_act.DIRECTIVE_ACT (polite-imperative branch)",
         "could you stop the vms?", "0/14 for the model, exact for the lookup"),
    Cell(TASK, "Suggest", "", "you could stop the ones that aren't doing anything",
         "⚠ A SUGGESTION IS NOT AN INSTRUCTION and nothing reads one. The difference is "
         "whether the operator asked for it or floated it"),
    Cell(TASK, "Offer", "", "shall i clean those up for you?",
         "⚠ ours to make, not theirs — and nothing produces one", inferred=True),
    Cell(TASK, "Promise", "", "i'll add the labels myself tomorrow",
         "⚠ COMMISSIVE is NAMED in speech_act and nothing emits it. It says the world will "
         "change WITHOUT us, which is a planning fact"),

    # ── AUTO-FEEDBACK · our own understanding ────────────────────────────────────────
    Cell(AUTO_FB, "Auto-Negative", "gates12 + residue -> the ASKs",
         "the request does not say what 'n1' is",
         "⇒ **WE HAVE HAD THIS ALL ALONG AND NEVER CALLED IT FEEDBACK.** Every gate-2 ask IS "
         "an auto-negative: *I did not understand this part*"),
    Cell(AUTO_FB, "Auto-Positive", "", "(the reading, echoed back)",
         "⚠ nothing states what WAS understood — only what was not. `plan --door` prints "
         "facts; no reading is ever confirmed to the operator in the ordinary path"),

    # ── ALLO-FEEDBACK · their evaluation of OUR understanding ────────────────────────
    Cell(ALLO_FB, "Allo-Negative", "", "no, that's not what i meant",
         "⚠⚠ HOW THE OPERATOR CORRECTS A MISREADING, and it is DISTINCT from answering a "
         "question we asked — `reading_answers` owns the answer, nothing owns this"),
    Cell(ALLO_FB, "Allo-Positive", "", "yes, exactly", "⚠ nothing reads it", inferred=True),

    # ── TURN MANAGEMENT ──────────────────────────────────────────────────────────────
    Cell(TURN, "Turn Keep", "", "hold on, i'm not finished",
         "low value in a text CLI — there is no floor to contest", inferred=True),

    # ── TIME MANAGEMENT ──────────────────────────────────────────────────────────────
    Cell(TIME, "Pausing", "speech_act.META_CONTROL -> gate4.told_not_to_act",
         "don't start any changes yet",
         "⇒ ours reads as *hold the program*, which is ISO's Pausing seen from our side"),
    Cell(TIME, "Stalling", "", "give me a second",
         "⚠ nothing reads it, and it is nearly free — same branch as Pausing", inferred=True),

    # ── DISCOURSE STRUCTURING ────────────────────────────────────────────────────────
    Cell(DISCOURSE, "Topic Shift", "", "list the vms. anyway, is alpha running?",
         "⚠⚠ IT STARTS A SECOND REQUEST and the clause splitter merges it into the first"),
    Cell(DISCOURSE, "Interaction Structuring", "", "first do the labels, then the network",
         "⚠ an AGENDA over several turns. Ordering WITHIN a request works; across them there "
         "is no turn to hold it", inferred=True),
    Cell(DISCOURSE, "Opening", "speech_act.EXPRESSIVE + pass1.agent_name",
         "good morning doorman", "the agent's own name is the discriminator"),

    # ── OWN COMMUNICATION MANAGEMENT · repairing our own talk ────────────────────────
    Cell(OWN_COMM, "Self-Correction", "", "stop alpha — sorry, i meant beta",
         "⚠⚠ THE OPERATOR REPAIRING THEIR OWN REQUEST. Schegloff, Jefferson & Sacks give the "
         "four-way grid — self/other initiated x self/other repair — and we have built ONE "
         "cell of it without knowing it was a grid (see Auto-Negative, which is an "
         "other-initiated repair INITIATION)"),
    Cell(OWN_COMM, "Retraction", "", "actually, never mind — cancel that",
         "⚠⚠ MEASURED HARM: the word `cancel` once CREATED A VM. One rule guards the confirm "
         "prompt; a retraction arriving as an ordinary turn is unread"),

    # ── PARTNER COMMUNICATION MANAGEMENT · repairing OUR talk ────────────────────────
    Cell(PARTNER_COMM, "Correct Misspeaking", "", "you mean the lab network, not lab",
         "⚠ the operator correcting OUR wording. Nothing reads it", inferred=True),

    # ── SOCIAL OBLIGATIONS MANAGEMENT ────────────────────────────────────────────────
    Cell(SOCIAL, "Greeting", "speech_act.EXPRESSIVE", "hi · good morning",
         "reached by the producer test: no manifest verb, no kind, no known word"),
    Cell(SOCIAL, "Thanking", "", "thanks, that worked",
         "⚠ AND IT CARRIES A RESOLUTION — the ticket closes. `Issues.answers()` is the writer "
         "that would take one"),
    Cell(SOCIAL, "Apology", "", "sorry to bother you",
         "⚠ nothing reads it, and `sorry` is also REPAIR's opener — the word settles nothing"),
    Cell(SOCIAL, "Goodbye", "", "that's all, thanks", "⚠ nothing closes a session",
         inferred=True),
]


# ⇒⇒ **OUR TYPES, AND WHERE EACH ONE LANDS.** The direction that matters for `--check`: a type
#   of ours with nowhere to go means the map is incomplete, and adding one forces the question
#   *what is this, in a vocabulary somebody else validated?*
OURS: Dict[str, str] = {t: f"{d} / {f}" for t, (d, f) in PLACED.items()}
# ⇒ ⚠ **AND THE ONE THAT DOES NOT FIT IS ANNOTATED HERE RATHER THAN IN THE TABLE.** A standing
#   rule — *"never delete a vm without asking me"* — is a DECLARATION in Searle's sense: it
#   changes what is PERMITTED by being said. ISO's Task dimension has no such function, because
#   ISO annotates dialogue ABOUT a task rather than dialogue that LEGISLATES over one. `PLACED`
#   files it under Inform; this is the note saying that is a compromise and not a fit.
MISMATCH = {"declaration": "no ISO function legislates — filed under Task/Inform"}


def holes() -> List[Cell]:
    return [c for c in MAP if c.hole]


def by_dimension() -> Dict[str, List[Cell]]:
    out: Dict[str, List[Cell]] = {d: [] for d in DIMENSIONS}
    for c in MAP:
        out[c.dimension].append(c)
    return out


def check() -> List[str]:
    """Every type of OURS is placed, and every cell names a real dimension."""
    from orchestrator.seam import speech_act as SA
    faults: List[str] = []
    for c in MAP:
        if c.dimension not in DIMENSIONS:
            faults.append(f"{c.function}: {c.dimension!r} is not one of the nine")
    ours = {SA.DIRECTIVE_ACT, SA.DIRECTIVE_INFORM, SA.ASSERTIVE, SA.DECLARATION,
            SA.META_CONTROL, SA.EXPRESSIVE, SA.COMMISSIVE, "answer"}
    for t in sorted(ours):
        if t not in OURS:
            faults.append(f"our type {t!r} is not placed anywhere in the ISO frame")
    for t in OURS:
        if t not in ours:
            faults.append(f"{t!r} is mapped and is not one of our types any more")
    # ⇒⇒ ⚠ **AND THE QUALIFIER CHECK HAD TO BE REWRITTEN THE DAY IT WAS MEANT TO FIRE.** The
    #   first version asserted the axis was EMPTY by looking for a qualifier name inside
    #   `OURS`, so that the day one was built this file would fail and somebody would come and
    #   say where it went. **It did not fire** — `OURS` was refactored to derive from `PLACED`
    #   the same hour, and the string it was watching stopped existing. A check that watches a
    #   REPRESENTATION rather than a FACT stops watching when the representation moves.
    #   ⇒ It now asks the emitter, which is the fact: three qualifiers are read and `sentiment`
    #     is declined, and if that ever changes silently this fails.
    from orchestrator.seam import iso as _iso
    reads = {q for q in QUALIFIERS
             if any(q in _iso.qualifiers_of(s) for s in
                    ("maybe stop them", "if alpha is stopped", "stop most of the vms"))}
    if reads != {"certainty", "conditionality", "partiality"}:
        faults.append(f"the qualifiers the emitter reads have changed — {sorted(reads)}")
    if "sentiment" in reads:
        faults.append("`sentiment` is being read — it was declined until somebody TEACHES it")
    return faults


if __name__ == "__main__":                                       # pragma: no cover
    import sys
    argv = sys.argv[1:]
    if "--check" in argv:
        bad = check()
        print("\n".join(bad) if bad else "every type of ours is placed — 0 faults")
        raise SystemExit(1 if bad else 0)

    only = "--holes" in argv
    print(f"\n  ISO 24617-2 · {len(DIMENSIONS)} dimensions · {len(MAP)} functions mapped · "
          f"{len(holes())} we do not fill")
    for dim, cells in by_dimension().items():
        shown = [c for c in cells if not only or c.hole]
        if not shown:
            continue
        print(f"\n═══ {dim} ═══")
        for c in shown:
            mark = "⚠ " if c.hole else "  "
            tag = "  ⚠ inferred name" if c.inferred else ""
            print(f" {mark} {c.function}{tag}")
            print(f"      ours    {c.ours or '*** NOTHING ***'}")
            if c.example:
                print(f"      e.g.    “{c.example}”")
            if c.note:
                print(f"      {c.note}")

    print(f"\n{'─' * 96}\n  OUR TYPES, PLACED")
    for t, where in sorted(OURS.items()):
        print(f"    {t:18} -> {where}")
    from orchestrator.seam import iso as _iso
    print(f"\n  THE QUALIFIER AXIS — orthogonal to every function above:")
    probes = {"certainty": "maybe stop them", "conditionality": "if alpha is stopped",
              "partiality": "stop most of the vms", "sentiment": "ugh, stop them"}
    read = 0
    for q in QUALIFIERS:
        got = _iso.qualifiers_of(probes[q]).get(q)
        read += 1 if got else 0
        print(f"    {q:16} {got or '*** NOT READ ***'}"
              + ("   ⚠ the one that needs a TEACHER, not a class" if q == "sentiment" else ""))
    print(f"\n  {len(MAP) - len(holes())} of {len(MAP)} ISO functions filled · "
          f"{read} of {len(QUALIFIERS)} qualifiers read")
