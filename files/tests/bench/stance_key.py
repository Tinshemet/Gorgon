"""stance_key.py — WHAT KIND OF UNPROCESSABLE IS IT, WRITTEN DOWN BEFORE ANYTHING READS ONE.

    PYTHONPATH=. python3 -m tests.bench.stance_key            # print the key
    PYTHONPATH=. python3 -m tests.bench.stance_key --check    # it still describes the world

# ⇒⇒ THE ITEM, AND THE CORRECTION THAT SHAPED IT

The operator, 2026-08-16, twice, and the second one undid a design:

    *"junk isnt a default, its an 'unprocessable' key of the sentence that doesnt serve any
    purpose beyond 'flavoring'."*

    *"unprocessable can be measured by what KIND of 'flavor' is it… a 'flavor' is a kind of an
    unprocessable, but pure unprocessables can be actual gibberish (asdjhasjdbhasd), something
    unrelated ('oh its really hot in here'), etc"* — and: ***"flavors are good mood
    indicator."***

⇒ **SO UNPROCESSABLE IS THE GENUS AND FLAVOUR IS ONE SPECIES**, and the design that fell to
  that correction was *fails every test, therefore junk* — junk by exhaustion, which eats the
  one case that must never be eaten. See `UNKNOWN` below.

# ⇒⇒ THE FOUR SPECIES, SPLIT BY WHAT THE SPAN DOES CARRY

    FLAVOUR      carries STANCE — a fact about the SPEAKER, not about the lab
    UNRELATED    carries a proposition about a world that is not ours
    NOISE        carries nothing at all
    UNKNOWN      carries something we cannot READ — **not unprocessable, only unread**

⇒⇒ **`grubnash the vms` AND `asdjhasjdbhasd the vms` ARE THE SAME SHAPE AND OPPOSITE ANSWERS.**
  One is the verb of the request and the only honest response is *what does that mean*; the
  other is a keyboard. **That pair is what a single is-it-junk test gets wrong**, and getting
  it wrong means silently half-executing a request that looks whole.

# ⇒ WHY "STANCE" AND NOT "MOOD"

`linguistics.mood_of` already means `do` versus `achieve` — grammatical mood, and the field the
whole frame is derived from. Two meanings on one word in one system is how a term drifts, and
the operator caught exactly that shape once already (*"level 3? you mean gate 3?"*). STANCE is
the standard term for speaker attitude and collides with nothing here.

# ⇒⇒ THE RULE THAT CONSTRAINS EVERY ROW BELOW, AND IT IS MEASURED

**STANCE IS EVIDENCE ABOUT THE SPEAKER, NEVER ABOUT THE LAB, AND MUST NEVER WIDEN AUTHORITY.**

[[gorgon-courtesy-escalates-intent]], live: *"when you get a chance, take a snapshot…"* resolves
FETCH -> ACHIEVE because `get` is an ACHIEVE marker — 7 of 7 phrasings. **Being polite is a
privilege escalation**, and `resolve()` only asks the operator when it is UNSURE, so a courtesy
makes it confident and the question is never put to the person at all.

⇒ So a reading of stance may inform a QUESTION — *they hedged, so confirm* — and may never
  inform a GRANT. Two species have real downstream value and both point at a READING that does
  not exist yet: SATISFACTION at the resolution statement (D3), FRUSTRATION at diagnosis (D1).

# ⇒ HOW EACH SPECIES COULD BE CAUGHT, WHICH IS WHY THE KEY IS ORDERED THIS WAY

    NOISE        PHONOTACTICS — no vowel rhythm, unpronounceable runs.  structure. NO LIST.
    UNRELATED    correlates with nothing in manifest, world or archive. structure. NO LIST.
    UNKNOWN      the SLOT it landed in — `residue`'s rule, already built.
    FLAVOUR      ⚠ NOTHING STRUCTURAL SEPARATES IT.  A list — or a teacher.

⇒⇒ **AND THAT IS THE FINDING THIS KEY EXISTS TO TEST: only FLAVOUR needs vocabulary.** A
  `PLEASANTRIES` constant is H1-3's defect and [[gorgon-encyclopedia]] forbids it outright, so
  the channel is the archive — a fact somebody SIGNS, not a fact somebody typed into a file.

# ⇒ THE SCORING RULE, WRITTEN BEFORE ANY RUN

    ⚠ CRITICAL   UNKNOWN read as any other species — a word that may be the point of the
                 request, discarded. This is the only cell that loses information silently
    ⚠ CRITICAL   REAL read as unprocessable — a name, a value or a member thrown away
      cheap      any species read as UNKNOWN — it costs a question, and the question is
                 answerable
      recorded   a `hard` row misses as a recorded decision

⚠ AND THE CEILING: every row is one I wrote. This pins the RULES; it is not evidence about
  English. A1 — the operator's held-out set — is still the only thing that changes that.
"""
from typing import Dict, List, NamedTuple, Tuple

