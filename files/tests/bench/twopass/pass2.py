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


def operators_offered(board: Optional[Board] = None) -> List[str]:
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
    return [o for o in ordered if o != "add_label"] + ["add_label"]


ASK = ("Say what has to be DONE, as a list of steps. Each step names one operation and the ONE "
       "already-identified thing it acts on. Some operations need a second thing as their "
       "value — otherwise leave value null. Use only the operations and the names offered. "
       "Do not invent a name.")


def _schema(handles: List[str], operators: List[str]) -> dict:
    return {
        "type": "object", "additionalProperties": False, "required": ["operations"],
        "properties": {"operations": {"type": "array", "minItems": 1, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["operator", "on", "value"],
            "properties": {
                "operator": {"type": "string", "enum": operators},
                "on": {"type": "string", "enum": handles},
                "value": {"type": ["string", "null"], "enum": handles + [None]},
            }}}},
    }


def _payload(request: str, table: List[Symbol], operators: List[str]) -> str:
    lines = ["these things have already been identified and confirmed:"]
    for sym in table:
        lines.append(f"  {sym.handle}  —  a {sym.row.object_type}  —  {sym.definition}"
                     f"  —  known {sym.settled}")
    return (f"{chr(10).join(lines)}\n\n"
            f"the operations you may use: {', '.join(operators)}\n\n"
            f"the request: {request}")


def operations_for(request: str, rows: List[S.Declared], board: Optional[Board] = None,
                   model=None, temp: float = 0.0, timeout: int = 300,
                   handles: str = "derived") -> List[Operation]:
    """THE ONE QUESTION PASS 2 ASKS. Everything in the answer is closed."""
    from engines.channel import constrained
    board = board or Board()
    table = symbol_table(rows, board, handles)
    names = [s.handle for s in table]
    if not names:
        return []
    operators = operators_offered(board)
    try:
        got = constrained(ASK, _payload(request, table, operators),
                          _schema(names, operators),
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
