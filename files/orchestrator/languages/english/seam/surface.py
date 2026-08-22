"""surface.py — WHAT THE OPERATOR IS TOLD, in the operator's words, in ONE place.

⇒⇒ **TWO KINDS OF THING REACH A PERSON, AND THEY ARE NOT THE SAME KIND OF THING.**

    A NOTICE   housekeeping. The AI did something beside what you asked, and it did not run.
               You are being TOLD. Nothing is waiting on you, and the verdict does not move.
    A FLAG     the AI wrote a call Gorgon will not run as it stands. You are being ASKED.
               Something IS waiting on you.

The operator, 2026-08-13, when both axes turned out to exist: *"I think all should be surfaced
to the user — all housekeeping should, and gate 4 bans [as] 'The AI created this call: <call>,
Gorgon flagged it for you, deny it? y/n, chat about it?'"*

⇒ **WHY THE TEXT LIVES HERE AND NOT AT EACH SITE.** It is going to be rendered twice — once by
  the bench's `main`, once by the chat when B2 lands — and a message formatted at each call site
  is two answers to one question, which is how the CLI and the chat came to disagree about
  everything else. `pipeline` decides WHAT to say; this decides HOW it reads.

⇒ **AND A FLAG OFFERS A CONVERSATION, NOT ONLY A VERDICT.** *"Deny it? y/n, chat about it?"* —
  because the operator is the one who knows whether a flagged call was the point of the request.
  A prompt with two answers makes them guess; three lets them ask.
"""
from typing import List, Optional

from .effects import Operation


def call_of(op: Operation) -> str:
    """One operation as a person would read it aloud."""
    inner = str(op.on) if op.value in (None, "") else f"{op.on}, {op.value}"
    return f"{op.operator}({inner})"


def flagged(op: Operation, why: str) -> str:
    """A call Gorgon will not run as it stands — the operator's to answer.

    ⇒ IT NAMES THE AUTHOR. *"The AI created this call"* is not blame, it is PROVENANCE: the
      operator did not write this and should not have to work out where it came from before
      deciding about it.
    """
    return (f"The AI created this call: {call_of(op)} — Gorgon flagged it for you: {why}. "
            f"Deny it? [y/n], or chat about it.")


def notices(suggested: List[Operation], discarded: List[Operation],
            conflicts: Optional[List[str]] = None) -> List[str]:
    """Housekeeping, surfaced. Never a question, and never a reason to hold the program.

    ⇒⇒ **SURFACED, NOT ASKED — AND THE DIFFERENCE IS THE VERDICT.** `_verdict` returns ASK the
      moment `asks` is non-empty, so routing housekeeping there would turn four of the fourteen
      rungs from SERVE into ASK for steps that never ran. That is the detector-makes-it-worse
      trap of 08-10 wearing a helpful costume: the operator asked to SEE these, not to be
      stopped by them.

    ⇒ THE TWO ARE DIFFERENT NEWS AND ARE WORDED AS SUCH. A SUGGESTION is something the AI
      would do and Gorgon can stand behind — an ops instinct, offered. A DISCARD is something
      the AI wrote that was neither asked for NOR legal; it is reported because *"I am fine
      with it existing as long as we treat it"*, and treating it starts with saying it happened.
    """
    out: List[str] = []
    for op in suggested or ():
        out.append(f"The AI would also do {call_of(op)} — nothing you asked for warrants it, "
                   f"so it was NOT run. Offered in case you want it.")
    for op in discarded or ():
        out.append(f"The AI wrote {call_of(op)} — nothing warrants it and it is not legal "
                   f"either, so it was dropped. Recorded so it is not silent.")
    # ⇒ AN ANSWER THAT DID NOT TAKE IS NEWS. Nothing here can check whether what you said is
    #   TRUE — but it can see that it conflicts, and a clarification that vanishes silently is
    #   worse than one that is refused out loud.
    for c in (conflicts or ()):
        out.append(f"Your answer was not applied: {c}.")
    return out
