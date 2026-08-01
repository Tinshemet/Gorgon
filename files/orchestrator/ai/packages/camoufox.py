"""camoufox.py — SEARCH THE WEB FROM INSIDE A MACHINE. A package, not an engine.

THE OPERATOR'S ACCEPTANCE TEST: *"build a package using camoufox as a webcrawler, through
gorgon alone — the AI, not you. The orchestrator only generates Medusa code, opens the
webcrawler in a vm, uses the guest agent to run a search."* It exercises everything at once —
two engines, a package, a program written by code from goals the model extracted, and PUBLISH
carrying an answer back up.

A PACKAGE BECAUSE IT PARSES THE INTERNET. Camoufox is a browser: it fetches whatever a
stranger serves and renders it. That is the exact definition of a capability that must not
have the host, and here it cannot — not because a check refuses it, but because a package has
no `run` and no `intents`, so there is no method by which the orchestrator could route to it.
Its HANDS belong to the loading engine, which reaches a machine's guest agent.

THREE KINDS AND ONE CHAIN NOBODY WRITES DOWN:

    a SEARCH needs a BROWSER      (`refs: browser`)
    a BROWSER needs a MACHINE     (`refs: vm`)

so "search the web for the diameter of the earth" becomes create-machine, launch-browser,
run-search — IN THAT ORDER — from two `refs` and nothing else. The webcrawl package proved
this at two levels; this is three, across a boundary the package does not own.

THE ANSWER IS OBSERVED, WHICH IS THE WHOLE EPISTEMIC POINT. A search does not "succeed"; it
either produced an answer or it did not, and the only way to know is to ASK. Declaring it
under `observed` means the writer probes rather than trusting a tool's exit code — the same
rule that stops a program claiming reachability it never measured, and the reason a crawler
that trusts its own success flags reports four hundred pages and delivers twelve.

NO DISPLAY, EVER, FOR THIS. Everything here happens over a shell inside the machine, so the
host has no reason to open a window or a VNC listener for it — see `launch_vm`'s `args` in the
manifest, where that is declared once as a fact about the tool.

STILL TO COME (1.1): SECURE SEARCH, as its own act rather than a flag on this one. Routed
through a VPS, run in a stealth-persona machine, and REPORTED as such — a normal search is
cheap and local, a secure one buys unattributability, and the operator must be able to tell
from the answer which of the two they got.

WHAT IS REAL HERE AND WHAT IS NOT. The manifest, the dependency chain, the observation and
the guest-command construction are exactly what ships. Whether a browser is actually INSTALLED
in a given machine is the lab's business, and when it is not, the guest command fails and the
ledger says which call, on which machine, with what error. That is the correct failure and
not a simulation of one.
"""
from __future__ import annotations

import json
import shlex
from typing import Any, Callable, Dict, Optional

from .base import Package

