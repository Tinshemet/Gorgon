"""PASS TWO — WHAT HAS TO BE DONE. One question, three closed fields, over pass 1's own rows.

    PYTHONPATH=. python3 -m orchestrator.seam.pass2 --runs 3
    PYTHONPATH=. python3 -m orchestrator.seam.pass2 --only 11 --handles span

# WHAT IS ALREADY PROVEN, AND WHAT IS NOT

`condition_probe` measured this exact shape at n=3, every cell byte-identical:

    framing A  {operator, on, value}      6 EXACT of 12      ⇐ this one
    framing B  {operator, on, condition}  3 of 12

    rung 11 EXACT 3/3   probe_alive on the fleet, stop_vm on the run-time set
    rung 3  EXACT 3/3   the cross-reference I predicted would break

⇒ **SO THE QUESTION IS NOT WHETHER THE MODEL CAN DO THIS.** It is whether it can still do it
  against the symbol table PASS 1 ACTUALLY PRODUCES — and that is a different table. The probe
  offered hand-written handles; pass 1 names a row by its span:

      probe            fleet · unresponsive · web · lab
      pass 1 today     'every vm' · 'stop the ones that do not answer' · 'a vm named web'

  Those go into an ENUM. A 34-character enum member is not the thing that was measured, so
  this file derives a HANDLE for every row and the `--handles` flag keeps the comparison
  runnable rather than assumed.

# ⇒ THE HANDLE IS COMPUTED, NEVER ASKED (rule W8)

    a row with a key value      ->  that value            alpha · web · lab · db · dmz
    a set with a condition      ->  <value>_<kind>s       stopped_vms · red_vms
    a boolean condition         ->  not_<attr>_<kind>s    not_alive_vms
    anything else               ->  <kind>s_<n>           vms_1 · network_1

**AND A HANDLE IS NOT A NAME.** It is an address into the symbol table, which is why it may be
mechanical. The DEFINITION column carries the meaning, exactly as it did in the probe.

# ⇒ THE OPERATOR ENUM'S ORDER IS PINNED, AND THAT IS LOAD-BEARING

The probe measured four orderings of the SAME closed set. Moving one entry — `add_label` —
from the front to the back **doubled exact matches and removed every spurious step**, with no
change to prompt, schema or model. Order is semantically meaningless in a closed set, which
makes it a hidden parameter: inherit `sorted()` and a manifest edit silently moves behaviour.
So the order is declared here and pinned by a test, the same treatment `types_offered` gets.
"""

# ⚠⚠ THIS FILE CONTAINS A MODEL-SPECIFIC TUNING — SEE two-pass-rules.md §4b
#
#   `operators_offered` pins `add_label` LAST. That was measured on llama3.1:8b and on nothing
#   else. Measured 2026-08-10 across three models on identical payloads:
#
#       pinned   llama 9/9 (0 risky)   mistral 9/9 (5 risky)   qwen 9/9 (3 risky)
#       alpha    llama 8/9 (4 risky)   mistral 9/9 (5 risky)   qwen 9/9 (0 risky)
#
#   ⇒ REMOVING IT DEGRADES LLAMA AND IMPROVES QWEN. It compensates for one model's position
#     bias; it does not fix a general defect. IF YOU CHANGE THE MODEL, re-measure the knobs or
#     run `--order alpha` and accept the unfitted ceiling. Do not assume this transfers.

import re
from collections import Counter
from typing import Dict, List, NamedTuple, Optional

from planner.formula.legal import Board
from . import schema as S
from .effects import Operation


class Symbol(NamedTuple):
    handle: str                  # the address pass 2 refers to
    row: S.Declared              # the declaration it points at
    definition: str              # what it means, in the request's own terms
    settled: str


def _plural(kind: str) -> str:
    return f"{kind}es" if kind.endswith(("s", "x", "ch")) else f"{kind}s"


def handle_for(row: S.Declared, board: Board, taken: Optional[set] = None) -> str:
    """A short address for a declaration. Deterministic, and never asked for.

    ⇒ **THE KEY VALUE WINS WHENEVER THERE IS ONE**, because that is the word the operator used
      and the one the request will refer to again. `a vm named alpha` addresses as `alpha`.

    ⇒⇒ **AND A SET THAT LEAVES SOMETHING OUT SAYS SO IN ITS NAME** — the operator's
      `all_vms_but_db`. The suffix is applied HERE, at the single exit, because `_stem_for` has
      five return paths and putting it on the last one meant it never fired for the row it was
      written for: rung 8's set takes the `where`-condition branch and left as `core_vms`.
      **A rule on one path of several is the defect this session found six times.**
    """
    taken = taken if taken is not None else set()
    stem = _stem_for(row, board)
    if row.excludes:
        stem = f"{stem}_but_{'_'.join(_slug(v) for f in row.excludes for v in f.values())}"
    return _free(stem, taken)