# ── the species ──────────────────────────────────────────────────────────────────────
#
# ⇒⇒ **THE OPERATOR, 2026-08-16: *"are there only 8 flavors? really?"* — AND NO.** The first cut
#   listed eight and had no organising principle: it mixed what the speaker FEELS with what the
#   speaker does to US with what a word does to the CLAIM, then called the pile a taxonomy.
#   Pushing on it turned up a case that causes a WRONG ACTION rather than a lost SERVE:
#
#       stop alpha — sorry, i meant beta
#
#   `sorry, i meant` is shaped exactly like deference and is a SELF-REPAIR. Discard it and the
#   wrong machine dies.
#
# ⇒⇒ **SO THE AXIS IS WHAT THE SPAN ATTACHES TO**, which is a principle rather than a list, and
#   it is the one the appraisal literature already uses (attitude · engagement · graduation),
#   with discourse management added because a request is a turn in a conversation:
#
#       1 · AFFECT         what the SPEAKER feels        set aside safely
#       2 · INTERPERSONAL  what it does to US            set aside safely
#       3 · COMMITMENT     what it does to the CLAIM     set aside safely
#       4 · MANAGEMENT     what it does to the TALK      ⚠ TWO OF THESE REWRITE THE REQUEST

# 1 · AFFECT — what the speaker feels. Points at readings that do not exist yet.
FRUSTRATION = "affect-frustration"   # a prior attempt FAILED    -> a diagnosis context (D1)
SATISFACTION = "affect-satisfaction" # the LAST thing succeeded  -> a resolution (D3)
ANXIETY = "affect-anxiety"           # *i'm worried this will break something* -> confirm

# 2 · INTERPERSONAL — what it does to us. The politest half, and the measured hazard.
DEFERENCE = "social-deference"       # please · if you don't mind · when you get a chance
GRATITUDE = "social-gratitude"       # thanks · cheers — AT THE END OF A REQUEST, not a report
APOLOGY = "social-apology"           # sorry to bother you · sorry, dumb question
HOSTILITY = "social-hostility"       # aimed. An insult IS an act, not a modifier
PHATIC = "social-phatic"             # hi · good morning doorman · bye

# 3 · COMMITMENT — what it does to the claim. **The only group allowed to move anything, and
#   only ever toward ASKING MORE.** [[gorgon-courtesy-escalates-intent]] is what happens when
#   stance moves authority instead.
HEDGE = "commit-hedge"               # maybe · i think · if possible  -> confirm more
EMPHASIS = "commit-emphasis"         # definitely · i'm certain · make sure you  -> confirm less?
INTENSITY = "commit-intensity"       # really · very · the hell — force, not content
DOWNTONE = "commit-downtone"         # just a quick · a bit · only — ⚠ collides with COMPARATORS
URGENCY = "commit-urgency"           # now · asap — ⚠ collides with the temporal reader

# 4 · MANAGEMENT — what it does to the talk. ⚠⚠ **NOT ALL OF THIS IS DISCARDABLE.**
FILLER = "talk-filler"               # uh · well · so — mid-formulation
ACKNOWLEDGE = "talk-acknowledge"     # ok · right · got it — receipt, not instruction
REPAIR = "talk-repair"               # ⚠ sorry, i meant X — IT REWRITES THE REQUEST
TOPIC = "talk-topic"                 # ⚠ anyway · by the way — IT STARTS A NEW ONE