# THE ENTIRE REGISTRATION. Three kinds; every ordering below is DERIVED from `refs`.
MANIFEST: Dict[str, Any] = {
    "browser": {
        "key": "browser_name",
        "attrs": ["browser_name", "vm", "status"],
        "nouns": ["browser", "camoufox", "webcrawler", "crawler"],
        "create": "camoufox_launch",
        "delete": "camoufox_close",
        "attr_values": {"status": ["running", "stopped"]},
        "create_defaults": {"status": "running"},
        # A BROWSER'S MACHINE IS FIXED AT BIRTH, not assigned afterwards. A process runs on
        # a host from the moment it starts — there is no launching one nowhere and binding
        # it later — and saying so is what makes the machine a REQUIREMENT rather than an
        # attribute somebody might set. Same shape as the kitchen's lesson: an ingredient's
        # dish is what the ingredient IS.
        # RUNNING, not merely existing. A browser process cannot start on a machine that is
        # switched off, and the writer turns that into `create_vm` then `launch_vm` — with
        # no display, because this machine is the program's own.
        "create_requires": [{"kind": "vm", "must": {"status": "running"}}],
        "setters": {
            "camoufox_stop": {"attr": "status", "member_arg": "browser_name",
                              "value": "stopped"},
        },
    },
    # A MACHINE FOR THIS WORK NEEDS A SHELL AND NOTHING ELSE. The manifest's `launch_vm`
    # carries `display: none` for exactly this reason — a program starting a machine so a
    # package can work inside it is not a request to LOOK at the machine, and a graphical
    # session per machine is cost with no reader. Display is what the operator asks for
    # through the tool path when they want the machine themselves.
    "search": {
        "key": "query",
        # A SEARCH IS NAMED BY ITS QUESTION, which is prose. "diameter of the earth" is the
        # member's identity here the way `bench-red-1` is a machine's, and the extractor's
        # name-shape floor has to be told that or it refuses every query for having spaces.
        "key_freetext": True,
        "attrs": ["query", "browser", "answered"],
        "nouns": ["search", "query", "lookup", "question"],
        # THE WORKED EXAMPLE FOR THIS KIND, and the package is the only thing that knows it.
        #
        # Loading the package joined `search` to the schema, the enums and the prompt's domain
        # line, and the model still answered a web-search request with the prompt's two
        # MACHINE examples copied verbatim — it had never been shown what asking for one of
        # these looks like. A kind that can be named and cannot be demonstrated is a kind the
        # model will not reach for.
        #
        # THE SENTENCE IS DELIBERATELY NOT THE ONE ANYBODY TESTS WITH. "The diameter of the
        # earth" is the acceptance request, and an example the model can copy straight into a
        # passing answer would measure copying — the exact defect this is here to remove.
        #
        # IT DEMONSTRATES THE FREE-TEXT KEY, which is the part that is genuinely unlike a
        # machine: the operator's own words become the member's identity, spaces and all.
        "example": {
            "request": "look up the boiling point of water",
            "goal": "count 1, select search where query=the boiling point of water",
        },
        "create": "camoufox_search",
        # THE ARGUMENT NAME MATCHES THE ATTRIBUTE, so the chain derives. An earlier version
        # renamed it to `in_browser`, which broke the tie `precondition` reads — the
        # attribute `browser` names the KIND browser, and that is the whole dependency.
        "create_args": {},
        "create_requires": ["browser"],
        "attr_values": {"answered": ["yes", "no"]},
        "create_defaults": {"answered": "no"},
        # OBSERVED — LEARNED BY ASKING, NEVER INFERRED. A search that ran is not a search
        # that answered, and the difference is the only thing the operator actually wanted.
        "observed": {
            "answer": {"fact": "answer({query})", "by": "camoufox_read",
                       "doc": "what the search came back with. A tool exit code is not an "
                              "answer — this is read from the browser, or it is unknown."},
        },
    },
}

# HOW A TOOL BECOMES A COMMAND INSIDE THE MACHINE. One place, so the guest contract is
# readable and a change to it is one edit rather than a hunt.
_GUEST = {
    "camoufox_launch": ("browser_name",
                        "camoufox start --profile {browser_name} --headless"),
    "camoufox_close":  ("browser_name", "camoufox stop --profile {browser_name}"),
    "camoufox_search": ("query", "camoufox search --profile {browser} --json {query!q}"),
    "camoufox_read":   ("query", "camoufox result --profile {browser} --json {query!q}"),
}


def guest_command(tool: str, args: Dict[str, Any]) -> Optional[str]:
    """The shell line this tool becomes inside the machine, or None if it is not a guest tool.

    EVERY OPERATOR-SUPPLIED VALUE IS QUOTED. A search query is a string a person typed and a
    browser will be handed; putting it into a shell line unquoted would make "diameter of the
    earth; rm -rf ~" a command rather than a question. `shlex.quote` is not a nicety here —
    it is the boundary between a query and an instruction.
    """
    spec = _GUEST.get(tool)
    if not spec:
        return None
    _key, template = spec
    out = template
    for name, value in (args or {}).items():
        text = str(value)
        out = out.replace("{" + name + "!q}", shlex.quote(text))
        out = out.replace("{" + name + "}", text)
    return out


class SearchWorld:
    """The package's own state, and the two questions asked of it.

    ITS HANDS ARE SOMEBODY ELSE'S. `execute` is injected by the loading engine, which is what
    keeps the guest boundary structural: this class cannot reach a machine, it can only be
    given something that can.
    """

    def __init__(self, execute: Optional[Callable] = None, vm_of=None):
        self.kinds = MANIFEST
        self.state: Dict[str, Dict[str, Dict[str, Any]]] = {"browser": {}, "search": {}}
        from ..planner.model_world import Ledger
        self.findings = Ledger()
        self._execute = execute
        # WHICH MACHINE A BROWSER SITS ON, asked of the engine rather than remembered here.
        # A package that kept its own copy of the lab would be a second registry.
        self._vm_of = vm_of or (lambda browser: None)

    @property
    def seams(self):
        from ..planner.model_world import seams as _generic
        return _generic(self)

    def names(self) -> set:
        return {n for rows in self.state.values() for n in rows}

    def execute(self, tool: str, args: Dict[str, Any]):
        if self._execute is not None:
            return self._execute(tool, args)
        # NO HANDS, NO ACTION. A package with nothing injected does not quietly pretend to
        # work — that is how a mock becomes production by accident.
        return {"success": False,
                "error": f"{tool}: this package has no hands — an engine must load it"}


