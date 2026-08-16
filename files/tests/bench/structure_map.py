"""structure_map.py — EVERY WAY AN ENGLISH SENTENCE IS BUILT, AND WHAT READS IT TODAY.

    PYTHONPATH=. python3 -m tests.bench.structure_map          # the map, with live readings
    PYTHONPATH=. python3 -m tests.bench.structure_map --holes  # only what nothing reads

# ⇒⇒ THE SECOND AXIS, AND IT IS NOT THE ONE `coverage_map` MEASURES

`coverage_map` asks **what kind of thing was said** — an order, a rule, a repair, a greeting.
This asks **how the sentence is BUILT**. They are orthogonal: *"if alpha is stopped, launch
it"* is an ORDER on the first axis and a CONDITIONAL on the second, and it fails on the second.

The operator, 2026-08-16: *"by the end of critical/brain, we need to able to cover everything in
the english language, meaning we complete at least our READ, hopefully even ROUTE… we aren
trying to resolve at 100% but READ should be really good"* — and *"a good read and a good route
means resolve and everything downstream gets better."*

⇒ **SO THIS MAP IS SCOPED TO READ.** A row is COVERED when something turns the structure into
  a fact the rest of the system can use. Whether the writer can then EMIT it is a different
  question and is noted, never scored — E5 (the writer cannot emit `if`) is a RESOLVE hole, and
  a conditional that is READ and cannot be emitted is strictly better than one nobody read.

# ⇒ EVERY ROW IS RUN. `speech_act`, `scan` and `temporal` cost no model call, so the whole map
  re-runs in a second and cannot claim a coverage the code does not have. What it CANNOT see is
  pass 1's model half — where a row's real answer needs the model, the note says so.

# ⇒⇒ FOUR LEVELS, AND THEY ARE EXHAUSTIVE OVER WHERE STRUCTURE LIVES

    PHRASE    inside one clause: what modifies the noun, what fills the slot
    CLAUSE    how clauses combine: coordination, subordination, conditions
    TURN      beyond one string: reference back, repair, the previous turn
    SURFACE   how it was typed: fragments, lists, paste, typos, casing
"""
from typing import List, NamedTuple, Optional

PHRASE, CLAUSE, TURN, SURFACE = "PHRASE", "CLAUSE", "TURN", "SURFACE"


class Feature(NamedTuple):
    level: str
    name: str
    example: str
    reads_it: str        # what turns this structure into a usable fact today; "" is a hole
    note: str = ""
    # ⇒⇒ ⚠ **GRADED ON THE OPERATIONS, NEVER ON THE VERDICT — CORRECTED 2026-08-16.** Four rows
    #   were marked dangerous from the free readers alone, and running the full seam showed two
    #   of them BOUNCE: the unread words reach the span-grain residue check and are asked about.
    #   ⇒ **AND THE OTHER TWO STAYED DANGEROUS FOR A REASON THE VERDICT HID.** They REFUSED —
    #     but because the lab did not hold the machines they named, not because the structure
    #     was caught. `stop alpha or beta` produced `[stop_vm(beta), stop_vm(beta)]`: alpha
    #     dropped, beta doubled. Against a lab that HAS them, that serves.
    #   ⇒ So the test is *what would it DO*, and a refusal caused by an absent machine proves
    #     nothing about the reading.
    danger: bool = False # a hole that changes WHAT RUNS rather than what is understood
    partial: bool = False

    @property
    def hole(self) -> bool:
        """⇒⇒ **A PARTIAL READING IS A HOLE, AND THE FIRST CUT OF THIS FILE COUNTED IT AS
        COVERAGE.** `negated filter` was given a `reads_it` describing what it reads — the
        negator — and scored as covered, while the filter it produces is the OPPOSITE SET.
        A row that names some machinery and still gets the answer wrong is worse than an
        empty one, because it reads as done. Caught by re-reading the tally, not by a test."""
        return (not self.reads_it) or self.partial


