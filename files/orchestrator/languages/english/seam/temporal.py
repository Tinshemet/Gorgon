"""temporal.py — WHEN, AND WHAT STARTS IT. The clock half and the event half, read apart.

    "every night"        -> a RECURRENCE   the clock calls it, again and again
    "at 9pm"             -> an INSTANT     the clock calls it once
    "after a vm stops"   -> an EVENT       the world calls it

# ⇒⇒ WHY THIS EXISTS, AND WHY IT IS ONE FILE RATHER THAN TWO READERS

The operator, 2026-08-16: *"routine requires a temporal reference (date, time, hour, etc), and
trigger needs a meta-declaration, IE a rule."* And `routines.py` already says the same thing
from the store's side — a procedure, a routine and a trigger are ONE object with one extra
field, *"a difference that is entirely about WHO DECIDES TO START IT."*

**So the reading is one question with three answers**, and splitting it across two files would
put `every night` in one and `whenever a vm stops` in the other, when both are answering *when
does this run*.

⇒ ⚠ **AND IT IS DELIBERATELY IN THE SEAM RATHER THAN AT THE DOOR.** [[gorgon-linguistic-sweep]]
  lists the temporal qualifier as Part 2's, unbuilt — *"at 9pm, tomorrow, by nine PM — routines
  exist, unwired"*. A private time reader inside `door.py` would be the twin-owner defect this
  project has filed more than a dozen times, waiting for Part 2 to write the second one. This
  is the first owner; Part 2 extends it.

# ⇒⇒ THE MEASUREMENT THAT MADE IT URGENT — 2026-08-16, through the live door

    stop every vm at 9pm                     -> program    RAN NOW
    stop alpha tomorrow                      -> tool       RAN NOW
    take a snapshot of every vm every hour   -> program    RAN NOW, and forever unset

**A request whose whole point is WHEN, carried out at the wrong when, is a false serve that
reads as a success.** That is why `ROUTINE -> TOOL` and `ROUTINE -> PROGRAM` are keyed CRITICAL.

# ⇒⇒ THE LICENCE FOR WRITING THESE WORDS DOWN, WHICH IS NOT THE USUAL ONE AND IS NARROWER

Everywhere else this seam reads closed classes — nine wh-words, the auxiliaries that invert, two
frequency adverbs. **Time vocabulary is bigger than any of those and it is still closed**: the
units are the ones the STORE can hold, the deictics are a handful English has never added to,
and the calendar names are seven and twelve. Nothing anyone says tomorrow adds a day of the week.

⇒ **AND THE UNITS ARE NOT INVENTED HERE — THEY ARE THE STORE'S.** `procedures._SECONDS` declares
  `s · m · h · d` and `_SPAN` parses `<n><unit>`; the English words below are those four spelled
  out, which makes this a fact about what Gorgon can HOLD rather than a fact about English.
  A unit with no field to go in would be a promise the store cannot keep.

⇒ ⚠ **WHAT IS NOT HERE, AND IS A GAP RATHER THAN AN OVERSIGHT.** `by nine PM`, `in an hour`,
  `next tuesday`, `the first of the month` — offsets, deadlines and dates. Reading them means
  RESOLVING them to a moment, which needs a clock and a calendar, and the store has no field
  for a one-off moment anyway (`every` recurs, `when` is a world predicate). **Detecting that a
  time is present is what the door needs; parsing it is what a schedule would need**, and only
  the first is claimed here.
"""
import re
from typing import Optional, Sequence, Tuple

# ── the clock ────────────────────────────────────────────────────────────────────────

from ..codex import UNITS

from ..codex import COARSE

from ..codex import FREQUENCY_ADVERBS as FREQUENCY

from ..codex import DEICTIC

from ..codex import WEEKDAYS
from ..codex import MONTHS

# ⇒ A CLOCK TIME IS A SHAPE, NOT A WORD — `9pm`, `09:30`, `9:30am`. Read structurally, so no
#   vocabulary is spent on it and every spelling is covered.
CLOCK = re.compile(r"^(?:[0-2]?\d[:.][0-5]\d(?:am|pm)?|[0-2]?\d(?:am|pm))$")

from ..codex import RECURRING

# ── the world ────────────────────────────────────────────────────────────────────────

from ..codex import EVENTS
from ..codex import EVENT_PHRASES

# ⇒⇒ **AND SOME OF THEM ARE STANDING BY THEMSELVES AND SOME ARE NOT**, which is the difference
#   between a trigger and a one-off ordering nothing can hold. `whenever` and `every time` mean
#   EVERY occasion in the word; `after` and `once` do not — *"delete the vm after it stops"* is
#   about that machine, this once.
ALWAYS_STANDING = frozenset({"whenever"})
from ..codex import ALWAYS_STANDING_PHRASES

