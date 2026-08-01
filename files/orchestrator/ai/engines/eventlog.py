"""eventlog.py — every interaction, in one line each, in the order they happened.

    <timestamp>  <txn>  <filed by>  <caught by>  <what was executed>  <description>

WHY A LEDGER AND NOT A LOG. `session.log` was a list of sentences, which is fine for reading
and useless for auditing: it cannot answer "who asked whom", "what actually ran", or "which
of these two components was wrong". An event names BOTH ENDS of every interaction, so a wrong
result can be walked back to the exchange that produced it rather than inferred from prose.

FILED BY / CAUGHT BY IS THE POINT. Every line in this system is one component saying something
to another — the operator to the orchestrator, the orchestrator to the extractor, an engine to
the orchestrator, a program to the world. Recording only the message loses which direction it
went, and direction is what separates "the engine asked to escalate" from "the orchestrator
granted an escalation".

IT RECORDS FAILURES AS FIRST-CLASS EVENTS, not as absences. A refusal, a promotion declined, a
tool that returned an error and a leaf that would not emit are all things that HAPPENED, and a
ledger that only records successes is a ledger you cannot debug from.

TRANSACTION IDS ARE PER-SESSION AND MONOTONIC. They are for pointing at a line while talking
about it, which is the whole reason event viewers number things.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

# The components that can file or catch. Not enforced — a new engine names itself and that is
# correct — but written down so the common ones stay spelled one way.
OPERATOR = "operator"
ORCHESTRATOR = "orchestrator"
REGISTRY = "registry"
CHANNEL = "channel"
WRITER = "writer"
WORLD = "world"


class Event:
    """One interaction. Immutable by convention — a ledger that gets edited is a story."""

    __slots__ = ("seq", "ts", "filed_by", "caught_by", "executed", "note", "level", "data")

    def __init__(self, seq: int, filed_by: str, caught_by: str, executed: str,
                 note: str = "", level: str = "info", data: Any = None,
                 ts: Optional[float] = None):
        self.seq = seq
        self.ts = time.time() if ts is None else ts
        self.filed_by = filed_by
        self.caught_by = caught_by
        self.executed = executed
        self.note = note
        # info / warn / error — so a reader can find the interesting lines without reading
        # every line, which is the only reason severity exists anywhere.
        self.level = level
        # ANYTHING TOO BIG FOR A LINE lives here and is never rendered inline: a whole Medusa
        # program, a raw model answer, a tool's full result. The line stays scannable and the
        # evidence stays attached.
        self.data = data

    def line(self, widths=(24, 6, 13, 13, 34)) -> str:
        t = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.ts))
        t += f".{int((self.ts % 1) * 1000):03d}"
        mark = {"info": " ", "warn": "!", "error": "X"}.get(self.level, " ")
        w = widths
        did = self.executed if self.executed and self.executed != self.note else "·"
        return (f"{t:<{w[0]}} {self.seq:0{w[1]}d} {mark} "
                f"{self.filed_by:<{w[2]}.{w[2]}} {self.caught_by:<{w[3]}.{w[3]}} "
                f"{did:<{w[4]}.{w[4]}} {self.note}")

    def as_dict(self) -> Dict[str, Any]:
        return {"seq": self.seq, "ts": self.ts, "filed_by": self.filed_by,
                "caught_by": self.caught_by, "executed": self.executed,
                "note": self.note, "level": self.level, "data": self.data}


class EventLog:
    """The ledger for one request. Append-only."""

    def __init__(self, request: str = ""):
        self.request = request
        self.events: List[Event] = []
        self._seq = 0
        # EVERY PROGRAM THIS REQUEST PRODUCED, in order. A rerouted request can produce more
        # than one, and showing only the last would hide the attempt that explains the
        # reroute.
        self.programs: List = []

    def file(self, filed_by: str, caught_by: str, executed: str, note: str = "",
             level: str = "info", data: Any = None) -> Event:
        self._seq += 1
        ev = Event(self._seq, filed_by, caught_by, executed, note, level, data)
        self.events.append(ev)
        return ev

    # ── reading it back ───────────────────────────────────────────────────────────────
    def render(self, show_data: bool = False) -> str:
        head = (f"{'TIMESTAMP':<24} {'TXN':<6}   {'FILED BY':<13} {'CAUGHT BY':<13} "
                f"{'EXECUTED':<34} DESCRIPTION")
        lines = [f"REQUEST: {self.request!r}", "", head, "-" * len(head)]
        for ev in self.events:
            lines.append(ev.line())
            if show_data and ev.data is not None:
                body = ev.data if isinstance(ev.data, str) else json.dumps(ev.data,
                                                                          default=str)
                for extra in str(body).splitlines():
                    lines.append(f"{'':<24} {'':<6}   |  {extra}")

        bad = self.failures()
        if bad:
            lines += ["", f"{len(bad)} EVENT(S) NEEDING A READER:"]
            lines += [f"  {e.seq:06d}  {e.note}" for e in bad]

        # THE PROGRAM GOES AT THE END, IN FULL. It is the artifact the whole ledger exists
        # to explain — every line above is either a decision that shaped it or a call it
        # made — and it is the one thing you cannot reconstruct from the lines. Truncating
        # it into an `EXECUTED` column would make the ledger tidy and useless.
        for label, text in self.programs:
            lines += ["", f"THE MEDUSA PROGRAM ({label}):"]
            lines += [f"  {ln}" for ln in (text or "").splitlines()] or ["  (empty)"]
        return "\n".join(lines)

    def jsonl(self) -> str:
        """One JSON object per line — for anything that wants to read this with a program."""
        return "\n".join(json.dumps(e.as_dict(), default=str) for e in self.events)

    def program(self, label: str, rendered: str) -> None:
        """Attach a program to the ledger. Shown in full at the end, never inline."""
        self.programs.append((label, rendered))

    def failures(self) -> List[Event]:
        return [e for e in self.events if e.level in ("warn", "error")]

    def __len__(self) -> int:
        return len(self.events)
