"""issue_map.py — EVERY KNOWN ISSUE, BY LEVEL AND BY FAMILY. The one list.

    PYTHONPATH=. python3 -m tests.bench.issue_map            # by level
    PYTHONPATH=. python3 -m tests.bench.issue_map --family   # by shared cause
    PYTHONPATH=. python3 -m tests.bench.issue_map --read     # only the level that MUST finish

# ⇒⇒ THE LEVELS, IN THE OPERATOR'S OWN WORDS — 2026-08-16

    *"READ is the only MUST complete because its needed, but after that each level has a few
    endings, our job is to make sure each is answered correctly not each one is served because
    not everything can be served."*

    READ      did we UNDERSTAND the sentence?
              ⇒ **THE ONLY LEVEL THAT MUST FINISH.** Everything else stands on it, and a
                wrong read cannot be recovered downstream — every gate below is checking a
                program against the manifest, never against the sentence
    ROUTE     did we pick the right ENDING — serve · ask · refuse · chat · hold · propose?
              ⇒ SEVERAL ENDINGS ARE CORRECT. The job is picking the right one, not serving
    RESOLVE   was the CONTENT of that ending right — the right question, the right proposal,
              the right refusal?
              ⇒ **SERVING IS ONE RESOLVE AMONG SEVERAL AND NOT THE TEST.** Most of what
                reaches a reader cannot be served at all: nothing in the manifest expresses it

⇒ ⚠ **SO A `0%` ON A DIMENSION IS NOT AUTOMATICALLY WORK.** DialogBank's Turn Management is 74
  segments we read as nothing, and reading them perfectly would change no ending we have — a
  CLI has no floor to contest. It is a READ gap with no ROUTE or RESOLVE behind it, and it is
  filed that way rather than counted as debt.

# ⇒⇒ THE FAMILIES, WHICH ARE WHERE THE WORK ACTUALLY IS

Seven causes produce nearly every issue below. Grouping by cause rather than by symptom is what
stops the same defect being fixed four times under four names — which has happened three times
in one session with the *same rule on two paths*.
"""
from typing import List, NamedTuple, Optional

READ, ROUTE, RESOLVE = "READ", "ROUTE", "RESOLVE"

# ── the families ─────────────────────────────────────────────────────────────────────
TURN = "THE MISSING TURN"                 # one string, no speaker, no history
QUALIFIER = "THE DISCARDED QUALIFIER"     # read correctly, the modifier dropped
TYPE = "THE MISSING SENTENCE TYPE"        # nothing reads this kind of utterance at all
DEFAULT = "THE CONFIDENT WRONG DEFAULT"   # we assert where we should decline
VOCAB = "THE HAND-WRITTEN ENGLISH"        # a list that cannot be finished
TWICE = "THE SAME RULE ON TWO PATHS"      # implementation, not linguistics
HOLD = "THE UNEXPRESSIBLE"                # read fine; the language or store cannot carry it

FAMILIES = (TURN, QUALIFIER, TYPE, DEFAULT, VOCAB, TWICE, HOLD)


class Issue(NamedTuple):
    level: str
    family: str
    name: str
    what: str
    state: str          # OPEN · FIXED · DECLINED · PARKED
    weight: str = ""    # how much it costs, measured where possible


