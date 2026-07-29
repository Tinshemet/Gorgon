"""
atomicity_probe.py — E1's KILL SWITCH. Can the model answer "ONE OPERATOR, or decompose?"

WHAT THIS DECIDES, and it decides it cheaply. Staged lowering (the program-regime
revision) rests on ONE unmeasured premise: that recursing on *"can you do this with one
operator?"* is the same KIND of question as the routing call the engine already makes at
every node — and that call scores 10/10.

    tool regime     one tool call, or decompose?        MEASURED 10/10 (regime_probe)
    program regime  one OPERATOR, or decompose?         THIS PROBE. Unmeasured.

If the answer is no, staged lowering dies here and no machinery was built for it. That is
the point: this probe exists to kill the design early, not to support it. Build the
leaves, the fusion and the whole-artifact review ONLY if this answers cleanly.

FAIRNESS OF THE COMPARISON. The two tools below are deliberately the SAME SHAPE as the
engine's own `decompose`-vs-primitive menu, with the vocabulary swapped from tool calls to
operators. Which tool the model CALLS is the judgment — nothing is parsed out of prose.
A different shape would measure the shape, not the question.

GROUND TRUTH IS WRITTEN DOWN BELOW, BEFORE ANY RUN, so grading cannot drift toward
whatever the model happened to do. Same discipline as `regime_probe.EXPECTED`.

Run:  PYTHONPATH=. python3 -m tests.bench.atomicity_probe
      PYTHONPATH=. python3 -m tests.bench.atomicity_probe -n 3 -p
"""
import argparse
import json
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from orchestrator.ai.planner.ir import config
from orchestrator.ai.planner.score import _first_tool_call

from .ladder import BENCH_MODEL, make_call_model
from .rungs import RUNGS

# ── CHANNEL RECOVERY — and why this is measurement, not repair ───────────────────────────
# MEASURED 2026-07-29: rung 7 answered `one_operator` correctly THREE TIMES OUT OF THREE
# and scored as "no call", because the model emitted the tool call as JSON in the CONTENT
# field instead of as a structured call. Scoring that as a routing failure blames the model
# for a channel fault — the precise mis-attribution `ladder_gate`'s layer taxonomy exists
# to prevent.
#
# So the answer is RECOVERED and counted SEPARATELY, never folded into the headline. Two
# numbers come out of one run: what the model DECIDED, and what a caller would actually
# RECEIVE. The gap between them is the channel's cost, which is the thing D1 is about.
#
# It EXTRACTS two facts; it does not parse and it never invents. The observed payload is
# not even valid JSON (`\'prod\'` — an escaped single quote has no JSON production), so a
# strict load is tried first and a narrow field-scrape second. Anything else is `none`.
_NAME_RE = re.compile(r'"name"\s*:\s*"(one_operator|decompose)"')
_OP_RE = re.compile(r'"operator"\s*:\s*"(\w+)"')


def _recover(reply: Any) -> Tuple[Optional[str], Dict[str, Any]]:
    """A tool call that arrived in `content`. Returns (name, args) or (None, {})."""
    try:
        content = (reply or {}).get("message", {}).get("content") or ""
    except AttributeError:
        return None, {}
    if not content.strip():
        return None, {}
    try:
        obj = json.loads(content)
        if isinstance(obj, dict) and obj.get("name") in ("one_operator", "decompose"):
            args = obj.get("parameters") or obj.get("arguments") or {}
            return obj["name"], (args if isinstance(args, dict) else {})
    except (ValueError, TypeError):
        pass
    m = _NAME_RE.search(content)
    if not m:
        return None, {}
    op = _OP_RE.search(content)
    return m.group(1), ({"operator": op.group(1)} if op else {})