def _stem_for(row: S.Declared, board: Board) -> str:
    """The address before dedupe and before any exclusion suffix."""
    from planner.gates import claims as _claims
    taken: set = set()                    # local: dedupe belongs to `handle_for`
    kind = row.kind if row.kind in board.kinds else "thing"

    key_attr = _claims.key_of(kind, board.kinds) if kind in board.kinds else None
    if key_attr and (row.where or {}).get(key_attr):
        return str(row.where[key_attr])
    if row.identity:
        return str(row.identity)

    # a CONDITION describes the set better than a number ever could
    for attr, value in (row.where or {}).items():
        if isinstance(value, bool) or str(value).lower() in ("true", "false"):
            truthy = value is True or str(value).lower() == "true"
            stem = f"{attr}_{_plural(kind)}" if truthy else f"not_{attr}_{_plural(kind)}"
            return stem
        return f"{_slug(value)}_{_plural(kind)}"

    # ⇒ A KINDLESS ROW STILL HAS THE OPERATOR'S OWN WORD IN IT, AND THAT BEATS `thing`.
    #   Rung 9's three machines addressed as `thing`, `thing_2`, `thing_3` — three
    #   indistinguishable enum members for three distinct objects, which is the surest way to
    #   make the model pick the wrong one. The span's last content word is `n1`, `n2`, `n3`.
    if kind not in board.kinds:
        from planner.ir import config as _config
        from .scan import GRAMMAR, _operation_words
        # ⇒ AND THE WORD MUST BE ONE NOTHING ELSE OWNS. Taking the last non-grammar word gave
        #   `ping` for *"n3 can all ping each other"* — a verb addressing a machine. A verb
        #   belongs to the operation and an attribute word belongs to the condition, so
        #   neither can be this row's address; what is left is the operator's own noun.
        attrs = set()
        for spec in (_config.KINDS or {}).values():
            if isinstance(spec, dict):
                attrs |= set(spec.get("attrs") or []) | set((spec.get("aliases") or {}).keys())
        verbs = _operation_words(board)
        words = [w.strip(".,'\"—–") for w in str(row.span or row.name).lower().split()]
        free = [w for w in words if w and w not in GRAMMAR and w not in verbs and w not in attrs]
        if free:
            return free[-1]

    return _plural(kind) if row.is_set else kind


def _slug(value) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "x"


def _free(stem: str, taken: set) -> str:
    stem = _slug(stem)
    if stem not in taken:
        taken.add(stem)
        return stem
    n = 2
    while f"{stem}_{n}" in taken:
        n += 1
    taken.add(f"{stem}_{n}")
    return f"{stem}_{n}"


def symbol_table(rows: List[S.Declared], board: Optional[Board] = None,
                 handles: str = "derived") -> List[Symbol]:
    """Pass 1's rows as addresses pass 2 may refer to — AND NOTHING ELSE MAY BE REFERRED TO.

    Rule D1: an undeclared reference is not caught by a check, it is UNDECODABLE, because the
    handles ARE the enum. That is the contract enforced by the grammar rather than by a gate.
    """
    board = board or Board()
    taken: set = set()
    out: List[Symbol] = []
    for row in rows:
        handle = row.name if handles == "span" else handle_for(row, board, taken)
        where = ", ".join(f"{k} = {v}" for k, v in (row.where or {}).items())
        kind = row.kind if row.kind in board.kinds else "thing"
        # ⇒⇒ THE EXCLUSION TRAVELS WITH THE SET, INTO THE ONLY THING PASS 2 READS.
        #   Rung 8's set is `all vms but db`, and until now the payload said only *"the vms
        #   where network = core"* — so the model was being asked to respect a subtraction it
        #   was never shown. Declaring it (`Declared.excludes`) and not SAYING it would have
        #   been the same defect one layer down.
        gone = "; ".join(", ".join(f"{k} = {v}" for k, v in f.items())
                         for f in (row.excludes or ()))
        definition = (f"{'the ' + kind if not row.is_set else 'the ' + _plural(kind)}"
                      f"{' where ' + where if where else ''}"
                      f"{' except ' + gone if gone else ''}")
        if row.count is not None:
            definition = f"{row.count} {definition}"
        out.append(Symbol(handle, row, definition, row.settled))
    return out


def operators_offered(board: Optional[Board] = None, order: str = "pinned",
                      request: str = "") -> List[str]:
    """creators + setters + delete + a probe per observed fact, IN A PINNED ORDER.

    ⇒ **`add_label` GOES LAST AND THAT IS A MEASUREMENT, NOT A PREFERENCE.** Four orderings of
      this same set, n=3: with `add_label` at index 0 or 1 the probe produced 6 spurious steps
      and 3/9 exact; moving that ONE entry to the end gave 0 spurious and 6/9, reproducing the
      fully-reversed ordering exactly. `stop_first` shares its head with `reversed` and behaved
      like alphabetical, so it is not first-member bias — it is that entry's position.

    ⇒ **AND IT IS PINNED HERE RATHER THAN SORTED SO IT CANNOT DRIFT.** A kind added to the
      manifest tomorrow would reshuffle `sorted()` and move behaviour with no visible cause.
    """
    from planner.ir import config as _config
    board = board or Board()
    table = _config.KINDS or {}
    out: List[str] = []
    for kind, spec in sorted(table.items()):
        if not isinstance(spec, dict):
            continue
        for name in (spec.get("creators") or {}):
            out.append(f"create_{kind}" if name == "create" else f"{name}_{kind}")
        for setter in (spec.get("setters") or {}):
            out.append(setter)
        if spec.get("delete"):
            out.append(f"delete_{kind}")
        for fact in (spec.get("observed") or {}):
            out.append(f"probe_{fact}")
    ordered = sorted(set(out))

    # ⇒⇒ `request=...` SHRINKS THE CHOICE SET BY EVIDENCE, AND THAT IS THE GENERAL MOVE.
    #
    #   The pin below was fitted to one model: remove it and llama degrades while qwen improves
    #   sharply. Compensating for a position bias is per-model by construction. REMOVING THE
    #   ROOM FOR ONE IS NOT — seventeen operators give position somewhere to hide, four do not.
    #   And the filter is the SAME `evidence_for` used to detect unasked steps afterwards,
    #   applied BEFORE the ask instead: a detector turned into a producer, which is the only
    #   direction this project has ever measured working.
    if request:
        from .linguistics import evidence_for
        from .scan import _stem
        said = {w.strip(".,'\"—–") for w in request.lower().split()}
        said |= {_stem(w) for w in said}
        warranted = [o for o in ordered if (evidence_for(o, board) & said)]
        if warranted:
            ordered = warranted

    # ⇒ `order="alpha"` IS THE UNTUNED CONTROL. The pin below was measured on llama3.1:8b and
    #   nothing else, so it is a candidate PROJECT BIAS: if the ranking of models changes when
    #   the pin is removed, the pin was fitting one model rather than fixing a general defect.
    if order == "alpha":
        return ordered
    return [o for o in ordered if o != "add_label"] + ["add_label"]


