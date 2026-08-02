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
import os
import re
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

    # THE COLUMNS, ONCE. The rendered ledger and the CSV are the same six fields in the same
    # order, so a reader who learned one has learned the other — plus `value`, which the line
    # form cannot carry.
    COLUMNS = ("timestamp", "txn", "level", "filed_by", "caught_by", "executed",
               "description", "value")

    def csv(self) -> str:
        """The ledger as CSV, with EVERY PUBLISHED VALUE IN FULL.

        WHY A SEVENTH COLUMN. The line form truncates — `claim: answer(the diameter of the
        earth) = 12,742 km mean (12,7...` — because a column has to fit on a screen. That is
        right for reading and wrong for keeping: the published value IS the answer, and a log
        that abbreviates the answer is a log of everything except the point.
        `data` already carries it whole; this is the first reader that says so.

        NOT ONLY PUBLICATIONS. Any event carrying `data` — a raw model answer, a tool's full
        result — puts it here, because deciding which evidence is worth keeping is the
        judgement that loses the evidence you needed.

        JSON-ENCODED WHEN IT IS NOT A STRING, so a dict stays machine-readable in a
        spreadsheet cell rather than becoming Python's repr, which nothing can parse back.

        `csv.writer` DOES THE QUOTING. A published answer is arbitrary text a browser
        returned — it contains commas, quotes and newlines — and hand-joining fields is how
        a log becomes unparseable exactly when something interesting happened.
        """
        import csv as _csv
        import io

        out = io.StringIO()
        w = _csv.writer(out, lineterminator="\n")
        w.writerow(self.COLUMNS)
        for ev in self.events:
            t = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ev.ts))
            t += f".{int((ev.ts % 1) * 1000):03d}"
            if ev.data is None:
                value = ""
            elif isinstance(ev.data, str):
                value = ev.data
            else:
                value = json.dumps(ev.data, default=str)
            w.writerow([t, f"{ev.seq:06d}", ev.level, ev.filed_by, ev.caught_by,
                        ev.executed, ev.note, value])
        return out.getvalue()

    def program(self, label: str, rendered: str) -> None:
        """Attach a program to the ledger. Shown in full at the end, never inline."""
        self.programs.append((label, rendered))

    def failures(self) -> List[Event]:
        return [e for e in self.events if e.level in ("warn", "error")]

    # ── keeping it, without being asked ───────────────────────────────────────────────
    def save(self, at: Optional[str] = None) -> Optional[str]:
        """Write this run's ledger to disk. Returns the CSV path, or None if it could not.

        AUTOMATIC, BECAUSE A LOG YOU HAVE TO REMEMBER TO ASK FOR IS A LOG OF THE RUNS YOU
        EXPECTED TO GO WRONG. Every interesting failure this week was found by reading a
        ledger after the fact, and the ones I lost were the ones nobody captured.

        ONE FILE PER RUN, which the operator asked for explicitly after a document that
        merged two separate tests read as one continuous story. The name carries the clock
        time and a slug of the request, so a directory listing is already an index.

        THREE FORMS, same run: `.csv` to read and pivot, `.jsonl` for anything reading it
        with a program, `.medusa` for the program itself — the artifact the ledger exists to
        explain, and the one thing that cannot be reconstructed from the lines.

        IT NEVER RAISES. A log that can break the run it is logging is worse than no log;
        the path comes back as None and the work carries on.

        WRITE-ONCE AND READ-ONLY, BECAUSE THIS IS THE OPERATOR'S GROUND TRUTH ABOUT ME.
        *"I want you to add it where there is no way for you to touch it, it's my grounding
        for you."* So: a file is never overwritten — an existing name takes a suffix rather
        than a replacement — and every file is chmod 0444 the moment it is closed. The run
        that produced a record cannot revise it, and neither can the next one.

        WHAT THIS DOES NOT DO, said plainly rather than implied: it is not a sandbox. Any
        process with the operator's permissions, including me, can `chmod` it back. It makes
        overwriting an ACT — deliberate, separate, and visible in a shell history — instead
        of something a stray `open(path, "w")` does silently. Real enforcement is
        `sudo chattr +a` on the directory, which only the operator can set and which the
        kernel then holds against everything, this code included.
        """
        try:
            base = at or os.path.join(
                os.environ.get("GORGON_HOME") or os.path.expanduser("~/.gorgon"), "logs")
            os.makedirs(base, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", (self.request or "run").lower()).strip("-")
            stem = time.strftime("%Y-%m-%dT%H-%M-%S", time.localtime()) + "_" + (slug[:48] or "run")
            # NEVER CLOBBER. Two runs inside one second, or a rerun of the same request, get
            # their own file — the second must not quietly become the only record.
            n, base_stem = 1, stem
            while os.path.exists(os.path.join(base, stem + ".csv")):
                n += 1
                stem = f"{base_stem}-{n}"

            def keep(suffix: str, body: str) -> str:
                path = os.path.join(base, stem + suffix)
                with open(path, "w") as fh:
                    fh.write(body)
                os.chmod(path, 0o444)
                return path

            csv_at = keep(".csv", self.csv())
            keep(".jsonl", self.jsonl() + "\n")
            if self.programs:
                keep(".medusa", "".join(f"-- {label}\n{(text or '').rstrip()}\n\n"
                                        for label, text in self.programs))
            return csv_at
        except Exception:
            return None

    def __len__(self) -> int:
        return len(self.events)
