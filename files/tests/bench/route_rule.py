"""`new` or `call`, decided by SHAPE and the manifest — or honestly declined.

D9's defect: the atomicity router names the right operator 4/10, and every error that costs
a rung is one shape — it answers `new` for a goal that acts on something ALREADY THERE.
Rung 3's "put web on lab" produced `NEW vm FROM $web` with the correct `add_vm_to_network`
demoted into the failure branch: a spurious clone, from a program that validated.

TEACHING IT HARDER WAS MEASURED AND IT TRADES (f3ccfd8): naming the sixteen tools and
showing earlier siblings each fixed one `call` cell alone, and together they fixed three and
BROKE TWO CONTROLS — "clone golden into a new vm" went 3/3 `new` to 0/3 `call`. Tell the
model more about acting and it stops creating. So this computes the answer instead, the way
`quantifier_rule` does, and DECLINES rather than guessing.

THE DISCRIMINATOR IS KIND-HOOD, NOT THE VERB, and that is the whole idea. A leading-verb
rule scores 7/7 on the tuning corpus and is wrong about the cases that matter:

    "create a snapshot of web"     CREATE, but `snapshot` is not a kind the world declares,
                                   so nothing is brought into existence — it is a tool call.
    "add a second disk to web"     ADD sounds like creation; `disk` is not a kind either.
    "set up a network called dmz"  no CREATE anywhere, and `network` IS a kind. A `new`.

`NEW` exists to bring a declared KIND into existence — it supplies the name and calls the
creator. So the question is not "does this sentence sound like creation", it is "does it
introduce an instance of something `config.KINDS` knows about". Everything else is a `call`.

CLONING IS THE EXCEPTION AND IT IS PRINCIPLED: "take a copy of golden" names no kind at all,
and copies an existing vm into a new one. `NEW ... FROM $source` is exactly that statement,
so a copy verb answers `new` without needing a kind noun.

WHAT MAKES IT SAFE. `None` means no rule applies and the router answers, unchanged. The
expensive error here is a wrong `new` — it fabricates a machine nobody asked for, which is
rung 3's failure — so the `new` branches require positive evidence (a copy verb, or a
creation verb with a declared kind) and everything else that is not clearly action falls
through.
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from orchestrator.ai.planner.ir import config

# Bringing something into existence. VERBS ONLY, and that restriction is the rule's whole
# point. My first version also listed the ADJECTIVE `new`, and it answered `new` for "launch
# the new vm" and "move resource to new network" — three of seven cells wrong, because in
# both the word describes a machine that ALREADY EXISTS. That is precisely the mistake the
# atomicity router makes and this rule was written to correct: seeing `new` and creating.
# A word that can modify a noun cannot be evidence of creation.
#
# `set up` and `spin up` are here because the ladder's paraphrases use them, and `set up`
# missing from one regex already cost a rung once.
CREATION = ("create", "make", "build", "set up", "spin up", "provision")

# Copying an existing object into a new one — `NEW ... FROM $source`. Answers `new` with no
# kind noun needed, because "take a copy of golden" names none.
COPYING = ("clone", "copy", "duplicate", "replicate")

# Acting on something already there. Present for readability; the rule reaches `call` by
# ELIMINATION, so this list can never cause a wrong `new`.
ACTION = ("put", "move", "launch", "start", "stop", "shut down", "ping", "label", "tag",
          "give", "add", "attach", "connect", "wire", "reboot", "restart", "snapshot",
          "archive", "boot", "check")


def kind_words() -> set:
    """Every noun that names a declared kind, plus the plain-English words the ladder's
    paraphrases use for the same things. From the manifest, so a new kind is recognised by
    adding a row and nothing else."""
    out = {"machine", "machines", "box", "boxes", "node", "nodes", "server", "servers"}
    for kind in config.KINDS:
        out.add(kind.lower())
        out.add(kind.lower() + "s")
    return out


def _created_names(done: Sequence[str]) -> set:
    """Names earlier sibling steps brought into existence — "create a vm named web" -> web."""
    names = set()
    for step in done or ():
        for match in re.finditer(r"\b(?:called|named|labelled|labeled)\s+'?\"?([\w-]+)",
                                 step.lower()):
            names.add(match.group(1))
    return names


def classify(goal: str, done: Optional[Sequence[str]] = None) -> Optional[str]:
    """`new`, `call`, or None when no rule applies."""
    text = " " + goal.lower().strip()

    # A COPY OF SOMETHING EXISTING IS STILL A NEW OBJECT. Checked first: "clone golden once
    # more" has no kind noun and no creation verb, and is unambiguously a `new`.
    if any(re.search(rf"\b{verb}", text) for verb in COPYING):
        return "new"

    names, kinds = _created_names(done), kind_words()
    creating = any(re.search(rf"\b{re.escape(verb.strip())}\b", text) for verb in CREATION)

    # A GOAL NAMING SOMETHING AN EARLIER SIBLING CREATED IS ACTING ON IT, whatever the verb.
    # This is D9's own sentence: a goal whose referents already exist cannot be a `new`.
    if names and any(re.search(rf"\b{re.escape(n)}\b", text) for n in names):
        if not creating:
            return "call"

    if creating:
        # THE DISCRIMINATOR. A creation verb introduces an instance of a DECLARED KIND, or
        # it is a tool call wearing a creation verb — "create a snapshot", "add a disk".
        return "new" if any(re.search(rf"\b{word}\b", text) for word in kinds) else "call"

    # No creation verb anywhere. If it reads as an action on something, it is a `call`;
    # otherwise say nothing.
    if any(re.search(rf"\b{re.escape(verb)}", text) for verb in ACTION):
        return "call"
    return None


def score(corpus: List[Tuple[str, str, str, List[str]]]) -> dict:
    fired = correct = wrong = 0
    misses = []
    for goal, want, _parent, done in corpus:
        got = classify(goal, done)
        if got is None:
            continue
        fired += 1
        correct += got == want
        if got != want:
            wrong += 1
            misses.append((goal, want, got))
    return {"n": len(corpus), "fired": fired, "correct": correct, "wrong": wrong,
            "deferred": len(corpus) - fired, "misses": misses}