ASK = ("Say what has to be DONE, as a list of steps. Each step names one operation and the ONE "
       "already-identified thing it acts on. Some operations need a second thing as their "
       "value — otherwise leave value null. Use only the operations and the names offered. "
       "Do not invent a name.")

CLAUSE_ASK = ("Say what has to be DONE for the marked part of the request, as a list of steps. "
              "Each step names one operation and the ONE already-identified thing it acts on. "
              "Some operations need a second thing as their value — otherwise leave value "
              "null. If the marked part needs no operation of its own, answer with no steps. "
              "Use only the operations and the names offered. Do not invent a name.")

# a clause ends at these; `of` is a PHRASE boundary and is deliberately not one of them
CLAUSE_MARKS = (",", ";", ".", "—", "–")
CLAUSE_WORDS = (" and then ", " then ", " and ", " but ")


def clauses_of(request: str) -> List[str]:
    """Cut the request where it joins itself — to ASK about, never to build from.

    ⇒ **THE RECORDED HAZARD, AND WHY IT DOES NOT APPLY HERE.** `clause_ledger` says plainly
      that *splitting prose to BUILD is what wrecked staged lowering: a fragment handed to an
      author has lost its referents.* True there, and not true here — **the fragment does not
      need to carry its referents, because the SYMBOL TABLE does.** Every call gets the whole
      handle table and the whole request; the clause only says which part to answer for.

    ⇒ **AND A MEMBER LIST IS NOT A CLAUSE BOUNDARY.** The same file records the splitter
      cutting *"make sure n1, n2 and n3 can all ping each other"* into three, which is the one
      bug it calls fixable. A comma between BARE NAMES with no verb between them is joining a
      list, not separating two things to do.
    """
    import re as _re
    parts, buf = [], []
    tokens = _re.split(r"([,;.—–])", request)
    for chunk in tokens:
        if chunk in CLAUSE_MARKS:
            buf.append(chunk)
            continue
        buf.append(chunk)
    text = "".join(buf)

    rough: List[str] = [text]
    for mark in CLAUSE_MARKS:
        rough = [bit for part in rough for bit in part.split(mark)]
    out: List[str] = []
    for part in rough:
        pieces = [part]
        for word in CLAUSE_WORDS:
            pieces = [bit for piece in pieces for bit in piece.split(word)]
        out.extend(pieces)

    # ⇒ REJOIN A MEMBER LIST. A piece with no verb the manifest knows, sitting between two
    #   others, is an item in a list rather than something to do — `n2` is not a clause.
    from .linguistics import manifest_verbs
    from .scan import GRAMMAR
    verbs = manifest_verbs()
    kept: List[str] = []
    for piece in out:
        words = [w.strip(".,'\"—–").lower() for w in piece.split()]
        content = [w for w in words if w and w not in GRAMMAR]
        has_verb = any(w in verbs for w in words)
        # ⇒⇒ **A PIECE WITH ITS OWN PREDICATE IS A CLAUSE, NOT A LIST MEMBER.** *"n1 is the
        #   jumpbox, so put it on core"* was rejoined whole — `n1 is the jumpbox` names no
        #   manifest verb and has two content words, so it looked exactly like `n2`. The order
        #   half then never got read at all.
        #   ⇒ A COPULA IS THE TEST, and it is what a list member never has: `n2` predicates
        #     nothing, `n1 IS the jumpbox` predicates. Rung 9's member list is untouched
        #     because none of its pieces carries one.
        #   ⇒ ⚠ AND THE TEST IS ON THE ABSORBING PIECE, NOT THE ABSORBED ONE. `so put it on
        #     core` carries no copula either — what makes it a separate clause is that the
        #     piece before it ALREADY predicates and has nothing left to take.
        from .speech_act import COPULA as _COPULA
        #   ⇒ EITHER SIDE SETTLES IT: a piece that already predicates has nothing left to
        #     take, and a piece that predicates on its own was never a list member.
        def _predicates(text):
            return any(w.strip(".,'\"—–").lower() in _COPULA for w in text.split())
        holds_a_predicate = (_predicates(kept[-1]) if kept else False) or _predicates(piece)
        if (kept and content and not has_verb and not holds_a_predicate
                and len(content) <= 2):
            kept[-1] = f"{kept[-1].rstrip()}, {piece.strip()}"
            continue
        if piece.strip():
            kept.append(piece.strip())
    return kept


