"""GATES 1 AND 2, ON DECLARATIONS — the confirm step between pass 1 and pass 2.

Item 4. Deterministic: no model call, so the suite owns it.

    GATE 1   DID YOU SAY THIS?      every declared name and every condition VALUE must trace
                                    to the request. A name tracing to nothing was invented.
    GATE 2   CAN THE WORLD HOLD IT? is the kind declared, the attribute real, the value legal,
                                    the reference resolvable — all from the manifest.

# ⇒ WHY THIS IS WHERE THE OPERATOR'S DECOUPLING ARRIVES FOR FREE

The standing rule was that every gate except 3 and 4 should be indifferent to Medusa changing.
The old gates broke it — gate 1 had 9 direct IR-shape reads and gate 2 had 12 — because they
ran on a PROGRAM. These run on a DECLARATION LIST. **There is no program shape here to read,**
so they cannot be coupled to it. The split did the decoupling; no refactor was needed.

# ⇒ WHAT THEY DO NOT DO

**NEITHER GATE REPAIRS.** Gate 1 says a name was invented; it does not invent a better one.
Gate 2 says a value is illegal; it does not choose a legal one. Everything they find becomes a
QUESTION, because we cannot know what the operator meant and it is theirs to say
([[gorgon-gates-check-legality]]).

**AND GATE 2'S WORLD ARM NEEDS A WORLD.** The manifest says what is POSSIBLE; only the lab says
what is THERE. `conflicts()` takes an optional world and is the arm that catches the operator's
own scenario — *"you asked me to create web and there is already a web"* — which is exactly
where pass 1's 85% existence answer gets checked rather than trusted.
"""
from typing import Dict, List, NamedTuple, Optional

from planner.formula.legal import Board
from . import schema as S


class Finding(NamedTuple):
    gate: int
    kind: str                # invented · unknown-kind · no-such-attribute · illegal-value · …
    about: str               # the declared name it concerns
    says: str                # the question, in the operator's terms

    def __repr__(self):
        return f"[gate {self.gate}] {self.about}: {self.says}"


# ⇒ THE RULE NAMES EACH GATE OWNS. Declared so `test_each_gate_owns_its_own_checks` can hold
#   them apart — the thing that would have caught the destructive guard living in the pipeline
#   and `role-unsettled` living in the grammar gate, instead of me noticing weeks later.
GATE1_OWNS = frozenset({"invented", "invented-value", "left-over", "unread-value",
                        "unused-declaration"})
GATE2_OWNS = frozenset({"unknown-kind", "kind-not-settled", "no-such-kind",
                        "no-such-attribute",
                        "illegal-value", "cannot-be-made", "unread-descriptor",
                        "already-there", "not-there", "unverifiable"})

# ⇒ NEITHER OF THESE MAY BE RETRIED. Only the operator or the lab can say what a kindless row
#   is, so handing it back to the model is inviting the guess the kindless row exists to
#   prevent. Named here rather than spelled out at the guard, because it was already one
#   literal in `pipeline.py` and a second copy is how the pair drifts apart.
UNSETTLED_KIND = frozenset({"kind-not-settled", "no-such-kind"})


def _words(text: str) -> set:
    return {w.strip(".,'\"!?:;()[]").lower() for w in str(text).split() if w.strip(".,'\"!?:;()")}


def _traces(value, request: str) -> bool:
    """Does this value appear in the request, allowing for the operator's own wording?"""
    token = str(value).strip().lower()
    if token in ("true", "false", ""):
        return True                       # a boolean is a reading of the words, not a quote
    if token in request.lower():
        return True
    return any(token in w or w in token for w in _words(request) if len(w) > 3)


