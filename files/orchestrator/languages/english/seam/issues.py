"""issues.py — AN OPEN QUESTION IS A THING WITH A LIFECYCLE, NOT A STRING IN A REPLY.

⇒⇒ **THIS IS B1 AND B2 AT ONCE, AND THAT IS WHY IT IS ONE MODULE.** The operator, 2026-08-13:
  *"are you missing the same pipeline for the ask as we use for the normal pipeline, but we wire
  it to an open ISSUE — same mechanic as claim and findings?"* … *"let's do the issue ledger,
  that dissolves B1 and B2 together."*

    B2 was  "nothing consumes an operator reply"
    B1 was  "an answered ASK should be kept globally, clarified ONCE, model-independent"

  **They are the same object seen twice.** An ASK that is recorded, stays open until somebody
  answers, and is remembered afterwards IS the write-back AND the Encyclopedia. Built as two
  items they would have been two stores.

⇒ **THE SHAPE IS THE FINDINGS LEDGER'S, DELIBERATELY.** `Findings.record` already says it:
  *"an UNVERIFIED claim … enters as `pending`: recorded and visible, but NOT usable to close a
  goal until a human confirms it."* That is an open issue described exactly. Copying the shape
  rather than inventing one means an operator learns the lifecycle once.

⇒ **KEYED BY THE WORD, NEVER THE PHRASE**, which is the thing today's build measured the hard
  way: a question came back about `'a grubnash named alpha'` while the answer was filed under
  `grubnash`, and an exactly-correct answer bound to nothing. **The word is what is reusable**
  across requests, sessions and models; the phrase is an artefact of how one sentence was cut.

⇒ **AND THE WORLD OUTRANKS THE LEDGER, ALWAYS.** `settle_with_answers` runs after the manifest,
  the lab and affordance, so a remembered answer can only ever fill a row nothing else settled.
  An entry that could overwrite a lookup would make a stale memory stronger than the live world,
  which is the wrong way round for a store whose whole value is that it persists.
"""
import json
import pathlib
import time
from typing import Dict, List, NamedTuple, Optional

OPEN, ANSWERED = "open", "answered"


class Issue(NamedTuple):
    """One question, its lifecycle, and its provenance."""
    key: str                  # rule:word — what an answer is addressed to
    rule: str
    word: str                 # THE REUSABLE PART
    says: str                 # the question in the operator's terms
    status: str = OPEN
    said: Optional[str] = None
    who: Optional[str] = None
    at: Optional[float] = None
    seen: int = 1             # how many times this question has come up

    @property
    def stale_risk(self) -> bool:
        """An answer about the WORLD ages; an answer about LANGUAGE does not.

        *"A jumpbox is a vm"* is a fact about vocabulary and stays true. *"Yes, create it"* was
        about one request's world and must never be replayed — see `answers()`.
        """
        return self.rule in {"not-there", "already-there", "destructive-confirm", "red-line"}


