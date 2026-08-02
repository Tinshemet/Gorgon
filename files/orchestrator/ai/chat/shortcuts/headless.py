"""
headless.py — run a REPL shortcut with NO TERMINAL, and hand back what it printed.

WHY THIS EXISTS. `plan` was reachable from a shell (`gorgon plan …`) and from the orchestrator
REPL, and from NEITHER of the two places an operator actually sits. Typed into the chat it was
prose: the model read *"plan procedure test: a windows vm"* as a request to make a machine,
answered that it had, and no procedure was ever written. Three times in one evening, because
the word means something everywhere except where it was typed.

THE THIRD DOOR, AND IT DELEGATES LIKE THE SECOND ONE. `client/cli/commands/_shortcut.py` says
why: reimplementing `plan` here would give two versions of its intent resolution, its consent
prompts and its ledger rendering, and they would disagree the first day one was edited. So the
shortcut that already handles this runs, unchanged, and this only supplies what a chat lacks —
somewhere for its output to go, and an answer for questions nobody is there to hear.

THE CHAT IS AN ABSENT TERMINAL, and that is not a workaround, it is the codebase's own rule:
`intent`, `consent`, `ask_destroy`, `ask_banned` and `procedures delete` each catch EOFError
and take the answer that changes nothing. So `console.input` and `getpass` are made to raise
for the duration, and every question in the shortcut answers itself the safe way. A server
that could block on its own stdin waiting for an operator who is in a different process is the
alternative, and it hangs the whole orchestrator.

WHICH IS WHY AN ACTING PLAN IS REFUSED HERE RATHER THAN DEGRADED. `plan <request>` runs the
program it writes, and the human questions guarding that — *this destroys these machines*, *a
red line, password?* — cannot be asked down a request/response wire without the multi-turn
protocol `needs_input` exists for. Answering them all NO would make acting plans mostly stop,
which teaches the operator the feature is broken; answering them YES is precisely the bug
fixed the same evening, where a confirmation nobody read granted itself. So the chat gets the
two dispositions that CANNOT touch the world:

    plan procedure NAME(TYPE arg): <english>   AUTHORING — `orchestrator._author`: the engine
                                               plans exactly as it would to act and the
                                               program is KEPT. Nothing runs, by construction.
    plan --dry <request>                       A PREVIEW — the decider returns STOP at the
                                               first step, so half a program cannot run either.
    procedures …                               Reading the library. Its one destructive verb
                                               (`delete`) already reads an absent terminal as
                                               "kept".

and an acting `plan` is told, in one line, where it can be run. A refusal that names the
working command is worth more than a capability that silently does less than it says.
"""
import getpass as _getpass
import threading

from shared.display import console

# Rich capture is process-wide state on one console singleton, and uvicorn serves requests on
# a thread pool. Two captures at once lose one operator's output into the other's; the lock
# makes the second wait rather than interleave. Shortcut runs are seconds, not minutes.
_LOCK = threading.Lock()

_PLAN    = "plan"
_LIBRARY = "procedures"

_ACTING_REFUSAL = (
    "`plan {req}` would ACT on the lab, and the chat cannot ask you the questions that\n"
    "guard that — what it would destroy, whether to lift a red line. Those need a terminal.\n"
    "\n"
    "Run it in a shell:   gorgon plan {req}\n"
    "\n"
    "From here you can do the two things that never touch the lab:\n"
    "  plan procedure NAME(STRING arg): <what it should do>   write it down, run nothing\n"
    "  plan --dry {req}                                       see what it WOULD do"
)


def _absent(*_a, **_kw):
    """The chat has no terminal. Every asking site in the shortcuts catches this."""
    raise EOFError("no terminal — this shortcut is running from the chat")


def _captured(ui: str, verbose: bool) -> str:
    """Run the shortcut `ui` matches, with stdin removed, and return its printed output."""
    from . import handle_command

    with _LOCK:
        was_input, was_getpass = console.input, _getpass.getpass
        console.input, _getpass.getpass = _absent, _absent
        try:
            with console.capture() as cap:
                # `messages` and `runtime_drift_count` are the chat's, and neither delegated
                # shortcut reads them — the same honest empties `_shortcut.py` passes.
                handled = handle_command(ui, [], 0, verbose)
            out = cap.get()
        finally:
            console.input, _getpass.getpass = was_input, was_getpass
    if not handled:
        # The grammar is the shortcut's own, asked rather than restated — so a phrase this
        # module offered to run and the registry then declined says so, instead of returning
        # an empty box that reads as success.
        return f"`{ui.strip()}` is not a command I can run from here."
    return out.strip() or "(nothing to show)"


def acts_on_the_world(rest: str) -> bool:
    """Would `plan <rest>` reach the lab? True unless it is authoring or a dry run.

    THE DECLARATION IS READ THE WAY `plan` READS IT — `procedures.declared_in`, the same
    parser — so this cannot come to a different conclusion about the same string than the
    shortcut it is gating.
    """
    low = rest.strip().lower()
    if low.startswith("--dry ") or low.startswith("-n "):
        return False
    from planner import procedures as _procs
    try:
        keep_as, _declared, _body = _procs.declared_in(rest.strip())
    except Exception:
        # A MALFORMED DECLARATION IS STILL A DECLARATION. `plan` prints the complaint and
        # runs nothing — refusing it here instead would answer a typo with the wrong lesson.
        return False
    return not keep_as


def run(message: str, verbose: bool = False):
    """Handle *message* if the chat can run it. Returns the text to show, or None.

    None means "not mine" — the caller falls through to the model, which is what every other
    sentence typed into the chat should do.

    Example::

        run("plan procedure test(STRING name): a windows vm called $name")   # → the program
        run("plan create a vm")                                              # → where to run it
        run("make me a vm")                                                  # → None
    """
    ui  = (message or "").strip()
    low = ui.lower()

    if low == _LIBRARY or low.startswith(_LIBRARY + " "):
        return _captured(ui, verbose)

    if low == _PLAN or low.startswith(_PLAN + " "):
        rest = ui[len(_PLAN):].strip()
        if not rest:
            # Bare `plan`. The shortcut prints its own usage, which is the one place that
            # usage is written down.
            return _captured(ui, verbose)
        if acts_on_the_world(rest):
            return _ACTING_REFUSAL.format(req=rest)
        return _captured(ui, verbose)

    return None