MAP: List[Feature] = [

    # ── PHRASE ───────────────────────────────────────────────────────────────────────
    Feature(PHRASE, "determiner", "create a vm · stop the vms · every vm",
            "scan.INDEFINITE · DEFINITE · UNIVERSAL · NOVEL -> existence_from_determiner",
            "the whole existence reading rests on this and it is complete"),
    Feature(PHRASE, "cardinal", "create 5 vms",
            "scan.ENUMERATORS", "numerals and universals in one declared table"),
    Feature(PHRASE, "count comparator", "make sure exactly 3 vms carry 'prod'",
            "scan.COMPARATORS -> max · min · eq", "rung 7 and rung 14 rest on it"),
    Feature(PHRASE, "declared attribute value", "launch every vm that is currently stopped",
            "config.attr_values + value_aliases", "`running`/`stopped`, and `up`/`down` too"),
    Feature(PHRASE, "member list", "make sure n1, n2 and n3 can ping each other",
            "pass2.clauses_of — the member-list rule",
            "took a recorded bug to get right: one clause, not three"),
    Feature(PHRASE, "relative clause", "launch every vm that is currently stopped",
            "speech_act.RELATIVIZERS + scan.conditions_from", "rung 5"),
    Feature(PHRASE, "exception", "put every vm on core, except db",
            "pass1.attach_exclusions", "rung 8"),
    Feature(PHRASE, "reciprocal", "make sure they all ping each other",
            "pass1.consume_reciprocal", "a PREDICATE, not an object — rung 13"),
    Feature(PHRASE, "magnitude comparative", "stop every vm with over 6gb of ram",
            "scan.MAGNITUDE + magnitudes_in -> linguistics/unexpressed-magnitude",
            partial=True,
            note="⚠ MEASURED: `over`, `6gb` and `ram` all come back unread. `scan.COMPARATORS` "
            "declares the COUNT comparators and nothing declares the magnitude ones. "
            "⇒ **READ 2026-08-16** as (gt, 6, gb, memory_mb) — the comparator class is new and "
            "closed, the attribute is the manifest's own through `aliases`. ⚠ PARTIAL: `where` "
            "holds one VALUE per attribute and cannot hold a comparison, so it is NAMED rather "
            "than applied. A representation limit, not a reading one. "
            "⇒ **DOWNGRADED FROM DANGEROUS 2026-08-16 BY RUNNING THE FULL SEAM**: it BOUNCES. "
            "`over` and `6gb` reach the span-grain residue check and are asked about, so the "
            "cost is service and not safety. My first grading said *stops the wrong machines* "
            "and was taken from the free readers alone. ⚠ It does declare a MACHINE CALLED "
            "`ram` — the alias `ram`->memory_mb read as a member name — which is its own bug"),
    Feature(PHRASE, "superlative", "stop the biggest vm",
            "",
            "⚠ `biggest` unread. A superlative needs an ORDERING over an attribute, which is a "
            "different mechanism from a filter — nothing in the manifest declares one",
            danger=True),
    Feature(PHRASE, "units", "give alpha 4 cores and 8gb",
            "",
            "⚠⚠ MEASURED: the whole sentence reads as **None** — unread. `give` is a LIGHT "
            "VERB and `4 cores`/`8gb` are quantity+unit, which nothing pairs. A spec-giving "
            "request is the commonest thing an operator types and it has no reading at all. "
            "⇒ DOWNGRADED FROM DANGEROUS: the full seam BOUNCES, declaring a vm named `4` and "
            "one named `8gb` and complaining about both. Lossy, not unsafe"),
    Feature(PHRASE, "possessive", "delete alpha's snapshots",
            "",
            "⚠ `alpha's` unread as one token — the apostrophe survives tokenisation and the "
            "name is lost. A genitive is a REFERENCE, and the reference is the target"),
    Feature(PHRASE, "prepositional filter", "stop the vms on the lab network",
            "scan — `on` is a declared alias for network", partial=True,
            note=
            "covered by ALIAS rather than by structure: `vm.aliases` maps `on` -> network. "
            "⚠ PARTIAL — it works for the prepositions the manifest happens to alias and for "
            "no others, which is a coincidence rather than a reading"),
    Feature(PHRASE, "reduced relative", "stop the vms running on lab",
            "",
            "⚠ `running` and `lab` unread. The same filter as the relative clause with the "
            "relativizer elided — and the relativizer is what the reader keys on"),
    Feature(PHRASE, "apposition", "alpha, the jumpbox, is down",
            "",
            "⚠ MEASURED: splits into two clauses and reads EXPRESSIVE + DIRECTIVE_INFORM. An "
            "apposition RENAMES — it is the archive's own `X is a Y` in a different shape"),
    Feature(PHRASE, "negated filter", "stop every vm that is not running",
            "scan._negates -> the complement of a closed two-valued set",
            note="⇒ **CLOSED 2026-08-16, AND IT WAS THE GENUINELY DANGEROUS ONE.** `running` "
            "read as a value with the negation discarded, giving `{status: running}` — a "
            "WELL-FORMED condition naming the exact set the operator excluded, which every "
            "gate accepts. `attr_values` declares the closed set, so with two members the "
            "complement is exact; with more it DECLINES rather than guessing"),

    # ── CLAUSE ───────────────────────────────────────────────────────────────────────
    Feature(CLAUSE, "coordination", "create a vm named beta and then launch it",
            "pass2.clauses_of", "rung 2, and the ordering falls out of the split"),
    Feature(CLAUSE, "temporal subordination", "whenever a vm stops, take a snapshot",
            "temporal.events_in + standing_event", "built 2026-08-16"),
    Feature(CLAUSE, "clock adjunct", "take a snapshot of the vms daily",
            "temporal.clock_in", "built 2026-08-16"),
    Feature(CLAUSE, "conditional", "if alpha is stopped, launch it",
            "",
            "⇒ **HALF CLOSED 2026-08-16.** It read ASSERTIVE — a piece of teaching — because "
            "`_main_clause_copula` scanned from `words[1:]` and never checked whether the "
            "clause OPENS on a subordinator; the per-chunk producer rule then dropped its rows "
            "in SILENCE. Now `None`: **UNREAD, which nothing drops**, so the condition is still "
            "reported. ⚠ STILL A HOLE — the condition is VISIBLE and not UNDERSTOOD. ISO "
            "24617-2 says the next step is to carry it as a QUALIFIER on the act (conditionality) "
            "rather than as clause structure, which closes READ without touching E5",
            danger=True),
    Feature(CLAUSE, "purpose", "stop the vms to free up memory",
            "",
            "⚠ `free` unread, the rest swallowed. A purpose says WHY and can license steps the "
            "request never named — Part 2"),
    Feature(CLAUSE, "cause", "stop the vms because they are stuck",
            "",
            "⚠ `because` and `stuck` unread; the clause now reads `None` rather than as "
            "teaching (2026-08-16, the same subordinator bound). **A cause is a SYMPTOM, and a "
            "symptom is D1's input** — this is the diagnosis hole wearing a subordinate clause",
            danger=True),
    Feature(CLAUSE, "concession", "stop the vms even though alpha is busy",
            "",
            "⚠ `even`, `though`, `alpha`, `busy` all unread, and it stays ONE clause. `though` "
            "is now a declared subordinator so a split clause would read `None` rather than as "
            "teaching. A concession names an EXCEPTION the operator has already thought about",
            danger=True),
    Feature(CLAUSE, "alternative", "stop alpha or beta",
            "linguistics/unexpressed-choice", partial=True,
            note="⇒ **READ 2026-08-16.** It produced `[stop_vm(beta), stop_vm(beta)]` — alpha "
            "dropped, beta doubled — and REFUSED only because the lab held neither machine. "
            "**Graded on the operations, not the verdict.** ⚠ PARTIAL: the choice is RAISED "
            "and not made, because only the operator can make it. And the clause must NOT be "
            "split — splitting a disjunction produces two orders, which is the acting-on-both "
            "this exists to stop"),
    Feature(CLAUSE, "comparison across clauses", "stop more vms than you did last time",
            "",
            "needs the previous turn AND an ordering. Blocked twice over"),

    # ── TURN ─────────────────────────────────────────────────────────────────────────
    Feature(TURN, "anaphora, same turn", "create a vm named beta and then launch it",
            "speech_act.ANAPHORA + pass2's symbol table", "rung 2 — `it` resolves in-turn"),
    Feature(TURN, "anaphora, cross turn", "launch it",
            "",
            "⚠ `pipeline.run` takes ONE string and has no previous turn. Part 3, and it is "
            "architectural rather than linguistic",
            danger=True),
    Feature(TURN, "ellipsis, cross turn", "the same for db",
            "", "⚠ Part 3. Nothing to resolve against"),
    Feature(TURN, "repair", "stop alpha — sorry, i meant beta",
            "",
            "⚠⚠ IT REWRITES THE REQUEST, and every stance rule wants to discard it as an "
            "apology. Found 2026-08-16",
            danger=True),
    Feature(TURN, "topic shift", "list the vms. anyway, is alpha running?",
            "",
            "⚠ a SECOND request. The clause splitter joins them into one reading",
            danger=True),
    Feature(TURN, "answer to our question", "yes, it's a label",
            "reading_answers.settle", "the one cross-turn thing that IS built"),

    # ── SURFACE ──────────────────────────────────────────────────────────────────────
    Feature(SURFACE, "casing", "STOP ALPHA",
            "everything lowercases on entry", "measured as an arm in `mutate`"),
    Feature(SURFACE, "typo", "créate a vm nemed alpha",
            "",
            "⚠ NOT NOISE — pronounceable, one edit from a naming cue. The operator's held-out "
            "set preserves typos as DATA because they were unconscious"),
    Feature(SURFACE, "contraction", "don't stop the vms · i'd like you to",
            "speech_act reads `don't`; `i'd` is unread", partial=True,
            note="⚠ MEASURED in the courtesy probe: `i'd` and `like` are asked about by name"),
    Feature(SURFACE, "multi-sentence", "stop alpha. then launch beta.",
            "pass2.clauses_of splits on the full stop", "reads as two clauses, correctly"),
    Feature(SURFACE, "fragment", "and the network?",
            "speech_act's elliptical question branch", "reads DIRECTIVE_INFORM"),
    Feature(SURFACE, "bullet list", "stop: alpha, beta, gamma",
            "",
            "⚠ one clause, and the colon is not a boundary. A pasted list is how an operator "
            "gives a set, and the member-list rule keys on `and`"),
    Feature(SURFACE, "pasted data", "the error says 'cannot allocate memory'",
            "scan.quoted_clauses -> linguistics/quoted-evidence",
            "⇒ **READ 2026-08-16.** A quoted span of TWO OR MORE words is evidence; one word "
            "is a value, which is what quotes already mean here and what every quoted span in "
            "the corpus is. Structural, so it costs no vocabulary. ⚠ IT IS NAMED, NOT USED — "
            "until D1 gives evidence somewhere to go, the finding says so out loud rather "
            "than swallowing the words"),
    Feature(SURFACE, "identifiers and paths", "tail /var/log/alpha.log",
            "",
            "⚠ a path is one token to a person and several to the tokenizer"),
]


