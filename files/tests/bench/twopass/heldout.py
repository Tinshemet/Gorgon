"""THE HELD-OUT SET FOR THE SPAN-GRAIN RESIDUE CHECK — SEALED BEFORE THE CHECK EXISTS.

    PYTHONPATH=. python3 -m tests.bench.twopass.heldout

Rule V5: *a measurement gets its expected answer written down BEFORE it runs, and a held-out
set is sealed and committed before the machinery that has to pass it.* This file is committed
in a tree where `residue.py` does not exist. If a later commit changes an expectation in here
to make a run pass, that is the failure this file exists to make visible.

# ⇒ WHY IT IS NEEDED, SAID PLAINLY

The mock-up scored 11 of 14 rungs silent with 1 false alarm — but every exemption in it was
chosen AFTER seeing which rungs it flagged. That is fitting to the corpus, and the 14 rungs
can no longer measure it. These requests use the same lab and none of the same sentences.

# ⇒ THE THREE VERDICTS, AND WHO EACH IS FOR

    BOUNCE      something correlates — a quoted value, a declared value, a lab object.
                The reading missed a clause it had already read. GOES BACK TO THE MODEL.
    ASK         nothing correlates and the word sits in a slot nothing closed could fill.
                *"At best a name or a label"* — GOES TO THE OPERATOR, as a closed choice.
    RELATIONAL  the word carries a set operation, not a description. BELONGS TO PASS 2.

    SILENT      every word was consumed. This is the majority case and the one that matters
                most: a check that speaks about a correct reading is worse than no check.

# ⇒ WHAT IS DELIBERATELY THIN, SAID NOW RATHER THAN AFTER THE RUN

  * **BOUNCE is thinly covered.** It needs a word that is a legal value AND is left unread,
    which is hard to construct on purpose — a correct reading consumes it. One case (E1).
  * **The world arm is not covered at all.** `orion` is only settled by a lab that has one,
    and no lab runs here. Cases marked `needs_lab` state the verdict expected WITHOUT one.
  * **`fresh` (F2) is an expectation about English, not about the manifest.** Nothing declares
    it. It is written as SILENT because that is what is correct, and if the check cannot reach
    it that is a miss to report, not an expectation to soften.
"""
from typing import Dict, List, NamedTuple


class Case(NamedTuple):
    tag: str
    request: str
    expect: Dict[str, str]      # word -> BOUNCE | ASK | RELATIONAL   ({} means SILENT)
    why: str
    needs_lab: bool = False


# ── A · CLEAN REQUESTS. Every one must be SILENT — these are the false-alarm controls, and
#        they outnumber the rest on purpose. A check that speaks here is not worth having.
CLEAN: List[Case] = [
    Case("A1", "create a vm named orion", {},
         "a name in an open slot is consumed by the key"),
    Case("A2", "stop every vm that is running", {},
         "a declared value of a closed attribute is consumed as a condition"),
    Case("A3", "create a network called mesh and put orion on it", {},
         "a naming cue on each kind, and a pronoun that refers"),
    Case("A4", "take a snapshot of orion", {},
         "two objects, one of them a bare name"),
    Case("A5", "make sure at least 2 vms carry the 'edge' label", {},
         "a comparator, an enumerator and a quoted label — all consumed by their own fields"),
    Case("A6", "launch the machines that do not answer", {},
         "an observed attribute reached through its doc, negated"),
    Case("A7", "give orion the 'edge' label", {},
         "a quoted value on a bare name"),
    Case("A8", "create 4 vms with 8192 memory", {},
         "an attribute alias and a numeric value"),
]

# ── B · JUNK IN A DESCRIPTOR SLOT. Nothing in the manifest can hold it, so the operator is
#        asked — and asked a CLOSED question, never "what does this mean".
JUNK_DESCRIPTOR: List[Case] = [
    Case("B1", "create a frobnitz vm named orion", {"frobnitz": "ASK"},
         "the name is settled and the adjective still is not"),
    Case("B2", "put every vm on a wibblesome network", {"wibblesome": "ASK"},
         "the same defect on a second kind"),
    Case("B3", "take a zarquon snapshot of orion", {"zarquon": "ASK"},
         "and on a third, whose key is spelt differently again"),
    Case("B4", "create a frobnitz wibblesome vm",
         {"frobnitz": "ASK", "wibblesome": "ASK"},
         "two junk words in one span — both must be named, not just the first"),
]

# ── C · THE SAME JUNK IN AN OPEN SLOT. The request assigns it a job, so nothing may object.
#        This is the operator's rule: *at best a name or a label* — and here it IS one.
JUNK_OPEN: List[Case] = [
    Case("C1", "create a vm named frobnitz", {},
         "a naming cue makes any string legal — the slot is open"),
    Case("C2", "create a network called frobnitz", {},
         "the same, through a key that is not called `name`"),
    Case("C3", "give every vm the 'frobnitz' label", {},
         "a quoted label is a value the request supplies"),
]

