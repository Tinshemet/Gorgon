"""procedures.py — the library surface: what Gorgon has written, and what it says.

THE GAP THIS CLOSES, stated by the handover on 2026-08-02: *"the `.medusa` files are meant
to be read and edited and there is currently no way to ask Gorgon what it has written."*
`plan procedure NAME: …` authored them and `routines` showed the scheduled ones; nothing
listed, showed, ran, verified or deleted them.

    procedures                 what is stored, and whether each one is well
    procedures show <name>     the program — the text a person reads IS the program
    procedures verify <name>   read it back and check it, or all of them with no name
    procedures run <name> k=v  run it, through the ordinary engine path
    procedures delete <name>   forget it, after showing what would go

A PROCEDURE IS A TOOL YOU WROTE, so none of this is a second way to run things. `run` calls
the stored program by name as a one-statement program through the SAME orchestrator, the
same guarded executor and the same consent seam as anything typed by hand — being named on
a command line earns a program nothing.

THE LISTING SAYS WHETHER EACH ONE IS WELL, and that is not decoration. `all()` SKIPS a
procedure it cannot read, which is right for planning and silent for the person who broke
it — so a library can quietly hold a file that no longer parses. Here the broken ones are
named first.
"""
from typing import Dict, List

from shared.display import console

from .base import Shortcut

_WORD = "procedures"
_VERBS = ("show", "run", "delete", "verify", "syntax")