ISSUES: List[Issue] = [

    # ══ THE MISSING TURN ═════════════════════════════════════════════════════════════
    Issue(READ, TURN, "anaphora across turns", '"launch it" with no antecedent',
          "OPEN", "Part 3. `pipeline.run` takes ONE string"),
    Issue(READ, TURN, "ellipsis across turns", '"the same for db"', "OPEN", "Part 3"),
    Issue(READ, TURN, "feedback direction", '"okay" is allo or auto by WHO checks WHOM',
          "DECLINED", "50 of 779 in DialogBank. DiAML carries `sender`; we see none"),
    Issue(READ, TURN, "turn management", "taking · keeping · yielding the floor",
          "DECLINED", "74 of 779 — and NO ENDING BEHIND IT: a CLI has no floor"),
    Issue(READ, TURN, "partner correction", '"you mean the lab network"', "OPEN", "3 of 779"),
    Issue(ROUTE, TURN, "topic shift", '"list the vms. anyway, is alpha running?"',
          "OPEN", "a SECOND request, merged into the first"),
    Issue(RESOLVE, TURN, "a ticket cannot close", "resolved needs the turns after the ask",
          "OPEN", "D2 — the ladder can say every next step was right, never *resolved*"),

    # ══ THE DISCARDED QUALIFIER ══════════════════════════════════════════════════════
    Issue(READ, QUALIFIER, "conditionality", '"if alpha is stopped, launch it"',
          "FIXED", "read as an ISO qualifier on the act — closes READ while E5 stands"),
    Issue(READ, QUALIFIER, "partiality", '"stop MOST of the vms"',
          "FIXED", "`scan.PARTIAL` — the quantifier between one and all, which nothing had"),
    Issue(READ, QUALIFIER, "certainty", '"maybe stop them" · "definitely stop them"', "FIXED"),
    Issue(READ, QUALIFIER, "magnitude", '"over 6gb of ram"',
          "FIXED", "read as (gt, 6, gb, memory_mb) and NAMED — `where` holds no comparison"),
    Issue(READ, QUALIFIER, "superlative", '"the biggest vm"',
          "OPEN", "needs an ORDERING over an attribute; no manifest declares one"),
    Issue(READ, QUALIFIER, "units", '"give alpha 4 cores and 8gb"',
          "OPEN", "the whole sentence reads as None — `give` is a light verb"),
    Issue(READ, QUALIFIER, "manner constraint", '"stop the vms, ONE AT A TIME"',
          "OPEN", "binds THIS request only. Not a rule, not part of the goal"),
    Issue(READ, QUALIFIER, "one-off clock time", '"stop alpha at 9pm"',
          "FIXED", "read as ROUTINE/instant — and see THE UNEXPRESSIBLE for where it stops"),
    Issue(RESOLVE, QUALIFIER, "sentiment", "the fourth ISO qualifier",
          "DECLINED", "the only one needing vocabulary — it waits for the archive"),

    # ══ THE MISSING SENTENCE TYPE ════════════════════════════════════════════════════
    Issue(READ, TYPE, "diagnosis", '"vm2 is not working, it boots to a blue screen"',
          "OPEN", "D1 — THE THESIS OF THE PRODUCT. Machinery exists; the READING does not"),
    Issue(READ, TYPE, "resolution", '"thanks, that worked" — the ticket CLOSES',
          "OPEN", "D3. `Issues.answers()` is the writer that would take one"),
    Issue(READ, TYPE, "evidence", "the error says 'cannot allocate memory'",
          "FIXED", "quoted CLAUSE read; ⚠ NAMED, not used — D1 gives it somewhere to go"),
    Issue(READ, TYPE, "commissive", "\"i'll add the labels myself tomorrow\"",
          "OPEN", "NAMED in speech_act and nothing emits it. A planning fact"),
    Issue(READ, TYPE, "suggestion", "\"you could stop the ones that aren't doing anything\"",
          "OPEN", "a suggestion is not an instruction and nothing reads one"),
    Issue(READ, TYPE, "self-correction", '"go— go south" — a FRAGMENT, not a marker',
          "FIXED", "the restart is the signal. ⚠ 0/31 on the corpus: segments arrive singly"),
    Issue(READ, TYPE, "retraction", '"actually, never mind"',
          "FIXED", "measured harm: `cancel` once CREATED A VM"),
    Issue(ROUTE, TYPE, "audit", '"what did you just run?" — about US, not the lab',
          "OPEN", "`events.log` is the arbiter and no sentence reaches it"),
    Issue(ROUTE, TYPE, "capability", '"can you even do snapshots?"',
          "OPEN", "answerable from the manifest alone; the door sends it at the lab"),
    Issue(RESOLVE, TYPE, "preference", "\"i'd rather use the smaller profile\"",
          "OPEN", "should BIAS a choice, never bind one. No store for it"),

    # ══ THE CONFIDENT WRONG DEFAULT ══════════════════════════════════════════════════
    Issue(READ, DEFAULT, "produces nothing -> GREETING", "574 of 779 on DialogBank",
          "FIXED", "the rung sat in front of the imperative rung and did not test for a verb"),
    Issue(READ, DEFAULT, "negation -> the opposite set", '"every vm that is NOT running"',
          "FIXED", "gave {status: running} — a WELL-FORMED condition, every gate accepts it"),
    Issue(READ, DEFAULT, "`if` -> teaching", "the copula scan skipped index 0",
          "FIXED", "and the per-chunk rule then dropped it in SILENCE"),
    Issue(READ, DEFAULT, "universal anywhere -> legislation", '"put EVERY vm on core"',
          "FIXED", "the rule said SUBJECT POSITION and the test said ANYWHERE"),
    Issue(READ, DEFAULT, "an attribute -> a machine", '`ram` declared as a vm',
          "FIXED", "the manifest aliases ram -> memory_mb and nothing asked it"),
    Issue(READ, DEFAULT, "a bare `sorry` -> a repair", "it is an APOLOGY",
          "FIXED", "cost every Social Obligations segment until the mark split it"),
    Issue(ROUTE, DEFAULT, "an unreadable order -> chat", '"sort out n1"',
          "FIXED", "at the door. ⚠ the READER still says EXPRESSIVE"),
    Issue(READ, DEFAULT, "`or` read as `and`", '"stop alpha or beta"',
          "FIXED", "ops were [stop_vm(beta), stop_vm(beta)] — a CHOICE nobody made"),

    # ══ THE HAND-WRITTEN ENGLISH ═════════════════════════════════════════════════════
    Issue(READ, VOCAB, "_operation_words leak", "`from` · `go` · `make` · `put` · `spin`",
          "OPEN", "D5. Bit twice in one session: `lab`->`label`, `good`->`go`, `from`"),
    Issue(READ, VOCAB, "ACHIEVE_MARKERS", "the last hand-written English list",
          "OPEN", "A3 — and it decides whether a goal is captured at all"),
    Issue(READ, VOCAB, "intent markers grant authority", '"when you get a chance" -> ACHIEVE',
          "OPEN", "⚠ 7/7 phrasings. BEING POLITE IS A PRIVILEGE ESCALATION, and live"),
    Issue(READ, VOCAB, "flavour needs a teacher", "courtesy · slurs · closure · frustration",
          "DECLINED", "of the whole taxonomy only FLAVOUR needs vocabulary — the archive"),

    # ══ THE SAME RULE ON TWO PATHS ═══════════════════════════════════════════════════
    Issue(READ, TWICE, "drop the row / forgive the word", "consume_* vs gate 1's exemption",
          "FIXED", "THREE TIMES IN ONE SESSION: meta-control, flavour, attribute words"),
    Issue(READ, TWICE, "one propose(), written twice", "first pass and retry, five steps each",
          "OPEN", "I5 — five of 08-11's twelve defects were this shape"),

    # ══ THE UNEXPRESSIBLE ════════════════════════════════════════════════════════════
    Issue(RESOLVE, HOLD, "the writer cannot emit `if`", "nothing to lower a condition into",
          "OPEN", "E5 — the RESOLVE half of the conditional. READ is now closed"),
    Issue(RESOLVE, HOLD, "`where` holds no comparison", "one value per attribute",
          "OPEN", "so a magnitude filter is named and not applied"),
    Issue(RESOLVE, HOLD, "no field for a one-off time", "`every` recurs, `when` is a predicate",
          "OPEN", "so *at 9pm, once* is routed and cannot be stored"),
    Issue(RESOLVE, HOLD, "the dry run drops a multi-exclusion SELECT", "~6 lines, confirmed",
          "PARKED", "G0 — it sits on the path that proves a program LEGAL"),
    Issue(RESOLVE, HOLD, "nothing types the payload", "the manifest types the operation only",
          "OPEN", "the media gap"),
]