def _schema(handles: List[str], operators: List[str], require_one: bool = True,
            free_value: bool = False) -> dict:
    """⇒ `require_one=False` IS THE REFUSAL ESCAPE, AND IT IS SUBTRACTIVE ON PURPOSE.

    Two attempts at reliable refusal have already been withdrawn after measurement
    ([[gorgon-refusal-enum-withdrawn]]): a closed enum of reasons, and a span-anchored
    quotation. Both ADDED a vocabulary for declining plus prompt text about when to use it,
    and the bisect proved the prompt text caused the gain and the damage alike. The standing
    conclusion is *"do not spend a third attempt on a better description of when to decline"*,
    beside the design law that **every additive schema move here has measured zero or
    negative** ([[gorgon-offering-is-not-using]]).

    So nothing is added. `minItems: 1` is REMOVED — the schema stops requiring an answer, and
    the empty list becomes representable. No new operator, no new field, no sentence about
    refusing anywhere in the prompt. That is the one form of this the evidence has not already
    refused: *removing a wrong option works; adding a right one does not.*

    Rung 9 is the row it exists for. *"make sure n1, n2 and n3 can all ping each other"* has
    NO legal answer — the manifest declares 21 acts for a vm and not one of them is
    connectivity — and the model answers `add_label(n1, n2)` 3 times out of 3 rather than
    nothing, because nothing was not expressible.
    """
    array: dict = {"type": "array", "items": None}
    if require_one:
        array["minItems"] = 1
    # ⇒ **THE VALUE ENUM MADE THE CORRECT ANSWER UNSAYABLE, AND THAT IS MY BUG NOT THE
    #   MODEL'S.** `enum: handles + [None]` permits only declared objects, so
    #   `add_label(prod_vms, "prod")` — a label is free text — cannot be expressed at all. The
    #   model is forced to pick a handle and picks the target itself:
    #
    #       add_label(prod_vms, prod_vms)   add_label(red_vms, red_vms)   ×5 across the corpus
    #
    #   That is five of the seven pass-2 errors in the first end-to-end run, and NOT a thing to
    #   retry around. The manifest already says which slots take text and which take an object
    #   (`refs`), and gate 3 already checks both directions — so the enum is doing no work the
    #   gate does not do better, while forbidding half the legal answers.
    value: dict = ({"type": ["string", "null"]} if free_value
                   else {"type": ["string", "null"], "enum": handles + [None]})
    return {
        "type": "object", "additionalProperties": False, "required": ["operations"],
        "properties": {"operations": {**array, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["operator", "on", "value"],
            "properties": {
                "operator": {"type": "string", "enum": operators},
                "on": {"type": "string", "enum": handles},
                "value": value,
            }}}},
    }


