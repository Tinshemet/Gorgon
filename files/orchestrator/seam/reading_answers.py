"""reading_answers.py — AN OPERATOR'S ANSWER IS ENGLISH TOO, AND IT GETS THE SAME LADDER.

⇒⇒ **THE FIRST VERSION SCANNED FOR A KIND NAME AND WAS WRONG THREE TIMES IN SEVEN.**

The operator, 2026-08-13: *"the same way that we use the AI to filter the prompt we can use [it]
on the user answer to determine if the data supplied from the user can resolve the conflict."*
Measured on the spot, against a substring scan over kind names and manifest nouns:

    'a grubnash is a vm'                        -> vm     ok
    'a grubnash is NOT a vm'                    -> vm     WRONG — negation ignored
    'a grubnash is like a machine but smaller'  -> vm     WRONG — a simile read as identity
    'a vm or a network'                         -> vm     WRONG — ambiguous, must decline
    'anything with an ip address'               -> none   (the operator's OWN answer, day one)

**A REQUEST GETS ANCHOR-AND-SCAN AND AN ANSWER GOT `in`.** Same language, half the care.

⇒ **THE LADDER, AND THE ORDER IS THE POINT — the same one pass 1 uses.** Compute what can be
  computed; ask only what cannot:

    1  READ the closed markers     `not` / `like` are FUNCTION WORDS — a closed class, finite
                                   and stable, which is the only kind of word list that survives
                                   ([[gorgon-six-iterations]]: never write down what the model
                                   knows better; do write down what it cannot know). They come
                                   FIRST because they are about POLARITY, and pass 1 reads what a
                                   phrase refers to, not whether it is being affirmed.
    2  RUN PASS 1 OVER THE ANSWER  the same reader the request gets. What comes back is DATA —
                                   the set of kinds the manifest and the lab could settle.
    3  COUNT                       exactly one settles it; several is AMBIGUOUS and the operator
                                   must choose; none is honest and asks again.

⇒ **A SECOND READER WAS WRITTEN AND DELETED THE SAME HOUR.** The first cut asked the model its
  own closed-enum question — a private copy of what pass 1 already does, and therefore a second
  answer to one question in the exact shape this project has filed fourteen times. Pass 1 IS the
  reading step; there is nothing left for a bespoke call to add.

⇒ **AND NOTHING HERE GROUNDS THE ANSWER.** The operator, same conversation: *"we can't really
  ground what the user response is."* True — this decides whether an answer NAMES A KIND, never
  whether it is true. Truth is the world's to say, which is why the answer settler runs last and
  never overrides a lookup.
"""
from typing import List, Optional, Tuple

from planner.formula.legal import Board

# ⇒ CLOSED FUNCTION-WORD CLASSES, and that is why they may be written down at all. Negation and
#   comparison are grammar: finite, stable, and the same for every speaker. A list of NOUNS that
#   might mean `vm` would be the other kind of list, the kind that rots.
NEGATION = {"not", "isn't", "isnt", "no", "nope", "nah", "never", "neither",
            "nor", "n't", "don't", "dont"}
SIMILE = {"like", "similar", "resembles", "sort", "kind"}   # "like a vm", "sort of like a vm"

AMBIGUOUS, NONE_NAMED, NEGATED, LIKENED = "ambiguous", "none", "negated", "likened"
UNCLEAR = "unclear"

# ⇒ AFFIRMATION IS A CLOSED CLASS TOO, and that is the whole licence for writing it down. These
#   are the particles English uses to agree; a list of VERBS meaning "go ahead" would be the
#   other kind of list, and would rot.
AFFIRMATION = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "aye", "please", "do", "y"}


def yes_no(said: str) -> Optional[bool]:
    """True / False / None — and None is a real answer, not a default.

    ⇒⇒ **AN UNREADABLE YES IS NOT A NO.** *"should it be created?"* answered with *"whatever you
      think"* has no reading, and guessing either way is worse than asking again: guessing NO
      strands a request the operator wanted, and guessing YES BUILDS SOMETHING NOBODY ASKED FOR.
      The second is the one that costs money and machines, which is why this declines instead.

    ⇒ NEGATION IS CHECKED FIRST. *"no, don't create it"* holds both a negation and an
      affirmation-shaped word, and the denial is the operative half — the same ordering
      `settle` uses for a kind answer, and for the same reason.
    """
    words = {w.strip(".,;:!'\"()") for w in str(said).lower().split()}
    if words & NEGATION:
        return False
    if words & AFFIRMATION:
        return True
    return None


def kinds_named(said: str, board: Board, world=None, model=None, timeout: int = 300
                ) -> List[str]:
    """Every kind this answer names — READ BY PASS 1, not scanned for.

    ⇒⇒ **THE SAME PIPELINE, TO EXTRACT DATA RATHER THAN BUILD A PROPOSAL.** The operator,
      2026-08-13: *"the same gates, the same pipeline, but this time to extract data not to build
      a proposal."* An answer is English; the project already has a reader for English, and it
      took a full month to get right. A second one — the substring scan this replaced — is a
      second answer to a question `run_scanned` already answers, and it was wrong three times in
      seven on ordinary phrasing.

    ⇒ WHAT COMES BACK IS DATA, NOT A PROGRAM. Pass 1 declares rows and the manifest settles the
      kinds it can; the SET OF SETTLED KINDS is the extraction. Nothing is proposed, nothing is
      run, no operation is ever built — the same machinery pointed at a different question.

    ⇒ AND IT INHERITS THE LADDER FOR FREE: the manifest settles what it can, the LAB settles what
      it can, and a word neither reaches stays kindless — which is the honest answer for
      *"anything with an ip address"* until the Encyclopedia can say otherwise.
    """
    from . import pass1
    rows = pass1.run_scanned(str(said), board=board, model=model, timeout=timeout)
    rows = pass1.settle_with_world(rows, world, board)
    return sorted({r.object_type for r in rows
                   if r.object_type and r.object_type != pass1.UNKNOWN_KIND})


def settle(said: str, board: Board, world=None, model=None, timeout: int = 300
           ) -> Tuple[Optional[str], Optional[str]]:
    """(kind, why-not) — the kind this answer names, or None with the reason it did not settle.

    The reason is returned rather than logged because the OPERATOR is owed it: a clarification
    that quietly fails to take will be re-asked forever with no clue why.
    """
    words = {w.strip(".,;:'\"()") for w in str(said).lower().split()}

    # ⇒ THE TWO GUARDS RUN BEFORE THE READER, because they are about POLARITY and pass 1 reads
    #   what a phrase REFERS TO, not whether it is being affirmed. Both are closed function-word
    #   classes — grammar, finite, the same for every speaker — which is the one kind of word
    #   list that survives ([[gorgon-six-iterations]]).
    if words & NEGATION:
        return None, NEGATED            # *"a grubnash is not a vm"* says what it ISN'T
    if words & SIMILE:
        return None, LIKENED            # *"like a machine but smaller"* is description, not identity

    found = kinds_named(said, board, world, model, timeout)
    if len(found) == 1:
        return found[0], None
    if len(found) > 1:
        return None, AMBIGUOUS          # *"a vm or a network"* — the operator must choose
    return None, NONE_NAMED