# ── GATE 1 · did you say this? ────────────────────────────────────────────────────────
def gate1(rows: List[S.Declared], request: str,
          board: Optional[Board] = None) -> List[Finding]:
    """Every name and every VALUE must trace to the request — AND NOTHING MAY BE LEFT OVER.

    THE ATTRIBUTE IS NOT CHECKED — it comes from a closed enum the manifest supplied, so it
    could not have been invented. Only what the model chose freely can be.

    ⇒ **AND THE OTHER HALF IS THE ONE NO GATE HAS EVER HAD.** The operator's rule: an object
      may stand alone, but a descriptor, an amount or an adjective may not. So after the
      declarations are made, every content word the request used must be COVERED by some
      declared span. What is left is a clause nobody read.

      Rung 13's dropped clique has been unowned by any gate precisely because no check that
      reasons over what is PRESENT can see what is ABSENT. Spans invert that: absence becomes
      a comparison against the request's own text.
    """
    out: List[Finding] = []
    for row in rows:
        if not _traces(row.name, request):
            out.append(Finding(1, "invented", row.name,
                               f"nothing in the request says {row.name!r} — did you mean it?"))
        for attr, value in (row.where or {}).items():
            if not _traces(value, request):
                out.append(Finding(1, "invented-value", row.name,
                                   f"the request never says {attr} is {value!r} — "
                                   f"did you mean that?"))

    # ⇒ NOTHING LEFT OVER. Anything the request said that no declaration claimed.
    #
    #   A DECLARED WORD IS CLAIMED WHEREVER IT APPEARS. Counting only the DECLARING span made
    #   every later mention look orphaned — rung 3 accused `web` and `lab`, which it had
    #   declared and then simply referred to again. A reference is not a lost clause.
    #   A REFERENCE CLAIMS ITS OWN WORD, NOT A FRESH SPAN AROUND IT. Re-scanning a span's
    #   words at their OTHER occurrences swallowed whole different phrases — `labelled` appears
    #   twice in rung 6, and re-scanning the second one claimed `'blue'`, hiding the very drop
    #   this check exists to find. So later mentions mark only themselves.
    import re as _re
    from .scan import scan, uncovered
    low = request.lower()
    spans = []
    for row in rows:
        located = scan(row.span or row.name, request, board)
        if located:
            spans.append((located.start, located.end))
        for word in {row.name, *(row.references or ())}:
            for m in _re.finditer(_re.escape(str(word).lower()), low):
                spans.append((m.start(), m.end()))
        for word in str(row.span or row.name).lower().split():
            for m in _re.finditer(rf"\b{_re.escape(word.strip(chr(34) + chr(39) + '.,'))}\b", low):
                spans.append((m.start(), m.end()))

    orphans = uncovered(request, spans, board)
    if orphans:
        # ⇒ THIS ONE BOUNCES TO THE AI, IT DOES NOT ASK THE OPERATOR. The operator, 2026-08-08:
        #   *"if there is a residual, gate 1 bounces it back to the AI."* Right — the words are
        #   in the request, so the operator already said them. Failing to read them is the
        #   model's miss, and the model gets another go with the residue named. An operator
        #   question is for what the request genuinely does not settle; this is not that.
        out.append(Finding(1, "left-over", ", ".join(orphans),
                           f"you did not account for {', '.join(repr(o) for o in orphans)} — "
                           f"read the request again and declare what it belongs to"))
    return out