def derive_creators(operations, table, board: Optional[Board] = None):
    """A thing the program DEPENDS ON and never brings about — supplied by arithmetic.

    ⇒⇒ **THIS IS A PRODUCER, NOT A DETECTOR, AND THAT DISTINCTION IS THE WHOLE POINT.**
      `uncreated-declaration` has reported rung 6 correctly for days and the request still did
      not get served, because a finding is a report and the operator wanted the machines on a
      network. A day of adding checks moved served-correct from 4 to 4
      ([[gorgon-detector-not-producer-again]]); rungs close by ADDING A FACT or REMOVING AN
      OPTION. The manifest declares that a `network` is made by `create`, so
      `create_network(network_2)` is not a guess — it is a lookup, the same shape as
      `effects.conditions_after`, and there is NO MODEL CALL anywhere in it.

    ⇒⇒ **THE DETERMINER MUST INDEPENDENTLY AGREE, AND THAT IS THE SAFETY PROPERTY.**
      The operator's presupposition frame, 2026-08-11: a step like `add_vm_to_network`
      PRESUPPOSES its argument, and when that presupposition fails the determiner decides
      whether looking can settle it —

          INDEFINITE   'a different network'   nothing ever established a referent, so no
                       probe could find one -> the program must BRING IT ABOUT
          DEFINITE
          or NAMED     'golden', 'core', 'db'  there IS a referent to go and find -> ASK or
                       probe. NEVER create: the operator named it, and quietly making a second
                       one is the worst thing this could do.

      So `row.existence` alone is not enough. It is the model's weakest field (85%, every error
      toward NEW) and acting on it would let a wrong NEW BUILD A REAL NETWORK NOBODY ASKED FOR —
      which is strictly worse than the spurious bounce it replaced. Requiring the determiner to
      say NEW too means **a creator is only ever derived for something no one could have meant
      to already exist.**

    ⇒⇒ **THE OPERATOR'S RULE, 2026-08-11 — AND IT IS THE ORGANISING PRINCIPLE, NOT A CAVEAT:**

        *"creation is not destructive, but we shouldn't create resources unless it's
         NECESSARY, ALLOWED / INTENDED."*

      Three conditions, and every guard here answers exactly one of them. They were bought
      piecemeal from rung 11 and rung 8; this is what they were always for:

        NECESSARY  something else DEPENDS on it — an operation names it in a value slot.
                   A row nobody relies on is not missing a creator, it is just a row.
        ALLOWED    the manifest declares a way to make one. A kind with no creator cannot
                   be made, and inventing an operator for it would be fabrication.
        INTENDED   there is NOTHING TO LOOK IT UP BY. See `_is_named`.

      Anything failing one of the three is left alone and reported, never filled in.

    ⇒⇒ **THE DETERMINER USED TO GATE THIS AND NO LONGER DOES — the operator, 2026-08-11:**

        *"it seems like it identified correctly that there are 2 networks, it just forgot that
         a prerequisite to use it is to check if it exists, and if not, create it. If something
         is referenced but not created, you need to supply it either through a FETCH or CREATE."*

      That is structural and needs no vocabulary. The earlier version read `a` / `the` /
      `different` to infer NEW-vs-EXISTING — **but that question never had to be answered.**
      What matters is whether the thing EXISTS, and that is found by LOOKING, not by reading an
      article. The determiner was a proxy for a lookup, and it cost a word list (`scan.NOVEL`)
      to maintain a guess the world could settle outright.

      ⇒ SO THE SUPPLY IS DECIDED BY WHETHER THERE IS ANYTHING TO LOOK UP BY:

            named or filtered   -> a FETCH establishes it; `settle_with_world` already ran and
                                   the lab either held it or did not. NEVER created here.
            nothing to find     -> no probe could resolve it, so the program must MAKE it.

    ⇒ THIS IS ONE HALF OF A LARGER UNIFICATION THE OPERATOR PLACED IN **GATE 3** — every
      referent needs an ESTABLISHER (a probe, a fetch, or a creator) and one must run before the
      step that uses it. `not-settled-yet` is already that rule for probes. Not yet built.
    """
    board = board or Board()
    operations = list(operations)
    by_handle = {sym.handle: sym.row for sym in table}
    makers = _creators_by_kind(board)

    out = list(operations)
    for handle, row in by_handle.items():
        # ⚠ `row.existence` IS A PLACEHOLDER FOR THE FETCH THAT IS NOT BUILT, NOT A GUARD THAT
        #   EARNS ITS PLACE. The operator's rule is *check whether it exists, and if not, create
        #   it* — but for an UNNAMED row there is nothing to check WITH: `settle_with_world`
        #   looks up by key value, and *"the network"* offers none. Without that lookup, dropping
        #   this line would build a second network beside the one the lab already holds.
        #   ⇒ AND IT IS A WEAK STAND-IN: the field reads 85% with EVERY ERROR TOWARD NEW, i.e.
        #     toward creating. It fails in the unsafe direction. It goes when gate 3's
        #     establisher rule lands and the world is asked properly.
        if row.existence != S.NEW or row.is_set or row.kind not in board.kinds:
            continue
        if _is_named(row, board) and not getattr(row, "sanctioned", False):
            # ⇐ there is something to LOOK IT UP BY — see below. UNLESS THE OPERATOR SAID
            #   CREATE IT: this guard exists because the model's NEW is untrustworthy, and an
            #   operator answering *"yes, create them"* is the one authority that is.
            continue
        if not any(str(op.value) == handle for op in operations if op.value):
            continue                      # nothing depends on it, so nothing is missing
        kinds_makers = makers.get(row.kind) or set()
        if any(op.operator in kinds_makers and str(op.on) == handle for op in operations):
            continue                      # already made
        if not kinds_makers:
            continue                      # the manifest declares no way to make one
        # ⇒⇒ ALLOWED MEANS DERIVABLE, NOT MERELY CREATABLE — and `planner.ir.derive` already
        #   owns that judgement, so it is ASKED rather than re-decided here. `_creator_args`
        #   returns the OTHER required arguments from `create_defaults`, or **None when a
        #   required argument has no declaration** — *"the gap goes to the author"*.
        #
        #   Measured 2026-08-11: `snapshot` and `profile` both return None. Without this,
        #   R2 emitted `create_snapshot(...)` for a kind the project's own deriver refuses,
        #   producing a step that cannot run. `network` returns {} — which is the only reason
        #   rung 6 was correct, and it was correct BY LUCK rather than by this check.
        #
        #   ⇒ AND `{}` IS THE ONLY ACCEPTABLE ANSWER HERE, not merely a non-None one. This
        #     `Operation` carries (operator, on, value) and has NOWHERE to put `os_type`, so a
        #     kind needing extra arguments — `vm` needs `{'os_type': 'linux'}` — must go to the
        #     author too. Deriving it would silently drop the argument.
        if _derivable_args(row.kind) != {}:
            continue
        # ⇒ IT GOES IN FRONT OF THE FIRST STEP THAT NEEDS IT. Binding time is an ORDER, and a
        #   creator appended at the end would satisfy the CHECK while still running too late.
        need = next(i for i, op in enumerate(out) if str(op.value) == handle)
        out.insert(need, Operation(sorted(kinds_makers)[0], handle, None))
    return out


def merge_split_creation(operations, table, request: str,
                         board: Optional[Board] = None):
    """A creation the model split in two, rejoined. The clone's product became its own step.

    ⇒⇒ **THE OPERATOR'S READING, 2026-08-11:** *"it reads it as it goes along, but this sentence
      wraps back on itself."* Rung 10 — *"clone golden into 3 new vms"* — is emitted
      left-to-right as `clone_vm(golden)` and then `create_vm(vms)`, because *"into 3 new vms"*
      arrives after the verb and is taken as a fresh instruction. It is not: it is that verb's
      OBJECT. The clause completes an earlier verb instead of starting a new one.

            clone golden into 3 new vms
                  ^^^^^^      ^^^^^^^^^^
                  source      product — read as a separate creation

    ⇒ **THE TWO HALVES IDENTIFY EACH OTHER, SO NOTHING IS GUESSED.** A sourcing creator with no
      product has an empty slot; a same-kind creator in the SAME CLAUSE has a row with no verb
      that needed it. `incomplete-creation` already proves the first half is broken. The clause
      boundary is what licenses joining them — two halves of one clause, not two clauses.

    ⇒ **AND IT REPAIRS BY MERGING INFORMATION ALREADY PRESENT, NOT BY RELAXING A CHECK.** Every
      earlier attempt to make this rung SERVE loosened something and hid a real defect for
      hours. `incomplete-creation` and `duplicate-creation` both stay armed: a clone with no
      product and no orphan to pair with is still illegal, and two creators that do NOT pair
      still bounce.

    ⇒ EXACTLY ONE CANDIDATE, OR NOTHING HAPPENS. Two orphans in one clause would be a guess.
    """
    from .linguistics import anchor_to_clauses
    from .gate3 import _made_kind, _takes_a_source
    board = board or Board()
    by_handle = {sym.handle: sym.row for sym in table}

    clause_of = {}
    for clause, op in anchor_to_clauses(request, list(operations), board):
        clause_of[id(op)] = clause

    incomplete = [op for op in operations
                  if _takes_a_source(op.operator) and op.value in (None, "")]
    if not incomplete:
        return list(operations)

    out, dropped = list(operations), set()
    for broken in incomplete:
        kind = _made_kind(broken.operator, board)
        here = clause_of.get(id(broken))
        orphans = [op for op in operations
                   if op is not broken and id(op) not in dropped
                   and clause_of.get(id(op)) == here
                   and _made_kind(op.operator, board) == kind
                   and str(op.on) in by_handle]
        if len(orphans) != 1:
            continue                       # nothing to pair with, or a guess — leave it
        product = orphans[0]
        dropped.add(id(product))
        out = [Operation(broken.operator, str(product.on), str(broken.on))
               if op is broken else op for op in out]
    return [op for op in out if id(op) not in dropped]


