"""ITEM 1 — CAN THE MODEL WRITE OPERATIONS AGAINST A CLOSED GRAMMAR?

    PYTHONPATH=. python3 -m tests.bench.twopass.condition_probe

A PROBE, NOT A BUILD. Nothing here is wired to anything; it exists to kill a design before
nine sessions are spent on it. The standing rule is never to spend a ladder arm on what a
probe can kill, and rule D6 names this as the risk:

    *"No free text in a condition. The moment a condition field takes prose, the parsing
     problem returns wearing a different hat."*

# THE ASSUMPTION UNDER TEST

Pass 1 has run and its declarations are CONFIRMED. Given that symbol table, can the model
state the operations — referring to declared names, choosing from a closed operator list, and
never writing prose?

**THE SYMBOL TABLE BECOMES THE ENUM.** `on` is restricted to the names pass 1 declared, so an
undeclared reference is not caught by a check — it is UNDECODABLE. That is rule D1 enforced by
the grammar rather than by a gate, and it is the strongest form the contract can take.

# THE FORK BEING MEASURED

The operator's sketch was `operator: if, condition: alpha=unresponsive, do: stop`. But if pass
1 has already declared `unresponsive` as a set, the condition may be redundant — the set IS the
condition, and the operation just names it. So two framings, same requests, same model:

    A · NAME THE SET      {operator, on: <declared name>, value}
                          no condition field exists at all

    B · IF / DO           {operator, on, condition: {subject, relation, object}, do}
                          the condition is a CLOSED TRIPLE over declared names, never prose

# ⇒ PREDICTIONS, SEALED BEFORE THE FIRST RUN (rule V5)

    P1  FRAMING A BEATS FRAMING B. Fewer decisions per operation, and B's condition is
        recoverable from A's `on` in every case below. If B wins I have the design backwards.
    P2  RUNG 11 COMES OUT RIGHT UNDER A — probe on `fleet`, then stop on `unresponsive`.
        THIS IS THE WHOLE BET. The set it could never name is named FOR it and it only has to
        point at it.
    P3  RUNG 12 is easy and will pass both framings.
    P4  RUNG 3's cross-reference is the risk under A — `add_vm_to_network on web value lab`
        needs `lab` as a VALUE, and a value is the one field that is not enum-constrained.
        I expect this to be where a name gets invented.
    P5  RUNG 8 is hardest: four operations, two of them differing only in their target.

    AND ONE STATED LIMIT: the operator enum below is the manifest's creators + setters +
    delete + probe. The manifest ALSO declares 21 `acts` for a vm which no rung uses. Enum
    size is therefore UNTESTED at its real width, and that is a known gap, not an oversight.
"""
import argparse
import json
from collections import Counter
from typing import Dict, List

# ── the symbol tables. HAND-WRITTEN: this is what a confirmed pass 1 would have produced. ──
TABLES: Dict[int, dict] = {
    11: {
        "request": "ping every vm and stop the ones that do not answer",
        "declared": [
            ("fleet", "vm_set", "every vm", "at plan time"),
            ("unresponsive", "vm_set", "fleet where alive = false", "AT RUN TIME"),
        ],
        "expect": [("probe_alive", "fleet", None), ("stop_vm", "unresponsive", None)],
    },
    12: {
        "request": "take a snapshot of every running vm",
        "declared": [
            ("running_vms", "vm_set", "every vm where status = running", "at plan time"),
        ],
        "expect": [("create_snapshot", "running_vms", None)],
    },
    3: {
        "request": "create a network called lab and a vm named web, then put web on lab",
        "declared": [
            ("lab", "network", "the network named lab", "at plan time"),
            ("web", "vm", "the machine named web", "at plan time"),
        ],
        "expect": [("create_network", "lab", None), ("create_vm", "web", None),
                   ("add_vm_to_network", "web", "lab")],
    },
    8: {
        "request": ("put every vm on a network called core, except db — "
                    "db goes on a network called dmz instead"),
        "declared": [
            ("others", "vm_set", "every vm except db", "at plan time"),
            ("db", "vm", "the machine named db", "at plan time"),
            ("core", "network", "the network named core", "at plan time"),
            ("dmz", "network", "the network named dmz", "at plan time"),
        ],
        "expect": [("create_network", "core", None), ("create_network", "dmz", None),
                   ("add_vm_to_network", "others", "core"),
                   ("add_vm_to_network", "db", "dmz")],
    },
}


def operators(kinds=None) -> List[str]:
    """The operator list, READ OFF THE MANIFEST (rule W5) — never hand-listed.

    creators + setters + delete + one probe per observed attribute. `acts` are deliberately
    excluded for this probe and the exclusion is declared in the module docstring.
    """
    from planner.ir import config as _config
    table = kinds if kinds is not None else (_config.KINDS or {})
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
    return sorted(set(out))