def completeness(rows: List[S.Declared], operations, table,
                 board: Optional[Board] = None,
                 goals: Optional[List[dict]] = None) -> List[Finding]:
    """GATE 1's OTHER HALF — nothing declared may go unused.

    ⇒ **THIS IS THE LEFTOVER RULE, ONE LEVEL UP.** Gate 1 already asks which WORDS no
      declaration claimed; this asks which DECLARATIONS no operation claimed. Same question,
      same gate, the other side of the pair — *an object may stand alone, but a thing nobody
      does anything with is a step missing*.

    ⇒ **AND IT LIVED IN THE LINGUISTICS GATE, WHICH OWNS GRAMMAR AND NOT COMPLETENESS.** It
      was written there because that is where I happened to be, and a check owned by the wrong
      gate is a check nobody audits. It needs BOTH artifacts, which is why it is a second entry
      point rather than part of `gate1` itself.
    """
    from planner.ir import config as _config

    used = {str(op.on) for op in operations}
    used |= {str(op.value) for op in operations if op.value}

    # ⇒⇒ A CREATOR ACCOUNTS FOR WHAT IT PRODUCES, NOT ONLY FOR WHAT IT NAMES.
    #
    #   Rung 12 — *"take a snapshot of every running vm"* — declares TWO rows, and once the
    #   program is right (`create_snapshot(running_vms)`) the second one looks orphaned:
    #   `'snapshot' was declared and no operation touches it`. But `snapshot` is not an
    #   independent object. **It is the PRODUCT of the step**, bound under *every*, and the
    #   step that makes it is exactly the one that "does not touch" it.
    #
    #   ⇒ THIS IS `gate3._referents`' RULE FROM THE OTHER SIDE. There, a creator's own target is
    #     exempt from needing an establisher, because *it is what brings it about*. Here, what a
    #     creator brings about is exempt from needing a toucher, for the same reason. One fact,
    #     two gates, and leaving it out of this one turned a CORRECT program into a bounce.
    #
    #   ⇒ AND IT IS READ OFF THE MANIFEST — the kind each operator creates, never a list.
    from .gate3 import _made_kind as _makes
    # ⇒⇒ **ONLY A ONE-PER-MEMBER CREATION ACCOUNTS FOR A ROW IT DOES NOT TARGET.**
    #   This exempted any row whose KIND some creator produced, which was too wide and I said so
    #   when I wrote it. It bit on rung 10: `clone_vm(vms, golden)` produces `vm`s, `golden` IS a
    #   vm, so a DECLARED AND COMPLETELY UNUSED `golden` was silently exempted while the program
    #   cloned from an operator name instead.
    #   ⇒ THE DISTINCTION IS THE KINDS. Rung 12's `create_snapshot(running_vms)` makes SNAPSHOTS
    #     from VMS — different kinds — so a `snapshot` row it never names is genuinely its
    #     product. A clone makes vms from vms, so another vm row is NOT accounted for by it.
    _board = board or Board()
    by_handle = {sym.handle: sym.row for sym in table}
    produced = set()
    for op in operations:
        kind = _makes(op.operator, _board)
        target = by_handle.get(str(op.on))
        if kind and target is not None and kind != target.kind:
            produced.add(kind)

    out: List[Finding] = []
    for sym in table:
        if sym.row.object_type == S.UNKNOWN_KIND:
            continue

        # ⇒⇒ A THING DECLARED **NEW** MUST BE MADE BY SOMETHING. The other half of completeness,
        #   and the one rung 6 needed.
        #
        #   *"put the blue ones on a DIFFERENT network"* declares a second network, pass 1 marks
        #   it NEW, and the program served `add_vm_to_network(blue_vms, 'network_2')` with no
        #   `create_network` anywhere. Every check passed it: gate 2 stays quiet BECAUSE it is
        #   new — a new thing is not expected to exist yet — and `unused-declaration` stays quiet
        #   because it IS used. Used, but never made.
        #
        #   ⇒ AND IT IS THE SAME QUESTION AS THE LINE ABOVE, NOT A NEW ONE: does the program
        #     account for every declaration? One asks whether anything TOUCHES it; this asks
        #     whether anything BRINGS IT ABOUT.
        # ⇒ ONLY A SINGLE THING SOMETHING ELSE DEPENDS ON. Two guards, and rung 11 bought both:
        #     A SET IS A SELECTION, NOT AN OBJECT. `vms` is *every vm* — declared NEW by pass 1's
        #     weakest field (85%, and every error toward NEW) — and demanding a creator for it
        #     bounced the one rung this whole design was built for.
        #     AND THE HARM IS DEPENDENCE, not the existence flag. `add_vm_to_network(blue_vms,
        #     'network_2')` needs `network_2` to be there; a row nobody relies on is harmless
        #     however it was labelled. Keying on dependence rather than on `existence` alone
        #     stops a weak field becoming a hard bounce.
        # ⇒⇒ `uncreated-declaration` LIVED HERE AND IS NOW GATE 3's `unestablished-referent`.
        #
        #   The operator placed it, 2026-08-11: *"gate 2 for the world check, and gate 3 to
        #   identify network_2 has been referenced with no maker/fetch."* Restated as *this
        #   step's referent is never established* it is a fact about ONE OPERATION's soundness,
        #   which is gate 3's grain — where phrased as *no step creates it* it read as an
        #   absence and looked like gate 4's.
        #
        #   ⇒ AND IT JOINED A RULE THAT ALREADY EXISTED THERE. `not-settled-yet` says a
        #     probe-defined set must be probed first; this says a thing must be fetched or made
        #     first. One rule, three establishers — a probe, a fetch, a creator.
        #
        #   ⇒ **THIS ALSO CONTRADICTS [[gorgon-orchestrator-proposes-a-scaffold]]**, which moved
        #     it gate 1 -> gate 4 on 08-11 morning. The operator's restatement is what changed
        #     it, and the memory is updated rather than left to drift.

        # ⇒⇒ A ROW A GOAL IS ABOUT IS ACCOUNTED FOR. *"make sure there are exactly two machines
        #   left"* declares `vms` and proposes NO steps over it — the engine derives whatever
        #   closes the goal. Reporting it untouched would be complaining that a scaffold whose
        #   whole content is a goal has not written the goal's implementation.
        #   ⇒ SAME SHAPE AS THE CREATOR EXEMPTION ABOVE, AND AS `mood-achieve` AND
        #     `count-ignored`: a check written when steps were the only expression.
        if sym.handle in used or sym.row.kind in produced:
            continue
        if any(S.governs(g, sym.row) for g in (goals or ())):
            continue
        out.append(Finding(1, "unused-declaration", sym.handle,
                           f"{sym.handle!r} was declared and no operation touches it — either "
                           f"it is not a thing, or a step is missing"))
    return out


