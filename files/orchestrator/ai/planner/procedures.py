"""procedures.py — a named Medusa program, kept, and reachable again.

THE OPERATOR'S TEST, and it is a better one than "can it write a snippet": *"the reason I
want to build this snippet is to also test if it can call those snippets when it's done."*
Writing an artifact proves the writer works. USING it later proves the system has a memory
that is made of its own code.

WHAT WAS ALREADY THERE and what was not. A program has carried `name` and typed `params`
since the language was designed, `render` prints `PROCEDURE name(INT x)`, and `run` binds
parameters. So DEFINING one was never the gap. The gap was that nothing kept it, nothing
could call it, and the writer did not know it existed — `PROCEDURE` was a keyword with a
renderer and no home, which is exactly what task #75 records.

THREE THINGS, AND THE THIRD IS THE POINT:

    KEEP      a named program is written to ~/.gorgon/procedures as BOTH the readable
              .medusa text and the IR it was rendered from
    CALL      `CALL setup_temp_vm(template: ...)` — the same keyword a tool takes, because
              A PROCEDURE IS A TOOL YOU WROTE. Medusa is bash for Gorgon and this is a
              shell function; giving it a second keyword would say it was a different kind
              of thing, and it is not
    TILE      a procedure DECLARES WHAT IT ACHIEVES, so the ghost writer can cover a goal
              with it exactly as it covers one with `create_vm`

The third is what makes this reuse rather than replay. Without it, calling a procedure means
somebody naming it — which is a macro. With it, the writer reaches for the operator's snippet
because the snippet is the better move, and the system's own library becomes part of how it
plans. That is also the honest form of "it can call what it wrote": nobody had to tell it to.

WHAT A PROCEDURE MAY NOT DO IS SKIP THE GAUNTLET. Its body is statements like any other, run
by the same visitor through the same guarded executor. Storing a program does not bless it —
a stored `delete_vm` meets the same commit gate it met the day it was written.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# WHERE THEY LIVE. Under the storage home rather than in the repo: a procedure is something
# the OPERATOR accumulated, not something that ships, and a checkout should not carry one
# lab's library into another.
def _home() -> str:
    base = os.environ.get("GORGON_HOME") or os.path.expanduser("~/.gorgon")
    return os.path.join(base, "procedures")


_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def legal_name(name: str) -> bool:
    """A procedure name is an identifier — lowercase, underscores, no spaces.

    STRICTER THAN A MACHINE NAME ON PURPOSE. A machine is named by a person and may be
    called anything; a procedure name is written INTO PROGRAMS, so it has to survive being
    parsed, and a name with a space or a quote in it is a name that breaks the one artifact
    this module exists to keep readable.
    """
    return bool(name and _NAME.match(str(name)))


class Store:
    """The procedure library. A directory of `.medusa` files and their IR.

    BOTH FORMS, DELIBERATELY. The `.medusa` file is what the operator reads, edits and
    shares — "a medusa script that can be used by me and you" was the request, and a JSON
    blob is not that. The `.json` is what the writer and the runtime consume, because
    re-parsing the surface would mean building a parser to read back what we just printed,
    and the two would drift the first time either changed.

    THE PAIR IS WRITTEN TOGETHER OR NOT AT ALL. A `.medusa` with no IR is a file nothing can
    run; IR with no text is a capability with no artifact.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or _home()

    # ── keeping ──────────────────────────────────────────────────────────────
    def save(self, program: Dict[str, Any], rendered: str = "") -> str:
        """Write a named program. Returns the `.medusa` path.

        `achieves` RIDES ALONG IF IT IS THERE and is not invented here. A procedure that
        declares nothing is still callable by name; it simply cannot be REACHED FOR, which
        is the honest consequence of not saying what you do.
        """
        name = program.get("name")
        if not legal_name(name):
            raise ValueError(
                f"{name!r} is not a legal procedure name — a procedure is written into "
                f"programs, so its name must be an identifier: lowercase, digits, underscores")
        os.makedirs(self.path, exist_ok=True)
        if not rendered:
            from .ir.render import render as _render
            rendered = _render(program)
        text_at = os.path.join(self.path, f"{name}.medusa")
        with open(text_at, "w") as fh:
            fh.write(rendered.rstrip() + "\n")
        with open(os.path.join(self.path, f"{name}.json"), "w") as fh:
            json.dump(program, fh, indent=1)
        return text_at

    # ── reading ──────────────────────────────────────────────────────────────
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        at = os.path.join(self.path, f"{str(name)}.json")
        if not os.path.exists(at):
            return None
        try:
            with open(at) as fh:
                return json.load(fh)
        except Exception:
            # A CORRUPT ENTRY IS NOT AN EMPTY LIBRARY. Returning None here would make a
            # damaged file indistinguishable from a procedure nobody wrote — the same
            # unknown-versus-empty confusion the lab registry was bitten by.
            raise

    def text(self, name: str) -> Optional[str]:
        at = os.path.join(self.path, f"{str(name)}.medusa")
        return open(at).read() if os.path.exists(at) else None

    def names(self) -> List[str]:
        if not os.path.isdir(self.path):
            return []
        return sorted(f[:-5] for f in os.listdir(self.path) if f.endswith(".json"))

    def all(self) -> List[Dict[str, Any]]:
        out = []
        for n in self.names():
            got = self.get(n)
            if got:
                out.append(got)
        return out

    def forget(self, name: str) -> bool:
        gone = False
        for ext in (".medusa", ".json"):
            at = os.path.join(self.path, f"{str(name)}{ext}")
            if os.path.exists(at):
                os.remove(at)
                gone = True
        return gone

    # ── reaching for one ─────────────────────────────────────────────────────
    def covering(self, goal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A stored procedure whose `achieves` matches this goal, or None.

        THIS IS THE WHOLE DIFFERENCE BETWEEN A LIBRARY AND A MACRO. A macro is expanded
        because somebody named it. A procedure found here is chosen because the writer was
        looking for something that makes the goal true and this makes the goal true — so the
        operator's own snippet enters the plan without the operator being in the room.

        MATCHED ON SHAPE AND SELECTOR, not on prose. `achieves` is a predicate in exactly the
        form a goal takes, so "does this cover that" is a comparison between two structures
        rather than a judgement about two sentences — which is the difference between this
        being deterministic and it being another place a model can be wrong.

        A PARAMETER MATCHES ANYTHING. `{"kind": "vm", "template": "$template"}` covers a goal
        naming any template, and the binding is returned so the caller can pass it. Without
        that a procedure would only ever match the exact world it was written against, which
        is a snippet that can be reused precisely once.
        """
        for proc in self.all():
            bound = _unify(proc.get("achieves"), goal, proc.get("params") or {})
            if bound is not None:
                return {"name": proc["name"], "params": bound, "procedure": proc}
        return None


def _unify(claim: Any, goal: Any, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Does `claim` describe `goal`? Returns the parameter bindings, or None.

    Structural and total: every key the claim states must be present in the goal and equal,
    and a `$param` in the claim binds whatever the goal has there. The goal may carry MORE
    than the claim mentions — a procedure that guarantees "a vm exists with this template"
    covers a goal that also wants a label, because the extra is simply not this procedure's
    business and the writer will cover the rest.
    """
    if not isinstance(claim, dict) or not isinstance(goal, dict):
        # A `$param` on its own binds; anything else must be equal.
        if isinstance(claim, str) and claim.startswith("$"):
            return {claim[1:]: goal}
        return {} if claim == goal else None
    out: Dict[str, Any] = {}
    for key, want in claim.items():
        if key not in goal:
            return None
        got = _unify(want, goal[key], params)
        if got is None:
            return None
        out.update(got)
    return out


# ONE STORE, so the writer, the runtime and the CLI are looking at the same library. A second
# instance pointed at the same directory would work; a second POINTED SOMEWHERE ELSE is how a
# procedure comes to exist for the thing that wrote it and not for the thing that runs it.
LIBRARY = Store()
