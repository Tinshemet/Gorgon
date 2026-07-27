"""
mutate.py — mechanical perturbations of a goal, for the ladder's third column.

WHY MECHANICAL RATHER THAN WRITTEN. The ladder has two columns, a literal wording and a
hand-written paraphrase, and the paraphrases are not the equal-difficulty rewrites they
were meant to be. Rung 7's says "there should END UP being precisely three… no more and no
fewer" where the literal says only "make sure exactly 3" — the constraint stated instead of
implied. Rung 9's says "sort out whatever is stopping that", which tells the model
something is BROKEN on the rung whose whole point is diagnosis. Measured over three samples
each: literal 9/13 every time, paraphrase 10-12/13. The gap is real and it is a gap in how
much the sentence SPECIFIES, not in how hard the capability is.

Nobody wrote those to cheat. That is the point — an author cannot audit their own
paraphrases for leakage, because the leak is the part they thought was clarity. A mutation
has no authorial intent to leak: it transforms a sentence by rule, so whatever it does to
rung 9 it does to rung 3 as well.

THE LOAD-BEARING CONSTRAINT IS MEANING PRESERVATION. A mutation that quietly changes the
goal does not measure robustness, it corrupts the benchmark — and it would look exactly
like a model failure, which is the one mistake this whole codebase keeps making. Two rules
keep that from happening:

  1. **WHITELIST, NEVER BLACKLIST.** Substitutions come from a table of GENERIC domain
     words (vm, network, label, launch…). Identity names — alpha, db, n1, golden, mesh0,
     core, dmz, prod, fleet, red, blue — are simply absent from it, so no rule can reach
     them. A blacklist would have to enumerate every name any future rung might use, and
     would silently fail the first time somebody forgot one.
  2. **QUOTED TEXT IS UNTOUCHABLE.** `'fleet'` and `'prod'` are values, not words. They
     are lifted out before any rule runs and put back afterwards.

Every mutation is DETERMINISTIC in its input: the seed is derived from the goal text and
the mutation's own name, so the same rung mutates the same way on every run and a result
is reproducible without storing the mutated sentences.

Run:  PYTHONPATH=. python3 -m tests.bench.mutate      # print every mutation of every rung
"""
from __future__ import annotations

import random
import re
from typing import Callable, Dict, List

# ── the whitelist ────────────────────────────────────────────────────────────────────
# GENERIC domain words only. Adding a row here is safe; adding an identity name is not,
# and the way to keep that true is that this table never contains one.
_SYNONYMS: Dict[str, List[str]] = {
    "vm": ["machine", "box", "host"],
    "vms": ["machines", "boxes", "hosts"],
    "machine": ["vm", "box"],
    "machines": ["vms", "boxes"],
    "network": ["net", "subnet"],
    "networks": ["nets", "subnets"],
    "label": ["tag"],
    "labelled": ["tagged"],
    "labeled": ["tagged"],
    "create": ["make", "build"],
    "creates": ["makes"],
    "launch": ["start", "boot"],
    "launched": ["started", "booted"],
    "stop": ["halt", "shut down"],
    "stopped": ["halted", "powered off"],
    # `up` is NOT here. It reads fine after a copula ("currently up") and badly in front
    # of a noun ("each up box", rung 12) — the same position-dependence that put `all` out
    # of this table. Caught by the consistency audit, which is worth re-running whenever a
    # row is added: the failure mode is awkward English that inflates difficulty, and it
    # looks exactly like a model failure.
    "running": ["powered on"],
    "clone": ["copy", "duplicate"],
    "snapshot": ["restore point"],
    "ping": ["poll", "probe"],
    "reach": ["talk to"],
    "put": ["place"],
    "every": ["each"],
    "exactly": ["precisely"],
    # NOT HERE: `all`. It was, mapped to "every one of", and produced "put them every one
    # of in a net" — broken English rather than a rewording. A word-level table can only
    # hold substitutions that are valid in EVERY position the word can occupy; anything
    # position-dependent changes the sentence's difficulty in a way nobody controls, which
    # is the corruption this module exists to prevent. If a phrase-level rewrite is wanted
    # it needs to match the phrase, not the word.
}

# Words whose option lists are written in the SAME ORDER so a shared index keeps a goal
# internally consistent: pick `box` for `vm` and you get `boxes` for `vms`, never a
# sentence that calls one thing two names.
_FAMILY: Dict[str, str] = {
    "vm": "vm", "vms": "vm",
    "machine": "machine", "machines": "machine",
    "network": "network", "networks": "network",
}

_ARTICLES = ("a", "an", "the")

# Words a typo may touch: only ones this module already knows are generic. A transposition
# in an identity name is not noise, it is a different goal.
_TYPOABLE = {w for w in _SYNONYMS if len(w) >= 5} | {
    v for vs in _SYNONYMS.values() for v in vs if len(v) >= 5 and " " not in v}

_QUOTED = re.compile(r"""(['"])(?:(?!\1).)*\1""")
_WORD = re.compile(r"[A-Za-z']+")


def _seed(goal: str, name: str) -> random.Random:
    """Deterministic per (goal, mutation). Same input, same mutation, every run — so a
    result is reproducible without recording the sentences it came from."""
    return random.Random(f"{name}::{goal}")