def bounces(findings: List[Finding]) -> List[Finding]:
    """What goes BACK TO THE MODEL rather than to the operator.

    ⇒ **AND A SPAN-GRAIN RESIDUE BOUNCES ON THE SAME GROUND.** `unread-value` is a word the
      REQUEST itself binds — quoted as a value, or named outright — that no declaration
      carries. The operator already said it, so failing to read it is the model's miss, which
      is precisely the test that decides this list.
    """
    return [f for f in findings if f.kind in ("left-over", "unread-value",
                                          "unused-declaration")]


def residues(rows: List[S.Declared], request: str, board: Optional[Board] = None,
             world=None) -> List[Finding]:
    """THE SPAN-GRAIN HALF OF THE LEFTOVER RULE — see `residue.py` for why it is needed.

    Gate 1 asks which words no SPAN claimed. This asks which words inside a span no CONDITION
    claimed, and routes each by the SLOT it landed in rather than by what it might mean:

        BOUNCE      the request binds it and the reading missed it   -> the model
        ASK         only an open slot could hold it                  -> the operator
        RELATIONAL  it carries a set operation                       -> pass 2
    """
    from .residue import ASK, BOUNCE, REJECT, report as _residue
    out: List[Finding] = []
    for r in _residue(rows, request, board, world):
        if r.verdict == BOUNCE:
            out.append(Finding(1, "unread-value", r.word,
                               f"{r.why} — read the request again and declare what "
                               f"{r.word!r} belongs to"))
        elif r.verdict in (ASK, REJECT):
            out.append(Finding(2, "unread-descriptor", r.word,
                               f"{r.why}. Is it a name, a label, or should it be ignored?"))
    return out


def _locate(row: S.Declared, request: str, board: Optional[Board] = None):
    from .scan import scan
    return scan(row.span or row.name, request, board)


# ── GATE 2 · can the world hold it? ───────────────────────────────────────────────────
def gate2(rows: List[S.Declared], board: Optional[Board] = None) -> List[Finding]:
    """Legality against the manifest. Nothing here needs the lab to be running."""
    board = board or Board()
    out: List[Finding] = []
    for row in rows:
        if row.kind not in board.kinds:
            # ⇒ AN UNSETTLED KIND IS A DIFFERENT QUESTION FROM A WRONG ONE, AND ONLY THE
            #   OPERATOR CAN ANSWER IT. `?` does not mean the lab lacks that kind; it means the
            #   request never said what the thing IS — `grubnash` may be a machine name or it
            #   may be noise, and nothing in the words decides. Phrased as *"this lab has no
            #   '?'"* the finding was unanswerable, which made the honest outcome of item 0
            #   look like a malfunction.
            if row.kind == S.UNKNOWN_KIND:
                # ⇒⇒ TWO DIFFERENT QUESTIONS WORE ONE SENTENCE UNTIL 2026-08-11.
                #
                #   *"the request does not say what X is"* is true of `n1` — a bare name that
                #   could be a machine or could be noise. It is NOT true of `routers`: that
                #   request says perfectly clearly what it wants and this lab has no such
                #   thing. Asking the operator to disambiguate a word they used correctly is
                #   the wrong question, and offering them six kinds none of which is the
                #   answer is the closed slot that manufactures a confident wrong one.
                #
                #   `unroutable` is set only when the routing stage RAN and declined, so an
                #   unmarked row means UNASKED rather than routable.
                if row.unroutable:
                    out.append(Finding(2, "no-such-kind", row.name,
                                       f"{row.name!r} is not one of the things this lab keeps "
                                       f"— it has {', '.join(sorted(board.kinds))}. Is there "
                                       f"another name for it, or is this out of scope?"))
                else:
                    out.append(Finding(2, "kind-not-settled", row.name,
                                       f"the request does not say what {row.name!r} is — "
                                       f"this lab has {', '.join(sorted(board.kinds))}"))
            else:
                out.append(Finding(2, "unknown-kind", row.name,
                                   f"this lab has no {row.kind!r}"))
            continue
        for attr, value in (row.where or {}).items():
            if attr not in board.filterable(row.kind):
                out.append(Finding(2, "no-such-attribute", row.name,
                                   f"a {row.kind} has no {attr!r}"))
                continue
            allowed = board.values(row.kind, attr)
            if allowed and str(value).lower() not in [a.lower() for a in allowed]:
                out.append(Finding(2, "illegal-value", row.name,
                                   f"{row.kind}.{attr} cannot be {value!r} — "
                                   f"it must be one of {allowed}"))
        # A SET DEFINED BY A PROBE CANNOT BE CREATED — you can only go and look.
        if row.residual and row.existence == S.NEW:
            out.append(Finding(2, "cannot-be-made", row.name,
                               f"{row.name!r} is decided by asking the machines, so it cannot "
                               f"be created — only found"))
    return out


