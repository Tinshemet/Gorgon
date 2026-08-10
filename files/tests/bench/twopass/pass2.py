"""PASS TWO — WHAT HAS TO BE DONE. One question, three closed fields, over pass 1's own rows.

    PYTHONPATH=. python3 -m tests.bench.twopass.pass2 --runs 3
    PYTHONPATH=. python3 -m tests.bench.twopass.pass2 --only 11 --handles span

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

import argparse
import re
from collections import Counter
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board
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
    """
    from planner.gates import claims as _claims
    taken = taken if taken is not None else set()
    kind = row.kind if row.kind in board.kinds else "thing"

    key_attr = _claims.key_of(kind, board.kinds) if kind in board.kinds else None
    if key_attr and (row.where or {}).get(key_attr):
        return _free(str(row.where[key_attr]), taken)
    if row.identity:
        return _free(str(row.identity), taken)

    # a CONDITION describes the set better than a number ever could
    for attr, value in (row.where or {}).items():
        if isinstance(value, bool) or str(value).lower() in ("true", "false"):
            truthy = value is True or str(value).lower() == "true"
            stem = f"{attr}_{_plural(kind)}" if truthy else f"not_{attr}_{_plural(kind)}"
            return _free(stem, taken)
        return _free(f"{_slug(value)}_{_plural(kind)}", taken)

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
            return _free(free[-1], taken)

    base = _plural(kind) if row.is_set else kind
    return _free(base, taken)


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
        definition = (f"{'the ' + kind if not row.is_set else 'the ' + _plural(kind)}"
                      f"{' where ' + where if where else ''}")
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
        if kept and content and not has_verb and len(content) <= 2:
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


def _payload(request: str, table: List[Symbol], operators: List[str],
             rejected: Optional[List[str]] = None) -> str:
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
    return out


def operations_by_clause(request: str, rows: List[S.Declared], board: Optional[Board] = None,
                         model=None, temp: float = 0.0, timeout: int = 300,
                         rejected: Optional[List[str]] = None):
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
        payload = (f"{_payload(request, table, operators, rejected)}\n\n"
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
                   rejected: Optional[List[str]] = None) -> List[Operation]:
    """THE ONE QUESTION PASS 2 ASKS. Everything in the answer is closed."""
    from engines.channel import constrained
    board = board or Board()
    table = symbol_table(rows, board, handles)
    names = [s.handle for s in table]
    if not names:
        return []
    operators = operators_offered(board)
    try:
        got = constrained(ASK, _payload(request, table, operators, rejected),
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="rule V3 — never diagnose from n=1")
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--handles", default="derived", choices=("derived", "span"),
                    help="`span` offers pass 1's raw span as the enum member — the thing the "
                         "original probe never tested")
    args = ap.parse_args()

    from . import pass1
    from .metrics import Lab
    board = Board()
    tally: Counter = Counter()
    print("=" * 100)
    print(f"PASS 2 · WHAT HAS TO BE DONE — handles={args.handles}, n={args.runs}")
    print("=" * 100)

    for n, want in sorted(pass1.EXPECTED.items()):
        if args.only and n != args.only:
            continue
        rows = pass1.settle_with_world(
            pass1.run_scanned(want.request, board=board, model=args.model), Lab(), board)
        table = symbol_table(rows, board, args.handles)
        print(f"\n{'─' * 100}\nrung {n} · “{want.request[:78]}”")
        for sym in table:
            print(f"    {sym.handle:<18} {sym.row.object_type:<10} {sym.definition:<40} "
                  f"{sym.settled}")
        expected = WANT.get(n)
        print(f"    WANT  {expected if expected else '— not keyed, reported only'}")
        for i in range(args.runs):
            got = operations_for(want.request, rows, board, model=args.model,
                                 handles=args.handles)
            steps = [(o.operator, o.on, o.value) for o in got]
            if expected is None:
                print(f"    run {i + 1}  {steps}")
                continue
            verdict = grade(got, expected)
            tally[verdict.split("/")[0] if "/" in verdict else verdict] += 1
            tally["cells"] += 1
            print(f"    run {i + 1}  {verdict:<12} {steps}")

    print(f"\n{'=' * 100}")
    for verdict, count in sorted(tally.items()):
        if verdict != "cells":
            print(f"    {verdict:<12} {count}/{tally['cells']}")


if __name__ == "__main__":
    main()
