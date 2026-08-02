"""packages — capabilities that run INSIDE a world engine, never on the host.

    ENGINE   host-level, MOUNTED, routed to.  Medusa, the executor, anything the host needs.
    PACKAGE  in-world, LOADED by an engine, never mounted and never routed to.

The boundary is structural: a package has no mount method, so a capability that reaches the
internet cannot get the host — not because something refuses it, but because it is not that
kind of object.
"""
from .base import Package, merge          # noqa: F401
from .webcrawl import WebCrawlPackage     # noqa: F401