def conflicts(rows: List[S.Declared], world, board: Optional[Board] = None) -> List[Finding]:
    """GATE 2'S WORLD ARM — the operator's own scenario, and it needs a lab to answer.

    *"What if a resource exists so fetch is triggered, but the user asks for creation anyway?
    Gate 2 has to know the difference based on the information from the AI."*

    Pass 1 states an intent at 85%, with every measured error toward `new`. This is where that
    intent is CHECKED rather than trusted, and the disagreement becomes a question.
    """
    board = board or Board()
    out: List[Finding] = []
    if world is None:
        return out
    from planner.gates import claims as _claims

    for row in rows:
        key_attr = _claims.key_of(row.kind, board.kinds)
        value = (row.where or {}).get(key_attr) if key_attr else None
        # ⇒ AND A CANDIDATE IDENTITY IS RESOLVED HERE, WHICH IS THE WHOLE POINT OF CARRYING IT.
        #   `box` is a declared noun for `vm` AND a plausible machine name; nothing in the
        #   request settles which, and only the lab can. Present means it was a REFERENCE;
        #   absent means the word was the common noun after all.
        if not value and row.identity:
            value = row.identity
        if not value:
            # ⇒⇒ AN UNIDENTIFIABLE ROW WAS SKIPPED **SILENTLY**, AND THAT IS THIS GATE'S HOLE.
            #
            #   `conflicts` asks the lab whether a declared thing is there, and gives up the
            #   moment it has no name to ask about. So a row with no key value is never checked
            #   AT ALL — it is assumed to exist, quietly, and everything downstream trusts it.
            #
            #   ⇒ RUNG 6 IS WHAT THAT COSTS. *"put the blue ones on a different network"*
            #     declares a second network with no name; nothing creates it; and the program
            #     served `add_vm_to_network(blue_vms, 'network_2')` — machines onto a network
            #     that will not exist when the step runs. Every later check passed it: the
            #     handle resolves in the symbol table and it IS used, so nothing called it
            #     orphaned.
            #
            #   ⇒ **A SINGLE THING MUST BE IDENTIFIABLE; A SET NEED NOT BE.** A set is defined
            #     by its filter and is looked up by that, so `5 vms` is not missing a name. One
            #     unnamed thing asserted to exist is a question, and asking it is exactly what
            #     this gate is for.
            if not row.is_set and row.existence == S.EXISTING:
                out.append(Finding(2, "unverifiable", row.name,
                                   f"{row.name!r} is referred to as if it exists, and it has "
                                   f"no name to look up — which {row.kind} is it, or should "
                                   f"one be made?"))
            continue
        try:
            there = bool(world.select({"kind": row.kind, key_attr: value}))
        except Exception:
            continue
        if row.existence == S.NEW and there:
            out.append(Finding(2, "already-there", row.name,
                               f"you asked to create {value!r} and there is already one — "
                               f"use it, or did you mean a second?"))
        if row.existence == S.EXISTING and not there:
            out.append(Finding(2, "not-there", row.name,
                               f"{value!r} is referred to as if it exists and the lab has "
                               f"none — should it be created?"))
    return out


def report(rows: List[S.Declared], request: str, board: Optional[Board] = None,
           world=None) -> Dict[str, object]:
    """Both gates over one symbol table. NOTHING IS REPAIRED — findings are questions."""
    board = board or Board()
    found = (gate1(rows, request, board) + gate2(rows, board)
             + conflicts(rows, world, board) + residues(rows, request, board, world))
    return {
        "findings": found,
        # ⇒ THE OPERATOR'S HALF ONLY. A bounce is not a question — the words are already in the
        #   request, so it goes back to the model instead of costing the operator a turn.
        "asks": [f.says for f in found if f not in bounces(found)],
        "bounces": bounces(found),
        "legal": not found,
        "by_gate": {1: [f for f in found if f.gate == 1],
                    2: [f for f in found if f.gate == 2]},
    }