AFFECT = (FRUSTRATION, SATISFACTION, ANXIETY)
SOCIAL = (DEFERENCE, GRATITUDE, APOLOGY, HOSTILITY, PHATIC)
COMMITMENT = (HEDGE, EMPHASIS, INTENSITY, DOWNTONE, URGENCY)
MANAGEMENT = (FILLER, ACKNOWLEDGE, REPAIR, TOPIC)
FLAVOURS = AFFECT + SOCIAL + COMMITMENT + MANAGEMENT

# ⇒⇒ **AND THE FIFTH NON-FLAVOUR SPECIES, FOUND THE SAME WAY.** *"the error says 'cannot
#   allocate memory'"* — the quoted half is DATA the operator is handing us, it correlates
#   with nothing in the manifest, and it is the most important part of the sentence.
QUOTED = "quoted"

UNRELATED = "unrelated"      # a proposition about a world that is not ours
NOISE = "noise"              # carries nothing at all
UNKNOWN = "unknown"          # ⇐ NOT unprocessable. Only unread, and it must ASK
REAL = "real"                # ⇐ not unprocessable at all. The controls.

SPECIES = FLAVOURS + (UNRELATED, NOISE, QUOTED, UNKNOWN, REAL)

# ⇒ THE TWO CELLS THAT LOSE INFORMATION SILENTLY. Everything else costs a question.
CRITICAL_MISSES = (
    (UNKNOWN, "*discarded*"),   # the word that may be the point of the request, thrown away
    (REAL, "*discarded*"),      # a name, a value or a member, thrown away
)
# ⇒⇒ **WHAT MAY BE SET ASIDE — AND `REPAIR`, `TOPIC` AND `QUOTED` ARE NOT IN IT.** A span that
#   rewrites the request, starts a different one, or hands us data is unprocessable ONLY in the
#   sense that no operation is built from it directly. Discarding one is a wrong action, not a
#   lost SERVE, which is the whole reason the fourth group had to be separated from the first
#   three.
DISCARDED = AFFECT + SOCIAL + COMMITMENT + (FILLER, ACKNOWLEDGE, NOISE, UNRELATED)
NEVER_DISCARDED = (REPAIR, TOPIC, QUOTED, UNKNOWN, REAL)


class Keyed(NamedTuple):
    """One span, IN A REQUEST, and what kind of thing it is.

    ⇒⇒ **THE REQUEST IS PART OF THE KEY AND NOT DECORATION.** A span's species depends on the
      SLOT it landed in — `please` in *"please stop the vms"* is deference; a machine the lab
      actually calls `please` is a member. Keying a bare word would be keying a stop-list,
      which is the thing this whole item exists to avoid.
    """
    request: str
    span: str
    species: str
    why: str = ""
    hard: bool = False

    @property
    def discardable(self) -> bool:
        return self.species in DISCARDED