def _table_text(entry: dict) -> str:
    lines = ["these things have already been identified and confirmed:"]
    for name, otype, definition, settled in entry["declared"]:
        lines.append(f"  {name}  —  a {otype}  —  {definition}  —  known {settled}")
    return "\n".join(lines)


def _schema_a(names: List[str], ops: List[str]) -> dict:
    return {
        "type": "object", "additionalProperties": False, "required": ["operations"],
        "properties": {"operations": {"type": "array", "minItems": 1, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["operator", "on", "value"],
            "properties": {
                "operator": {"type": "string", "enum": ops},
                "on": {"type": "string", "enum": names},
                "value": {"type": ["string", "null"], "enum": names + [None]},
            }}}},
    }


def _schema_b(names: List[str], ops: List[str]) -> dict:
    return {
        "type": "object", "additionalProperties": False, "required": ["operations"],
        "properties": {"operations": {"type": "array", "minItems": 1, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["operator", "on", "condition", "value"],
            "properties": {
                "operator": {"type": "string", "enum": ops},
                "on": {"type": "string", "enum": names},
                "value": {"type": ["string", "null"], "enum": names + [None]},
                "condition": {
                    "type": ["object", "null"], "additionalProperties": False,
                    "required": ["subject", "relation", "object"],
                    "properties": {
                        "subject": {"type": "string", "enum": names},
                        "relation": {"type": "string", "enum": ["member_of", "is"]},
                        "object": {"type": "string", "enum": names},
                    }},
            }}}},
    }


_PROMPT_A = ("Say what has to be DONE, as a list of steps. Each step names one operation and "
             "the ONE already-identified thing it acts on. Some operations need a second thing "
             "as their value (for example, putting a machine on a network) — otherwise leave "
             "value null. Use only the operations and the names offered. Do not invent a name.")

_PROMPT_B = ("Say what has to be DONE, as a list of steps. Each step names one operation and "
             "the ONE already-identified thing it acts on, and may carry a condition saying "
             "which members it applies to. Leave condition null when the step applies to all "
             "of them. Use only the operations and names offered. Do not invent a name.")


def run_one(n: int, framing: str, model=None, temp=0.0, timeout=300) -> List[tuple]:
    from engines.channel import constrained

    entry = TABLES[n]
    names = [d[0] for d in entry["declared"]]
    ops = operators()
    schema = _schema_a(names, ops) if framing == "A" else _schema_b(names, ops)
    prompt = _PROMPT_A if framing == "A" else _PROMPT_B
    payload = (f"{_table_text(entry)}\n\n"
               f"the operations you may use: {', '.join(ops)}\n\n"
               f"the request: {entry['request']}")
    try:
        got = constrained(prompt, payload, schema, model=model, temp=temp, timeout=timeout) or {}
    except Exception as exc:
        return [("<call failed>", f"{type(exc).__name__}", None)]
    out = []
    for step in got.get("operations") or []:
        if isinstance(step, dict):
            out.append((step.get("operator"), step.get("on"), step.get("value")))
    return out


def grade(got: List[tuple], want: List[tuple]) -> str:
    if got == want:
        return "EXACT"
    if sorted(got) == sorted(want):
        return "SET-EQUAL"
    hit = len(set(got) & set(want))
    return f"{hit}/{len(want)} steps"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="rule V3 — never diagnose from n=1")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    ops = operators()
    print("=" * 98)
    print(f"ITEM 1 · CONDITION GRAMMAR PROBE   ·   {len(ops)} operators offered, "
          f"n={args.runs} per cell")
    print("=" * 98)
    print(f"  operators: {', '.join(ops)}\n")

    tally: Counter = Counter()
    for n in sorted(TABLES):
        entry = TABLES[n]
        print(f"\n{'─' * 98}\nrung {n} · “{entry['request']}”")
        for name, otype, definition, settled in entry["declared"]:
            print(f"    declared  {name:<14} {otype:<10} {definition:<32} {settled}")
        print(f"    WANT      {entry['expect']}")
        for framing in ("A", "B"):
            for i in range(args.runs):
                got = run_one(n, framing, model=args.model)
                verdict = grade(got, entry["expect"])
                tally[(framing, verdict.split("/")[0] if "/" in verdict else verdict)] += 1
                print(f"    {framing} run {i + 1}   {verdict:<12} {got}")

    print(f"\n{'=' * 98}\nTALLY")
    for (framing, verdict), count in sorted(tally.items()):
        print(f"    framing {framing}   {verdict:<12} {count}")


if __name__ == "__main__":
    main()