# ── GROUND TRUTH ────────────────────────────────────────────────────────────────────────
# What each rung IS, judged by its shape against the seven operators, written down before
# any model ran. `None` = decomposes; a string = one operator, and WHICH.
#
# THE CORPUS IS DELIBERATELY BALANCED IN BOTH ERROR DIRECTIONS. 5 atomic / 8 decompose,
# and the atomic ones are the NON-OBVIOUS ones: 5, 7, 9 and 12 all read as plural or
# multi-step in English while being a single statement. A router keying on "does the
# sentence mention many things" gets all four wrong, which is exactly the discrimination
# the premise needs. Over-decomposing an atomic goal and under-decomposing a compound one
# are both visible here.
EXPECTED: Dict[int, Any] = {
    1:  "new",       # create a vm named alpha — one creation
    2:  None,        # create, THEN launch — two statements
    3:  None,        # two creations and an attach
    4:  None,        # create, attach-all, label-all, assure reachability
    5:  "foreach",   # launch every STOPPED vm — one loop over a filtered select
    6:  None,        # a partition: two groups, two networks, kept apart
    7:  "achieve",   # exactly 3 carry 'prod' — one achieve; derive() closes both directions
    8:  None,        # every vm on core EXCEPT db, which goes on dmz — the carve-out is a
                     # second statement, the exception cannot ride the same loop
    9:  "achieve",   # n1,n2,n3 all reach each other — one achieve over an INCLUDE select
    10: None,        # clone from a source, then launch the results
    11: None,        # ping all, then stop the non-answerers — decision 6 makes this TWO
                     # loops: the first probes, the ledger remembers, the second reads back
    12: "foreach",   # snapshot every running vm — one loop, second resource kind
    13: None,        # rung 4's shape, re-entrant
}

_ATOMIC = {n for n, op in EXPECTED.items() if op is not None}


# ── THE TWO TOOLS — the same menu shape the engine offers, operators instead of calls ────
def _one_operator_tool() -> Dict[str, Any]:
    """Built from `config.OPS`, which is the SSOT for what an operator IS. Hardcoding the
    seven here would make this probe a 34th vocabulary — the thing the language exists to
    end."""
    ops = list(config.OPS.keys())
    menu = "\n".join(f"  {name} — {(spec.get('doc') or '').split('.')[0]}"
                     for name, spec in config.OPS.items())
    return {
        "type": "function",
        "function": {
            "name": "one_operator",
            "description": (
                "Use when the goal is ONE operator — a single statement, with nothing "
                "left over. Name which operator it is. If the goal needs more than one "
                "statement, call `decompose` instead.\n\nThe operators:\n" + menu
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operator": {"type": "string", "enum": ops,
                                 "description": "which single operator expresses this goal"},
                    "why": {"type": "string",
                            "description": "one short sentence: why nothing is left over"},
                },
                "required": ["operator"],
            },
        },
    }


def _decompose_tool() -> Dict[str, Any]:
    """Mirrors DECOMPOSE_TOOL's shape exactly, with 'operator' where it says 'tool call'.

    `operator` is asked for but does NOT gate the kill-switch verdict — staged lowering
    requires that a decomposing node NAME ITS OWN OPERATOR or fusion has nothing to attach
    children to, and asking costs no extra call. Reported separately, below the line.
    """
    ops = list(config.OPS.keys())
    return {
        "type": "function",
        "function": {
            "name": "decompose",
            "description": (
                "Use ONLY when the goal needs MORE than one operator. Break it into an "
                "ordered list of smaller sub-goals; each will then be one operator (or "
                "decomposed again if still too big). If the goal is ONE operator, call "
                "`one_operator` instead — do not decompose."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array", "items": {"type": "string"},
                        "description": (
                            "Ordered sub-goals in PLAIN ENGLISH, e.g. ['create a vm "
                            "called dev', 'launch dev']. Each is a short instruction of "
                            "WHAT to do — never operator names or code."
                        ),
                    },
                    "operator": {
                        "type": "string", "enum": ops,
                        "description": (
                            "the operator this node itself is, that the sub-goals sit "
                            "inside — e.g. a loop over a set is `foreach`"
                        ),
                    },
                },
                "required": ["steps"],
            },
        },
    }