def drop_redundant_creators(operations, table, request: str,
                            board: Optional[Board] = None):
    """One row, two makers — keep the one the REQUEST names and drop the other.

    ⇒⇒ **THE OPERATOR'S RULE, 2026-08-11:** *"if the model refuses to act on an error CAUGHT, it
      should be fixed regardless, because it's a cancerous defect — like a brain tumour, since
      everything but the reasoning is correct."* Rung 10 is exactly that: the reading, the roles,
      the establisher and the ordering are all right, and one step is wrong in a way that does
      not improve by asking. It was handed back three ways — a plain rejection, a split payload,
      and a direct statement of the contradiction — and came back byte-identical each time.

    ⇒ **AND THE PRECEDENT IS ALREADY HERE.** `housekeeping.sort_out` PURGES a cancerous
      suggestion rather than reporting it, on the operator's own reasoning that *"a cancerous
      housekeeping should be dropped but the core proposal shipped."* Same species, same remedy.

    ⇒ **WHICH ONE SURVIVES IS READ OFF THE REQUEST, NOT CHOSEN.** *"CLONE golden into 3 new
      vms"* names `clone` and never says `create`, so `clone_vm` is what was asked for. If BOTH
      verbs appear, or NEITHER does, nothing is dropped and gate 4's `duplicate-creation` stands
      — the same zero/one/several honesty used everywhere else, because a repair that guesses is
      worse than a finding that asks.
    """
    from .gate3 import _makers
    board = board or Board()
    words = {w.strip(".,'\"—–?!").lower() for w in str(request).split()}
    by_handle = {sym.handle: sym.row for sym in table}

    made_by: Dict[str, list] = {}
    for op in operations:
        row = by_handle.get(str(op.on))
        if row is not None and op.operator in _makers(row.kind):
            made_by.setdefault(str(op.on), []).append(op)

    doomed = set()
    for handle, makers in made_by.items():
        if len(makers) < 2:
            continue
        named = [op for op in makers if str(op.operator).split("_")[0].lower() in words]
        if len(named) == 1:
            doomed |= {id(op) for op in makers if op is not named[0]}
    return [op for op in operations if id(op) not in doomed]


def normalise_creator_args(operations, table, board: Optional[Board] = None):
    """A sourcing creator's target is its PRODUCT and its value is its SOURCE. Put them that way.

    ⇒⇒ **THE `Operation` TRIPLE IS POSITIONAL AND THE MANIFEST'S ROLES ARE NAMED.**
      `creators.clone` declares `key: new_name` and `from: source_name`, but an Operation is
      `(operator, on, value)` with nothing saying which is which. Rung 10 came back as
      `clone_vm(golden, vms)` — the SOURCE in the target slot — and every downstream rule read
      `on` as the thing being made, i.e. backwards.

    ⇒ **THE ROWS SETTLE IT WITHOUT A MODEL CALL.** A clone's product is the thing that does not
      exist yet and its source is the thing that does; `settle_sources` already marks `golden`
      EXISTING and `3 new vms` NEW. So the order is arithmetic, and the convention it restores
      is the one every other operation already follows — **`on` is what the step is ABOUT.**

    ⇒ ⚠ **AND IT ONLY SWAPS WHEN THE ROWS ARE UNAMBIGUOUS** — one NEW, one EXISTING. Two NEW or
      two EXISTING and nothing is touched, because guessing would be inventing a reading the
      declarations do not support.
    """
    from .gate3 import _takes_a_source
    board = board or Board()
    by_handle = {sym.handle: sym.row for sym in table}
    out = []
    for op in operations:
        target, source = by_handle.get(str(op.on)), by_handle.get(str(op.value or ""))
        if (op.value is not None and _takes_a_source(op.operator)
                and target is not None and source is not None
                and target.existence == S.EXISTING and source.existence == S.NEW):
            out.append(Operation(op.operator, str(op.value), str(op.on)))
            continue
        out.append(op)
    return out