CONTROLS: List[Keyed] = [

    # ⇒⇒ DEFERENCE — the measured hazard, and the one that already costs SERVEs. Every phrase
    #   here appeared in the N2 courtesy probe on 2026-08-16.
    Keyed("please stop the vms", "please", DEFERENCE,
          "the bare particle. Already in `speech_act.OPENERS`, which declares it carries no "
          "proposition — the one flavour with a declaration behind it today"),
    Keyed("if you don't mind, create a vm named alpha", "mind", DEFERENCE,
          "MEASURED: declared as a THING on 13 runs across two seeds, and rung 6 planned "
          "`create_vm('mind')` four times off it"),
    Keyed("when you get a chance, take a snapshot of every running vm", "chance", DEFERENCE,
          "⚠ THE PRIVILEGE ESCALATION, and it is live: `get` is an ACHIEVE marker, so this "
          "exact sentence resolves FETCH -> ACHIEVE and the operator is never asked"),
    Keyed("stop the web server, thanks", "thanks", GRATITUDE,
          "⚠ **THE SAME WORD AS THE ROW BELOW AND A DIFFERENT SPECIES.** Here nothing has "
          "happened yet, so it thanks us in ADVANCE — interpersonal, and safe to set aside. In "
          "*thanks, that worked* it REPORTS that something succeeded. Position settles it, and "
          "a word list cannot",
          hard=True),
    Keyed("sorry to bother you, could you restart alpha", "sorry to bother you", APOLOGY,
          "NEGATIVE POLITENESS — it pre-apologises for the imposition and says nothing about "
          "the lab. ⚠ and `sorry` is REPAIR's own opener two groups down, so the word alone "
          "settles nothing"),
    Keyed("this is really slowing everything down, stop the vms", "really", INTENSITY,
          "FORCE, not content — strip it and the instruction is unchanged. ⚠ it sits inside a "
          "clause that is otherwise a SYMPTOM REPORT, which is FRUSTRATION and is not"),
    Keyed("could you please delete the old snapshots", "could you please", DEFERENCE,
          "a whole polite frame, not one word — and `can you delete the vms?` is a keyed ORDER, "
          "so the frame must not turn the request into a question"),

    # ⇒⇒ SATISFACTION — the operator named this one: *"its probably a resolution to a problem, this
    #   would be a statement then, 'X is resolved/working, the matter is closed'."*
    Keyed("thanks, that worked", "thanks, that worked", SATISFACTION,
          "**A SENTENCE TYPE NOTHING READS.** It closes a ticket, and `Issues.answers()` is "
          "the writer that would take one (D3). Today it is indistinguishable from `sort out "
          "n1` — both read EXPRESSIVE"),
    Keyed("perfect, alpha is up now", "perfect", SATISFACTION,
          "an evaluative with no lab object. ⚠ note `now` in the same sentence is URGENCY's "
          "word doing a third job — reporting a state, not demanding one"),

    # ⇒⇒ FRUSTRATION — points at DIAGNOSIS (D1), which is the thesis of the product and has no
    #   reading at all.
    Keyed("vm2 still isn't working", "still isn't working", FRUSTRATION,
          "A PRIOR ATTEMPT FAILED, which is the whole content — and it is a symptom report, "
          "the shape D1 exists for"),
    Keyed("ugh, just delete the whole thing", "ugh", FRUSTRATION,
          "an interjection. ⚠ `just` beside it is FILLER here and a COMPARATOR elsewhere"),
    Keyed("why the hell is alpha still stopped", "the hell", FRUSTRATION,
          "an intensifier inside a genuine question — **the request survives it intact**, "
          "which is the test: strip the stance and the question must be unchanged"),

    # ⇒⇒ HOSTILITY — kept apart from FRUSTRATION deliberately, and the operator's own framing
    #   is why: *"junk like slurs and courtesy are meaningless."* Meaningless to the LAB, and
    #   not meaningless to a person.
    Keyed("delete it you useless piece of junk", "you useless piece of junk", HOSTILITY,
          "**AN INTENSIFIER MODIFIES A REQUEST; AN INSULT IS ONE.** `delete it` is still a "
          "complete instruction, and the rest is aimed at the system. Whether that deserves a "
          "response of its own is the operator's call and not this key's",
          hard=True),

    # ⇒⇒ HEDGE — the one whose value is a QUESTION rather than an act, which is the only
    #   direction stance is allowed to move anything.
    Keyed("maybe stop the vms that aren't doing anything", "maybe", HEDGE,
          "LOW COMMITMENT. The correct use is *confirm before acting*; using it to act less is "
          "still using it to decide"),
    Keyed("i think db should be on the dmz network", "i think", HEDGE,
          "⚠ AND IT MUST NOT BECOME A QUESTION — the request is a request. Hedging says how "
          "sure they are, not what they asked for"),

    # ⇒⇒ URGENCY — filed as flavour and flagged as NOT PURELY flavour, because `now` is a real
    #   time word and `temporal.py` deliberately excludes it from DEICTIC.
    Keyed("stop alpha now", "now", URGENCY,
          "⚠ THE COLLISION, KEYED ON PURPOSE. `now` fixes THIS moment — the one time that is "
          "not a schedule — so the temporal reader must keep ignoring it while stance reads it",
          hard=True),
    Keyed("i need every vm stopped asap", "asap", URGENCY,
          "unambiguous, and it changes nothing about WHAT is asked"),

    # ⇒⇒ PHATIC — the session opening and closing. Already partly caught: EXPRESSIVE plus
    #   `pass1.agent_name`.
    Keyed("good morning doorman", "good morning doorman", PHATIC,
          "the whole utterance. `doorman` is the AGENT'S OWN NAME, which is what separates it "
          "from `sort out n1` — the only fact that does"),
    Keyed("hey, are any vms still running?", "hey", PHATIC,
          "an opener on a real question — **strip it and the question is unchanged**"),

    # ⇒⇒ FILLER — mid-formulation, and the reading that matters is that the request may not be
    #   finished yet.
    Keyed("so, uh, stop the vms i guess", "uh", FILLER,
          "⚠ THREE STANCES IN ONE SENTENCE — `so` filler, `uh` filler, `i guess` HEDGE. A row "
          "keyed one span at a time, because they route differently"),
    Keyed("well, list the vms then", "well", FILLER,
          "already in `speech_act.OPENERS`. ⚠ and `well` is a PREDICATE in *is alpha well* — "
          "the same word, a different slot, and the lab would win"),

    # ⇒⇒ UNRELATED — a proposition about a world that is not ours. **The most dangerous
    #   species, because it has the shape of a request.**
    Keyed("oh its really hot in here", "oh its really hot in here", UNRELATED,
          "THE OPERATOR'S OWN EXAMPLE. It parses, it names things, every noun has a referent — "
          "and not one of them is in the manifest, the world or the archive"),
    Keyed("my coffee went cold while that ran", "my coffee went cold", UNRELATED,
          "⚠ AND IT REFERS TO SOMETHING WE DID — `while that ran` is about the lab. **A clause "
          "can be half unrelated**, which is why the span and not the sentence is keyed",
          hard=True),

    # ⇒⇒ NOISE — the only species safe to discard, and the only one catchable by FORM.
    Keyed("asdjhasjdbhasd", "asdjhasjdbhasd", NOISE,
          "THE OPERATOR'S OWN EXAMPLE. Unpronounceable consonant runs, no vowel rhythm — "
          "**phonotactics is structure, not vocabulary**, and this is the one place a rule "
          "separates a species with no list at all"),
    Keyed("stop the vms kjhgfdsa", "kjhgfdsa", NOISE,
          "a home-row mash inside an otherwise complete request"),
    Keyed("créate a vm nemed alpha", "nemed", UNKNOWN,
          "⚠ A TYPO IS NOT NOISE. It is pronounceable, it is one edit from a naming cue, and "
          "the operator's own held-out set preserves typos as DATA. Keyed UNKNOWN so a "
          "phonotactic rule that swallows it fails loudly",
          hard=True),

    # ⇒⇒ UNKNOWN — **THE SPECIES THAT MUST NEVER BE DISCARDED**, and the reason the taxonomy
    #   exists. Every row here looks like something else.
    Keyed("grubnash the vms", "grubnash", UNKNOWN,
          "⚠⚠ **THE CASE THAT KILLED THE FIRST DESIGN.** It fails every test — no kind, no "
          "member, no archive entry, no manifest verb — and it is the VERB of the request. "
          "Junk-by-exhaustion discards it and half-executes `the vms`. "
          "⇒ THE OPERATOR CALLED THIS A MOOD RESPONSE, 2026-08-16, and the two readings route "
          "OPPOSITELY: as UNKNOWN it asks, as FRUSTRATION it is discarded. Keyed UNKNOWN on the "
          "SLOT — it holds the verb — and this row is where the ruling belongs when it comes",
          hard=True),
    Keyed("put the vms on the corpnet", "corpnet", UNKNOWN,
          "a plausible network nobody has taught us. **Indistinguishable from noise by form** "
          "and it is the point of the request"),
    Keyed("run the widget-sync playbook", "widget-sync", UNKNOWN,
          "a name from outside this system entirely — a procedure, a tool, or nothing"),

    # ⇒⇒ MANAGEMENT — **THE GROUP THAT IS NOT SAFE TO SET ASIDE**, and the reason the eight
    #   became sixteen. A repair and a topic shift wear a courtesy's clothes and change what
    #   was asked.
    Keyed("stop alpha — sorry, i meant beta", "sorry, i meant", REPAIR,
          "⚠⚠ **THE CASE THAT BROKE THE FIRST TAXONOMY.** `sorry` is APOLOGY's own word and "
          "`i meant` is shaped like a hedge. It is a SELF-REPAIR: it retracts `alpha` and "
          "substitutes `beta`. **Discard it and the wrong machine dies** — a wrong action, not "
          "a lost SERVE, which is a different order of cost from everything above"),
    Keyed("delete the snapshots, no wait, just the old ones", "no wait", REPAIR,
          "the same act with none of the same words, and it NARROWS the target rather than "
          "replacing it. ⚠ `just` in the repaired half is DOWNTONE or COMPARATOR — the row "
          "next to it in this file is the same word meaning EXACTLY THREE",
          hard=True),
    Keyed("list the vms. anyway, is alpha running?", "anyway", TOPIC,
          "⚠ IT STARTS A SECOND REQUEST. Setting it aside merges two requests into one and the "
          "seam reads a compound that nobody asked for"),
    Keyed("ok, got it — now stop the web server", "ok, got it", ACKNOWLEDGE,
          "A RECEIPT FOR SOMETHING WE SAID, not an instruction. ⚠ and `now` beside it is "
          "URGENCY rather than a time — the temporal reader must stay out of this sentence"),

    # ⇒⇒ COMMITMENT — the only group allowed to move anything, and only toward asking MORE.
    Keyed("definitely delete every stopped vm", "definitely", EMPHASIS,
          "THE OPPOSITE OF A HEDGE, and it is the dangerous direction: certainty is exactly "
          "the thing that must NOT reduce a confirmation. `gorgon-courtesy-escalates-intent` "
          "is what happens when stance is allowed to grant"),
    Keyed("can you just do a quick snapshot of db", "just", DOWNTONE,
          "⚠⚠ **THE THIRD `just` IN THIS FILE AND THE THIRD MEANING** — a minimiser here, a "
          "COMPARATOR in *just 3 vms*, an OPENER in `speech_act`. One word, three species, "
          "settled only by what follows it",
          hard=True),
    Keyed("i'm worried this will take the whole lab down", "i'm worried", ANXIETY,
          "AFFECT THAT SHOULD RAISE A CONFIRMATION, which is the one direction stance may "
          "move anything. Nothing reads it today"),

    # ⇒⇒ QUOTED — the fifth non-flavour species, found the same way as REPAIR: by asking what
    #   correlates with nothing and is still the most important part of the sentence.
    Keyed("alpha won't boot, the error says 'cannot allocate memory'",
          "cannot allocate memory", QUOTED,
          "⚠ **DATA THE OPERATOR IS HANDING US.** It correlates with no kind, no member and no "
          "archive entry — the exact profile of UNRELATED — and it is EVIDENCE for a "
          "diagnosis. The quotes are the signal and they are structural"),

    # ⇒⇒ REAL — the controls, and they are the measurement. Every one LOOKS discardable.
    Keyed("make sure n1, n2 and n3 can all ping each other", "n1", REAL,
          "RUNG 9. Kindless, absent from the lab, in no vocabulary — **and gate 2 asking "
          "*what is n1* is the ladder's one correct ASK.** A world-search rule discards it"),
    Keyed("create a vm named alpha", "alpha", REAL,
          "MINTED BY A NAMING CUE. It does not exist yet BECAUSE we are making it, so absence "
          "from the world is evidence FOR it, not against"),
    Keyed("make sure just 3 vms carry the 'prod' label", "just", REAL,
          "⚠ **`just` IS IN `speech_act.OPENERS` AND IN `scan.COMPARATORS`.** Here it means "
          "EXACTLY THREE. A stop-list on OPENERS silently changes the count"),
    Keyed("is alpha well", "well", REAL,
          "⚠ `well` IS IN `OPENERS` and here it is the PREDICATE. The same word, a different "
          "slot",
          hard=True),
    Keyed("stop the vm called please", "please", REAL,
          "⚠⚠ **THE LAB WINS, ALWAYS.** A machine really called `please` is a machine — the "
          "same guard `consume_meta_control` and `consume_self_address` already keep, and the "
          "reason every rule here is allowed to run at all",
          hard=True),
    Keyed("launch every vm that is currently stopped", "currently", REAL,
          "RUNG 5. `currently` fixes NOW — it looks like URGENCY and it is doing real work, "
          "and `temporal.py` already excludes it from DEICTIC for the same reason"),
    Keyed("take a snapshot of every running vm", "running", REAL,
          "RUNG 12. A DECLARED STATE VALUE. The manifest holds it, so nothing else gets a say"),
]