def _system() -> str:
    return (
        "You are given a goal. Decide whether it is ONE operator or must be broken up.\n"
        "  - If ONE statement expresses the whole goal, call `one_operator` and say which.\n"
        "  - If it needs several statements, call `decompose` and list the sub-goals.\n"
        "A loop over a set is ONE operator, not one per member. An end-state to make true "
        "is ONE operator, however much work it implies.\n"
        "Choose one. Do not explain outside the call."
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="E1 kill switch: one operator, or decompose?")
    p.add_argument("-r", "--rung", type=int, action="append")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("-n", "--repeats", type=int, default=3,
                   help="runs per rung. NEVER diagnose from n=1 — see the ladder note.")
    p.add_argument("-p", "--paraphrase", action="store_true")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    call_model = make_call_model(a.model, a.temp, 300)
    tools = [_one_operator_tool(), _decompose_tool()]

    print(f"atomicity probe (E1 kill switch) · model={a.model} temp={a.temp} n={a.repeats}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}")
    print(f"corpus: {len(rungs)} rungs · {len(_ATOMIC & {r.n for r in rungs})} atomic / "
          f"{len(rungs) - len(_ATOMIC & {r.n for r in rungs})} decompose\n")

    route_hits = op_hits = op_asked = 0
    parent_named = parent_total = 0
    atomic_routed = atomic_total = 0
    flaky: List[int] = []
    errors = 0
    channel_losses = 0
    delivered_hits = 0

    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        want_op = EXPECTED[rung.n]
        want = "one_operator" if want_op else "decompose"

        got: List[str] = []
        ops_said: List[str] = []
        parents: List[str] = []
        via_content = 0
        for _ in range(a.repeats):
            try:
                reply = call_model([{"role": "system", "content": _system()},
                                    {"role": "user", "content": goal}], tools)
                name, args = _first_tool_call(reply)
            except Exception as e:
                got.append(f"ERROR:{type(e).__name__}")
                errors += 1
                continue
            if name is None:                       # the call may have arrived in `content`
                name, args = _recover(reply)
                if name:
                    via_content += 1
                    channel_losses += 1
            got.append(name or "none")
            if name == "one_operator":
                ops_said.append((args or {}).get("operator") or "?")
            elif name == "decompose":
                parents.append((args or {}).get("operator") or "-")

        tally = Counter(got)
        majority, count = tally.most_common(1)[0]
        unanimous = count == len(got)
        if not unanimous:
            flaky.append(rung.n)

        routed_ok = majority == want
        route_hits += 1 if routed_ok else 0
        # DELIVERED = routed right AND arrived as a real tool call. A cell recovered from
        # `content` counts for the model and NOT for the caller — that gap is the point.
        if routed_ok and via_content == 0:
            delivered_hits += 1
        if want_op:
            atomic_total += 1
            atomic_routed += 1 if routed_ok else 0

        # The operator name is graded ONLY where the routing was right and atomic was the
        # right answer — "which operator" is meaningless on a goal that should decompose.
        op_note = ""
        if want_op:
            op_asked += 1
            op_tally = Counter(ops_said)
            said = op_tally.most_common(1)[0][0] if ops_said else "-"
            if routed_ok and said == want_op:
                op_hits += 1
            op_note = f"  op: want {want_op:8} got {said:8}"
        elif parents:
            parent_total += 1
            named = [x for x in parents if x != "-"]
            if named:
                parent_named += 1
                op_note = f"  parent: {Counter(named).most_common(1)[0][0]}"
            else:
                op_note = "  parent: (unnamed)"

        mark = "OK " if routed_ok else "MISS"
        spread = "" if unanimous else f"  ~flaky {dict(tally)}"
        chan = f"  [channel: {via_content}/{len(got)} via content]" if via_content else ""
        print(f"   rung {rung.n:2}  want {want:13} got {majority:13} {mark}"
              f"  {count}/{len(got)}{op_note}{spread}{chan}")

    n = len(rungs)
    # THE TRIVIAL BASELINE, printed so the headline cannot be read as better than it is.
    # The corpus is deliberately unbalanced toward decompose (that is what the ladder's
    # goals ARE), so a router that answers "decompose" every time already scores this.
    floor = n - len(_ATOMIC & {r.n for r in rungs})
    print(f"\n── summary · harness=atomicity_probe · model={a.model} · n={a.repeats}")
    print(f"   MODEL DECIDED RIGHT : {route_hits}/{n}   <- the kill-switch number")
    print(f"   …AND IT ARRIVED     : {delivered_hits}/{n}   "
          f"<- what a caller actually receives")
    print(f"   always-'decompose'  : {floor}/{n}   <- the floor. Read the headline against")
    print(f"                                          THIS, not against zero.")
    print(f"   ON THE ATOMIC CELLS : {atomic_routed}/{atomic_total}   "
          f"<- where the information is: the")
    print(f"                                          only cells the floor gets wrong.")
    print(f"   operator named right: {op_hits}/{op_asked}" if op_asked else
          "   operator named right: n/a")
    if parent_total:
        print(f"   parent operator named: {parent_named}/{parent_total}"
              f"  (secondary — does not gate the verdict)")
    if channel_losses:
        print(f"   CHANNEL             : {channel_losses} answer(s) arrived in `content`, "
              f"not as a tool call —")
        print(f"                         recovered for the model's score, NOT for the "
              f"caller's. See D1.")
    if flaky:
        print(f"   NOT UNANIMOUS       : rungs {flaky} — undecided, not data")
    if errors:
        print(f"   errors              : {errors}")
    print("\n   Compare against regime_probe's 10/10 on the tool-regime question.")
    print("   This number is the whole premise of staged lowering. If it is poor, the")
    print("   design dies here — which is the cheapest possible place for it to die.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