class Issues:
    """The ledger. Open questions, and the answers to the ones already settled."""

    def __init__(self, path: Optional[str] = None):
        self.path = pathlib.Path(path) if path else None
        self._by_key: Dict[str, Issue] = {}
        if self.path and self.path.exists():
            self.load()

    # ── recording ────────────────────────────────────────────────────────────────────────
    def raise_(self, rule: str, word: str, says: str) -> Issue:
        """Record a question. Asking the same one twice does not lose its answer.

        ⇒ AN ALREADY-ANSWERED ISSUE IS NOT REOPENED. That is the whole point of *clarified
          ONCE*: the second time the word appears, the ledger already knows.
        """
        key = f"{rule}:{str(word).strip().lower()}"
        found = self._by_key.get(key)
        if found:
            self._by_key[key] = found._replace(seen=found.seen + 1)
            return self._by_key[key]
        made = Issue(key, rule, str(word).strip().lower(), says)
        self._by_key[key] = made
        return made

    def answer(self, key_or_word: str, said: str, who: str = "operator") -> Optional[Issue]:
        """Settle an issue. Addressable by its full key or by the bare word."""
        k = str(key_or_word).strip().lower()
        hit = self._by_key.get(k) or next(
            (i for i in self._by_key.values() if i.word == k and i.status == OPEN), None)
        if not hit:
            return None
        done = hit._replace(status=ANSWERED, said=said, who=who, at=time.time())
        self._by_key[done.key] = done
        return done

    # ── reading ──────────────────────────────────────────────────────────────────────────
    def open(self) -> List[Issue]:
        return sorted((i for i in self._by_key.values() if i.status == OPEN),
                      key=lambda i: (-i.seen, i.key))

    def answers(self) -> Dict[str, str]:
        """What to hand `run(answers=…)` — the ENCYCLOPEDIA half.

        ⇒⇒ **A WORLD ANSWER IS NEVER REPLAYED, AND THAT IS THE SAFETY PROPERTY OF THIS STORE.**
          *"A jumpbox is a vm"* is a fact about the LANGUAGE: true tomorrow, true for a different
          model, true in a different lab — exactly what *"clarified once"* means. *"Yes, create
          it"* is a fact about ONE REQUEST'S WORLD, and replaying it would build machines on the
          strength of a decision made about a different sentence last week.

          The two are told apart by the RULE that asked, not by reading the answer — a lookup,
          not a judgement.
        """
        return {i.word: i.said for i in self._by_key.values()
                if i.status == ANSWERED and i.said and not i.stale_risk}

    # ── persistence ──────────────────────────────────────────────────────────────────────
    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([i._asdict() for i in self._by_key.values()], indent=2))

    def load(self) -> None:
        try:
            rows = json.loads(self.path.read_text())
        except Exception:
            return
        for r in rows:
            try:
                self._by_key[r["key"]] = Issue(**r)
            except Exception:
                continue          # a row this version cannot read is skipped, never fatal


def word_of(about: str, board=None) -> str:
    """The REUSABLE word inside a phrase — what the ledger must file under.

    ⇒⇒ **FILING BY THE PHRASE MAKES THE STORE USELESS, AND THAT IS EXACTLY WHAT IT DID FIRST.**
      Measured on the round trip: an issue was filed under `'a jumpbox named bastion'`, so
      answering *"a jumpbox is a vm"* matched nothing and the next request — *"launch every
      jumpbox"* — learned nothing. **A phrase is an artefact of one sentence; the word is what
      recurs**, which is the whole of *clarified once, globally, model-independent*.

    ⇒ IT IS FOUND BY SUBTRACTION, from closed classes only. Strip the GRAMMAR words (a, the,
      every, named — function words, finite and stable), strip anything the manifest already
      knows as a kind or noun, strip the row's own identity if it has one — and what is left is
      the word nobody could settle. No content-word list is consulted or needed.
    """
    from . import scan
    from .scan import _operation_words
    # ⇒ EVERY CLOSED CLASS THIS PROJECT ALREADY OWNS, and not one new list. `GRAMMAR` alone left
    #   `every`, `called` and the verbs standing — measured on the first cut, which filed
    #   *"launch every jumpbox"* under `launch`.
    closed = (set(scan.GRAMMAR) | set(scan.INDEFINITE) | set(scan.DEFINITE)
              | set(scan.UNIVERSAL) | set(scan.NOVEL) | set(scan.NAMING_CUES)
              | set(scan.LINKING) | set(scan.ENUMERATORS) | set(scan.COMPARATORS))
    words = [w.strip(".,;:'\"()") for w in str(about).lower().split()]
    known = set(_operation_words(board) if board is not None else ())
    if board is not None:
        for kind, spec in (board.kinds or {}).items():
            known.add(kind.lower())
            known.update(str(n).lower() for n in (spec.get("nouns") or ()))
    left = [w for w in words if w and w not in closed and w not in known]
    # ⇒ THE HEAD COMES FIRST. *"a jumpbox named bastion"* leaves ['jumpbox', 'bastion'], and the
    #   one being TYPED is the head — `named X` marks X as the name, not the kind.
    return left[0] if left else str(about).strip().lower()


def raise_from(ledger: Issues, run, board=None) -> List[Issue]:
    """Record every answerable question a run produced.

    ⇒ ONLY THE ADDRESSABLE ONES. A question with no `about` cannot be answered by key, so filing
      it would create an issue nobody could ever close — an open item that is permanently open
      is worse than none, because it makes the list of real ones unreadable.
    """
    from . import asking
    out = []
    for q in asking.asks_of(getattr(run, "questions", None) or []):
        if q.rule and q.about:
            out.append(ledger.raise_(q.rule, word_of(q.about, board), q.says))
    return out