def holes() -> List[Feature]:
    return [f for f in MAP if f.hole]


def dangerous() -> List[Feature]:
    return [f for f in MAP if f.hole and f.danger]


def read_now(f: Feature):
    """What the FREE readers make of this example today. No model call."""
    from planner.formula.legal import Board
    from orchestrator.seam import scan as SC, speech_act as SA
    b = Board()
    try:
        acts = [a for _, a in SA.read(f.example, b)]
        return acts, SC.anchors_in(f.example, b), SC.uncovered(f.example, [], b)
    except Exception as e:                                       # pragma: no cover
        return [f"ERROR {type(e).__name__}"], [], []


def main(argv: Optional[List[str]] = None) -> int:               # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    only = "--holes" in argv
    print(f"\n  {len(MAP)} structural features · {len(holes())} holes · "
          f"{len(dangerous())} of them change WHAT RUNS")
    level = None
    for f in MAP:
        if only and not f.hole:
            continue
        if f.level != level:
            level = f.level
            print(f"\n═══ {level} ═══")
        acts, anchors, unread = read_now(f)
        mark = "⚠⚠" if (f.hole and f.danger) else ("⚠ " if f.hole else "  ")
        print(f"\n {mark} {f.name.upper()}   “{f.example}”")
        print(f"      reads it   {f.reads_it or '*** NOTHING ***'}")
        print(f"      today      acts={acts} anchors={anchors} unread={unread}")
        if f.note:
            print(f"      {f.note}")
    print(f"\n{'─' * 96}")
    part = [f for f in MAP if f.partial]
    print(f"  COVERED {len(MAP) - len(holes()):2} of {len(MAP)}     HOLES {len(holes()):2}"
          f"  (of which {len(part)} PARTIAL — machinery exists and the answer is wrong)"
          f"     of which {len(dangerous())} change WHAT RUNS:")
    for f in dangerous():
        print(f"      {f.level:8} {f.name}")
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