def _protect(goal: str):
    """Lift quoted values out so no rule can touch them, and give back a restorer.

    `'fleet'` is a VALUE the checker matches on, not a word to be reworded. Substituting
    inside it would change what the program has to do while looking like a rephrasing.
    """
    held: List[str] = []

    def _take(m):
        held.append(m.group(0))
        return f"\x00{len(held) - 1}\x00"

    masked = _QUOTED.sub(_take, goal)
    return masked, (lambda s: re.sub(r"\x00(\d+)\x00",
                                     lambda m: held[int(m.group(1))], s))


def _sub_words(text: str, pick: Callable[[str], str]) -> str:
    """Rewrite whole words through `pick`, preserving the original capitalisation."""
    def _one(m):
        w = m.group(0)
        out = pick(w.lower())
        if out is None or out == w.lower():
            return w
        return out.capitalize() if w[:1].isupper() else out
    return _WORD.sub(_one, text)


# ── the mutations ────────────────────────────────────────────────────────────────────
def synonym(goal: str) -> str:
    """Swap generic domain words for equivalents, CONSISTENTLY within one goal.

    One word gets one replacement for the whole sentence, and singular/plural move
    together. This chose independently per OCCURRENCE and rung 8 showed what that costs:

        "place each machine on a SUBNET called core, except db —
         db goes on a NET called dmz instead"

    Two words for one concept in a single sentence. No person rewording would do that,
    and "subnet" against "net" plausibly reads as two different kinds of thing — so the
    mutation was adding difficulty of its own rather than measuring the language's
    robustness. A mutation that is harder than any real rephrasing measures nothing you
    can act on.
    """
    rng = _seed(goal, "synonym")
    masked, restore = _protect(goal)
    chosen: Dict[str, int] = {}

    def _pick(w: str) -> str:
        if w not in _SYNONYMS:
            return w
        # Singular and plural share a decision, because their option lists are written in
        # the same order for exactly this purpose: `vm`->box implies `vms`->boxes.
        family = _FAMILY.get(w, w)
        options = _SYNONYMS[w]
        if family not in chosen:
            chosen[family] = rng.randrange(len(options))
        return options[chosen[family] % len(options)]

    return restore(_sub_words(masked, _pick))


def filler(goal: str) -> str:
    """Wrap the request in politeness. Adds tokens and says nothing — a pure test of
    whether irrelevant text displaces the parts that matter."""
    rng = _seed(goal, "filler")
    openers = ["could you please ", "when you get a chance, ", "i'd like you to ",
               "if you don't mind, "]
    closers = [" thanks", " if that's alright", " please"]
    return rng.choice(openers) + goal + rng.choice(closers)


def terse(goal: str) -> str:
    """Strip articles. Shortens without removing information — the opposite direction
    from `verbose`, so the two together bracket the specification axis."""
    masked, restore = _protect(goal)
    out = _sub_words(masked, lambda w: "" if w in _ARTICLES else w)
    return restore(re.sub(r"\s{2,}", " ", out).strip())


def verbose(goal: str) -> str:
    """Restate the request around itself. Same information, more of it — the axis the
    hand-written paraphrases accidentally moved along."""
    rng = _seed(goal, "verbose")
    frames = ["here is what i need: {g}. that's the whole job.",
              "the task is as follows. {g}. nothing beyond that.",
              "i want the lab to end up like this: {g}."]
    return rng.choice(frames).format(g=goal)


def reorder(goal: str) -> str:
    """Swap independent clauses.

    ONLY across `;`, and only when no clause carries an ordering word. "create a vm named
    beta and THEN launch it" is sequenced, and reordering it would change the goal rather
    than reword it — which is the corruption this module exists to avoid.
    """
    if ";" not in goal:
        return goal
    parts = [p.strip() for p in goal.split(";") if p.strip()]
    if len(parts) < 2 or any(re.search(r"\b(then|after|once|before|first)\b", p)
                             for p in parts):
        return goal
    rng = _seed(goal, "reorder")
    rng.shuffle(parts)
    return "; ".join(parts)


def casing(goal: str) -> str:
    """Shout it. Tests nothing about language and everything about tokenisation."""
    masked, restore = _protect(goal)
    return restore(masked.upper())


def typo(goal: str) -> str:
    """Transpose two letters in ONE generic word — the only mutation that produces text a
    person would call wrong. Restricted to words this module already knows are generic:
    a transposition inside an identity name is a different goal, not noise."""
    rng = _seed(goal, "typo")
    masked, restore = _protect(goal)
    hits = [m for m in _WORD.finditer(masked) if m.group(0).lower() in _TYPOABLE]
    if not hits:
        return goal
    m = rng.choice(hits)
    w = m.group(0)
    i = rng.randrange(len(w) - 1)
    swapped = w[:i] + w[i + 1] + w[i] + w[i + 2:]
    return restore(masked[:m.start()] + swapped + masked[m.end():])


MUTATIONS: Dict[str, Callable[[str], str]] = {
    "synonym": synonym,
    "filler": filler,
    "terse": terse,
    "verbose": verbose,
    "reorder": reorder,
    "casing": casing,
    "typo": typo,
}


def apply(goal: str, name: str) -> str:
    """One named mutation, or the goal unchanged if the name is unknown."""
    fn = MUTATIONS.get(name)
    return fn(goal) if fn else goal


if __name__ == "__main__":                                     # pragma: no cover
    from .rungs import RUNGS
    for r in RUNGS:
        print(f"\n── rung {r.n} ({r.name})\n   ORIGINAL : {r.goal}")
        for nm in MUTATIONS:
            out = apply(r.goal, nm)
            print(f"   {nm:9}: {out}" + ("   (no change)" if out == r.goal else ""))
