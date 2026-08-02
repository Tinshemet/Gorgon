"""
atomicity_probe.py — E1's KILL SWITCH. Can the model answer "ONE OPERATOR, or decompose?"

WHAT THIS DECIDES, and it decides it cheaply. Staged lowering (the program-regime
revision) rests on ONE unmeasured premise: that recursing on *"can you do this with one
operator?"* is the same KIND of question as the routing call the engine already makes at
every node — and that call scores 10/10.

    tool regime     one tool call, or decompose?        MEASURED 10/10 (regime_probe)
    program regime  one OPERATOR, or decompose?         THIS PROBE.

If the answer is no, staged lowering dies here and no machinery was built for it. That is
the point: this probe exists to kill the design early, not to support it.

FAIRNESS OF THE COMPARISON. The tools below are deliberately the SAME SHAPE as the
engine's own `decompose`-vs-primitive menu, with the vocabulary swapped from tool calls to
operators. Which tool the model CALLS is the judgment — nothing is parsed out of prose.

TWO MENUS, ONE HARNESS (`--split`). The flat menu offers all seven ops as one enum. The
split menu offers only the STRUCTURAL four, plus `assertion` for a goal that is a state to
make true rather than work to arrange. Running both from one probe is what makes the delta
readable; two probes would measure two harnesses.

    flat     new fetch call foreach ensure achieve if        the original question
    split    new call foreach if | assertion | decompose     intent withheld

WHY THE SPLIT EXISTS — the operator, 2026-07-29: *"ensure, achieve and fetch should be in
a different category as to not confuse the ai since those 3 are intent and context derived
rather than a normal decomp."* Measured on the flat menu: the operator name was right on
4 of 10 atomic cells across both columns, and TWO OF THE THREE ERRORS WERE `ensure` WHERE
`achieve` WAS RIGHT (rungs 7 and 9, identically, both columns). That is a choice the
author was never authorised to make — `ir/intent.py` enforces it before the first call.
Categories live in `config.OP_CATEGORIES`, never here.

GROUND TRUTH IS WRITTEN DOWN BELOW, BEFORE ANY RUN, so grading cannot drift toward
whatever the model happened to do. Same discipline as `regime_probe.EXPECTED`.

Run:  PYTHONPATH=. python3 -m tests.bench.atomicity_probe -n 3
      PYTHONPATH=. python3 -m tests.bench.atomicity_probe -n 3 --split -p
"""
import argparse
import json
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from planner.ir import config
from planner.score import _first_tool_call

from .ladder import BENCH_MODEL, make_call_model
from .rungs import RUNGS

_STRUCTURAL = list(config.OP_CATEGORIES["structural"])
_INTENT_OPS = list(config.OP_CATEGORIES["intent"])
_ALL_OPS = list(config.OPS.keys())

# ── GROUND TRUTH ────────────────────────────────────────────────────────────────────────
# What each rung IS, judged by its shape, written down before any model ran.
#   None                  -> decomposes
#   ("structural", op)    -> one statement, and its op is a STRUCTURAL one
#   ("assertion", op)     -> one statement that is a STATE TO MAKE TRUE; `op` is what it
#                            is under today's intent, and is NOT asked for under --split
#
# THE CORPUS IS BALANCED IN BOTH ERROR DIRECTIONS. 5 atomic / 8 decompose, and the atomic
# ones are the NON-OBVIOUS ones: 5, 7, 9 and 12 all read as plural or multi-step in English
# while being a single statement. A router keying on "does the sentence mention many
# things" gets all four wrong. Over-decomposing an atomic goal and under-decomposing a
# compound one are both visible.
EXPECTED: Dict[int, Optional[Tuple[str, str]]] = {
    1:  ("structural", "new"),      # create a vm named alpha — one creation
    2:  None,                       # create, THEN launch — two statements
    3:  None,                       # two creations and an attach
    4:  None,                       # create, attach-all, label-all, assure reachability
    5:  ("structural", "foreach"),  # launch every STOPPED vm — one loop, filtered select
    6:  None,                       # a partition: two groups, two networks, kept apart
    7:  ("assertion", "achieve"),   # exactly 3 carry 'prod' — derive() closes both ways
    8:  None,                       # every vm on core EXCEPT db — the carve-out is a
                                    # second statement; it cannot ride the same loop
    9:  ("assertion", "achieve"),   # n1,n2,n3 all reach each other — one INCLUDE select
    10: None,                       # clone from a source, then launch the results
    11: None,                       # ping all, then stop the non-answerers — decision 6
                                    # makes this TWO loops: probe, ledger, read back
    12: ("structural", "foreach"),  # snapshot every running vm — one loop, second kind
    13: None,                       # rung 4's shape, re-entrant
}