class CamoufoxPackage(Package):
    """Search the web from inside a disposable machine, through its guest agent."""

    name = "camoufox"
    description = ("search the web from inside a virtual machine using a Camoufox browser, "
                   "and read back what it found")
    runs_in = "guest"

    @property
    def manifest(self) -> Dict[str, Any]:
        return MANIFEST

    def world(self, execute: Optional[Callable] = None) -> "SearchWorld":
        return SearchWorld(execute)

    def hands(self, execute):
        """These tools, as guest-agent commands run through the engine's own executor.

        `run_guest_command` IS THE ONE DOOR. Every Camoufox tool becomes a shell line inside a
        machine, and it gets there through the same `execute` a `create_vm` goes through — the
        legal filter, the commit gate, the contract tier, the watchdog. Nothing here holds a
        manager or a socket.

        A BROWSER'S MACHINE IS REMEMBERED FROM ITS LAUNCH, because the later tools do not carry
        one and should not have to. `camoufox_search` names a browser; the browser named a
        machine when it started; a process cannot move hosts. The manifest already says exactly
        this — `create_requires` on a RUNNING vm — so the lookup is reading back a fact the
        program has already established rather than guessing at one.
        """
        host_of: Dict[str, str] = {}

        def run_guest(vm: str, command: str):
            return execute("run_guest_command", {"name": vm, "command": command})

        def host_for(args: Dict[str, Any]) -> Optional[str]:
            args = args or {}
            # THE LAUNCH IS THE ONLY PLACE A MACHINE IS NAMED, so it is the only place the
            # binding can be recorded. `browser` on a search, `browser_name` on a close —
            # same identity, two argument names, because one is the member and the other is
            # a reference to it.
            vm = args.get("vm")
            browser = args.get("browser_name") or args.get("browser")
            if vm and browser:
                host_of[str(browser)] = str(vm)
            return vm or host_of.get(str(browser)) if browser else vm

        return guest_hands(run_guest, host_for=host_for)

    def claims(self, request: str) -> bool:
        words = {w.strip(".,!?;:'\"").lower() for w in request.split()}
        for kind, spec in (self.manifest or {}).items():
            nouns = {kind, *(spec.get("nouns") or ())}
            if nouns & words or {n + "s" for n in nouns} & words:
                return True
        return bool({"web", "google", "internet", "browse", "find"} & words)


def guest_hands(run_guest, host_for=None, say=None):
    """An `execute` that turns this package's tools into guest-agent commands.

    `run_guest(vm_name, command) -> result` is the ENGINE'S — one door, not two. A package
    never holds an executor of its own, so what "running a search" means is decided by
    whoever loaded it, and this function is only the translation.

    THE ANSWER COMES BACK AS A FINDING, not as a return value nobody looked at. `camoufox_read`
    is the observer the manifest names, so its output is what the ledger records and what
    PUBLISH later carries to the operator.
    """
    def execute(tool: str, args: Dict[str, Any]):
        command = guest_command(tool, args)
        if command is None:
            return {"success": False, "error": f"{tool} is not a Camoufox tool"}
        vm = (args or {}).get("vm_name") or (host_for(args) if host_for else None)
        if not vm:
            # A GUEST TOOL WITH NO GUEST is a program that got the order wrong, and saying so
            # is more useful than running it somewhere arbitrary.
            return {"success": False,
                    "error": f"{tool} needs a machine to run in, and none was named"}
        if say:
            say(vm, command)
        out = run_guest(vm, command) or {}
        if tool == "camoufox_read" and out.get("success"):
            # WHATEVER THE BROWSER SAID, parsed if it is JSON and kept whole if it is not.
            # A reader that dropped unparseable output would lose the error message that
            # explains the run.
            raw = out.get("stdout") or out.get("output") or ""
            try:
                out["answer"] = json.loads(raw).get("answer", raw)
            except Exception:
                out["answer"] = raw.strip()
        return out
    return execute
