"""packages — capabilities that run INSIDE a world engine, never on the host.

    ENGINE   host-level, MOUNTED, routed to.  Medusa, the executor, anything the host needs.
    PACKAGE  in-world, LOADED by an engine, never mounted and never routed to.

The boundary is structural: a package has no mount method, so a capability that reaches the
internet cannot get the host — not because something refuses it, but because it is not that
kind of object.

THERE ARE NO PACKAGES RIGHT NOW. `camoufox` and `webcrawl` were deleted on 2026-08-02 — the
operator is reworking what a package is, and `webcrawler/` and `git/` are the empty folders
the rework lands in. What survives is the CONTRACT (`base.py`), because that is what a
reworked package will implement rather than one of the things being replaced.

CONSEQUENCES, SO NOBODY REDISCOVERS THEM. `rig._packages()` already degraded to `()` on
ImportError and now takes that path, so no kinds join the manifest: `browser` and `search`
are gone from the schema, the writer cannot plan a search, and a stored program naming
`camoufox_launch` no longer parses. `~/.gorgon/procedures/webcrawler.medusa` is in exactly
that state — it reads back as a ParseError, which is what `LIBRARY.verify` now says out loud.
"""
from .base import Package, merge          # noqa: F401