def order_by_dependency(operations, table, board: Optional[Board] = None):
    """Every establisher before its dependents. Deterministic, no model call.

    ⇒⇒ **RUNG 8, MEASURED 2026-08-11.** Once the payload gained a `needed` section the model
      supplied BOTH missing creators — and put one of them in the wrong place:

          create_network(core) · add_vm_to_network(db, dmz) · create_network(dmz) · …
                                 ^^^^ uses dmz              ^^^^ makes it, too late

      Gate 3's establisher rule caught it, correctly: **binding time is an ORDER**, and a
      creator that runs after its dependent is not a creator that ran.

    ⇒ **AND ORDER IS NOT THE MODEL'S TO GET RIGHT.** Which step must precede which is a fact
      about the manifest and the symbol table, computable by arithmetic — `derive_creators`
      already places the creators IT inserts correctly, and only model-supplied ones went
      unsorted. Asking for correct ordering would be inviting a guess where a lookup exists.

    STABLE: an operation moves only far enough to sit behind what it needs, so a program that
    was already ordered comes back byte-identical. Cycles are broken rather than followed.
    """
    from .gate3 import _makers
    board = board or Board()
    ops = list(operations)
    by_handle = {sym.handle: sym.row for sym in table}

    made_at: Dict[str, int] = {}
    for i, op in enumerate(ops):
        row = by_handle.get(str(op.on))
        if row is not None and op.operator in _makers(row.kind):
            made_at.setdefault(str(op.on), i)

    out: List[Operation] = []
    placed: set = set()

    def needs(i: int) -> List[str]:
        op = ops[i]
        row = by_handle.get(str(op.on))
        out_refs = []
        if row is not None and op.operator not in _makers(row.kind):
            out_refs.append(str(op.on))          # a creator does not presuppose its own target
        if op.value is not None:
            out_refs.append(str(op.value))
        return out_refs

    def emit(i: int, seen: set) -> None:
        if i in placed or i in seen:
            return                                # already down, or a cycle — leave it be
        seen.add(i)
        for ref in needs(i):
            j = made_at.get(ref)
            if j is not None and j != i:
                emit(j, seen)
        if i not in placed:
            placed.add(i)
            out.append(ops[i])

    for i in range(len(ops)):
        emit(i, set())
    return out


def _derivable_args(kind: str):
    """`planner.ir.derive`'s own answer to *can a NEW of this kind be derived at all?*

    ⇒ ASKED, NEVER RE-DECIDED. That module is the SSOT for what a derived creation may pass to
      its creator, and a second copy of the rule here is how the pair drifts apart. Imported
      through `importlib` because `planner.ir.__init__` re-exports the FUNCTION `derive`, which
      shadows the module of the same name.
    """
    import importlib
    try:
        return importlib.import_module("planner.ir.derive")._creator_args(kind)
    except Exception:
        return None                       # cannot ask -> cannot derive. Fail closed.


def _is_named(row, board: Board) -> bool:
    """Does the request give this thing a NAME? Then it is INTENDED as a reference, not a make.

    ⇒⇒ **MEASURED 2026-08-11, AND IT IS WHY THE DETERMINER ALONE IS NOT ENOUGH.** Rung 8 says
      *"put every vm on A NETWORK CALLED CORE"*. The article is indefinite, so the determiner
      answers NEW and R2 built `core` — verified, not theorised. But `core` is a NAME, and the
      operator's presupposition frame settles what that means:

          INDEFINITE AND UNNAMED   'a different network'   nothing ever established a referent,
                                   so NO probe could find one -> the program must make it
          NAMED                    'a network called core'  there IS a referent to go and look
                                   for -> ASK or probe. **NEVER MAKE A SECOND ONE.**

    ⇒ **AND `already-there` IS NOT SUFFICIENT COVER.** It fires only when the lab is PROBED and
      holds one. Against an unseeded or unreachable kind it stays silent, and silence there is
      indistinguishable from absence ([[gorgon-book-keeper]]'s decision 6). That is precisely
      the case where quietly building a second `core` beside the operator's real one does the
      most damage and reports nothing.

    A name is either the row's confirmed identity or the kind's own KEY carried as a condition.
    """
    from planner.gates import claims as _claims
    if row.identity:
        return True
    key = _claims.key_of(row.kind, board.kinds)
    return bool(key and (row.where or {}).get(key))


def _creators_by_kind(board: Board):
    """{kind: {operator names that make one}} — read off the manifest, nothing hardcoded."""
    from planner.ir import config as _config
    out = {}
    for kind in board.kinds:
        spec = (_config.KINDS or {}).get(kind) or {}
        out[kind] = {f"create_{kind}" if n == "create" else f"{n}_{kind}"
                     for n in (spec.get("creators") or {})}
    return out


def _payload(request: str, table: List[Symbol], operators: List[str],
             rejected: Optional[List[str]] = None,
             needed: Optional[List[str]] = None) -> str:
    """The symbol table, the operators, the request — and, on a retry, what was REJECTED.

    ⇒ **THE REJECTIONS GO IN THE PAYLOAD AND NEVER IN THE PROMPT, AND THAT IS THE WHOLE SAFETY
      ARGUMENT.** The last time prompt text was added to make the model behave differently, a
      bisect proved the text caused the gain AND the damage together
      ([[gorgon-refusal-enum-withdrawn]]). Here the base question is byte-identical on the
      first attempt, so **a request that succeeds first time never sees any of this** — the
      retry cannot regress what already worked, by construction rather than by measurement.

    ⇒ **AND IT IS EVIDENCE, NOT INSTRUCTION.** Each line is a step that was produced and the
      manifest's reason it is illegal. Nothing tells the model how to behave, which is the
      distinction W7b draws: it is asked to MOVE again, given a fact it did not have.
    """
    lines = ["these things have already been identified and confirmed:"]
    for sym in table:
        lines.append(f"  {sym.handle}  —  a {sym.row.object_type}  —  {sym.definition}"
                     f"  —  known {sym.settled}")
    out = (f"{chr(10).join(lines)}\n\n"
           f"the operations you may use: {', '.join(operators)}\n\n"
           f"the request: {request}")
    if rejected:
        out += ("\n\nthese steps were rejected by the lab and cannot be used:\n  "
                + "\n  ".join(rejected))
    # ⇒⇒ A SECOND SECTION, BECAUSE ONE SECTION COULD ONLY EVER SAY "REMOVE THIS".
    #
    #   Measured on rung 8, 2026-08-11: `core` and `dmz` are both used and neither is supplied.
    #   Both were reported, and the retry added `create_network(core)` and never `dmz` — at
    #   `--retries 1`, `2` and `3`, byte-identical. The model was being handed a MISSING STEP
    #   under a heading that says *cannot be used*, which is the opposite instruction, and it
    #   inferred the addition once and could not repeat it.
    #
    #   ⇒ THE SPLIT IS BY WHAT THE FINDING ASKS FOR, not by which gate raised it. An illegal
    #     step asks to be REMOVED; an unestablished referent asks for a step to be ADDED. Those
    #     are different requests and a single list cannot carry both.
    #
    #   ⇒ AND IT STAYS EVIDENCE RATHER THAN INSTRUCTION (rule W7b): each line names a thing the
    #     lab does not hold, which is a FACT the model did not have. Nothing here tells it how
    #     to behave, and a request that succeeds first time never sees this section at all.
    if needed:
        out += ("\n\nthese things are used by a step but nothing in the program supplies them, "
                "and the lab does not hold them:\n  " + "\n  ".join(needed))
    return out


