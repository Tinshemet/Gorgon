"""reporter.py — findings back out as English. The last seam, and the one that can lie.

    English    -> components      EXTRACTOR   the model
    components -> engine work     WRITER      code
    findings   -> English         REPORTER    the model      <- this file

WHAT MAKES IT DIFFERENT FROM THE OTHER TWO: nothing downstream checks it. A bad extraction
produces a program that fails; a bad program fails its own ENSURE. A bad REPORT is the last
thing anyone sees, and it is fluent by construction — the failure mode is a sentence that
reads exactly like a true one.

SO THE REPORTER IS HANDED FINDINGS ONLY. Never the request, never the program, never the
goals. That is not tidiness: a model that can see what was ASKED will write a fluent answer
to the question, and a model that can see only what was FOUND can only describe the evidence.
The difference between a system that says "spotted between 1am and 2am" because a finding
carries that timestamp and one that says it because it sounds like an answer is the whole of
whether any of this can be trusted.

AND IT DECLARES ITS OWN CLAIMS, which is what makes checking possible at all. Asking "is
every word of this prose supported?" is an open question that flags ordinary English; asking
"are these listed names and numbers supported?" is a closed one. So the reporter lists what
it is claiming and `unsupported()` checks that list against the ledger — the same
declare-then-check the extractor uses, pointed the other way. A reporter cannot be trusted;
it can be verified.

"NO" IS A FIRST-CLASS ANSWER. "Nothing was found; 340 frames scanned, 12 people seen" is a
finding, not a failure. An answering engine that cannot say no is one whose yes means nothing.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Set

SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": ("one or two plain sentences describing WHAT WAS FOUND. If the "
                            "findings show nothing was found, say so — that is a complete "
                            "answer."),
        },
        # THE REPORTER DECLARES ITS OWN CLAIMS, and this is what makes it checkable at all.
        #
        # The first version scanned every word of the prose against the findings and flagged
        # anything absent — which flagged "findings" and "show". Growing a stop list to cover
        # ordinary English is fragile, endless, and ends with a guard that fires on correct
        # output until people stop reading it.
        #
        # Asking the model to LIST the names and numbers it used turns an open problem
        # (which words are claims?) into a closed one (are these claims supported?). It is
        # the same declare-then-check the extractor uses, pointed the other way — and a
        # reporter that omits a claim from this list to smuggle it past the check has to
        # decide to lie about a separate field, which is a harder failure than fluency.
        "mentions": {
            "type": "array",
            "items": {"type": "string"},
            "description": ("every NAME, NUMBER and VALUE your answer uses — one per entry, "
                            "exactly as it appears in the findings. Ordinary words do not "
                            "belong here; only the things you are claiming."),
        },
    },
    "required": ["answer", "mentions"],
    "additionalProperties": False,
}

PROMPT = """You are shown FINDINGS — what a system observed. Describe them in one or two
plain sentences, for the person who asked.

You do not know what was asked and you do not need to. Say what the findings show.

Use only names, numbers and values that appear in the findings, and LIST THEM in `mentions`.
Do not add detail, do not estimate, and do not explain what it means. If the findings show
that nothing was found, say that plainly — it is a complete and useful answer."""

def _atoms(findings: Any) -> Set[str]:
    """Every name, number and value the findings contain, lowercased.

    Walks the whole structure rather than reading known keys, because a reporter must be
    checkable against findings whose shape nobody anticipated — a crawl package's, a vision
    package's, one written next year.
    """
    out: Set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                out.add(str(k).lower())
                walk(v)
        elif isinstance(node, (list, tuple, set)):
            for v in node:
                walk(v)
        elif node is not None and not isinstance(node, bool):
            for piece in re.split(r"[\s,;:/]+", str(node).lower()):
                if piece:
                    out.add(piece.strip(".'\"()[]"))
    walk(findings)
    return {a for a in out if a}


def unsupported(mentions: Sequence[str], findings: Any) -> List[str]:
    """Declared claims that no finding supports. Empty means every claim is grounded.

    Checks what the reporter SAID IT WAS CLAIMING, not every word it wrote. Meaning cannot be
    verified mechanically; a list of names and numbers can, and that is the whole trick —
    a reporter mentioning `vm7` when no finding does has invented a machine, which is the
    failure worth catching. Whether its adjective was apt is not.

    Numbers are checked the same way as names because they are the most persuasive kind of
    invention: "spotted between 1am and 2am" is exactly the claim this exists to police, and
    a timestamp is something the ledger either carries or does not.
    """
    have = _atoms(findings)
    bad: List[str] = []
    for raw in mentions or ():
        for piece in re.split(r"[\s,;:/]+", str(raw).lower()):
            word = piece.strip(".!?'\"()[]—-")
            if word and word not in have:
                bad.append(word)
    return bad


def report(findings: Any, ask, verify: bool = True) -> Dict[str, Any]:
    """Turn findings into a sentence, and say whether every word of it is supported.

    `ask(prompt, payload) -> str` is the channel — the same interface the extractor uses, so
    there is one place a model is called and one place to stub.

    NEVER RAISES ON AN UNGROUNDED ANSWER, and returns it flagged instead. Suppressing it
    would leave the operator with silence where there was an answer; returning it silently
    would be the hallucination this file exists to prevent. Both facts go back: what it said,
    and what it could not support.
    """
    if not findings:
        # NO FINDINGS IS AN ANSWER, and it does not need a model. Asking one to describe an
        # empty ledger is asking it to invent something, which is the failure mode.
        return {"answer": "Nothing was found.", "unsupported": [], "grounded": True,
                "source": "empty"}
    try:
        said = ask(PROMPT, findings)
    except Exception as e:
        return {"answer": None, "unsupported": [], "grounded": False,
                "source": f"error: {type(e).__name__}"}
    # The channel may hand back the parsed object or just the prose. A bare string means no
    # claims were declared, which is not the same as no claims being made — so it is treated
    # as UNVERIFIABLE rather than clean.
    if isinstance(said, dict):
        text = str(said.get("answer") or "").strip()
        mentions = said.get("mentions") or []
        declared = True
    else:
        text, mentions, declared = str(said or "").strip(), [], False
    missing = unsupported(mentions, findings) if verify else []
    return {"answer": text, "mentions": list(mentions), "unsupported": missing,
            "grounded": bool(declared) and not missing,
            "source": "model" if declared else "model (undeclared claims — unverifiable)"}
