"""test_structure.py — HOW THE SENTENCE IS BUILT, pinned one structural feature at a time.

`tests/bench/structure_map.py` is the map: 39 ways an English sentence is built, what reads
each one today, and 23 holes of which 12 change WHAT RUNS. This suite is where a hole gets
closed — one feature, one test, written BEFORE the fix and kept as the regression.

⇒ **SCOPED TO READ, ON THE OPERATOR'S INSTRUCTION, 2026-08-16:** *"we need to able to cover
  everything in the english language, meaning we complete at least our READ… we aren trying to
  resolve at 100% but READ should be really good"* — and *"a good read and a good route means
  resolve and everything downstream gets better."*

⇒ **AND READ IS SEPARABLE FROM EMIT, WHICH IS WHAT MAKES THIS WORTH DOING NOW.** ISO 24617-2
  treats CONDITIONALITY as a QUALIFIER on a dialogue act rather than as clause structure, so a
  conditional can be READ and carried as a flag while E5 — the writer cannot emit `if` — stays
  open. A conditional that is read and cannot be emitted is strictly better than one nobody
  read, because the first can decline and the second acts on half the sentence.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english.seam import pass1, speech_act as SA
from planner.formula.legal import Board

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_a_subordinate_clause_is_not_a_predication():
    """⇒⇒ **AN `if` CLAUSE WAS READING AS TEACHING, AND THE LOOP BOUND IS WHY.**

    `_main_clause_copula` walks `words[1:]` looking for a copula that belongs to THIS clause,
    stopping at a relativizer because everything after one belongs to a subordinate clause.
    **It never looks at index 0**, so a clause that OPENS on a subordinator was never
    recognised as subordinate: *"if alpha is stopped"* found `is` and came back ASSERTIVE.

    ⇒ **AND THE VOCABULARY WAS ALREADY DECLARED.** `CONJUNCTIONS` holds `if`, `unless`,
      `while`, `because`, `although`, `though`, `whether`; the coordinating members of the same
      class — `and`, `or`, `but`, `nor`, `yet` — must NOT count, because a clause joined by one
      of those IS a main clause. A subset of a declared class, which is the move `DEONTIC`
      already makes on `AUXILIARIES`.

    ⇒⇒ ⚠ **AND IT WENT FROM WRONG TO SILENT ON 2026-08-16.** The per-chunk producer rule drops
      the rows of any clause that cannot BUILD, and ASSERTIVE is one of those — so a condition
      stopped being mis-declared and started being discarded without a word. `None` is the
      honest answer here: an unread clause is not dropped, so the seam still reports it.
    """
    board = Board()
    for clause in ("if alpha is stopped",
                   "unless alpha is running",
                   "because the vms are stuck",
                   "although alpha is busy",
                   "while the snapshot is running"):
        got = SA.act_of(clause, board)
        check(f"a subordinate clause is not teaching — {clause!r} -> {got}",
              got != SA.ASSERTIVE)

    # ⇒ AND THE COORDINATING HALF MUST BE UNTOUCHED. `and`/`but` join main clauses, so the
    #   copula behind one is this clause's own predication — that is the archive's input.
    for clause in ("and alpha is the jumpbox", "but n1 is a vm"):
        check(f"a coordinated clause still predicates — {clause!r}",
              SA.act_of(clause, board) == SA.ASSERTIVE)

    # ⇒ THE STANDING CONTROL: teaching still reads as teaching.
    check("`a jumpbox is a vm` is still teaching",
          SA.act_of("a jumpbox is a vm", board) == SA.ASSERTIVE)


def test_a_condition_is_not_dropped_in_silence():
    """⇒ **THE WHOLE SENTENCE, NOT THE CLAUSE** — and the reason this test exists beside the
    one above. `pass1.BUILDS` decides whose rows survive; a clause read ASSERTIVE loses its
    rows, and a clause read `None` keeps them because UNREAD is not UNPRODUCTIVE.

    ⇒ So the pin is not *"the condition is understood"* — it is not, and E5 is why. It is that
      **the condition is still VISIBLE to everything downstream**, which is the difference
      between declining and acting on half a request.
    """
    board = Board()
    request = "if alpha is stopped, launch it"
    read = SA.read(request, board)
    dropped = [c for c, a in read if a is not None and a not in pass1.BUILDS]
    check(f"the `if` clause is not dropped as unproductive — read={[a for _, a in read]}",
          not any("if alpha" in c for c in dropped))


def test_a_negation_selects_the_complement():
    """⇒⇒ **A NEGATED FILTER WAS READING AS ITS OWN OPPOSITE.** *"every vm that is NOT
    running"* came back `{status: running}` — the exact set the operator excluded.

    `conditions_from` computes `negated` and spends it on ONE of its three rules: an OBSERVED
    attribute gets `out[attr] = not negated`. Rule 1 — a declared VALUE naming its own
    attribute — ignored it, and rule 1 is the one every status filter goes through.

    ⇒ **AND THE MANIFEST MAKES THE FIX EXACT RATHER THAN APPROXIMATE.** `attr_values.status`
      is a CLOSED set of exactly two — `running` and `stopped` — so the complement of one is
      the other, by declaration. Nothing is inferred and no new field is needed.
    ⇒ **WITH MORE THAN TWO IT DECLINES**, because the complement is then a SET and `where`
      holds one value. Saying nothing leaves gate 2 to ask; saying `stopped` when there are
      four states would be confidently wrong.
    """
    from orchestrator.languages.english.seam.scan import conditions_from
    board = Board()
    got = conditions_from("that is not running", "vm", board)
    check(f"`not running` is the complement — {got}", got.get("status") == "stopped")
    got = conditions_from("that is not stopped", "vm", board)
    check(f"`not stopped` is the complement — {got}", got.get("status") == "running")
    # ⇒ THE ALIAS RESOLVES FIRST, so the complement is taken of what the lab stores.
    got = conditions_from("that is not up", "vm", board)
    check(f"`not up` resolves then complements — {got}", got.get("status") == "stopped")

    # ⇒ THE CONTROLS: an unnegated filter is untouched, and a negator belonging to a DIFFERENT
    #   value must not reach this one.
    check("`that is running` is unchanged",
          conditions_from("that is running", "vm", board).get("status") == "running")
    check("`currently stopped` is unchanged",
          conditions_from("that is currently stopped", "vm", board).get("status") == "stopped")
    # ⇒ AND THE OBSERVED ARM, WHICH ALREADY HAD THE NEGATION, STILL HAS IT — rung 11.
    got = conditions_from("that do not answer", "vm", board)
    check(f"the observed arm still negates — {got}", got.get("alive") is False)


def test_a_disjunction_is_a_choice_nobody_made():
    """⇒⇒ **`or` READ AS `and` ACTS ON BOTH, AND THE VERDICT HID IT.** *"stop alpha or beta"*
    came back REFUSE — but only because the lab held neither machine. The OPERATIONS are what
    show the reading:

        stop alpha or beta    ops=[stop_vm(beta), stop_vm(beta)]

    alpha dropped, beta doubled. **Against a lab that holds them, that serves.**

    ⇒ **A DISJUNCTION IS A CHOICE AND ONLY THE OPERATOR CAN MAKE IT.** The clause must NOT be
      split — splitting produces two orders, which is the acting-on-both this exists to stop.
      It is one clause carrying two candidates and no way to pick.

    ⇒ **`or` IS ALREADY IN `CONJUNCTIONS`**, so this adds no vocabulary — it adds a finding,
      which is `unexpressed-exclusion`'s own shape one word over: the sentence says something
      the program does not express.
    """
    from orchestrator.languages.english.seam import linguistics as L
    from orchestrator.languages.english.seam.effects import Operation
    board = Board()
    ops = [Operation("stop_vm", "beta", None), Operation("stop_vm", "beta", None)]
    got = L.findings("stop alpha or beta", [], ops, [], board=board)
    kinds = [f.rule for f in got]
    check(f"a disjunction is raised — {kinds}", "unexpressed-choice" in kinds)

    # ⇒ THE CONTROLS. `or` inside a QUOTED value is not a choice, and a request with no `or`
    #   must stay silent — a finding that fires on everything is a finding nobody reads.
    quiet = L.findings("stop the vms", [], [Operation("stop_vm", "vms", None)], [], board=board)
    check("no disjunction, no finding",
          "unexpressed-choice" not in [f.rule for f in quiet])
    check("the rule belongs to linguistics", "unexpressed-choice" in L.OWNS)


def test_a_quoted_clause_is_evidence_not_a_value():
    """⇒⇒ **QUOTES ALREADY MEAN *A VALUE* IN THIS SYSTEM, AND THAT IS RIGHT FOR ONE WORD.**
    `residue.classify` bounces on a quoted word — *"3 vms labelled 'red'"* binds `red` — and
    the whole corpus quotes labels that way.

    ⇒ **A QUOTED CLAUSE IS A DIFFERENT ACT.** *"the error says 'cannot allocate memory'"* is
      the operator handing us DATA: it correlates with no kind, no member and no archive entry
      — the exact profile of something unrelated — and it is the EVIDENCE a diagnosis runs on.

    ⇒ **THE DISCRIMINATOR IS LENGTH AND IT IS STRUCTURAL.** One word inside quotes is a value;
      two or more is a quotation. No vocabulary, and it matches the corpus exactly — every
      quoted span in the fourteen rungs is a single word.
    """
    from orchestrator.languages.english.seam.scan import quoted_clauses
    check("a multi-word quote is evidence",
          quoted_clauses("the error says 'cannot allocate memory'")
          == ("cannot allocate memory",))
    check("double quotes read the same",
          quoted_clauses('it said "no space left on device"')
          == ("no space left on device",))
    # ⇒⇒ ⚠ THE CONTRACTION, AND IT IS HERE BECAUSE THE UNIT TEST MISSED IT. Every example
    #   above avoids apostrophes, so the first cut matched from the one in `won't` to the one
    #   opening the real quotation and reported "t boot, the error says" as evidence. Found by
    #   running the whole seam, which is why the end-to-end check is not optional.
    check("an apostrophe inside a word is not a quote",
          quoted_clauses("alpha won't boot, the error says 'cannot allocate memory'")
          == ("cannot allocate memory",))
    check("a possessive does not open a quote",
          quoted_clauses("delete alpha's snapshots") == ())
    # ⇒ THE CONTROLS — every quoted span in the rung corpus is a single word, and must stay one.
    for value in ("make sure exactly 3 vms carry the 'prod' label",
                  "create 3 vms labelled 'red' and 2 vms labelled 'blue'",
                  "give them all the 'fleet' label"):
        check(f"a quoted VALUE is not evidence — {value[:34]!r}",
              quoted_clauses(value) == ())


def test_a_magnitude_comparison_is_read_and_named():
    """⇒⇒ **`over 6gb` WAS LOST AND `ram` BECAME A MACHINE.** The full seam declared
    `('ram', 'vm', {'name': 'ram'})` and asked whether to create it — because `ram` is a
    declared ALIAS for `memory_mb` and pass 1 read it as a member name.

    ⇒ `where` holds ONE VALUE per attribute and cannot hold a comparison. That is a
      REPRESENTATION limit, not a reading one — so the comparison is read and named, the same
      move the choice and the quotation make.
    ⇒ The comparator class is new and closed; the ATTRIBUTE is the manifest's own, through
      `aliases`. A comparison whose attribute is undeclared is not raised at all.
    """
    from orchestrator.languages.english.seam.scan import magnitudes_in
    board = Board()
    check("`over 6gb of ram` resolves to memory_mb",
          magnitudes_in("stop every vm with over 6gb of ram", board)
          == (("gt", 6, "gb", "memory_mb"),))
    check("`more than 4 cores` resolves to cpu_cores",
          magnitudes_in("stop vms with more than 4 cores", board)
          == (("gt", 4, "cores", "cpu_cores"),))
    # ⇒ THE CONTROLS. A COUNT comparator is not a magnitude — `exactly 3 vms` belongs to
    #   `COMPARATORS` and rung 7 rests on it — and an undeclared attribute is not guessed at.
    check("a count comparator is not a magnitude",
          magnitudes_in("make sure exactly 3 vms carry the 'prod' label", board) == ())
    check("an undeclared attribute is not raised",
          magnitudes_in("stop every vm with over 6 widgets", board) == ())
    check("no comparison, nothing raised",
          magnitudes_in("stop every vm that is running", board) == ())


def test_an_attribute_word_is_not_a_thing():
    """⇒⇒ **`ram` WAS DECLARED AS A MACHINE, AND THE MANIFEST ALREADY KNEW BETTER.**
    *"stop every vm with over 6gb of ram"* produced `('ram', 'vm', {'name': 'ram'})` and asked
    whether to create it — while `vm.aliases` declares `ram -> memory_mb` in as many words.

    ⇒ `scan._index` indexes declared NOUNS only, so nothing ever said *this word names a
      PROPERTY, not a thing*. The fact was present and unused, which is the shape this project
      has filed most.

    ⇒ **THE SAME TWO GUARDS AS EVERY OTHER `consume_`:** kindless rows only, and THE LAB STILL
      WINS — a machine really called `ram` is a machine.
    """
    from orchestrator.languages.english.seam.scan import attribute_words
    from orchestrator.languages.english.seam import schema as S
    board = Board()
    words = attribute_words(board)
    for w in ("ram", "memory", "cores", "cpu", "tag", "os", "label", "status"):
        check(f"{w!r} is known to name an attribute", w in words)
    # ⇒ THE CONTROL: a KIND is not an attribute, however property-ish it sounds.
    for w in ("vm", "network", "snapshot", "machine"):
        check(f"{w!r} is a kind, not an attribute", w not in words)

    row = S.Declared(name="ram", object_type=S.UNKNOWN_KIND, where={},
                     existence=S.EXISTING, settled="", span="ram")
    kept = pass1.consume_attribute_words([row], board, None)
    check(f"a kindless attribute row is dropped — {[r.name for r in kept]}", not kept)
    # ⇒ AND A SETTLED ROW IS NEVER TOUCHED — this drops only rows nobody could settle.
    settled = S.Declared(name="ram", object_type="vm", where={},
                         existence=S.NEW, settled="", span="a vm named ram")
    check("a settled row survives",
          len(pass1.consume_attribute_words([settled], board, None)) == 1)

    # ⇒⇒ **AND THE LAB OUTRANKS EVERY OTHER SUPPLIER.** A machine really called `ram` is a
    #   machine — the same guard `consume_self_address` and `consume_meta_control` keep, and
    #   the reason any of these rules is allowed to run at all.
    class LabWithRam:
        def names(self): return ["ram"]
        def select(self, *a, **k): return [{"name": "ram"}]
    check("a machine really called `ram` survives",
          len(pass1.consume_attribute_words([row], board, LabWithRam())) == 1)


def test_the_archive_can_teach_an_attribute():
    """⇒⇒ **THE OPERATOR, 2026-08-16:** *"the ram and cores — its because the AI needs to
    correlate ram with an encyclopedia entry as well as it being an attribute."*

    The manifest aliases the words it happens to know. `vram`, `nics`, `disk size` it does not,
    and until now the archive could only teach *"X is a KIND"* — so a word naming a PROPERTY
    was unteachable. An entry may now resolve to an attribute, walking `classes` exactly as
    `kind_of` does.

    ⇒ **AND IT ROUTES ONLY WHEN SIGNED**, which is the archive's whole safety property: a
      proposal DESCRIBES and never PERMITS.
    """
    from orchestrator.languages.english.seam.archive import Archive, Entry, RATIFIED, TOLD
    a = Archive(None)
    a._rows.append(Entry(word="vram", attribute="memory_mb", status=RATIFIED, source=TOLD))
    check("a ratified entry resolves to an attribute", a.attribute_of("vram") == "memory_mb")
    # ⇒ THROUGH ITS CLASSES, the same walk `kind_of` makes — `vram is memory`, `memory` is the
    #   attribute — so a chain of ordinary sentences reaches the manifest.
    b = Archive(None)
    b._rows.append(Entry(word="vram", classes=("memory",), status=RATIFIED, source=TOLD))
    b._rows.append(Entry(word="memory", attribute="memory_mb", status=RATIFIED, source=TOLD))
    check("it resolves through a class", b.attribute_of("vram") == "memory_mb")
    # ⇒ AND UNSIGNED IS SILENT.
    c = Archive(None)
    c._rows.append(Entry(word="vram", attribute="memory_mb"))
    check("an unratified entry resolves nothing", c.attribute_of("vram") is None)


def test_the_iso_annotation():
    """⇒⇒ **THE READING, SAID IN SOMEBODY ELSE'S VOCABULARY** — and the reason it matters is
    not the printout. Every number in this project is measured against a corpus one of us
    wrote; a published ISO-annotated corpus is the first that is not, and comparing to it
    needs our reading in their terms.

    ⇒ **A CONDITION IS NOT A SECOND ACT.** ISO carries conditionality as a QUALIFIER, so
      *"if alpha is stopped, launch it"* is ONE Instruct held conditionally. The first cut
      emitted TWO, because `speech_act` reads the condition clause as directive-act.
    """
    from orchestrator.languages.english.seam import iso
    got = iso.annotate("if alpha is stopped, launch it")
    check(f"a conditional is ONE act — {[str(a) for a in got]}", len(got) == 1)
    check("held conditionally", got[0].qualifiers.get("conditionality") == "conditional")
    check("and it is the INSTRUCT that survives", got[0].segment == "launch it")

    got = iso.annotate("maybe stop most of the vms")[0]
    check("hedged", got.qualifiers.get("certainty") == "uncertain")
    check("partial", got.qualifiers.get("partiality") == "partial")
    check("definitely -> certain",
          iso.annotate("definitely stop them")[0].qualifiers.get("certainty") == "certain")

    # ⇒ THE CONTROLS. `how many` is a COUNT question and not a partial quantifier — one word
    #   apart from `many vms`, which is — and an ordinary order carries no qualifier at all.
    check("`how many` is not partiality",
          "partiality" not in iso.annotate("how many vms are running")[0].qualifiers)
    check("`many vms` IS partiality",
          iso.annotate("many vms are stopped")[0].qualifiers.get("partiality") == "partial")
    check("a plain order carries no qualifier", not iso.annotate("stop alpha")[0].qualifiers)
    # ⇒ AND SENTIMENT IS DECLINED — the one qualifier that needs a teacher rather than a class.
    check("sentiment is not read",
          "sentiment" not in iso.annotate("ugh, stop the vms")[0].qualifiers)
    # ⇒ EVERY TYPE OF OURS LANDS SOMEWHERE, and the emitter owns that table.
    check("the dimension is one of the nine",
          all(a.dimension in iso.DIMENSIONS for a in iso.annotate("good morning doorman")))


def test_the_operator_taking_something_back():
    """⇒⇒ **PHASE 4 — SELF-REPAIR, AND THE TWO CASES ARE TREATED DIFFERENTLY ON PURPOSE.**

        A RETRACTION IS UNAMBIGUOUS   "never mind" withdraws, and withdrawing is a complete
                                      instruction
        A CORRECTION IS NOT           substituting a constituent needs an alignment, and the
                                      wrong one STOPS THE WRONG MACHINE — so it is reported
                                      and ASKED, never silently applied

    ⇒ And the grid's third cell was already built: **every gate-2 ASK is an other-initiated
      repair initiation.** Naming it that way is what showed the rest.
    """
    from orchestrator.languages.english.seam import iso, self_repair as SR

    got = SR.read("stop alpha — sorry, i meant beta")
    check(f"a correction is read — {got!r}", got and got.kind == SR.REPAIRED)
    check("the trouble source is trimmed of its apology", got.withdrawn == "stop alpha")
    check("and the replacement is offered", got.offered == "beta")

    got = SR.read("stop the vms. actually, never mind")
    check(f"a retraction is read — {got!r}", got and got.kind == SR.RETRACTED)

    # ⇒⇒ ⚠ THE CONTROL THAT MATTERS MOST. `sorry` is an APOLOGY on its own — ISO files it under
    #   Social Obligations Management — and treating it as a repair would HOLD A REQUEST NOBODY
    #   WITHDREW.
    check("`sorry to bother you` is not a repair",
          SR.read("sorry to bother you, restart alpha") is None)
    check("an ordinary order is not a repair", SR.read("stop every vm") is None)
    # ⇒ AND A CUT-OFF ALONE IS PUNCTUATION, not a repair — it counts only beside a marker.
    check("a dash alone is not a repair", SR.read("stop alpha — the one on lab") is None)

    # ⇒ THE ISO SIDE: the repair is its own act, and the TASK act is read from what was ASKED
    #   rather than from the raw string — with the markers still in, `i meant beta` came back
    #   a GREETING.
    ann = iso.annotate("stop alpha — sorry, i meant beta")
    check(f"the repair is its own act — {[str(a) for a in ann]}",
          ann[0].dimension == iso.OWN_COMM and ann[0].function == "Self-Correction")
    check("and the task act is what was asked",
          any(a.dimension == iso.TASK and a.segment == "stop alpha" for a in ann))
    check("no segment reads as a greeting",
          not any(a.function == "Greeting" for a in ann))


def test_self_correction_is_a_fragment_not_a_marker():
    """⇒⇒ **THE OPERATOR, 2026-08-16: *"fix the self-correction, its fragments not markers."***

    DialogBank's gold proves it. 27 of 31 self-corrections are `go`, `you're pass`,
    `vertically in line` — ABANDONED FRAGMENTS. The lexical reader built in Phase 4 scores
    **0 of 31** on real dialogue: I built the tidy written form of a phenomenon that is
    overwhelmingly spoken and messy.

    ⇒ **THE SIGNAL IS THE RESTART, NOT THE FRAGMENT.** `go` alone is a complete imperative; it
      is a self-correction only because the speaker said it and began again.
    ⇒ **AND THE SEPARATOR DECIDES HOW MUCH A REPEAT IS WORTH** — after a CUT-OFF a repeat is a
      restart on its own; after a COMMA the head must also break off mid-constituent, or
      *"stop alpha, stop beta"* reads as a disfluency.
    ⇒ ⚠ AND THE BARE FRAGMENT RULE IS MEASURED AND NOT SHIPPED ALONE: 22% recall at 25%
      precision against the gold. A detector wrong three times in four is worse than the zero
      it replaces.
    """
    from orchestrator.languages.english.seam import self_repair as SR

    for text, kept in (("go— go south from the mine", "go south from the mine"),
                       ("stop the— stop the vms on lab", "stop the vms on lab"),
                       ("launch a— launch alpha", "launch alpha")):
        got = SR.read(text)
        check(f"a restart is read — {text!r}", got and got.kind == SR.REPAIRED)
        check(f"and the resumed half is kept — {kept!r}", got and got.offered == kept)

    # ⇒ THE CONTROLS. Two clauses that repeat a verb are a REQUEST, not a disfluency.
    for text in ("stop alpha, stop beta", "stop alpha and stop beta",
                 "create a vm, then launch it", "put web on lab, and db on dmz", "stop alpha"):
        check(f"not a disfluency — {text!r}", SR.read(text) is None)
    # ⇒ AND THE LEXICAL FORM STILL WINS WHERE BOTH ARE PRESENT — a marker says more than a mark.
    got = SR.read("stop alpha — sorry, i meant beta")
    check("a marker outranks a cut-off", got and got.marker == "i meant")


def test_a_numeral_is_a_value_unless_it_was_spent_as_a_count():
    """⇒⇒ **THREE WAYS THE READER THREW A VALUE AWAY, ALL FOUND BY A FOREIGN CORPUS.**

    MultiWOZ was written for hotels and trains and knows nothing about this project, and it
    caught three defects that bite the lab exactly as hard:

      1 `_tokens` could not cross a colon, so *"arrive by 24:30"* became `24` and `30` — and
        the enumerator loop then read the `24` as a COUNT. 127 clock times lost there, and
        *"snapshot every vm at 21:30"* loses its hour the same way.
      2 `scan` deleted EVERY digit from the modifiers, spent or not. A count is taken at most
        once from one position; every other numeral is a value somebody typed.
      3 `conditions_from` would take the phrase's own NOUN as one of its attributes' values —
        *"a 4 core vm"* came back `cpu_cores = vm`, with the real `4` one word to the left.

    ⇒ **AND THE COUNT MUST STAY A COUNT WHERE IT IS ONE.** `create 3 vms` is three machines;
      the demotion fires only where the digit is followed by a DECLARED ATTRIBUTE, which is a
      manifest lookup and not a word list.
    """
    from orchestrator.languages.english.seam.scan import _tokens, conditions_from, scan
    board = Board()

    check("a clock time is ONE token",
          [w for w, _s, _e in _tokens("leaving at 24:30")] == ["leaving", "at", "24:30"])
    check("a numeral before a declared attribute is that attribute's value",
          conditions_from("4 core vm", "vm", board) == {"cpu_cores": "4"})
    got = scan("vm", "a 4 core vm", board)
    check("and it is NOT the count", got.count is None and "4" in got.modifiers)

    # ⇒ THE CONTROLS. A numeral before a NOUN is still an enumerator; a numeral after one is
    #   still part of the identity; and none of it may reach the operator as unread residue.
    check("a numeral before a noun is still a count", scan("vms", "create 3 vms", board).count == 3)
    check("and it is spent, so it is not a modifier", scan("vms", "create 3 vms", board).modifiers == "")
    named = scan("network", "stop network 1", board)
    check("a numeral after a noun is still the identity",
          named.identity == "network 1" and "1" not in named.modifiers)
    # ⇒ superseded 08-20: the CLOCK READER owns the phrase now — it is read as a
    #   trigger with offsets, never residue in the modifiers (certified qual-0005)
    from orchestrator.languages.english.seam.temporal import clock_tail
    check("the clock phrase belongs to the trigger reader, not the modifiers",
          clock_tail("snapshot the vm at 24:30") == "at 24:30"
          and scan("vm", "snapshot the vm at 24:30", board).span == "the vm")

    from orchestrator.languages.english.seam import pass1 as P, residue as R
    rows = P.run_scanned("make sure at least 2 vms carry the 'edge' label", board=board)
    check("a numeral spent on `count` is never unread residue",
          all("2" not in R.unread(r, "make sure at least 2 vms carry the 'edge' label",
                                  board=board) for r in rows))


def test_a_declared_noun_may_be_more_than_one_word():
    """⇒⇒ **THREE DECLARED NOUNS THE READER COULD NEVER MATCH, ON THE MANIFEST WE SHIP.**

    `hardware profile`, `restore point` and `golden image` are in `KINDS`, and `anchors_in`
    scanned `[\\w']+` — a pattern that cannot cross a space. So none of the three was ever
    found, and **`_kind_of` says in its own docstring that it exists for this case** — *"longest
    noun wins, 'restore point' before 'point'"*. That branch was unreachable from the anchor
    path: built, and never called.

        *"delete every restore point older than a week"*  -> ZERO anchors. Read as NOTHING.
        *"clone the golden image into 3 vms"*             -> template `identity = image`

    The first is a destructive request that reads as empty. The second is worse than empty: it
    reads as a template CALLED image, which is a confidently wrong name from a sentence that
    looks perfectly understood.

    ⇒ ⚠ **AND THE ANCHOR-IS-THE-HEAD RULE TESTS *DECLARED*, NOT *MULTI-WORD*.** An anchor the
      manifest does not know is a NAME the operator typed. The first cut stripped every
      anchor's own tokens out of the modifiers and deleted the very word the naming cue points
      at — `scan("alpha", "create a vm named alpha")` came back `named`. Five checks caught it.
    """
    from orchestrator.languages.english.seam.scan import anchors_in, scan
    board = Board()

    check("a two-word declared noun is found at all",
          anchors_in("delete every restore point older than a week", board) == ["restore point"])
    got = scan("restore point", "delete every restore point older than a week", board)
    check("and it carries its own kind", got.kind == "snapshot" and got.count == "all")
    check("and its own words are not modifiers of itself", got.modifiers == "older than week")
    check("the longest declared noun wins over the word inside it",
          anchors_in("clone the golden image into 3 vms", board) == ["golden image", "vms"])
    check("a declared phrase is never somebody's NAME",
          scan("golden image", "clone the golden image into 3 vms", board).identity is None)
    check("a naming cue reaches a two-word noun's key",
          scan("hardware profile", "create a hardware profile called fast", board).modifiers
          == "called fast")

    # ⇒ THE CONTROLS. An UNDECLARED anchor is a name and keeps every one of its own words, and
    #   a one-word declared noun behaves exactly as it did.
    check("an undeclared anchor keeps its own word",
          scan("alpha", "create a vm named alpha", board).modifiers == "named alpha")
    check("a bare declared noun may still be a name",
          scan("box", "stop box", board).identity == "box")
    check("and the ordinary reading is untouched",
          scan("vm", "stop every vm that is running", board).modifiers == "that is running")
    check("anchors stay in request order",
          anchors_in("create 3 vms on a network called lab", board) == ["vms", "network"])


def test_a_quoted_run_is_one_value_and_its_words_are_not_cues():
    """⇒⇒ **THE OPERATOR QUOTED THE NAME AND WE TRUNCATED IT ANYWAY.**

        *"a vm named 'web server one'"*   -> `{name: web}`   — a machine created under a
                                                                name nobody typed
        *"a network called 'core net'"*   -> `{name: core, network: core}`

    The second is the worse one. `net`, INSIDE the operator's quotes, prefix-matched the
    `network` alias and MINTED A SECOND CONDITION out of a literal — so the reading invented a
    constraint the request never carried, from characters the operator had explicitly fenced.

    ⇒ **`quoted_clauses` HAS READ THESE SINCE IT WAS WRITTEN, AND `span` HAS BEEN A PARAMETER
      OF `conditions_from` SINCE GATE 1.** The two were never joined. `_tokens` drops the quote
      marks, so by the time `modifiers` exists the boundary is gone and the span is the only
      place it survives.

    ⇒ **AND THIS BOUNDS THE LENGTH RULE RATHER THAN CONTRADICTING IT.** `quoted_clauses` calls
      a run of two or more words a QUOTATION — evidence, not a value — and that stays true of
      a quote no cue governs. A quote a cue DOES govern is that cue's value at any length,
      because the slot decides, never the length and never the meaning.
    """
    from orchestrator.languages.english.seam.scan import conditions_from, quoted_clauses
    board = Board()

    check("a quoted name is taken whole",
          conditions_from("named 'web server one'", "vm", board,
                          span="a vm named 'web server one'") == {"name": "web server one"})
    check("and so is a quoted label",
          conditions_from("labelled 'prod fleet'", "vm", board,
                          span="vms labelled 'prod fleet'") == {"label": "prod fleet"})
    check("a word inside the quotes cannot mint a second condition",
          conditions_from("called 'core net'", "network", board,
                          span="a network called 'core net'") == {"net_name": "core net"})

    # ⇒ THE CONTROLS. Every quoted value in the fourteen rungs is ONE word and must be
    #   untouched, and a quotation NO cue governs is still a quotation.
    for mods, kind, span, want in (
            ("labelled 'red'", "vm", "3 vms labelled 'red'", {"label": "red"}),
            ("labelled 'blue'", "vm", "2 vms labelled 'blue'", {"label": "blue"}),
            ("carry the 'prod' label", "vm", "exactly 3 vms carry the 'prod' label",
             {"label": "prod"}),
            ("named alpha", "vm", "a vm named alpha", {"name": "alpha"}),
            ("called lab", "network", "a network called lab", {"net_name": "lab"})):
        check(f"unchanged — {span!r}", conditions_from(mods, kind, board, span=span) == want)
    check("a quotation no cue governs is still a quotation",
          quoted_clauses("the error says 'cannot allocate memory'")
          == ("cannot allocate memory",))
    check("and one quoted word is still not a quotation",
          quoted_clauses("3 vms labelled 'red'") == ())


def test_an_unquoted_multi_word_name_is_a_KNOWN_LIMIT_and_the_naive_fix_is_forbidden():
    """⇒⇒ **A NEGATIVE RESULT, PINNED SO IT IS NOT RE-ATTEMPTED.**

    *"create a vm named data pipeline"* reads `name = data`. The key takes ONE word, so the lab
    would hold a machine under a name nobody typed — a confident wrong reading, which is worse
    than a missing one.

    ⇒ **THE OBVIOUS FIX WAS BUILT ON 2026-08-16 AND A KEYED CONTROL KILLED IT.** The rule tried
      was the operator's own — the open naming slot accepts whatever no declaration claims
      ([[slot-decides-junk]]) — so the name runs on through words that are in no manifest
      column and no closed class, stopping at an OPENER (`please`), a RELATIVIZER (`which`), a
      LINKING word (`with`), a BOUNDARY, or a declared value. Eleven traps held. **Rung 8 did
      not:**

          "…put them on a network called dmz instead"   ->   net_name = 'dmz instead'

      `instead` is a discourse adverb, and there is NO structural difference between
      `dmz instead` and `data pipeline` — both are a bare unclaimed word after the name at the
      end of a clause. Separating them needs a list of English adverbs, which is an OPEN class
      and is exactly what this project forbids ([[gorgon-deterministic-rules]]).

    ⇒ **SO THE BOUNDARY MUST BE DECLARED, NOT GUESSED.** Quotes are the operator's own boundary
      mark and those already work — see the quoted-run check above. The right resolution for
      the unquoted case is an ASK at gate 2 (*is the name `dmz` or `dmz instead`?*), not a
      cleverer scan. Reading one word and declining the rest is the correct behaviour until
      that ask exists.

    ⇒ ⚠ **AND ONE REAL BUG WAS FOUND ON THE WAY, WHICH SURVIVES THE REVERT AS KNOWLEDGE:** rule
      2 CLOBBERS rule 0's key. `named` stems to `nam`, a vm's key is `name`, so `_cue_hit`
      fires and the descriptor arm overwrites the naming arm. It is invisible today only
      because both arms currently produce the same single word — anything that widens rule 0
      must fix this first.
    """
    from orchestrator.languages.english.seam import pass1 as P
    board = Board()

    def where(text):
        return [row.where for row in P.run_scanned(text, board=board)]

    check("the limit is real and is one word",
          where("create a vm named data pipeline") == [{"name": "data"}])
    check("the quoted form is NOT limited — the operator drew the boundary",
          where("create a vm named 'data pipeline'") == [{"name": "data pipeline"}])
    # ⇒ THE CONTROL THAT FORBIDS THE NAIVE FIX. If a future change makes this `dmz instead`,
    #   that change is the one this test exists to stop.
    check("rung 8's trailing adverb is not part of the name",
          {"net_name": "dmz"} in where(
              "put every vm on a network called core except db, put db on a network "
              "called dmz instead"))


def test_a_clause_takes_its_kind_from_the_clause_that_named_it():
    """⇒⇒ **`create a vm named alpha. give it 4 cores.` READ THE CORES AS NOTHING.**

    The second clause names no kind, so `scan` returned `kind=None`, and the row came out `?`
    with an empty `where` — the cores extracted nowhere and attached to nothing.

    ⇒ **THE MECHANISM WAS ALREADY THERE AND COULD NOT REACH ITS EVIDENCE.** `pass1`'s
      contextual kind lets a noun-less span inherit the request's kind on proof of a pro-form,
      and it asked `_has_pronoun(first.span)`. That row's span is drawn as `4 cores` — the left
      walk stops at the enumerator — so `give it` was never in the window. **The pro-form that
      licenses the whole rule sat one word outside the only place anybody looked.** Rung 11
      passed throughout because ITS pro-form happens to fall inside its span. The clause is the
      right window; `BOUNDARIES` already marks it.

    ⇒ ⚠ **AND SETTING A KIND IS NOT THE SAME AS READING WITH ONE — THAT HALF WAS A REGRESSION
      AND WAS MEASURED BEFORE IT SHIPPED.** `_replace(kind=…)` patches the field on a row read
      WITHOUT a kind, and every rule downstream of the kind had already made the kindless
      choice: the demotion could not ask whether `cores` names a declared attribute, so `4` was
      spent as an ENUMERATOR and the row emerged as a vm_set of **FOUR MACHINES**. An honest
      `?` (which asks) became a confident wrong reading (which acts). `scan` now takes a
      `kind_hint` and the rules that already exist do the rest.

    ⇒ **A STATED NOUN ALWAYS WINS.** The hint only fills a hole, or a caller could rename a
      thing the operator named.
    """
    from orchestrator.languages.english.seam import pass1 as P
    from orchestrator.languages.english.seam.scan import clause_around, scan
    board = Board()

    def rows(text):
        return [(r.object_type, r.count, r.where) for r in P.run_scanned(text, board=board)]

    check("the clause is the window, not the span",
          clause_around("create a vm named alpha. give it 4 cores.", "4 cores").strip()
          == "give it 4 cores")
    # ⇒ 08-23, ATTRIBUTES ARE LEAVES: the value is the owner's TYPED 4 (Board.accept), not
    #   the raw string '4' — the reading is the same, the carrier is now scrutinised.
    check("a following clause is read against the kind that was named",
          ("vm_set", None, {"cpu_cores": 4})
          in rows("create a vm named alpha. give it 4 cores."))
    check("and the same across `and` rather than a full stop",
          ("vm_set", None, {"cpu_cores": 4})
          in rows("create a vm named alpha and give it 4 cores"))
    check("the numeral is NOT a count — that reading was four machines",
          all(r[1] != 4 for r in rows("create a vm named alpha. give it 4 cores.")))

    # ⇒ THE CONTROLS. The pro-form guard exists because of `grubnash`; rung 11 inherits a kind
    #   too and so is directly in the blast radius; and a clause with NO pro-form must still
    #   decline, because gate 2 asking is the honest answer.
    check("junk in its own clause still declines — the grubnash case",
          ("?", None, {}) in rows("create a vm named alpha and launch it, grubnash"))
    check("rung 11 is unmoved",
          ("vm_set", None, {"alive": False})
          in rows("ping every vm and stop the ones that do not answer"))
    # ⇒ 08-23, ATTRIBUTES ARE LEAVES: `4 cores` is no longer a kindless `?` row but a VALUE
    #   row of its own (cpu_cores, owner vm). The control's point stands unchanged — nothing
    #   INHERITED the vm kind through a pro-form, because there is no pro-form.
    check("no pro-form, no inheritance",
          ("value", None, {}) in rows("create a vm named alpha, with 4 cores")
          and ("vm_set", None, {"cpu_cores": "4"})
          not in rows("create a vm named alpha, with 4 cores"))
    check("a stated noun outranks the hint",
          scan("network", "create a vm and a network", board, kind_hint="vm").kind == "network")


def test_a_folded_reference_carries_what_its_clause_SAYS():
    """⇒⇒ **THE FOLD KEPT THE WORDS AND DROPPED THE MEANING.**

    A kindless clause holding a pro-form already folded into the row it refers to — but only as
    a STRING in `references`. So *"create a vm named alpha and make it running"* declared
    `{name: alpha}` and lost the `running` completely: the operator asked for a state and the
    reading carried no trace of it. `label it prod` lost the label the same way, and recorded
    the clause TWICE while doing it.

    It could not have read them — the clause has no noun, so `conditions_from` refuses without
    a kind. **But the kind is known: it is the kind of the row the pronoun refers to.**

    ⇒ **SETDEFAULT, NEVER OVERWRITE.** *"…and rename it beta"* would otherwise silently replace
      a key the operator stated in the same sentence. A contradiction is a conflict, and a
      conflict is gate 2's to ask about.

    ⇒ ⚠⚠ **AND ONLY WITH ONE ROW DECLARED, BECAUSE THE ANTECEDENT IS A GUESS.** The fold takes
      `rows[-1]` — "the most recent declaration it could be about" — which was harmless while
      it recorded an inert string. Carrying CONDITIONS makes the guess consequential, and rung
      6 priced it: *"put the red ones together on their own network, and put the blue ones on a
      DIFFERENT network"* folded a leftover clause about the RED group onto the BLUE row and
      gave it a network. Two attempts to name the offending word failed the same way — first
      `network = own`, then `network = together` once `own` was excluded — because the word
      after the cue is an ADVERB, an open class. The fix is not a better word list, it is to
      stop guessing.

    ⇒ **AND TWO CLOSED CLASSES THAT WERE NEVER CONSULTED, FOUND ON THE WAY.** A pro-form REFERS
      and a distinctness marker CONTRASTS; neither ever names a value. `label it prod` read
      `{label: it}` and `on their own network` read `{network: own}` — both live before any of
      this, both now declined from the manifest's own declarations.
    """
    # ⇒ THE CHANNEL IS MOCKED — this test asserted a fold that rides a MODEL anchor and so
    #   flickered with the KV cache (one flake in the 15:20 suite, green standalone twice).
    #   A suite test that consults the live model is a nondeterministic suite; the
    #   deterministic half is what this fixture pins.
    import engines.channel as CH
    _was = CH.constrained
    CH.constrained = lambda *a, **k: None
    from orchestrator.languages.english.seam import pass1 as P
    from orchestrator.languages.english.seam.scan import conditions_from
    board = Board()

    def rows(text):
        return [(r.object_type, r.where) for r in P.run_scanned(text, board=board)]

    check("a state named by a following clause reaches the row",
          rows("create a vm named alpha and make it running")
          == [("vm", {"name": "alpha", "status": "running"})])
    check("and a label",
          rows("create a vm named alpha and label it prod")
          == [("vm", {"name": "alpha", "label": "prod"})])
    check("a pro-form is never a value",
          conditions_from("label it prod", "vm", board) == {"label": "prod"})
    check("a distinctness marker is never a value",
          conditions_from("on their own network", "vm", board) == {})

    # ⇒ THE CONTROLS.
    check("a contradiction never overwrites what the operator stated",
          rows("create a vm named alpha and rename it beta") == [("vm", {"name": "alpha"})])
    check("with more than one row the antecedent is not guessed at",
          ("vm_set", {"label": "blue"}) in rows(
              "create 3 vms labelled 'red' and 2 vms labelled 'blue', put the red ones "
              "together on their own network, and put the blue ones on a different network"))
    check("rung 2 is unmoved",
          rows("create a vm named beta and then launch it") == [("vm", {"name": "beta"})])
    check("a declared value beside a cue still reads",
          conditions_from("on a network called lab", "vm", board) == {"network": "lab"})
    CH.constrained = _was


def test_the_repair_is_applied_before_anything_is_scanned():
    """⇒⇒ **`self_repair` WAS BUILT 08-16 AND NEVER WIRED INTO PASS 1** — the dominant defect
    class by its own name, priced by the certified baseline at 15 hallucinations across four
    sentences: *"restart the web vm, no wait, the db one"* extracted BOTH targets and
    declared `no wait` a THING.

    ⇒ SUBTRACTIVE: the overridden text is never scanned. A retraction scans only what
      FOLLOWS the marker; a correction drops the withdrawn clause's LAST declaration and
      scans the replacement. The ghost row is never produced, so nothing has to catch it.
    ⇒ THE MODEL IS MOCKED OUT — this test runs the deterministic half only, so it neither
      needs nor loads ollama. The full-seam numbers come from the eval, not from here.
    """
    import engines.channel as CH
    was = CH.constrained
    CH.constrained = lambda *a, **k: None
    try:
        from orchestrator.languages.english.seam import pass1 as P
        board = Board()

        def names(text):
            return [r.name for r in P.run_scanned(text, board=board)]

        check("a correction keeps ONLY the corrected target",
              names("restart the web vm, no wait, the db one") == ["the db one"])
        check("and the marker never becomes a row",
              "no wait" not in names("restart the web vm, no wait, the db one"))
        check("the lexical marker form works too",
              names("stop alpha — sorry, i meant beta") == ["beta"])
        check("a mid-request retraction keeps only what follows",
              # the row is `the web vm` since the E1 edge rule (08-20): a kind word
              # in verb position is the VERB — certified gold's own span for sc-0003
              names("snapshot the db vm, scratch that, snapshot the web vm")
              == ["the web vm"])
        check("a bare retraction reads as nothing",
              names("actually, never mind") == [])
        # ⇒ THE CONTROLS — no marker, no mending
        check("an ordinary request is untouched",
              names("create a vm named alpha") == ["a vm named alpha"])
        check("two clauses that repeat a verb are a REQUEST, not a repair",
              names("stop alpha, stop beta") == ["alpha", "beta"])
    finally:
        CH.constrained = was


def test_a_questions_skin_is_not_part_of_the_thing():
    """⇒⇒ **THE CERTIFIED EVAL'S LAST TWO CLEAN-SINGLE MISSES (08-18).** `is alpha running`
    span'd as the whole clause — the fronting auxiliary walked in from the left, the asked
    predicate from the right. Inversion and wh-fronting are grammar (the scatter the answer
    re-gathers), and both marks are closed classes: AUXILIARIES and WH_WORDS.
    """
    from orchestrator.languages.english.seam.scan import scan
    board = Board()
    check("the fronted auxiliary is excluded",
          scan("alpha", "is alpha running?", board).span == "alpha")
    check("the wh-word STAYS — it is the NP's determiner",
          scan("vms", "which vms are stopped?", board).span == "which vms")
    check("descriptors inside the NP survive",
          scan("vm", "is the red vm running", board).span == "the red vm")
    # ⇒ THE CONTROLS — statements are untouched
    check("a relative clause keeps its predicate",
          scan("vm", "every vm that is running", board).span == "every vm that is running")
    check("a pre-nominal participle stays inside",
          scan("vm", "launch every stopped vm", board).span == "every stopped vm")


def test_the_carve_out_reaches_every_consumer():
    """⇒⇒ **THE READER PUT THE SPARED MACHINE ON THE MENU.** The `except` boundary (08-18)
    bought exact spans and lost the SET semantics: `every vm` carried `excludes=()` and
    pass 2's symbol table offered `db — "the thing"` as an ordinary target. The model
    stopped it because the reading disarmed the carve-out — the deadly class with the
    reader as the cause.

    Three defects, one attacher, all pinned here:
      · the span-starts-with test never fired once the boundary STRIPPED the word — the
        second surface (span PRECEDED by an excluder) is the same rule's other face
      · a kindless excluded row built NO carve (`_key_of('?')` is None) — it borrows the
        HOST's key now, which is the vocabulary the carve speaks
      · the host search walked LIST order while `launch everything but…` discovers the
        carve-out first — text position is the rule's order, and a UNIVERSAL pronoun
        heads a set even when nothing typed it
    ⇒ AND THE ATTACH RUNS ON run_scanned's OWN PATH — the pipeline was the only caller,
      so every other consumer (the eval included) read sets with carve-outs missing.
    """
    import engines.channel as CH
    was = CH.constrained
    CH.constrained = lambda *a, **k: None
    try:
        from orchestrator.languages.english.seam import pass1 as P
        board = Board()

        def excl(text):
            return {r.name: r.excludes for r in P.run_scanned(text, board=board)
                    if r.excludes}

        got = excl("stop every vm except the db vm")
        check("the bare `except` carves the set",
              got.get("every vm") == ({"name": "db vm"},))
        got = excl("launch everything but the vms carrying the test label")
        check("`everything but` carves by PREDICATE",
              got.get("everything") == ({"label": "test"},))
        got = excl("put every vm on a network called core, except db, and put db on "
                   "a network called dmz instead")
        check("the comma form still carves, and cleanly",
              any(v == ({"name": "db"},) for v in got.values()))
        # ⇒ THE CONTROLS
        check("a contrastive `but` between two acts attaches nothing",
              excl("stop alpha but launch beta") == {})
        check("an ordinary create attaches nothing",
              excl("create a vm named alpha") == {})
    finally:
        CH.constrained = was


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "structure")


if __name__ == "__main__":
    raise SystemExit(main())