_ATOMIC = {n for n, e in EXPECTED.items() if e is not None}

# ── CHANNEL RECOVERY — and why this is measurement, not repair ───────────────────────────
# MEASURED 2026-07-29: rung 7 answered correctly THREE TIMES OUT OF THREE and scored as
# "no call", because the model emitted the tool call as JSON in the CONTENT field instead
# of as a structured call. Scoring that as a routing failure blames the model for a channel
# fault — the precise mis-attribution `ladder_gate`'s layer taxonomy exists to prevent.
#
# So the answer is RECOVERED and counted SEPARATELY, never folded into the headline. Two
# numbers come out of one run: what the model DECIDED, and what a caller would actually
# RECEIVE. The gap between them is the channel's cost, which is what D1 is about.
#
# It EXTRACTS two facts; it does not parse and it never invents. The observed payload is
# not even valid JSON (`\'prod\'` — an escaped single quote has no JSON production), so a
# strict load is tried first and a narrow field-scrape second. Anything else is `none`.
_CALLABLE = ("one_operator", "assertion", "decompose")
_NAME_RE = re.compile(r'"name"\s*:\s*"(one_operator|assertion|decompose)"')
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
        if isinstance(obj, dict) and obj.get("name") in _CALLABLE:
            args = obj.get("parameters") or obj.get("arguments") or {}
            return obj["name"], (args if isinstance(args, dict) else {})
    except (ValueError, TypeError):
        pass
    m = _NAME_RE.search(content)
    if not m:
        return None, {}
    op = _OP_RE.search(content)
    return m.group(1), ({"operator": op.group(1)} if op else {})


# ── THE MENUS ────────────────────────────────────────────────────────────────────────────
def _menu(ops: List[str]) -> str:
    return "\n".join(f"  {name} — {(config.OPS[name].get('doc') or '').split('.')[0]}"
                     for name in ops)