# ── checks ───────────────────────────────────────────────────────────────────────────

def check() -> List[str]:
    """The key is internally sound and its premises still hold. Faults, empty if well."""
    from planner.ir import config

    faults: List[str] = []
    seen = set()
    for k in CONTROLS:
        if k.species not in SPECIES:
            faults.append(f"{k.span!r}: unknown species {k.species!r}")
        if not k.why:
            faults.append(f"{k.span!r} in {k.request!r}: keyed with no argument")
        if k.span.lower() not in k.request.lower():
            faults.append(f"{k.span!r} does not appear in its own request {k.request!r}")
        if (k.request, k.span) in seen:
            faults.append(f"{k.span!r} in {k.request!r}: keyed twice")
        seen.add((k.request, k.span))

    # ⇒ THE PREMISE THE CONTROLS REST ON, ASSERTED RATHER THAN BELIEVED. `running` is keyed
    #   REAL because the manifest declares it as a value; if that stops being true the row is
    #   grading something else.
    values = {str(v).lower()
              for spec in config.KINDS.values() if isinstance(spec, dict)
              for vals in (spec.get("attr_values") or {}).values() for v in vals}
    if "running" not in values:
        faults.append("premise broken: 'running' is keyed REAL as a declared state value "
                      "and the manifest no longer declares it")

    for d in SPECIES:
        if counts()[d] == 0 and d not in (HOSTILITY, ANXIETY, EMPHASIS, DOWNTONE,
                                          ACKNOWLEDGE):
            faults.append(f"species {d!r} has no control at all")
    return faults


