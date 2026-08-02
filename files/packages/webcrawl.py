"""webcrawl.py — a MOCK PACKAGE, and the proof that a new capability is essentially an API.

A PACKAGE, NOT AN ENGINE, and the distinction is the safety property. Engines run the HOST —
Medusa, the executor, and whatever else the host genuinely needs. Packages run INSIDE a world
engine: crawling, vision, scanning. A crawler reaches the internet and parses whatever comes
back, which is the precise definition of a capability that must not have the host — and here
it cannot, not because a check refuses it but because a package is not a mountable thing.
There is no method by which it could be routed to.

Written to answer one question: what does it take to add a capability Gorgon has never had?
A manifest fragment and no changes anywhere else. This file imports nothing from the planner
and the planner imports nothing from it.

IT IS DELIBERATELY THE HARD CASE. A crawler that ran locally would prove only that a second
manifest parses. This one runs inside virtual machines through their guest agents, which is
how one would really build it — the machines are already isolated, already disposable,
already fingerprinted the way an operator wants them. So the contract has to survive a
capability whose kinds are its own but whose HANDS belong to somebody else.

WHAT MAKES THAT WORK is that execution is the ENGINE'S. The package names the tools it needs
and the loading engine decides what running them means: here a stub, in production the QEMU
engine's guarded executor with `run_guest_command`. The package never learns which, and never
holds an executor of its own — one door, not two.

MOCK MEANS THE BACKEND IS FAKE, NOT THE INTERFACE. Everything except `CrawlWorld.execute` is
exactly what a real crawl package would ship.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .base import Package

# THE ENTIRE REGISTRATION. Two kinds, five tools, and the postconditions are DERIVED — the
# writer works out that a crawl must exist before a page can belong to it, that a page is
# fetched after creation while its crawl is fixed at creation, and in what order to do any of
# it. None of that is written here.
MANIFEST: Dict[str, Any] = {
    "crawl": {
        "key": "crawl_name",
        "attrs": ["crawl_name", "seed", "status", "runner"],
        "nouns": ["crawl", "scrape", "sweep"],
        "create": "start_crawl",
        "delete": "abandon_crawl",
        "create_args": {"seed": "from_url"},
        "attr_values": {"status": ["running", "finished"]},
        "setters": {
            "finish_crawl": {"attr": "status", "member_arg": "crawl_name",
                             "value": "finished"},
            # `refs` is what tells the writer that a runner names a MACHINE — which is how a
            # crawl comes to depend on a vm existing without anybody stating the dependency.
            "assign_runner": {"attr": "runner", "member_arg": "crawl_name",
                              "value_arg": "vm_name", "refs": "vm"},
        },
    },
    "page": {
        "key": "url",
        "attrs": ["url", "crawl", "fetched"],
        "nouns": ["page", "document", "url"],
        "create": "record_page",
        "create_args": {"crawl": "in_crawl"},
        "attr_values": {"fetched": ["yes", "no"]},
        "create_defaults": {"fetched": "no"},
        "setters": {"fetch_page": {"attr": "fetched", "member_arg": "url", "value": "yes"}},
        # OBSERVED, so a reader must ASK. Whether a page actually answered is a FINDING and
        # never an inference from a tool's success flag — the same rule that stops a program
        # claiming reachability it never probed (decision 6). A crawler that trusted its own
        # success flags is exactly the crawler that reports 400 pages and delivers 12.
        "observed": {"reachable": {"fact": "reachable({url})", "by": "probe_page",
                                   "doc": "whether the page answered when asked"}},
    },
}


class CrawlWorld:
    """State plus the two questions. A mock backend behind a real interface.

    The dict IS the mock. Swap this class for one whose `execute` shells into a VM's guest
    agent and nothing above it changes — not the manifest, not the writer, not the
    orchestrator.
    """

    def __init__(self, execute: Optional[Callable] = None):
        self.kinds = MANIFEST
        self.state: Dict[str, Dict[str, Dict[str, Any]]] = {"crawl": {}, "page": {}}
        self.findings: Dict[str, Any] = {}
        self._execute = execute

    @property
    def seams(self):
        from planner.model_world import seams as _generic
        return _generic(self)

    def names(self) -> set:
        return {n for rows in self.state.values() for n in rows}

    def execute(self, tool: str, args: Dict[str, Any]):
        """Hand the call to whoever owns the hands, or run the mock.

        THE INJECTION IS THE POINT. In production this delegates to the QEMU engine's guarded
        executor, so a crawl's work reaches the world through the same gauntlet a VM
        operation does — one door, not two. The engine cannot tell the difference and must
        not be able to.
        """
        if self._execute is not None:
            return self._execute(tool, args)
        from planner.model_world import World
        proxy = World(MANIFEST)
        proxy.state = self.state
        return proxy.execute(tool, args)


class WebCrawlPackage(Package):
    """Crawl the web from inside disposable machines."""

    name = "webcrawl"
    description = ("crawl or scrape web pages from inside a virtual machine, and record "
                   "which pages answered")
    runs_in = "guest"

    @property
    def manifest(self) -> Dict[str, Any]:
        return MANIFEST

    def world(self, execute: Optional[Callable] = None) -> "CrawlWorld":
        """A world to plan against. Handed to an engine, which owns execution."""
        return CrawlWorld(execute)

    def claims(self, request: str) -> bool:
        words = {w.strip(".,!?;:'\"").lower() for w in request.split()}
        for kind, spec in (self.manifest or {}).items():
            nouns = {kind, *(spec.get("nouns") or ())}
            if nouns & words or {n + "s" for n in nouns} & words:
                return True
        return bool({"crawl", "scrape", "web", "site", "website"} & words)
