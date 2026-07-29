"""
export_failures.py — every failing cell, with the program the model actually wrote.

A ladder summary says WHICH cells are red. It does not say what the model produced, and
that is the thing you need to tell a channel failure from a reasoning one — twice on
2026-07-29 a rung was diagnosed from the wrong artifact (the POST-REPAIR wreckage rather
than the first draft, and a schema the measured path does not use). This writes the
programs down beside the verdicts so the next reading starts from evidence.

It PARSES A RUN LOG rather than calling a model: the report describes the run it is given,
not a fresh one, so the same log always produces the same file. Cells with no program say
so explicitly — "no program" is a finding, not a blank.

Run:  PYTHONPATH=. python3 -m tests.bench.export_failures <run.log> [-o failures.md]
"""
import argparse
import re
import sys
from typing import Dict, List, Optional

from .rungs import RUNGS

# What we have established about each failing cell, written here rather than inferred, so
# the report cannot quietly restate the log back at itself as though it were analysis.
DIAGNOSIS: Dict[str, str] = {
    "lit:8": (
        "CHANNEL. The decoder dies at the same character position every time and no "
        "program is ever produced, so we have NEVER OBSERVED what the model would write "
        "for the literal wording — which matters, because the literal column says "
        "`except db`, the same word few-shot 7 demonstrates a carve-out with. Whether the "
        "model can do rung 8 at all is unknown, not answered."),
    "para:8": (
        "MODEL, two separate defects. (1) CARDINALITY: `db` is one object identified by "
        "the kind's key, so its statement is a plain `call` naming it — the model writes a "
        "`foreach` over a select of one, and that loop is what let the missing `kind` "
        "exist at all. (2) THE CARVE-OUT IS ABSENT from the first loop, so every vm "
        "including db lands on core, which the checker forbids. Fixing (1) alone leaves "
        "the rung red. NOTE the scored program is the POST-REPAIR one: the first draft "
        "gets `db` right and the repair loop, handed `select must name a kind` twice, "
        "rewrote `name = 'db'` into the complement `['app1','app2','app3']` — inverting "
        "the goal while still not supplying the kind."),
    "para:9": (
        "WORLD BLINDNESS — the same defect rung 13 was reworded to expose on 2026-07-28. "
        "CURRENT STATE shows `n1: networks=mesh0`, `n2: networks=mesh0`, `n3:` with none. "
        "One line identifies the fault. The model writes `NEW vm` three times into a lab "
        "already holding all three. Its earlier 3/3 was NOT a pass worth having: it "
        "re-created three existing machines and an existing network, then re-attached "
        "everything, which satisfies an end-state-only checker without ever diagnosing "
        "anything. Rung 9 has no `best`/`minimum`, so a 10-call bulldoze scores the same "
        "as the single `add_vm_to_network` the task needs."),
    "para:7": (
        "NOT A STABLE FAILURE — this cell is roughly 60%. It came back 2/3 on two separate "
        "targeted re-runs, splitting WITHIN a single run, and its history is 0/3 then 3/3 "
        "three times then 0/3 twice on a byte-identical authoring path (prompt and schema "
        "hashes verified equal). Read it as a coin flip, not as red or green. n=3 cannot "
        "tell a 60% cell from a broken one, which is the real defect here."),
    "para:11": "CHANNEL. Malformed JSON at the same character position, unchanged all day.",
    "lit:13": (
        "WORLD BLINDNESS, VISIBLE — and I had this wrong until this report printed the "
        "program. I wrote that rung 13's reasoning failure was 'unobservable because "
        "repair returns nothing'. It is not: the first draft is right here, and the "
        "validator names the defect outright — `the lab already holds 5 vm(s) — AMOUNT "
        "makes 5 MORE, not 5 in total`. The model writes `NEW AMOUNT(5) vm` into a lab "
        "holding five, which is the exact mistake `f2ae63c` states the rule against and "
        "the same defect as para:9. The CHANNEL is what stops it RECOVERING — repair "
        "delivers nothing — but the reasoning failure is observed, not hidden. Two "
        "distinct faults in one cell, and reporting only the terminal outcome hid the "
        "more important one."),
    "para:13": (
        "As lit:13 — world blindness in the draft, channel failure in the repair. The "
        "terminal `REPAIR_UNDELIVERED:empty` names the second and buries the first."),
}