from ..codex import STANDING

RECURRENCE, INSTANT, EVENT = "recurrence", "instant", "event"


def _words(text: str) -> Tuple[str, ...]:
    """Tokens, with a number glued to a unit kept whole — `9pm` is one word, not nine and pm."""
    return tuple(re.findall(r"[a-z][a-z0-9_']*|[0-9]+[a-z:.]*[a-z0-9]*|[0-9]+",
                            str(text).lower()))


def clock_in(text: str) -> str:
    """RECURRENCE, INSTANT, or "" — does this name a time, and does it come round again?

    ⇒ **THE DISTINCTION IS WHAT THE STORE CAN HOLD.** `every: <span>` takes a recurrence and
      has no field for a one-off moment, so the two are told apart here rather than downstream
      where only one of them would fit.

    >>> clock_in("take a snapshot every night")
    'recurrence'
    >>> clock_in("stop every vm at 9pm")
    'instant'
    >>> clock_in("launch every vm that is currently stopped")
    ''
    """
    words = _words(text)
    if not words:
        return ""
    for i, w in enumerate(words):
        # ⇒⇒ **`every` IS ONLY A RECURRENCE WHEN A TIME FOLLOWS IT**, which is the entire
        #   difference between *"every night"* and *"every vm"*. `scan.UNIVERSAL` owns the
        #   other reading and neither has to know about the other — the word is the same and
        #   the noun decides, exactly as `the verb decides what the noun is` does one layer up.
        if w in RECURRING:
            tail = words[i + 1:i + 3]
            if any(t in UNITS or t in COARSE or t in WEEKDAYS for t in tail):
                return RECURRENCE
            # ⇒ `every 2 hours` — a number between the quantifier and its unit.
            if len(tail) > 1 and tail[0].isdigit() and (tail[1] in UNITS or tail[1] in COARSE):
                return RECURRENCE
        if w in FREQUENCY:
            return RECURRENCE
    for w in words:
        if w in DEICTIC or w in WEEKDAYS or w in MONTHS or CLOCK.match(w):
            return INSTANT
    return ""


def clock_tail(clause: str) -> Optional[str]:
    """The clock ADJUNCT with its own words, locatable — or None.

    ⇒ `clock_in` classifies but carries no offsets, so *"at 21:30"* scored as a missed
      trigger from the day the eval was born (qual-0005 — the slot was held open by
      design). Closed shapes only: `at` + CLOCK | N am/pm | noon | midnight. `at the
      door` names a PLACE and is refused by the same closed test.
    """
    import re as _re
    low = str(clause).lower()
    m = _re.search(r"\bat ((?:[0-2]?\d[:.][0-5]\d(?:\s?[ap]m)?)"
                   r"|(?:[0-2]?\d\s?[ap]m)|noon|midnight)\b", low)
    return m.group(0) if m else None


def events_in(text: str, speech_act=None) -> bool:
    """Does something HAPPENING start this? The world-called half.

    ⇒ ⚠ **`when` IS ADMITTED ONLY AS AN ADJUNCT**, never as the interrogative. *"when did you
      stop it"* is inverted over the addressee and asks about the past; *"when a vm stops"* has
      a subject and no inversion, and is a condition. The same pair cost a defect on 2026-08-16
      read the other way round, so the test is written from that finding rather than from the
      word.
    """
    low = f" {str(text).lower()} "
    if any(f" {p} " in low for p in EVENT_PHRASES):
        return True
    words = _words(text)
    for i, w in enumerate(words):
        if w in EVENTS:
            return True
        if w == "when" and i + 2 < len(words):
            # ⇒ A SUBJECT AFTER `when` MEANS AN ADJUNCT. The auxiliary test is the inversion
            #   one `speech_act` already makes; without that module we take the conservative
            #   reading and treat a bare `when` as interrogative.
            if speech_act is None:
                continue
            if words[i + 1] not in speech_act.AUXILIARIES:
                return True
    return False


def standing_in(text: str) -> bool:
    """Is this about EVERY future occasion rather than this one?

    ⇒ The phrase half only. A deontic modal or a frequency adverb says the same thing and
      `speech_act` owns both — `governing.rules_from` is what reads those, and a trigger asks
      that reader rather than repeating it here.
    """
    low = f" {str(text).lower()} "
    return any(f" {p} " in low for p in STANDING)


