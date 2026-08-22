"""governing.py — A DECLARATION IS A RULE, AND A RULE IS PROPOSED, NEVER ENACTED.

    "never delete a vm without asking me"       ->  a pending amendment
    "prod vms must always keep a snapshot"      ->  a pending amendment

# ⇒⇒ THE HALF OF THE STATEMENT TYPE THAT WAS NEVER BUILT

`archive.py` covers the statements that TEACH — *"kaya is a vm"*, a fact about a word. This
covers the ones that GOVERN — a rule about what may be done, ever. Both are declarative in
form and they are opposite in effect, which is why they needed separating rather than one
larger reader.

**AND THE GOVERNING HALF WAS A FALSE SERVE UNTIL 2026-08-16.** *"prod vms must always keep a
snapshot"* read as `directive-act` and would have TAKEN A SNAPSHOT NOW — carrying out, once,
a sentence that was legislating forever. That is the most expensive way to misread a rule.

# ⇒⇒ IT PROPOSES. IT NEVER ENACTS — AND THAT IS `proposals.py`'s OWN RULE, NOT A NEW ONE

Its module note: *"The AI can propose but never enact — consent of the governed, with the
human as the final weight."* A proposal lands `pending` and only the operator's safeword plus
an assigned weight turns it into law, through the versioned re-sign in `forge.amend`.

⇒ **SO THIS DIFFERS FROM THE ARCHIVE ON PURPOSE.** A statement that TEACHES is signed on the
  spot — the operator's own words are the signature, because a wrong entry is repairable by
  teaching. A statement that GOVERNS is not, because a rule constrains every future act and
  the contract already has a formal amendment path. **Teaching is cheap to correct; law is
  not.**

# ⇒ WHAT IT READS, AND IT ADDS NO VOCABULARY

`speech_act` settles which clauses are declarations, from two closed classes it already owns:
the deontic modals (a subset of the auxiliaries) and the frequency adverbs `never`/`always`.
A rule quantifies over TIME, and those are the words English uses to do it. Nothing here
re-decides that.

⇒ ⚠ **AND IT IS DOCUMENTARY, WHICH IS THE HONEST SHAPE FOR TODAY.** `proposals.validate`
  demands a typed `effect` for an enforceable kind — `access` needs a forbid/allow/scope,
  `decree` needs a success predicate. Deriving one of those from English is a real piece of
  work and guessing it would write a law nobody meant. A `rule` proposal carries the
  operator's sentence verbatim and enforces nothing until they type the effect themselves.
"""
from typing import List, Optional, Tuple

from planner.formula.legal import Board

# ⇒ THE DOCUMENTARY KIND. `rules.KINDS` owns the vocabulary; this names the one entry that
#   needs no typed effect, and `proposals.validate` is what enforces that distinction.
DOCUMENTARY = "rule"

from ..codex import CONTRACT_VERBS


def rules_from(request: str, board: Optional[Board] = None, world=None) -> List[dict]:
    """Every rule this request proposes. Reported, never filed — the caller decides.

    ⇒ **THE SEAM READS AND THE DOOR FILES**, the same split `teaches` uses. Writing to the
      contract from inside the reading stage would put the law one import away from every
      bench and test that runs a request, and [[gorgon-orchestrator-proposes-a-scaffold]] is
      the standing rule: the orchestrator proposes, somebody else enacts.
    """
    from . import speech_act

    from .linguistics import manifest_verbs

    board = board or Board()
    lab = manifest_verbs(board)
    out: List[dict] = []
    for clause, act in speech_act.read(request, board, world):
        governs = act == speech_act.DECLARATION
        if not governs:
            # ⇒ THIS STORE'S OWN FRAME — `treat X as Y`. Read HERE rather than in `speech_act`
            #   so the reader stays free of any one store's vocabulary, and so the two files
            #   do not import each other. The manifest is checked first: a declared verb may
            #   never shadow one the lab owns (`mark … as a template` stays an order).
            words = speech_act.words_of(clause)
            head = speech_act._after_openers(words)
            head = head[0] if head else ""
            governs = (head in CONTRACT_VERBS and head not in lab and "as" in words)
        if not governs:
            continue
        out.append({"kind": DOCUMENTARY,
                    "text": str(clause).strip(),
                    "said": str(clause).strip()})
    return out


def file_all(rules: List[dict], agent: Optional[str] = None,
             origin: str = "human") -> List[str]:
    """File each as a PENDING amendment and say what happened, in the operator's terms.

    ⇒ `origin="human"` BECAUSE THE OPERATOR LEGISLATED. `proposals.py` distinguishes a
      REFERENDUM (the AI asking, after a gate blocked it) from an AMENDMENT (the human
      legislating directly), and a sentence the operator typed is plainly the second. Getting
      that wrong would file the operator's own rule as though the machine had asked for it.
    """
    from orchestrator.ai.agent import proposals as _proposals

    said: List[str] = []
    for rule in rules:
        try:
            filed = _proposals.propose(agent, kind=rule.get("kind", DOCUMENTARY),
                                       text=rule["text"], origin=origin)
        except Exception as e:                      # a malformed proposal is not a crash
            said.append(f"could not file {rule['text']!r} — {e}")
            continue
        said.append(f"filed as a pending rule ({filed['id']}) — {rule['text']!r}. "
                    f"It enforces nothing until you sign it with a weight.")
    return said
