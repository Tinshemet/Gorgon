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

# ⇒ THE UNITS THE STORE CAN HOLD, spelled in English. `procedures._SECONDS` is the authority
#   for which four exist; a fifth here would be a schedule nobody could file.
UNITS = frozenset({"second", "seconds", "minute", "minutes", "hour", "hours",
                   "day", "days"})

# ⇒ AND THE UNITS THE OPERATOR USES THAT THE STORE DOES NOT NAME. A night is a day and a week
#   is seven of them — both are expressible as a span, so both are admitted; a MONTH is not
#   (they differ in length), and it is deliberately absent rather than rounded.
COARSE = frozenset({"night", "nights", "week", "weeks"})

# ⇒ THE FREQUENCY ADVERBS — a unit and a recurrence folded into one word. Closed, and derived:
#   each one is a unit above with `-ly` on it, which is why the set cannot drift from `UNITS`.
FREQUENCY = frozenset({"hourly", "daily", "nightly", "weekly"})

# ⇒ THE DEICTICS — time named relative to now. English has these and has never added one.
#   ⇒ ⚠ `now` AND `currently` ARE NOT HERE, AND THAT IS THE WHOLE POINT OF THE CLASS. They fix
#     the time as THIS MOMENT, which is the one time that is not a schedule — *"launch every vm
#     that is CURRENTLY stopped"* is rung 5 and runs now, correctly.
DEICTIC = frozenset({"tomorrow", "tonight", "yesterday", "overnight"})

# ⇒ THE CALENDAR. Seven and twelve, and neither list grows.
WEEKDAYS = frozenset({"monday", "tuesday", "wednesday", "thursday",
                      "friday", "saturday", "sunday"})
MONTHS = frozenset({"january", "february", "march", "april", "may", "june", "july",
                    "august", "september", "october", "november", "december"})

# ⇒ A CLOCK TIME IS A SHAPE, NOT A WORD — `9pm`, `09:30`, `9:30am`. Read structurally, so no
#   vocabulary is spent on it and every spelling is covered.
CLOCK = re.compile(r"^(?:[0-2]?\d[:.][0-5]\d(?:am|pm)?|[0-2]?\d(?:am|pm))$")

# ⇒ WHAT MAKES A TIME A RECURRENCE RATHER THAN AN INSTANT. `every` is `scan.UNIVERSAL`'s own
#   word doing a second job — over OCCASIONS instead of over members — and `each` behaves the
#   same way. The distinction is not in the word; it is in what follows it.
RECURRING = frozenset({"every", "each"})

# ── the world ────────────────────────────────────────────────────────────────────────

# ⇒⇒ THE EVENT SUBORDINATORS — the words that say *something happening starts this*. Closed,
#   and this is the half the operator called the meta-declaration: *"the rule is 'delete vm'
#   triggered by 'stop vm/being done with it'."*
#
#   ⇒ ⚠ **`when` IS ABSENT FROM THE SET AND HANDLED SEPARATELY, BECAUSE IT IS TWO WORDS.**
#     *"WHEN did you stop it"* asks about the past and *"WHEN you get a chance"* is an adjunct
#     — a distinction that already cost this project a defect on 2026-08-16, in the other
#     direction. Inversion is what separates them, and `events_in` asks for a subject.
EVENTS = frozenset({"after", "whenever", "once"})
EVENT_PHRASES = ("every time", "each time", "as soon as", "any time")

# ⇒⇒ **AND SOME OF THEM ARE STANDING BY THEMSELVES AND SOME ARE NOT**, which is the difference
#   between a trigger and a one-off ordering nothing can hold. `whenever` and `every time` mean
#   EVERY occasion in the word; `after` and `once` do not — *"delete the vm after it stops"* is
#   about that machine, this once.
ALWAYS_STANDING = frozenset({"whenever"})
ALWAYS_STANDING_PHRASES = ("every time", "each time", "any time")

# ⇒ THE STANDING FRAME. A trigger is a RULE plus an event; this is the phrase that makes a
#   sentence standing when no modal or frequency adverb does it. The operator's own example
#   opens with it.
STANDING = ("from now on", "from here on", "going forward", "in future", "in the future")

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