def by_level(level: str) -> List[Issue]:
    return [i for i in ISSUES if i.level == level]


def open_reads() -> List[Issue]:
    """⇒ THE ONLY LIST THAT IS A MUST. Everything else has several correct endings."""
    return [i for i in ISSUES if i.level == READ and i.state == "OPEN"]


def check() -> List[str]:
    faults = []
    for i in ISSUES:
        if i.level not in (READ, ROUTE, RESOLVE):
            faults.append(f"{i.name}: {i.level!r} is not a level")
        if i.family not in FAMILIES:
            faults.append(f"{i.name}: {i.family!r} is not a family")
        if i.state not in ("OPEN", "FIXED", "DECLINED", "PARKED"):
            faults.append(f"{i.name}: {i.state!r} is not a state")
    return faults


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--check" in argv:
        bad = check()
        print("\n".join(bad) if bad else "the issue map is sound — 0 faults")
        return 1 if bad else 0

    groups = FAMILIES if "--family" in argv else (READ, ROUTE, RESOLVE)
    pick = (lambda i, g: i.family == g) if "--family" in argv else (lambda i, g: i.level == g)
    only_read = "--read" in argv

    for g in groups:
        rows = [i for i in ISSUES if pick(i, g) and (not only_read or i.level == READ)]
        if not rows:
            continue
        shown = f"  ({sum(1 for r in rows if r.state == 'OPEN')} open of {len(rows)})"
        print(f"\n═══ {g}{shown} ═══")
        for i in sorted(rows, key=lambda r: (r.state != "OPEN", r.name)):
            tag = {"OPEN": "⬜", "FIXED": "✅", "DECLINED": "⊘ ", "PARKED": "⏸ "}[i.state]
            extra = "" if "--family" in argv else f"  [{i.family}]"
            print(f"  {tag} {i.name}{extra}")
            print(f"      {i.what}")
            if i.weight:
                print(f"      {i.weight}")

    print(f"\n{'─' * 96}")
    for lvl in (READ, ROUTE, RESOLVE):
        rows = by_level(lvl)
        o = sum(1 for r in rows if r.state == "OPEN")
        must = "   ⇐ THE ONLY LEVEL THAT MUST FINISH" if lvl == READ else ""
        print(f"  {lvl:8} {o:2} open of {len(rows):2}{must}")
    print(f"\n  ⇒ AND A 0% IS NOT AUTOMATICALLY WORK: `turn management` is 74 unread segments "
          f"with\n    NO ENDING BEHIND IT — a CLI has no floor to contest. Filed DECLINED, not "
          f"counted as debt.")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