def _one_operator_tool(split: bool) -> Dict[str, Any]:
    """Built from `config.OPS`/`config.OP_CATEGORIES`, the SSOT for what an operator IS.
    Hardcoding the seven here would make this probe a 34th vocabulary."""
    ops = _STRUCTURAL if split else _ALL_OPS
    extra = ("\n\nA goal that is a STATE TO MAKE TRUE rather than work to arrange is not "
             "one of these — call `assertion` instead." if split else "")
    return {
        "type": "function",
        "function": {
            "name": "one_operator",
            "description": (
                "Use when the goal is ONE operator — a single statement, with nothing "
                "left over. Name which operator it is. If the goal needs more than one "
                "statement, call `decompose` instead.\n\nThe operators:\n"
                + _menu(ops) + extra
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


def _assertion_tool() -> Dict[str, Any]:
    """--split only. The honest third answer for rungs 7 and 9: one statement, but a STATE
    to be made true, not work to arrange. WHICH intent word it becomes (fetch/ensure/
    achieve) is deliberately NOT asked — the operator's intent decides it and `intent.py`
    enforces it, so asking invites the model to overrule an authority it does not have."""
    return {
        "type": "function",
        "function": {
            "name": "assertion",
            "description": (
                "Use when the goal is ONE statement that names a STATE THAT MUST HOLD, "
                "rather than an action or a loop — e.g. 'exactly three machines carry "
                "this label', 'these hosts can all reach each other'. However much work "
                "it implies, it is still one statement. Do NOT say whether to check it or "
                "make it so: that is decided elsewhere."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": "string",
                              "description": "the state that must hold, in plain English"},
                },
                "required": ["state"],
            },
        },
    }


def _decompose_tool(split: bool) -> Dict[str, Any]:
    """Mirrors DECOMPOSE_TOOL's shape exactly, with 'operator' where it says 'tool call'.

    `operator` is asked for but does NOT gate the kill-switch verdict — staged lowering
    requires that a decomposing node NAME ITS OWN OPERATOR or fusion has nothing to attach
    children to, and asking costs no extra call. Reported separately, below the line.
    """
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
                        "type": "string", "enum": _STRUCTURAL if split else _ALL_OPS,
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


def _system(split: bool) -> str:
    third = ("  - If it is ONE statement naming a STATE that must hold, call `assertion`.\n"
             if split else "")
    return (
        "You are given a goal. Decide whether it is ONE operator or must be broken up.\n"
        "  - If ONE statement expresses the whole goal, call `one_operator` and say which.\n"
        + third +
        "  - If it needs several statements, call `decompose` and list the sub-goals.\n"
        "A loop over a set is ONE operator, not one per member. An end-state to make true "
        "is ONE statement, however much work it implies.\n"
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
    p.add_argument("--split", action="store_true",
                   help="withhold the intent ops; offer `assertion` as the third answer")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    call_model = make_call_model(a.model, a.temp, 300)
    tools = [_one_operator_tool(a.split), _decompose_tool(a.split)]
    if a.split:
        tools.insert(1, _assertion_tool())

    print(f"atomicity probe (E1 kill switch) · model={a.model} temp={a.temp} n={a.repeats}"
          f" · menu={'SPLIT' if a.split else 'flat'}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}")
    n_atomic = len(_ATOMIC & {r.n for r in rungs})
    print(f"corpus: {len(rungs)} rungs · {n_atomic} atomic / {len(rungs) - n_atomic} "
          f"decompose\n")

    route_hits = op_hits = op_asked = 0
    parent_named = parent_total = 0
    atomic_routed = atomic_total = 0
    flaky: List[int] = []
    errors = channel_losses = delivered_hits = 0

    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        exp = EXPECTED[rung.n]
        # Under --split an assertion has its OWN tool; under the flat menu it is still
        # `one_operator`, named with an intent word. Same ground truth, two spellings.
        if exp is None:
            want, want_op = "decompose", None
        elif exp[0] == "assertion" and a.split:
            want, want_op = "assertion", None
        else:
            want, want_op = "one_operator", exp[1]

        got: List[str] = []
        ops_said: List[str] = []
        parents: List[str] = []
        via_content = 0
        for _ in range(a.repeats):
            try:
                reply = call_model([{"role": "system", "content": _system(a.split)},
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
        if count != len(got):
            flaky.append(rung.n)

        routed_ok = majority == want
        route_hits += 1 if routed_ok else 0
        if routed_ok and via_content == 0:
            delivered_hits += 1
        if exp is not None:
            atomic_total += 1
            atomic_routed += 1 if routed_ok else 0

        op_note = ""
        if want_op:
            op_asked += 1
            said = Counter(ops_said).most_common(1)[0][0] if ops_said else "-"
            if routed_ok and said == want_op:
                op_hits += 1
            op_note = f"  op: want {want_op:8} got {said:8}"
        elif exp is not None and a.split:
            op_note = "  (intent withheld — not asked)"
        elif parents:
            parent_total += 1
            named = [x for x in parents if x != "-"]
            if named:
                parent_named += 1
                op_note = f"  parent: {Counter(named).most_common(1)[0][0]}"
            else:
                op_note = "  parent: (unnamed)"

        mark = "OK " if routed_ok else "MISS"
        spread = "" if count == len(got) else f"  ~flaky {dict(tally)}"
        chan = f"  [channel: {via_content}/{len(got)} via content]" if via_content else ""
        print(f"   rung {rung.n:2}  want {want:13} got {majority:13} {mark}"
              f"  {count}/{len(got)}{op_note}{spread}{chan}")

    n = len(rungs)
    floor = n - n_atomic
    print(f"\n── summary · harness=atomicity_probe · model={a.model} · n={a.repeats}"
          f" · menu={'SPLIT' if a.split else 'flat'}")
    print(f"   MODEL DECIDED RIGHT : {route_hits}/{n}   <- the kill-switch number")
    print(f"   …AND IT ARRIVED     : {delivered_hits}/{n}   "
          f"<- what a caller actually receives")
    print(f"   always-'decompose'  : {floor}/{n}   <- the floor. Read the headline against")
    print(f"                                          THIS, not against zero.")
    print(f"   ON THE ATOMIC CELLS : {atomic_routed}/{atomic_total}   "
          f"<- where the information is: the")
    print(f"                                          only cells the floor gets wrong.")
    print(f"   operator named right: {op_hits}/{op_asked}"
          + ("   (structural only — intent is not asked)" if a.split else "")
          if op_asked else "   operator named right: n/a")
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