class Procedures(Shortcut):
    """`procedures [show|verify|run|delete <name>]` — the stored-program library."""

    def matches(self, ui: str) -> bool:
        said = ui.strip().lower().split()
        if not said or said[0] != _WORD:
            return False
        if len(said) == 1:
            return True
        return said[1] in _VERBS

    # ── the doors ────────────────────────────────────────────────────────────
    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        # IMPORTED HERE for the reason `plan` states: a shortcut registers at class
        # definition, so every import in this file is paid by a session that never types it.
        from planner import procedures as _procs

        said = ui.strip().split()
        verb = said[1].lower() if len(said) > 1 else ""
        name = said[2] if len(said) > 2 else ""
        rest = said[3:]
        lib = _procs.LIBRARY

        if verb == "show":
            return self._show(lib, name)
        if verb == "verify":
            return self._verify(lib, name)
        if verb == "delete":
            return self._delete(lib, name)
        if verb == "run":
            return self._run_one(lib, name, rest, verbose)
        if verb == "syntax":
            return self._syntax(lib)
        return self._list(lib)

    # ── list ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _list(lib) -> None:
        names = lib.names()
        # `names()` RECORDS WHAT IT COULD NOT READ, and reading it back is the only way a
        # damaged library is distinguishable from a small one.
        broken = list(lib.broken)
        if not names and not broken:
            console.print("[dim]nothing written yet. `plan procedure NAME: <what you "
                          "want>` writes one; `procedures syntax` explains the "
                          "language.[/dim]")
            return

        if broken:
            console.print(f"[warn]{len(broken)} cannot be read[/warn]")
            for n in broken:
                why = next((c["why"] for c in lib.verify(n)["checks"]
                            if c["ok"] is False), "unreadable")
                console.print(f"  · [warn]{n}[/warn]  [dim]{why}[/dim]")
            console.print("[dim]`procedures verify <name>` for the detail.[/dim]\n")

        if not names:
            return
        console.print("[bold]what Gorgon has written[/bold]")
        for prog in lib.all():
            n = prog["name"]
            # THE SIGNATURE IS WHAT MAKES IT A LIBRARY ENTRY RATHER THAN A MACRO. A
            # procedure full of literals can only ever cover the goal it was written from,
            # so an empty one is worth seeing at a glance.
            params = prog.get("params") or {}
            sig = ", ".join(f"{t.upper()} {p}" for p, t in params.items())
            how = (f"every {prog['every']}" if prog.get("every")
                   else "when the world says so" if prog.get("when") else "")
            claims = "" if prog.get("achieves") else "  [dim]claims nothing[/dim]"
            console.print(f"  · [bold]{n}[/bold]({sig})"
                          + (f"  [dim]{how}[/dim]" if how else "") + claims)
        console.print(f"\n[dim]{lib.path}  ·  `procedures show <name>` to read one[/dim]")

    # ── show ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _show(lib, name: str) -> None:
        if not name:
            console.print("[dim]`procedures show <name>`[/dim]")
            return
        try:
            text = lib.text(name)
        except Exception as e:
            text = None
            console.print(f"[warn]{name} could not be read: {e}[/warn]")
        if text is None:
            console.print(f"[warn]nothing called {name}.[/warn] "
                          f"[dim]`procedures` lists what there is.[/dim]")
            return
        console.print(f"[bold]{name}[/bold]  [dim]{lib.path}/{name}.medusa[/dim]\n")
        for line in text.splitlines():
            console.print(f"  {line}")

    # ── verify ───────────────────────────────────────────────────────────────
    @staticmethod
    def _verify(lib, name: str) -> None:
        """THE ONE THAT CATCHES A HAND EDIT — see `Store.verify`.

        Shown for ALL of them when no name is given, because the question "is my library
        well" is the one somebody actually has, and asking it once per procedure is how a
        broken file stays unnoticed.
        """
        reports = [lib.verify(name)] if name else lib.verify_all()
        if not reports:
            console.print("[dim]nothing written yet.[/dim]")
            return
        for rep in reports:
            head = ("[ok]well[/ok]" if rep["clean"]
                    else "[warn]readable, with findings[/warn]" if rep["ok"]
                    else "[bold red]will not load[/bold red]")
            console.print(f"\n[bold]{rep['name']}[/bold]  {head}")
            for c in rep["checks"]:
                if c["ok"] is True:
                    console.print(f"  [ok]ok[/ok]   {c['check']}")
                elif c["ok"] is None:
                    console.print(f"  [dim]—    {c['check']}  {c['why']}[/dim]")
                else:
                    # FATAL MEANS THE FILE IS NOT THE PROGRAM; the rest is about MEANING.
                    tag = "[bold red]FAIL[/bold red]" if c["fatal"] else "[warn]note[/warn]"
                    console.print(f"  {tag} {c['check']}  [dim]{c['why']}[/dim]")

    # ── syntax ───────────────────────────────────────────────────────────────
    @staticmethod
    def _syntax(lib) -> None:
        at = lib.write_reference()
        console.print(f"[bold]the language, written out of its own definition[/bold]\n"
                      f"  {at}\n"
                      f"[dim]generated — editing it changes nothing, and every save "
                      f"rewrites it.[/dim]")

    # ── delete ───────────────────────────────────────────────────────────────
    @staticmethod
    def _delete(lib, name: str) -> None:
        """SHOWN BEFORE IT GOES. A procedure is something the operator accumulated, and
        `forget` removes the artifact AND its run state with nothing to undo it."""
        if not name:
            console.print("[dim]`procedures delete <name>`[/dim]")
            return
        if "." in name:
            # A METHOD IS NOT A FILE. `forget` takes a file stem, so deleting `C.m` would
            # silently remove nothing and report success.
            whole = name.partition(".")[0]
            console.print(f"[warn]{name} is a method of {whole}, not a file of its own.[/warn]"
                          f" [dim]Delete the class with `procedures delete {whole}`.[/dim]")
            return
        try:
            text = lib.text(name)
        except Exception:
            text = None
        # ABSENT AND UNREADABLE ARE DIFFERENT ANSWERS, and `text()` gives None to both. A
        # name nobody wrote must not be offered for deletion — confirming it would teach the
        # operator that the prompt means nothing.
        report = lib.verify(name)
        missing = any(c["check"] == "exists" and c["ok"] is False for c in report["checks"])
        if missing:
            console.print(f"[warn]nothing called {name}.[/warn] "
                          f"[dim]`procedures` lists what there is.[/dim]")
            return
        if text is None:
            # A DAMAGED FILE IS STILL DELETABLE — that may be exactly why they are here —
            # but it cannot be shown, and saying so is better than showing nothing.
            console.print(f"[warn]{name} cannot be read; deleting it unread.[/warn]")
        else:
            console.print(f"[bold]{name}[/bold] — this would go:\n")
            for line in text.splitlines():
                console.print(f"  [dim]{line}[/dim]")
        try:
            said = console.input(f"\n[bold cyan]delete {name}? (y/n):[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            said = ""
        # AN ABSENT TERMINAL IS A NO. The same rule `plan` applies to consent: with nobody
        # to ask, the answer is the one that changes nothing.
        if said.strip().lower() not in ("y", "yes"):
            console.print("[dim]kept.[/dim]")
            return
        console.print(f"[ok]forgotten[/ok] {name}" if lib.forget(name)
                      else f"[warn]nothing was removed[/warn]")

    # ── run ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _arguments(given: List[str], wanted: Dict[str, str]):
        """`['name=box9']` + the signature -> `({'name': 'box9'}, [complaints])`.

        `key=value`, NOT `key: value`. The language writes a call the second way and this
        is the one place the two diverge on purpose: a colon needs quoting in a shell and
        reads as a path, and `procedures run mk name: box9` would arrive as three words with
        the colon glued to the wrong one. The signature it fills is the same signature.

        MISSING IS REFUSED, AND THAT IS THE POINT OF WRITING THIS AT ALL. An unbound `$name`
        resolves to itself, so a procedure run with no arguments CREATES A MACHINE CALLED
        `$name` and reports success — the exact failure `validate`'s own docstring warns
        about, arriving through the front door. UNKNOWN is refused too: a caller who spells
        `os` where the signature says `os_type` has said something false about the procedure,
        and silently ignoring it would run a program missing the value they meant to give.
        """
        got, bad = {}, []
        for pair in given:
            key, sep, val = pair.partition("=")
            if not sep or not key:
                bad.append(f"{pair!r} is not key=value")
            elif key not in wanted:
                bad.append(f"{key!r} is not a parameter of this procedure")
            else:
                got[key] = val
        missing = [p for p in wanted if p not in got]
        if missing:
            bad.append("no value for " + ", ".join(f"{p} ({wanted[p].upper()})"
                                                   for p in missing))
        return got, bad

    @staticmethod
    def _run_one(lib, name: str, given: List[str], verbose: bool) -> None:
        """Run a stored procedure BY NAME, through the ordinary path.

        THE SAME DOOR AS EVERYTHING ELSE, and the shape is `routines run`'s: a stored
        procedure is a legal call target, so it goes as a ONE-STATEMENT PROGRAM through the
        same visitor. Being asked for by name does not let it skip a gate it would meet if
        the writer had reached for it.

        `achieve` BECAUSE THE OPERATOR NAMED IT. They did not describe a goal and ask what
        to do about it; they pointed at a program they wrote and said run it, which is the
        authority the intent ladder is asking about. The CONSENT seam is still passed — a
        program that acts and vouches for nothing asks before it runs, and that question is
        answerable here because there is a person at the terminal.
        """
        if not name:
            console.print("[dim]`procedures run <name>`[/dim]")
            return
        try:
            found = lib.get(name)
        except Exception as e:
            console.print(f"[warn]{name} could not be read: {e}[/warn]  "
                          f"[dim]`procedures verify {name}` for the detail.[/dim]")
            return
        if not found:
            console.print(f"[warn]nothing called {name}.[/warn]")
            return

        wanted = found.get("params") or {}
        args, bad = Procedures._arguments(given, wanted)
        if bad:
            for line in bad:
                console.print(f"[warn]{line}[/warn]")
            sig = ", ".join(f"{t.upper()} {p}" for p, t in wanted.items())
            console.print(f"[dim]procedures run {name}"
                          + "".join(f" {p}=…" for p in wanted)
                          + (f"   [{sig}][/dim]" if sig else "[/dim]"))
            return

        from engines import rig as _rig
        from orchestrator.pipeline import execute_tool
        from orchestrator.ai.active_library import LIBRARY
        # THE CONSENT QUESTION IS ASKED IN ONE PLACE. `plan` owns it because that is where
        # the person is, and asking it a second way here would be a second answer to the
        # same question the day one of them changed.
        from .plan import Plan

        def guarded(tool, args):
            # THE SAME DOOR, AND THE SAME BOOKKEEPING — see `plan.py`, which records what
            # broke when a program's calls changed the lab and never told the registry.
            result = execute_tool(tool, args, verbose=verbose)
            try:
                LIBRARY.apply(tool, args, result=result)
            except Exception:
                pass
            return result

        # THE SAME QUESTION `plan` ASKS, and for the same reason: a stored procedure is not
        # more trusted for being stored. `Plan` owns the asking so there is one wording and
        # one default (no) rather than two that drift.
        from engines import insession as _insession

        def decide(step, session):
            if step.destroys and not Plan.ask_destroy(step):
                return _insession.Verdict(_insession.STOP, "not granted — nothing was done")
            return _insession.Verdict(step.kind)

        orch = _rig.build(guarded, narrate=True, consent=Plan._ask_consent, decide=decide,
                          permit=Plan.ask_banned)
        shown = "".join(f" {k}={v}" for k, v in args.items())
        console.print(f"\n[bold]{name}[/bold]{shown}")
        out = orch.handle(name, intent="achieve",
                          components=[{"_call": (name, args)}])
        colour = {"DONE": "ok", "REFUSED": "warn"}.get(out.get("outcome"), "warn")
        console.print(f"  [{colour}]{out.get('outcome')}[/{colour}]  {out.get('why') or ''}")
        for line in (out.get("log") or []):
            console.print(f"  [dim]{line}[/dim]")