def standing_event(text: str) -> bool:
    """Does the event generalise over OCCASIONS, or name one that is about to happen?

    ⇒⇒ **A TRIGGER IS A RULE PLUS AN EVENT, AND THIS IS THE `RULE` HALF WHEN NO PHRASE SAYS SO.**
      The operator's example carries *"from now on"* and most real ones will not.

    ⇒ **TWO SIGNALS, BOTH ALREADY DECLARED.** Some subordinators mean every occasion in the word
      itself; for the rest, **the DETERMINER in the event clause decides**, which is
      `scan.INDEFINITE` doing the job it already does everywhere else:

          once A snapshot finishes, delete the old one   an indefinite -> ANY snapshot -> standing
          delete the vm after IT stops                   a pronoun     -> that one     -> once

    ⇒ ⚠ AND IT READS ONLY THE EVENT CLAUSE, not the sentence. *"whenever a vm stops, delete THE
      old snapshot"* has a definite in its main clause and is still standing — the determiner
      that matters is the one on the thing that HAPPENS.
    """
    from .scan import INDEFINITE

    low = f" {str(text).lower()} "
    if any(f" {p} " in low for p in ALWAYS_STANDING_PHRASES):
        return True
    words = _words(text)
    for i, w in enumerate(words):
        if w in ALWAYS_STANDING:
            return True
        if w in EVENTS or w == "when":
            # ⇒ THE EVENT CLAUSE RUNS TO THE NEXT BOUNDARY, and a comma is the one that
            #   matters — it is what separates the condition from the act in every one of
            #   these sentences.
            clause = []
            for x in words[i + 1:]:
                if x in ("then", "and"):
                    break
                clause.append(x)
            head = str(text).lower().split(",", 1)[0] if "," in str(text) else ""
            span = clause if not head else _words(head)[i + 1:] or clause
            if any(x in INDEFINITE for x in span):
                return True
    return False


def read(text: str, speech_act=None) -> Optional[str]:
    """RECURRENCE, INSTANT, EVENT, or None. **THE EVENT WINS, AND THE ORDER IS THE DESIGN.**

    *"from now on after you are done with a vm, delete it at 9pm"* is started by the world; the
    clock only says when the act happens once the world has started it. A routine that fires on
    a schedule and a trigger that fires on a state are different objects, and the thing that
    STARTS it is the one that decides which — the operator's own framing, and `routines.py`'s.
    """
    if events_in(text, speech_act):
        return EVENT
    return clock_in(text) or None


# ── the DEFERRED-TIME adjuncts — regions, for the walk to give back (08-25) ──────────────

_ADJUNCT = None


def adjunct_regions(text):
    """`in 10 minutes` · `for an hour` · `tomorrow morning` — a DELAY or a DATE riding an
    act. The store can hold them (deferred-time's own machinery); a THING cannot: a row
    that swallowed one gives it back, exactly as a reason clause is given back
    ([[reasons.py]]). Regions at offsets; the trigger reader stays the one owner of
    `at 9pm` / `every night`."""
    import re as _re
    global _ADJUNCT
    if _ADJUNCT is None:
        from ..codex import COARSE, UNITS
        unit = "|".join(sorted(set(UNITS) | set(COARSE), key=len, reverse=True))
        _ADJUNCT = _re.compile(
            r"\b(?:(?:in|within|after|for)\s+(?:a|an|\d+)\s+(?:%s)"
            r"|(?:tomorrow|today|tonight|yesterday)(?:\s+(?:morning|afternoon|evening"
            r"|night))?)\b" % unit)
    return [(m.start(), m.end()) for m in _ADJUNCT.finditer(str(text).lower())]


def strip_adjuncts(rows, request, board=None):
    """Subtractive on the rows: fully-inside rows vanish, overlapping rows are trimmed."""
    from . import schema as S
    regions = adjunct_regions(request)
    if not regions:
        return rows
    low = str(request).lower()
    out = []
    for row in rows:
        span = str(row.span or row.name)
        at = low.find(span.lower())
        if at < 0:
            out.append(row)
            continue
        s0, e0 = at, at + len(span)
        if any(rs <= s0 and e0 <= re_ for rs, re_ in regions):
            continue
        cut = min((rs for rs, re_ in regions if s0 < rs < e0), default=None)
        if cut is None:
            out.append(row)
            continue
        new = request[s0:cut].strip().rstrip(",;")
        if not new:
            continue
        out.append(S.declare_from(new, row.object_type, dict(row.where or {}),
                                  row.existence, board, references=list(row.references),
                                  count=row.count, comparator=row.comparator, span=new,
                                  identity=row.identity, sanctioned=row.sanctioned
                                  )._replace(excludes=row.excludes,
                                             unroutable=row.unroutable,
                                             mentions=row.mentions,
                                             assigned=row.assigned))
    return out