# ── D · JUNK WITH NO KIND AT ALL. Item 0 already owns this: the row is declared with kind `?`
#        and GATE 2 asks. The span check must stay out of its way — a kindless row has no
#        conditions to read, so every word in it would look unread.
JUNK_KINDLESS: List[Case] = [
    Case("D1", "frobnitz", {}, "gate 2 asks kind-not-settled; the span check is silent"),
    Case("D2", "create a vm named orion, frobnitz", {},
         "same, with a correct declaration beside it that must be untouched"),
]

# ── E · A REAL UNREAD CLAUSE. The word correlates, so it goes BACK TO THE MODEL.
LOST_CLAUSE: List[Case] = [
    Case("E1", "create 3 vms labelled 'edge' and put the edge ones on a network",
         {"edge": "BOUNCE"},
         "'edge' is quoted as a value earlier in this very request"),
]

# ── F · EXISTENCE WORDS. Consumed by the `existence` field exactly as a comparator word is
#        consumed by `comparator`. Neither is a descriptor.
EXISTENCE: List[Case] = [
    Case("F1", "clone orion into 2 new vms", {},
         "`new` is the existence answer, not an adjective about the machines"),
    Case("F2", "create a fresh vm named orion", {},
         "SAME IN ENGLISH, AND NOTHING DECLARES IT. Written as correct, not as reachable"),
]

# ── G · RELATIONAL WORDS. A set operation is not a description and not junk.
RELATIONAL_CASES: List[Case] = [
    Case("G1", "put every vm on mesh, except orion — orion goes on lab instead",
         {"except": "RELATIONAL", "instead": "RELATIONAL", "orion": "ASK"},
         "the exclusion is pass 2's; the bare name is the operator's, absent a lab",
         needs_lab=True),
]

ALL: List[Case] = (CLEAN + JUNK_DESCRIPTOR + JUNK_OPEN + JUNK_KINDLESS
                   + LOST_CLAUSE + EXISTENCE + RELATIONAL_CASES)


# ⇒ THE GRADER LIVES HERE, NOT BESIDE THE CHECK IT GRADES. It sat in `residue.py` until
#   2026-08-13, when that module moved to `orchestrator/languages/english/seam/` — and it was the ONE thing in the file
#   that reached up into `engines.channel` (to silence the model) and printed a scoreboard.
#   A production module carrying its own bench harness is how the test tree gets shipped; the
#   docstring already said the expectations live here, so the reading of them does too.
def score_heldout(cases, board=None, world=None) -> Dict[str, object]:
    """Grade the SEALED set against `orchestrator.languages.english.seam.residue`."""
    import engines.channel as channel

    from planner.formula.legal import Board
    from orchestrator.languages.english.seam import pass1
    from orchestrator.languages.english.seam.residue import report

    was, channel.constrained = channel.constrained, lambda *a, **k: {}
    board = board or Board()
    try:
        exact = silent_ok = 0
        false_alarms: List[str] = []
        missed: List[str] = []
        wrong: List[str] = []
        print(f"{'case':<5} {'verdict':<38} {'':<3} request")
        print("─" * 104)
        for case in cases:
            rows = pass1.run_scanned(case.request, board=board)
            got = {r.word: r.verdict for r in report(rows, case.request, board, world)}
            ok = got == case.expect
            exact += ok
            silent_ok += ok and not case.expect
            for word, verdict in got.items():
                if word not in case.expect:
                    false_alarms.append(f"{case.tag} {word!r} -> {verdict}")
                elif case.expect[word] != verdict:
                    wrong.append(f"{case.tag} {word!r} -> {verdict}, "
                                 f"wanted {case.expect[word]}")
            for word in case.expect:
                if word not in got:
                    missed.append(f"{case.tag} {word!r} — wanted {case.expect[word]}, silent")
            shown = ", ".join(f"{w}:{v}" for w, v in got.items()) or "silent"
            print(f"{case.tag:<5} {shown[:38]:<38} {'ok ' if ok else 'FAIL'} {case.request[:48]}")
        total = len(cases)
        quiet = sum(1 for c in cases if not c.expect)
        print("=" * 104)
        print(f"  exact                {exact}/{total}")
        print(f"  clean stayed silent  {silent_ok}/{quiet}   ⇐ the false-alarm controls")
        print(f"  FALSE ALARMS         {len(false_alarms)}   {false_alarms}")
        print(f"  MISSED               {len(missed)}   {missed}")
        print(f"  WRONG VERDICT        {len(wrong)}   {wrong}")
        return {"exact": exact, "total": total, "false_alarms": false_alarms,
                "missed": missed, "wrong": wrong}
    finally:
        channel.constrained = was


def main() -> None:
    print(f"{len(ALL)} held-out cases, sealed "
          f"({sum(1 for c in ALL if not c.expect)} of them SILENT)")
    try:
        from orchestrator.languages.english.seam import residue                      # noqa: F401
    except ImportError:
        print("the check does not exist yet — which is the point of sealing this first")
        return
    score_heldout(ALL)


if __name__ == "__main__":
    main()
