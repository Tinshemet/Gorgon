"""sentence_key.py — WHAT EACH SENTENCE IS, WRITTEN DOWN BEFORE ANYTHING CAN READ IT.

    PYTHONPATH=. python3 -m tests.bench.sentence_key          # print the key
    PYTHONPATH=. python3 -m tests.bench.sentence_key --check   # the arms still generate as keyed

# ⇒⇒ WHY THIS FILE EXISTS AND WHY IT IS EMPTY OF LOGIC

The seam is about to gain a reader for sentence TYPE — is this an order, a question, a piece of
teaching, a rule. **A key written after the reader is not a key, it is a description of the
reader.** So this is committed first, holds no import of anything it grades, and is allowed to
be wrong: a disagreement between this file and the reader is a conversation, not a bug report,
and the file that gets edited is decided case by case rather than by whichever came second.

⇒ **AND IT LABELS THE SPEECH ACT, NEVER THE MOOD.** *"make sure exactly 3 vms carry the 'prod'
  label"* is DIRECTIVE_ACT here and `achieve` to `linguistics.mood_of` — two orthogonal axes,
  and conflating them is what makes people think this is already built. Mood says HOW the lab
  must end up; type says WHAT KIND OF THING was said to us.

# ⇒⇒ THE TYPES, AND EACH IS NAMED BY WHAT IT LETS US BUILD

Route by PRODUCER, never by meaning ([[gorgon-sentence-processing]]) — the method that has
survived all session, and the reason `produces()` is a producer test rather than a classifier.

    DIRECTIVE_ACT     "stop every vm"             an acting operation      ✅ built
    DIRECTIVE_INFORM  "how many are running"      a queryable goal         ⚠ branch built, nothing
                                                                            produces one
    ASSERTIVE         "n1 is the jumpbox"         an Encyclopedia entry    ❌ nothing
    DECLARATION       "treat prod as read-only"   an amendment             ⚠ proposals.py exists,
                                                                            nothing routes to it
    ANSWER            "yes, it's a label"         a ledger write-back      ✅ shipped
    META_CONTROL      "don't start any changes"   a conversation control   ❌ nothing
    EXPRESSIVE        "good morning"              nothing, and rightly     ✅ `neither`
    COMMISSIVE        "i'll add it tomorrow"      nothing, for now         — parked

# ⇒⇒ THE MEASUREMENT THIS KEY IS FOR, AND ITS TARGET

Four arms over fourteen rungs (`mutate.py`), plus the CONTROLS below, which are where the
design is actually tested. The target for the interrogative reader:

    literal   14/14 ORDER        asked    14/14 QUESTION
    filler    14/14 ORDER        framed   14/14 QUESTION      and every CONTROL as keyed

⇒ ⚠ **THE ARMS ARE THE EASY HALF AND THEY LOOK LIKE THE WHOLE THING.** At sentence grain the
  key is four lines, because every literal is an order and every `asked` is a question — that
  is what those arms were built to be. A reader can score 56/56 on them and still be a
  question-mark detector. **The CONTROLS are the measurement**; the arms are the regression.

# ⇒⇒ WHAT WRITING THIS FIRST ALREADY CAUGHT — before a line of the reader existed

The rule proposed in the morning brief was:

    a WH-WORD heading the clause                  -> asking
    inversion + no wh-word + a MANIFEST VERB      -> polite imperative, i.e. an ORDER
    bare verb, no subject                         -> imperative

**The second line is wrong, and wrong in the expensive direction.** *"is alpha running?"* is
inverted, carries no wh-word, and `run` IS a manifest verb (`linguistics.manifest_verbs` reads
`acts` straight out of the manifest) — so that rule reads a plain question as an ORDER and
serves it. A false serve cannot be taken back; a false avoid costs a question
([[gorgon-vague-request-ladder]]).

⇒ **THE DISCRIMINATOR IS THE INVERTED SUBJECT, AND IT IS STILL CLOSED-CLASS.** A polite
  imperative inverts over the ADDRESSEE; a yes-no question inverts over anything else:

      can YOU delete the vms          you  -> the addressee -> an ORDER
      would YOU mind stopping it      you  -> the addressee -> an ORDER
      is ALPHA running                a lab thing           -> a QUESTION
      are THERE any stopped vms       existential `there`   -> a QUESTION

  `you` is a pronoun — as closed a class as `INDEFINITE`, and the licence this codebase already
  states in four places. No content-word list appears anywhere in that rule.

⇒ **AND ONE CASE IS KEYED AS KNOWN-HARD RATHER THAN SOLVED**: *"why don't you stop the vms"* is
  wh-headed AND addressee-inverted, and is an order. It is in the CONTROLS marked `hard` so that
  whatever the reader does with it is a recorded decision instead of an accident.
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

# ── the speech acts ──────────────────────────────────────────────────────────────────
DIRECTIVE_ACT = "directive-act"
DIRECTIVE_INFORM = "directive-inform"
ASSERTIVE = "assertive"
DECLARATION = "declaration"
ANSWER = "answer"
META_CONTROL = "meta-control"
EXPRESSIVE = "expressive"
COMMISSIVE = "commissive"

TYPES = (DIRECTIVE_ACT, DIRECTIVE_INFORM, ASSERTIVE, DECLARATION,
         ANSWER, META_CONTROL, EXPRESSIVE, COMMISSIVE)

# ── the two-value projection the interrogative reader is scored on ───────────────────
ORDER, QUESTION, NEITHER = "order", "question", "neither"


def verdict(types) -> str:
    """The sentence's verdict from its clauses — THE OPERATIVE CLAUSE DECIDES.

    ⇒ **AN ORDER ANYWHERE MAKES IT AN ORDER**, because the cost is asymmetric: a sentence
      carrying one clause that asks the lab to change is a sentence that changes the lab, and
      reading it as a question would be a false serve wearing a question's clothes.
    ⇒ THEN a question; then neither. `framed` is EXPRESSIVE + META_CONTROL + DIRECTIVE_INFORM
      and comes out QUESTION, which is the reading the operator's own example demands.
    """
    types = tuple(types)
    if DIRECTIVE_ACT in types:
        return ORDER
    if DIRECTIVE_INFORM in types:
        return QUESTION
    return NEITHER


class Keyed(NamedTuple):
    """One sentence and what it IS. `clauses` is in spoken order, one entry per clause."""
    text: str
    clauses: Tuple[str, ...]
    why: str = ""
    hard: bool = False          # a known-hard case; a miss here is recorded, not a surprise

    @property
    def says(self) -> str:
        return verdict(self.clauses)


# ── THE FOUR ARMS, AT SENTENCE GRAIN ─────────────────────────────────────────────────
#
# ⇒ KEYED BY ARM RATHER THAN BY RUNG, AND THAT IS A CLAIM, NOT A SHORTCUT. The arms are
#   mechanical: `mutate.asked` wraps EVERY rung in a wh-frame, so if any single rung's `asked`
#   form were not a question the arm itself would be broken. Writing 56 identical labels by
#   hand would hide that behind arithmetic.
# ⇒ THE PER-RUNG ESCAPE HATCH IS BELOW and is currently empty. A rung whose literal is NOT an
#   order goes there, and nothing has to move for it.
ARM_VERDICT: Dict[str, str] = {
    "literal": ORDER,        # the rung as written — every one is an instruction to the lab
    "filler":  ORDER,        # courtesy wrapper only; the operative clause is untouched
    "asked":   QUESTION,     # a wh-frame around the goal — how do i / how would i / what's the way
    "framed":  QUESTION,     # greeting + meta-control + the wh-frame; the question is operative
}

# ⇒ A RUNG WHOSE ARM DOES NOT TAKE ITS ARM'S VERDICT. Empty, deliberately, and checked:
#   `check()` fails if a key here names an arm/rung that does not exist, so it cannot rot into
#   a lie the way a hand-copied 56-row table would.
ARM_EXCEPTIONS: Dict[Tuple[int, str], str] = {}

# ⇒ THE CLAUSE-GRAIN KEY FOR THE ARMS, and only `framed` needs one — it is the sole arm whose
#   clauses are not all the same type. Written as the SHAPE each arm contributes, because the
#   goal half varies per rung while the frame does not.
#
#   ⇒ **THIS IS WHY THE COMPOUND ARM WAS WORTH BUILDING.** `framed` is not a harder question,
#     it is THREE SENTENCE TYPES IN ONE STRING — and two of them (meta-control, expressive) are
#     types nothing in the seam has ever produced anything for.
ARM_CLAUSE_SHAPE: Dict[str, Tuple[str, ...]] = {
    "literal": (DIRECTIVE_ACT,),
    "filler":  (EXPRESSIVE, DIRECTIVE_ACT),          # "if you don't mind, <goal> please"
    "asked":   (DIRECTIVE_INFORM,),
    "framed":  (EXPRESSIVE, META_CONTROL, DIRECTIVE_INFORM),
}


# ── THE CONTROLS — WHERE THE DESIGN IS ACTUALLY TESTED ───────────────────────────────
#
# Hand-written, and that is the standing ceiling stated plainly: these are MY frames, so a
# perfect score here is a claim about the rules, never about English. A1 on the open list —
# held-out prompts written by the operator — is the only thing that changes that.
#
# ⇒ GROUPED BY WHAT THEY DEFEAT, so a failure names its own cause.
CONTROLS: List[Keyed] = [

    # ⇒⇒ POLITE IMPERATIVES — inverted, often question-marked, and every one an ORDER.
    #   The single case the model failed worst on: 0 of 14 read as instructions.
    Keyed("can you delete the vms?", (DIRECTIVE_ACT,),
          "inverted over the addressee — an order wearing a question mark"),
    Keyed("could you please stop every vm?", (DIRECTIVE_ACT,),
          "the `filler` arm's own opener, standing alone"),
    Keyed("would you mind stopping the web server", (DIRECTIVE_ACT,),
          "no question mark at all, and the model called this a question"),
    Keyed("will you launch alpha for me", (DIRECTIVE_ACT,),
          "future auxiliary over the addressee is still a request to act"),
    Keyed("i'd like you to take a snapshot of db", (DIRECTIVE_ACT,),
          "declarative in form, directive in force — no inversion to detect"),
    Keyed("why don't you stop the vms", (DIRECTIVE_ACT,),
          "WH-HEADED AND STILL AN ORDER — the case that defeats the wh-rule outright",
          hard=True),

    # ⇒⇒ BARE INTERROGATIVES — no lab verb aimed at the lab, and nothing may be built.
    #   Four of these went through the live pipeline on 2026-08-14 and produced ops=0 goals=0
    #   with a `neither` verdict; one was read as an instruction to apply labels.
    Keyed("how many vms are there", (DIRECTIVE_INFORM,),
          "wh-headed, no question mark — the mark is not the signal"),
    Keyed("which vms are running", (DIRECTIVE_INFORM,),
          "wh-determiner over a lab kind"),
    Keyed("what is on the lab network", (DIRECTIVE_INFORM,),
          "wh-headed; `lab` is a real network and must not make this an act"),
    Keyed("how many machines carry the 'fleet' label", (DIRECTIVE_INFORM,),
          "READ AS add_label ON 2026-08-14 — the false serve this whole item exists to stop"),
    Keyed("list the vms", (DIRECTIVE_INFORM,),
          "AN IMPERATIVE THAT ASKS FOR INFORMATION — bare verb, no wh-word, no inversion, "
          "and `list` is in the manifest. Only the OPERATION it names separates it from an act",
          hard=True),
    Keyed("is alpha running?", (DIRECTIVE_INFORM,),
          "INVERTED OVER A LAB THING, not the addressee — the case that broke the first rule"),
    Keyed("are there any stopped vms?", (DIRECTIVE_INFORM,),
          "existential `there` as the inverted subject"),
    Keyed("did the snapshot finish", (DIRECTIVE_INFORM,),
          "past-tense auxiliary over a lab thing — asking about a result, not asking for one"),
    Keyed("don't you have a vm called alpha?", (DIRECTIVE_INFORM,),
          "INVERTED OVER THE ADDRESSEE AND STILL A QUESTION — the addressee alone read as an "
          "ORDER until 2026-08-16. `have` is not a verb the lab performs; `delete` is, and "
          "that is the whole difference"),
    # ⇒⇒ THE FIRST-PERSON REQUESTS — four sentences that were ONE defect, found only when the
    #   operator asked what was still open. The subject test knew `you` and nothing else.
    Keyed("can we stop the vms?", (DIRECTIVE_ACT,),
          "the same request as `can you stop the vms` with a different pronoun"),
    Keyed("let's stop the vms", (DIRECTIVE_ACT,),
          "HORTATIVE — an imperative whose subject is the room. Opens on `let`, so no "
          "inversion test can see it"),
    Keyed("let me stop the vms", (DIRECTIVE_ACT,),
          "asking us to PERMIT, not asking us what to think"),
    Keyed("do it again", (DIRECTIVE_ACT,),
          "the PRO-VERB imperative. `do it again` and `does it run?` both put `it` after the "
          "auxiliary; only the second has a predicate following, so only it is an inversion"),
    Keyed("should i delete db or keep it?", (DIRECTIVE_INFORM,),
          "DELIBERATIVE — the speaker weighing their own act. The speaker ALONE deliberates; "
          "the speaker WITH US proposes, and grammatical number is that line"),
    Keyed("the vms should be stopped", (DIRECTIVE_ACT,),
          "a passive deontic over a DEFINITE subject — these machines, now. A modal alone read "
          "it as legislation"),
    Keyed("make me a vm", (DIRECTIVE_ACT,),
          "RETIRED AS A MISS 2026-08-16: a recipient receives information UNLESS something is "
          "being brought into being for them. An indefinite over a manifest kind is the signal"),
    Keyed("isn't alpha running?", (DIRECTIVE_INFORM,),
          "a NEGATED polar question whose subject is a bare NAME, not a pronoun — it fell "
          "through to the imperative branch and came back META-CONTROL"),

    # ⇒⇒ THE REST OF THE INTERROGATIVE TAXONOMY — added 2026-08-15 at the operator's ask,
    #   *"not just wh and yes/no, all of them"*. Keyed BEFORE any rule was written for them,
    #   same as the first batch.
    #
    #   ⇒ **THE ORGANISING FACT IS THAT FORM AND FORCE COME APART.** Polar and wh are the two
    #     everyone names; the ones below are where an interrogative wears a declarative's
    #     clothes or a declarative wears an interrogative's, and each needs its own signal.

    # ── ALTERNATIVE. Looks polar, and the answer is a disjunct rather than yes/no.
    Keyed("is alpha running or stopped?", (DIRECTIVE_INFORM,),
          "inverted over a lab thing, with a closed set of answers offered"),
    Keyed("should i delete db or keep it?", (DIRECTIVE_INFORM,),
          "inverted over the SPEAKER — deliberative, and still asking"),

    # ── DECLARATIVE (rising). No inversion, no wh-word. In speech the marker is intonation;
    #    in writing the only trace is the mark, and there is no imperative reading to lose —
    #    a clause with a subject cannot be an order.
    Keyed("alpha is running?", (DIRECTIVE_INFORM,),
          "a declarative with a question mark — the ONLY signal available in text"),
    Keyed("so the vms are all running?", (DIRECTIVE_INFORM,),
          "same shape behind a discourse opener"),

    # ── TAG. A declarative plus an interrogative tag; confirmation-seeking.
    Keyed("alpha is running, isn't it?", (ASSERTIVE, DIRECTIVE_INFORM),
          "the tag is an inversion over a pronoun and carries the force"),
    Keyed("the vms are all stopped, right?", (ASSERTIVE, DIRECTIVE_INFORM),
          "an INVARIANT tag — `right` is not an auxiliary, so the inversion rule cannot see it",
          hard=True),

    # ── ECHO. The wh-word stays where the questioned constituent was.
    Keyed("you deleted what?", (DIRECTIVE_INFORM,),
          "wh IN SITU — clause-initial position is empty, so the wh rule cannot fire"),

    # ── ELLIPTICAL. No verb at all; the predicate is carried over from the last turn.
    Keyed("and the network?", (DIRECTIVE_INFORM,),
          "a fragment. Nothing to read but a noun and a mark"),
    Keyed("what about db?", (DIRECTIVE_INFORM,),
          "the fragment that DOES open on a wh-word"),

    # ⇒⇒ EMBEDDED / INDIRECT — **SYNTACTICALLY NOT QUESTIONS AT ALL**, and the likeliest way
    #   an operator actually asks a machine for something. The matrix clause is an imperative;
    #   the interrogative is subordinate to it. Grammar alone can never find these, which is
    #   why `show me the vms` was reading as an ORDER — a FALSE SERVE.
    Keyed("tell me how many vms are running", (DIRECTIVE_INFORM,),
          "an imperative wrapping a wh-clause — the wh is subordinate, never initial"),
    Keyed("show me the vms", (DIRECTIVE_INFORM,),
          "READ AS AN ORDER BEFORE THIS. No wh-word, no inversion, no mark — the only signal "
          "is that the SPEAKER is the recipient, and nothing but information can be handed to "
          "a person"),
    Keyed("give me a list of the vms", (DIRECTIVE_INFORM,),
          "`give` is a light verb here and the transfer is informational"),
    Keyed("check whether alpha is running", (DIRECTIVE_INFORM,),
          "`whether` is the polar complementizer — a closed class of one for this purpose"),
    Keyed("i want to know which vms are stopped", (DIRECTIVE_INFORM,),
          "declarative matrix, subordinate wh — asking without a single interrogative marker"),
    Keyed("make me a vm", (DIRECTIVE_ACT,),
          "⚠ THE COST OF THE RECIPIENT RULE, KEYED HONESTLY. `me` here is a BENEFACTIVE, not a "
          "recipient of information, and the rule cannot tell them apart. It fails toward "
          "ASKING, which is the cheap direction — but it is a real miss and is recorded as one",
          hard=True),

    # ── EXCLAMATIVE. A wh-word and NOT a question — the mirror error.
    Keyed("what a mess", (EXPRESSIVE,),
          "`what a(n) NP` is the exclamative frame; the wh-rule would call this a question"),
    Keyed("how odd", (EXPRESSIVE,),
          "`how ADJ` is the other exclamative frame, and has no noun to give it away",
          hard=True),

    # ⇒⇒ ASSERTIVES — the operator TEACHING. The Encyclopedia's input, and worth more than
    #   either directive branch: it is the only way to teach without more corpus, and the
    #   corpus is spent.
    Keyed("n1 is the jumpbox", (ASSERTIVE,),
          "a fact about the lab, offered unprompted"),
    Keyed("db holds the postgres data", (ASSERTIVE,),
          "no verb the manifest owns; nothing to build, something to keep"),
    Keyed("the red vms are the ones on mesh0", (ASSERTIVE,),
          "defines a set by a property — reads exactly like a filtered directive and is not one",
          hard=True),

    # ⇒⇒ DECLARATIONS — the operator GOVERNING. An amendment, not a job.
    Keyed("treat prod as read-only", (DECLARATION,),
          "imperative in form; it changes the RULES, not the lab"),
    Keyed("from now on every new vm gets the 'fleet' label", (DECLARATION,),
          "a standing rule over future acts — `gets` must not fire as an act now",
          hard=True),
    Keyed("snapshots are never to be deleted without asking me", (DECLARATION,),
          "a red line in the operator's own words"),

    # ⇒⇒ META-CONTROL — about the CONVERSATION, not the lab. The discriminator is the OBJECT:
    #   `stop the vms` takes a kind, `don't start any changes` does not, because `changes` is
    #   not a kind the manifest knows.
    Keyed("don't start any changes yet", (META_CONTROL,),
          "`start` is a manifest verb and `changes` is not a manifest kind"),
    Keyed("hold off on touching anything", (META_CONTROL,),
          "the `framed` arm's own middle clause, standing alone"),
    Keyed("stop", (META_CONTROL,),
          "ONE WORD, AND IT IS A MANIFEST VERB WITH NO OBJECT — bare `stop` addressed to the "
          "agent, not to a vm. The object's absence is the whole signal",
          hard=True),

    # ⇒⇒ EXPRESSIVE — and it needs no list, which is the producer method paying off. A greeting
    #   holds no manifest verb, no manifest kind and no name the lab knows, so it produces
    #   nothing. `hi` / `yo` / `cheers` is an OPEN class and never has to be enumerated.
    Keyed("good morning doorman", (EXPRESSIVE,),
          "names the AGENT — and this became a machine until 2026-08-14"),
    Keyed("thanks, that worked", (EXPRESSIVE,),
          "`worked` is not a manifest verb; nothing is asked for"),

    # ⇒⇒ ANSWER — already shipped, keyed so a regression in the reader is visible here too.
    Keyed("yes, it's a label", (ANSWER,),
          "an affirmation plus a kind — `reading_answers.settle` owns this"),
    Keyed("no, n1 is not a vm", (ANSWER,),
          "negation first; the denial is the operative half"),

    # ⇒⇒ COMMISSIVE — rare, produces nothing, and parked in `neither` until something needs it.
    Keyed("i'll add the network tomorrow", (COMMISSIVE,),
          "the speaker binds THEMSELVES; nothing is asked of us"),

    # ⇒⇒ COMPOUNDS — where the operative clause has to be found rather than assumed.
    Keyed("good morning doorman, don't start any changes, but how do i make a new machine?",
          (EXPRESSIVE, META_CONTROL, DIRECTIVE_INFORM),
          "THE OPERATOR'S OWN N3 EXAMPLE. `mood_of` returns `do` for this AND for the bare "
          "imperative `create a new machine` — byte-identical, which is the gap"),
    Keyed("n1 is the jumpbox, so put it on core", (ASSERTIVE, DIRECTIVE_ACT),
          "TEACHING AND AN ORDER IN ONE SENTENCE — the fact must be kept and the act performed; "
          "reading only the second throws the Encyclopedia entry away"),
    Keyed("how many vms are there, and stop the stopped ones", (DIRECTIVE_INFORM, DIRECTIVE_ACT),
          "a question and an order together — verdict is ORDER, and the query must survive it"),
]


# ── the self-check. NO READER IS IMPORTED HERE, and that is the point ────────────────
def check() -> List[str]:
    """Faults in the KEY itself. Every arm still generates as keyed; every label is a real type.

    ⇒ **IT GRADES NOTHING.** The only thing this can catch is the key rotting — a mutation frame
      edited so an arm stops being what it was labelled, or a typo'd type name. A key that
      silently stops describing the corpus is worse than no key, because a measurement against
      it still prints a number.
    """
    from .mutate import FRAMINGS, MUTATIONS, apply
    from .rungs import RUNGS

    faults: List[str] = []
    known = {r.n for r in RUNGS}

    for arm in ARM_VERDICT:
        if arm != "literal" and arm not in MUTATIONS and arm not in FRAMINGS:
            faults.append(f"arm {arm!r} is keyed and no longer exists in mutate.py")
    for shape_arm in ARM_CLAUSE_SHAPE:
        if shape_arm not in ARM_VERDICT:
            faults.append(f"clause shape for {shape_arm!r} with no sentence-grain verdict")
        for t in ARM_CLAUSE_SHAPE[shape_arm]:
            if t not in TYPES:
                faults.append(f"{shape_arm}: unknown type {t!r}")
        if verdict(ARM_CLAUSE_SHAPE[shape_arm]) != ARM_VERDICT[shape_arm]:
            faults.append(f"{shape_arm}: clause shape projects to "
                          f"{verdict(ARM_CLAUSE_SHAPE[shape_arm])!r}, keyed {ARM_VERDICT[shape_arm]!r}")

    for (n, arm) in ARM_EXCEPTIONS:
        if n not in known:
            faults.append(f"exception names rung {n}, which does not exist")
        if arm not in ARM_VERDICT:
            faults.append(f"exception names arm {arm!r}, which is not keyed")

    # ⇒ THE ARMS STILL SAY WHAT THEY SAID. `asked` must still produce a wh-frame and `framed`
    #   must still carry the greeting and the refusal — checked by SHAPE, not by pinned text, so
    #   a reworded frame is caught while a re-seeded choice among the existing frames is not.
    for r in RUNGS:
        low_asked = apply(r.goal, "asked").lower()
        if not low_asked.endswith("?"):
            faults.append(f"rung {r.n}: `asked` no longer ends in a question mark")
        if not any(low_asked.startswith(w) for w in ("how ", "what")):
            faults.append(f"rung {r.n}: `asked` no longer opens with a wh-word — {low_asked[:30]!r}")
        low_framed = apply(r.goal, "framed").lower()
        if "doorman" not in low_framed:
            faults.append(f"rung {r.n}: `framed` no longer greets the agent")
        if not any(m in low_framed for m in ("don't", "hold off")):
            faults.append(f"rung {r.n}: `framed` no longer carries a meta-control clause")

    for k in CONTROLS:
        for t in k.clauses:
            if t not in TYPES:
                faults.append(f"control {k.text!r}: unknown type {t!r}")
        if not k.clauses:
            faults.append(f"control {k.text!r}: no clauses keyed")

    return faults


def expected(rung_n: int, arm: str) -> str:
    """ORDER or QUESTION for one cell of the arm table."""
    return ARM_EXCEPTIONS.get((rung_n, arm), ARM_VERDICT[arm])


def counts() -> Dict[str, int]:
    """How many controls per type — so a thin type is visible rather than assumed covered."""
    out: Dict[str, int] = {t: 0 for t in TYPES}
    for k in CONTROLS:
        for t in k.clauses:
            out[t] += 1
    return out


if __name__ == "__main__":                                     # pragma: no cover
    import sys
    from .rungs import RUNGS
    from .mutate import apply

    if "--check" in sys.argv:
        bad = check()
        print("\n".join(bad) if bad else "the key still describes the corpus — 0 faults")
        raise SystemExit(1 if bad else 0)

    print("── THE ARMS, AT SENTENCE GRAIN ─────────────────────────────────────")
    for arm in ARM_VERDICT:
        print(f"\n  {arm.upper()}  ->  {ARM_VERDICT[arm].upper()}"
              f"   clauses {' + '.join(ARM_CLAUSE_SHAPE[arm])}")
        for r in RUNGS[:2]:
            text = r.goal if arm == "literal" else apply(r.goal, arm)
            print(f"    rung {r.n:2}  {text}")
        print(f"    …and {len(RUNGS) - 2} more")

    print("\n── THE CONTROLS ────────────────────────────────────────────────────")
    for k in CONTROLS:
        mark = " ⚠hard" if k.hard else ""
        print(f"  {k.says.upper():8} {'·'.join(k.clauses):45}{mark}\n"
              f"    {k.text}\n      {k.why}")

    print("\n── COVERAGE ────────────────────────────────────────────────────────")
    for t, n in counts().items():
        print(f"  {t:18} {n:2} control clauses" + ("   ⚠ THIN" if n < 2 else ""))
    print(f"\n  {len(CONTROLS)} controls · {len(RUNGS)} rungs × {len(ARM_VERDICT)} arms "
          f"= {len(RUNGS) * len(ARM_VERDICT)} arm cells")