def operations_by_clause(request: str, rows: List[S.Declared], board: Optional[Board] = None,
                         model=None, temp: float = 0.0, timeout: int = 300,
                         rejected: Optional[List[str]] = None,
                         needed: Optional[List[str]] = None):
    """ASK ONCE PER CLAUSE, AND KEEP WHICH CLAUSE EACH STEP CAME FROM.

    ⇒ **THIS IS A PRODUCER, NOT A DETECTOR, AND THAT IS THE WHOLE REASON FOR IT.** Asked over
      the whole request with seventeen operators offered, the model emits steps no clause
      warrants — `launch_vm` on a request that never says launch, `stop_vm` on one that says
      launch. `unasked-step` catches those AFTERWARDS. Asked per clause, a step with no clause
      **cannot be emitted at all**: there is no call it could come from.

    ⇒ **THE FRAGMENT IS WHAT IS ASKED ABOUT, NEVER WHAT IS READ FROM.** Every call carries the
      WHOLE request and the WHOLE symbol table; the clause only marks which part to answer for.
      That is the difference from staged lowering, where a fragment was handed to an author
      with nothing else and lost its referents. Here `put web on lab` can still see `web` and
      `lab` even when the clause naming them is a different one.

    Returns [(clause, Operation)], in clause order — which also gives the program a sequence
    the whole-request form never had.
    """
    from engines.channel import constrained
    board = board or Board()
    table = symbol_table(rows, board)
    names = [s.handle for s in table]
    if not names:
        return []
    operators = operators_offered(board)
    out = []
    for clause in clauses_of(request):
        payload = (f"{_payload(request, table, operators, rejected, needed)}\n\n"
                   f"the part to answer for: {clause}")
        try:
            got = constrained(CLAUSE_ASK, payload, _schema(names, operators, False, True),
                              model=model, temp=temp, timeout=timeout) or {}
        except Exception:
            continue
        for step in got.get("operations") or []:
            if isinstance(step, dict) and step.get("operator") and step.get("on"):
                out.append((clause, Operation(step["operator"], step["on"], step.get("value"))))
    return out


def operations_for(request: str, rows: List[S.Declared], board: Optional[Board] = None,
                   model=None, temp: float = 0.0, timeout: int = 300,
                   handles: str = "derived", require_one: bool = True,
                   free_value: bool = True,
                   rejected: Optional[List[str]] = None,
                   needed: Optional[List[str]] = None) -> List[Operation]:
    """THE ONE QUESTION PASS 2 ASKS. Everything in the answer is closed."""
    from engines.channel import constrained
    board = board or Board()
    table = symbol_table(rows, board, handles)
    names = [s.handle for s in table]
    if not names:
        return []
    operators = operators_offered(board)
    try:
        got = constrained(ASK, _payload(request, table, operators, rejected, needed),
                          _schema(names, operators, require_one, free_value),
                          model=model, temp=temp, timeout=timeout) or {}
    except Exception:
        return []
    out: List[Operation] = []
    for step in got.get("operations") or []:
        if isinstance(step, dict) and step.get("operator") and step.get("on"):
            out.append(Operation(step["operator"], step["on"], step.get("value")))
    return out


# ── the expected operations, WRITTEN DOWN BEFORE THE FIRST RUN (rule V5) ───────────────
#
# Keyed by HANDLE, so they say what the program must do without depending on how pass 1
# happens to phrase a span. Only the rungs whose operations are unambiguous are graded; the
# rest are REPORTED so a regression is visible without inventing a key for a judgement call.
WANT: Dict[int, List[tuple]] = {
    1: [("create_vm", "alpha", None)],
    2: [("create_vm", "beta", None), ("launch_vm", "beta", None)],
    3: [("create_network", "lab", None), ("create_vm", "web", None),
        ("add_vm_to_network", "web", "lab")],
    5: [("launch_vm", "stopped_vms", None)],
    11: [("probe_alive", "vms", None), ("stop_vm", "not_alive_vms", None)],
    12: [("create_snapshot", "running_vms", None)],
}


def grade(got: List[Operation], want: List[tuple]) -> str:
    steps = [(o.operator, o.on, o.value) for o in got]
    if steps == want:
        return "EXACT"
    if sorted(steps, key=str) == sorted(want, key=str):
        return "SET-EQUAL"
    return f"{len(set(steps) & set(want))}/{len(want)} steps"
