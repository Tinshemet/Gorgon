"""Does the author know ENSURE from ACHIEVE?

The two words are the only thing separating "check that this is true" from "bring this
about", and the operator's sentence is often ambiguous between them — *"make sure exactly
three carry the prod label"* reads as both. Ladder rung 7 flipped from ACHIEVE to ENSURE
on a prompt change and stopped converging, which is what a wrong word costs.

Measured HERE and not on the ladder, deliberately. Improving the prompt against the
ladder's own goals would be tuning against the benchmark; these goals are separate, and
none of them is a rung. The ladder stays the held-out set.

Each item declares which word the goal calls for and why. Scored on the word the author
actually reached for while writing a whole program — not on a classification question,
because the choice that matters is the one made in situ.

    PYTHONPATH=. python3 -m tests.bench.word_probe
"""
from __future__ import annotations

import argparse
import sys
from typing import List, NamedTuple, Optional

from orchestrator.ai.planner.ir import render

from .author_probe import author, render as _r  # noqa: F401  (render re-exported)
from .sim_world import SimWorld


class Item(NamedTuple):
    goal: str
    want: str                    # "achieve" | "ensure"
    why: str
    hard: bool = False
    seed: Optional[object] = None


def _lab(w):
    """A small ordinary lab: golden plus two workers, one of them running."""
    w.execute("create_vm", {"name": "golden", "os_type": "linux"})
    w.execute("create_vm", {"name": "web", "os_type": "linux"})
    w.execute("create_vm", {"name": "db", "os_type": "linux"})
    w.execute("launch_vm", {"name": "web"})
    w.execute("create_network", {"net_name": "dmz"})
    w.execute("add_vm_to_network", {"net_name": "dmz", "vm_name": "db"})


ITEMS: List[Item] = [
    # ── the operator wants an END STATE brought about ────────────────────────
    Item("label four machines 'web'", "achieve",
         "an outcome the operator wants to exist afterwards"),
    Item("get two machines running on a network called lab", "achieve",
         "'get' is unambiguous — it asks for a change"),
    Item("there should be exactly one snapshot of db", "achieve",
         "states the world as it ought to end up"),
    Item("make sure at least 4 machines carry the 'web' label", "achieve",
         "'make sure' phrasing an OUTCOME — the hard direction", hard=True),

    # ── the operator wants to KNOW, and nothing to change ────────────────────
    Item("check whether a machine named golden exists", "ensure",
         "'check whether' asks a question, not for a change"),
    Item("verify that db is on the dmz network", "ensure",
         "'verify' is pure inspection"),
    Item("confirm nothing is running before I leave for the day", "ensure",
         "'confirm' — and acting on it would be destructive"),
    Item("make sure golden has not been deleted", "ensure",
         "'make sure' phrasing a CHECK — the hard direction", hard=True),

    # ── both, in one sentence ────────────────────────────────────────────────
    Item("only if golden exists, clone it twice, and end with at least 3 machines",
         "both", "a precondition AND a goal — needs one of each"),
]


def _words(prog) -> tuple:
    """Which of the two words the program used, anywhere in it."""
    def walk(body):
        out = []
        for st in body or []:
            if not isinstance(st, dict):
                continue
            out.append(st.get("op"))
            for f in ("do", "then", "else", "ifails"):
                if isinstance(st.get(f), list):
                    out += walk(st[f])
        return out
    ops = walk((prog or {}).get("body") or [])
    return ("achieve" in ops), ("ensure" in ops)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="ENSURE vs ACHIEVE word choice")
    p.add_argument("--model", default="llama3.1:8b")
    p.add_argument("--temp", type=float, default=0.0)
    p.add_argument("--no-shots", action="store_true")
    a = p.parse_args(argv)

    print(f"word probe · model={a.model} temp={a.temp}"
          f"{' · NO shots' if a.no_shots else ' · few-shot'}\n")

    right = hard_right = hard_total = 0
    for it in ITEMS:
        world = SimWorld()
        _lab(world)
        world.calls.clear()
        prog, problems = author(it.goal, a.model, a.temp, not a.no_shots,
                                known_names=world.names())
        if prog is None:
            print(f"  [ERROR] {it.goal}\n          {problems[0]}\n")
            continue
        has_a, has_e = _words(prog)
        if it.want == "both":
            ok = has_a and has_e
            got = ("both" if (has_a and has_e) else
                   "achieve" if has_a else "ensure" if has_e else "neither")
        else:
            ok = (has_a if it.want == "achieve" else has_e) and not (has_a and has_e)
            got = ("both" if (has_a and has_e) else
                   "achieve" if has_a else "ensure" if has_e else "neither")
        right += ok
        if it.hard:
            hard_total += 1
            hard_right += ok
        mark = "ok  " if ok else "MISS"
        print(f"  [{mark}] want {it.want:8} got {got:8} · {it.goal}")
        if not ok:
            print(f"          ({it.why})")
            for line in render(prog).splitlines():
                print(f"          | {line}")
        print()

    print(f"── {right}/{len(ITEMS)} correct"
          + (f" · of the ambiguous ones, {hard_right}/{hard_total}" if hard_total else ""))
    print("\n   These goals are NOT ladder rungs. Tune the prompt here; the ladder\n"
          "   stays held out, or the number it reports stops meaning anything.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
