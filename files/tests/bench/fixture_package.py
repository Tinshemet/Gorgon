"""fixture_package.py — a minimal PACKAGE, for the tests that are about the CONTRACT.

WHY THIS EXISTS. The suite's package tests — a package is not mountable, has no `run`, is
never routed to, and its kinds join the loading engine's manifest — were all written against
`WebCrawlPackage`. Those properties are about what a PACKAGE IS, not about crawling, so the
coupling was wrong before it was inconvenient: when `camoufox` and `webcrawl` were deleted on
2026-08-02 for a rework, the host-boundary guarantee lost its test along with them.

SO THE CONTRACT IS TESTED AGAINST A PACKAGE THAT EXISTS ONLY TO BE ONE. It declares two
kinds and one tool, and its `hands` routes that tool through `run_guest_command` — which is
the shape every real package has had, and the half that was missing the day a machine was
created and launched for a browser that could never start.

IT IS NOT A REPLACEMENT FOR A REAL PACKAGE and must not grow into one. Anything that needs
to assert what CRAWLING does belongs with the crawler; this asserts only what LOADING does.
"""
from typing import Any, Dict

from packages.base import Package

# SHAPED LIKE A REAL ONE: a thing that is started and a thing that is recorded against it,
# so `create_requires` has something to order and the writer has a chain to plan rather
# than a single call.
_MANIFEST: Dict[str, Any] = {
    "crawl": {"package": "guest", "key": "crawl_name",
              "attrs": ["crawl_name"], "nouns": ["crawl"],
              "create": "start_crawl", "delete": "finish_crawl",
              "creators": {"create": {"tool": "start_crawl", "key": "crawl_name"}}},
    "page": {"package": "guest", "key": "page_name",
             "attrs": ["page_name", "crawl"], "nouns": ["page"],
             "create": "record_page",
             "creators": {"create": {"tool": "record_page", "key": "page_name"}},
             "create_requires": [{"kind": "crawl"}]},
}


class GuestPackage(Package):
    """Two kinds and one tool, running inside a machine the engine provides."""

    name = "guest"
    description = "a capability that runs inside a machine"
    runs_in = "guest"

    @property
    def manifest(self) -> Dict[str, Any]:
        """The rows, and THE SAME OBJECTS EVERY TIME.

        `merge` refuses a kind defined twice and tells them apart BY IDENTITY (`is not`), so
        a property that rebuilt its rows on each read would collide with itself the moment
        anything asked twice — which reads as "two packages define `crawl`" and is a lie.
        A real package holds its manifest; this holds one too.
        """
        return _MANIFEST

    def claims(self, request: str) -> bool:
        return "crawl" in (request or "").lower()

    def world(self):
        """A world made of THIS PACKAGE'S KINDS ALONE.

        The engine that loads a package merges the kinds into its own; this is the other
        use, where the package IS the domain — which is how a capability gets exercised on
        its own before anything mounts it.
        """
        from planner.model_world import World
        return World(self.manifest)

    def hands(self, execute):
        """Its tools MEAN a guest command. `None` would mean "nameable but not runnable"."""
        def start_crawl(args):
            return execute("run_guest_command",
                           {"name": args.get("vm") or "guest1",
                            "command": f"crawler start {args.get('crawl_name')}"})

        def record_page(args):
            return execute("run_guest_command",
                           {"name": args.get("vm") or "guest1",
                            "command": f"crawler record {args.get('page_name')}"})

        return {"start_crawl": start_crawl, "record_page": record_page}