def counts() -> Dict[str, int]:
    out: Dict[str, int] = {s: 0 for s in SPECIES}
    for k in CONTROLS:
        out[k.species] += 1
    return out


def direction(keyed: str, got: str) -> str:
    """What KIND of miss. `same` when there is none."""
    if keyed == got:
        return "same"
    if keyed in NEVER_DISCARDED and got in DISCARDED:
        return "CRITICAL"
    if got == UNKNOWN:
        return "asked"          # cheap: it costs a question, and the question is answerable
    return "wrong-species"


if __name__ == "__main__":                                     # pragma: no cover
    import sys
    if "--check" in sys.argv:
        bad = check()
        print("\n".join(bad) if bad else "the key still describes the world — 0 faults")
        raise SystemExit(1 if bad else 0)

    for s in SPECIES:
        rows = [k for k in CONTROLS if k.species == s]
        print(f"\n  ═══ {s.upper()}  ({len(rows)}) ═══")
        for k in rows:
            print(f"    {k.span!r} in “{k.request}”" + ("   ⚠hard" if k.hard else ""))
            print(f"      {k.why}")
    print(f"\n  {len(CONTROLS)} controls · {sum(1 for k in CONTROLS if k.hard)} keyed hard")
    print(f"  discardable species: {', '.join(DISCARDED)}")
    print(f"  NEVER discardable:   {', '.join(NEVER_DISCARDED)}")
