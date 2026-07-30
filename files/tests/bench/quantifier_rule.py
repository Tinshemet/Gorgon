"""all/any/single/not decided by SHAPE, with no model call — or honestly declined.

THE OPERATOR'S RULE, 2026-07-30: *"'all X (attribute)' means a filtered group (any) while
'all X (object)' means all."* The same doctrine the language already runs on — compute the
fix where the answer is determined, rather than asking a model and hoping. `derive()` does
it for arithmetic; this does it for cardinality.

IT ANSWERS OR IT DEFERS, NEVER GUESSES. `None` means "no rule applies", and the caller
falls back to the router. That is the whole safety property: a wrong deterministic answer
would narrow the schema and make a correct program UNREPRESENTABLE, which is far worse than
a missing one. So every branch below fires on a shape that is actually present in the
clause, and anything unrecognised falls through.

THE THREE SHAPES, in the order they are tested and the order matters:

  1. AN EXCLUSION MARKER WINS OUTRIGHT — "except db", "apart from golden". A whole is named
     and members are subtracted, which is `not` however the rest of the clause reads. Tested
     first because "every vm except golden" contains a universal quantifier too, and the
     universal branch would answer `all` and be wrong.
  2. A UNIVERSAL QUANTIFIER + A MODIFIER ON THE HEAD NOUN is `any`. "every RUNNING vm" and
     "all vms THAT ARE RUNNING" are the same clause written two ways; the condition may sit
     before the noun as an adjective or after it as a relative clause, and both are read.
     THE MODIFIER IS NOT MATCHED AGAINST THE MANIFEST'S VOCABULARY, deliberately: that
     vocabulary is five words ('running', 'stopped', and three booleans), so a value-driven
     test could not see `red` or `prod` at all and would miss rung 6's own clause. Any
     non-determiner word modifying the head noun is a filter.
  3. A UNIVERSAL QUANTIFIER WITH A BARE HEAD NOUN is `all`. "ping every vm".

WHAT IT DELIBERATELY WILL NOT TOUCH. `single` is never returned: one identified object is
recognised by naming, not by shape, and inventing a rule for it would be the guessing this
module exists to avoid. Clauses with no universal quantifier and no exclusion marker defer
— which covers every `single` in both corpora, and "any machine that isn't running", where
`any` is doing quantifier work this rule does not model.

THE HEAD NOUN MUST BE A KIND. "give them all the 'fleet' label" has a universal and a
quoted value, and its head is `label` — not a machine — so the rule defers rather than
reading the label as a filter on a set. That single restriction is what keeps shape 2 from
firing on the object of an action, which is the OTHER half of the operator's rule.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from orchestrator.ai.planner.ir import master

# A whole is named and members subtracted. `but not` is included because it is the spoken
# form of the same move; `without` is NOT — "a network without a name" is a description.
EXCLUSION = (" except", " apart from", " other than", " excluding", " but not", " besides")

UNIVERSAL = ("all", "every", "each")

# Words that carry no meaning between a quantifier and its noun.
DETERMINERS = {"the", "a", "an", "of", "its", "their", "our", "my", "them", "those", "these"}

# A relative clause reopening the noun phrase to add a condition.
RELATIVE = re.compile(r"^(that|which|who)\s+(is|are|was|were|do|does|not|isn't|aren't|"
                      r"doesn't|don't)\b")

# THE NOUNS THAT NAME A KIND come from `master`, which reads them from the manifest. This
# module used to carry its own set, and `route_rule` carried a second one that had already
# diverged — one knew `host` and `resource`, the other did not, on the day both were
# written. One lexicon or two routers eventually answer differently about the same word.
kind_nouns = master.kind_nouns


def _words(text: str) -> List[str]:
    return re.findall(r"[\w'-]+", text.lower())


def classify(text: str) -> Optional[str]:
    """`all`, `any`, `not`, or None when no rule applies. Never returns `single`."""
    lowered = " " + text.lower()
    if any(marker in lowered for marker in EXCLUSION):
        return "not"

    words, nouns = _words(text), kind_nouns()
    for i, word in enumerate(words):
        if word not in UNIVERSAL:
            continue
        # The head noun, and whatever modifies it on the way there. Bounded: a kind noun
        # four words past the quantifier is not that quantifier's head, it is a later
        # phrase, and reaching for it would invent a relationship the sentence does not
        # have.
        modifiers: List[str] = []
        for offset in range(1, 5):
            if i + offset >= len(words):
                break
            candidate = words[i + offset]
            if candidate in nouns:
                rest = " ".join(words[i + offset + 1:])
                if RELATIVE.match(rest):
                    return "any"
                return "any" if modifiers else "all"
            if candidate not in DETERMINERS:
                modifiers.append(candidate)
        # A universal with no kind noun after it — "give them all the 'fleet' label", where
        # the head is not a machine. Not this rule's business.
        return None
    return None


def score(corpus: List[Tuple[str, str]]) -> dict:
    """Fired / correct / wrong / deferred over a labelled corpus."""
    fired = correct = wrong = 0
    misses = []
    for text, want in corpus:
        got = classify(text)
        if got is None:
            continue
        fired += 1
        if got == want:
            correct += 1
        else:
            wrong += 1
            misses.append((text, want, got))
    return {"n": len(corpus), "fired": fired, "correct": correct, "wrong": wrong,
            "deferred": len(corpus) - fired, "misses": misses}