_RUNG_RE = re.compile(r"^── rung (\d+) \(([^)]+)\)")
_GOAL_RE = re.compile(r"^\s+goal: (.*)$")


def parse(path: str) -> List[dict]:
    """Every authored attempt in the log, in order, with its program and objections."""
    out: List[dict] = []
    cur: Optional[dict] = None
    for line in open(path, errors="replace"):
        line = line.rstrip("\n")
        m = _RUNG_RE.match(line)
        if m:
            cur = {"n": int(m.group(1)), "name": m.group(2), "goal": None,
                   "program": [], "objections": [], "verdict": None, "checker": None,
                   "noresult": None}
            out.append(cur)
            continue
        if cur is None:
            continue
        g = _GOAL_RE.match(line)
        if g:
            cur["goal"] = g.group(1)
        elif "| " in line and line.strip().startswith("|"):
            cur["program"].append(line.split("| ", 1)[1])
        elif line.strip().startswith("- "):
            cur["objections"].append(line.strip()[2:])
        elif "[NO RESULT]" in line:
            cur["noresult"] = line.split("[NO RESULT]", 1)[1].strip()
        elif "[VALID]" in line or "[INVALID]" in line:
            cur["verdict"] = "VALID" if "[VALID]" in line else "INVALID"
        elif "RUNG CHECKER:" in line:
            cur["checker"] = line.split("RUNG CHECKER:", 1)[1].strip()
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Export failing cells with their programs")
    p.add_argument("log", help="a ladder_gate / author_probe run log")
    p.add_argument("-o", "--out", default="failures.md")
    a = p.parse_args(argv)

    attempts = parse(a.log)
    by_rung = {r.n: r for r in RUNGS}
    # A cell is identified by rung + which wording was used; the log prints the goal, so
    # match on it rather than trusting run order (a resumed or partial log breaks order).
    def column(att) -> str:
        r = by_rung.get(att["n"])
        if r and att["goal"]:
            if r.paraphrase and att["goal"].strip() == r.paraphrase.strip():
                return "para"
            if att["goal"].strip() == r.goal.strip():
                return "lit"
        return "?"

    lines: List[str] = []
    w = lines.append
    w("# Ladder failures, with the programs")
    w("")
    w(f"Source log: `{a.log}`")
    w("")
    w("Every cell below is one the ladder scored 0/3. The program shown is the LAST one "
      "the run produced for that cell — after any repair rounds — which is not always what "
      "the model first wrote. Where they differ it is called out in the diagnosis.")
    w("")

    seen = set()
    for att in attempts:
        cell = f"{column(att)}:{att['n']}"
        if cell not in DIAGNOSIS or cell in seen:
            continue
        seen.add(cell)
        r = by_rung.get(att["n"])
        w(f"## {cell} — rung {att['n']}, {att['name']}")
        w("")
        if r:
            w(f"**Tests:** {r.why}")
            w("")
        w(f"**Goal:** {att['goal']}")
        w("")
        if att["noresult"]:
            w(f"**Outcome:** NO PROGRAM — `{att['noresult']}`")
            w("")
            w("> The decoder never delivered a parseable program, so there is nothing to "
              "read. This is the finding, not a gap in the report.")
        else:
            w(f"**Outcome:** {att['verdict'] or '?'}"
              + (f" · checker {att['checker']}" if att["checker"] else ""))
            w("")
            if att["objections"]:
                w("**Objections:**")
                w("")
                for o in att["objections"]:
                    w(f"- `{o}`")
                w("")
            if att["program"]:
                w("**Program:**")
                w("")
                w("```")
                for pl in att["program"]:
                    w(pl)
                w("```")
            else:
                w("_(no program rendered)_")
        w("")
        w(f"**Diagnosis:** {DIAGNOSIS[cell]}")
        w("")
        w("---")
        w("")

    missing = [c for c in DIAGNOSIS if c not in seen]
    if missing:
        w(f"> Not found in this log: {', '.join(sorted(missing))} — the run may be partial.")
        w("")

    open(a.out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {a.out} · {len(seen)} failing cell(s): {', '.join(sorted(seen))}")
    if missing:
        print(f"  NOT in this log: {', '.join(sorted(missing))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
