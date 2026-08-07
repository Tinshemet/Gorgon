"""THE FULL PIPELINE, MOCKED END TO END — request in, program out, nothing authored.

    PYTHONPATH=. python3 -m tests.bench.formula.pipeline

The operator's pipeline, with the formula in the seat the translator used to hold:

    request
      │
      ├─ 1 SPLIT        the request into claims, IN THE REQUESTER'S OWN WORDS
      │                 (`extract.in_words` — measured excellent, and the half of the
      │                  two-pass experiment that was worth keeping)
      │
      ├─ 2 BOARD        the manifest says which slots this kind can legally fill.
      │                 128 legal moves for a vm, out of a 7168 key space.
      │
      ├─ 3 FILL         the AI answers ordinary questions FOR ONE CLAIM AT A TIME
      │                 — staged lowering. It never names a shape.
      │
      ├─ 4 KEY          the formula computes the sub-key. Nobody chose it.
      │
      ├─ 5 GATES 1+2    the VALUES: did you say this? does the world have it?
      │                 (the shape is not in question — it was computed)
      │
      ├─ 6 FOLD         sub-keys + DERIVED edges -> the final key. Order recovered here,
      │                 not supplied; residual moves marked here, not guessed.
      │
      ├─ 7 GATES 3+4    the PATTERN: is this folded shape legal, and is it viable?
      │                 serve · bounce · block
      │
      └─ 8 EMIT         the key SELECTS the program form; the values FILL it.
                        -> Medusa

WHAT MOVED, IN ONE LINE: steps 4, 6 and 8 used to be the model's job and are now
arithmetic. The model's remaining job is step 3 — supply values for slots it was handed.

WHAT THIS MOCK-UP DOES NOT DO, said plainly:
  * it does not fix the WRITER. A perfect program here still meets
    [[gorgon-the-writer-fails-rung-11]], which resolves an observed filter at plan time.
    The fold now MARKS those moves residual, which is the information the writer lacks —
    but nothing consumes the mark yet.
  * the gates here are called through their real modules, but on goals rebuilt from slots.
    Wiring the real orchestrator to this path is a separate job.
"""
from typing import Callable, Dict, List, NamedTuple, Optional

from .fold import Signature, fold
from .legal import Board
from .slots import Move, build

SERVE, BOUNCE, BLOCK = "SERVE", "BOUNCE", "BLOCK"

# a filler answers ordinary questions for ONE claim, given only what the board permits.
Filler = Callable[[str, Dict[str, object]], Dict[str, object]]


class Turn(NamedTuple):
    claim: str
    subject: Optional[str]
    filled: Dict[str, object]
    move: Optional[Move]
    complaints: List[str]


class Outcome(NamedTuple):
    request: str
    turns: List[Turn]
    signature: Optional[Signature]
    verdict: str
    asks: List[str]
    program: List[dict]

    @property
    def key(self) -> Optional[int]:
        return self.signature.number if self.signature else None


def split(request: str, splitter: Optional[Callable[[str], List[str]]] = None) -> List[str]:
    """STEP 1 — the request into claims, in the requester's own words.

    Deliberately NOT a translation. The measured finding is that pass one of the two-pass
    experiment is excellent at exactly this and pass two — re-translating those claims — is
    what failed. Here pass two is not a translation at all; it is slot-filling.
    """
    if splitter:
        return splitter(request)
    parts = [p.strip() for p in request.replace(";", ",").split(",") if p.strip()]
    return parts or [request]


def choose_subject(claim: str, board: Board) -> Optional[str]:
    """STEP 2a — which piece is this claim about? Declared nouns only, longest match wins.

    `nouns` holds the SYNONYMS, so the kind's own name has to be added back. Matching is on
    word boundaries because `net` is a declared noun and a substring of `network` — the
    exact shape of the regex bug that once made rung 6 pass while an identical request
    created nothing ([[gorgon-rungs]] paraphrase note).
    """
    import re

    low = claim.lower()
    best, at, length = None, len(low) + 1, 0
    for kind in board.subjects():
        names = [kind] + list((board.kinds.get(kind) or {}).get("nouns") or [])
        for noun in names:
            word = str(noun).lower()
            hit = re.search(rf"\b{re.escape(word)}s?\b", low)
            if not hit:
                continue
            # FIRST MENTION WINS, not longest. "give every vm on the dmz network the label
            # quarantine" is about the vm; longest-match picks `network` and is wrong.
            if hit.start() < at or (hit.start() == at and len(word) > length):
                best, at, length = kind, hit.start(), len(word)
    return best


def run(request: str, filler: Filler, board: Optional[Board] = None,
        splitter: Optional[Callable[[str], List[str]]] = None,
        world=None) -> Outcome:
    board = board or Board()
    turns: List[Turn] = []

    carried: Optional[str] = None
    for claim in split(request, splitter):
        # THE SUBJECT IS ITSELF A SLOT, filled from a CLOSED SET of declared kinds. Where the
        # claim names one we start from it; where it does not we carry the last one forward,
        # because that is what an anaphor IS — rung 11's "stop the ones that do not answer"
        # names no kind and means the machines the previous clause just pinged.
        guess = choose_subject(claim, board) or carried
        offers = (board.offers(guess) if guess
                  else {"subject": board.subjects()})        # STEP 2 — the legal moves
        filled = dict(filler(claim, offers) or {})           # STEP 3 — the AI fills slots
        subject = filled.get("subject") or guess
        if not subject:
            turns.append(Turn(claim, None, filled, None,
                              ["this claim names no kind the lab has, and none to carry"]))
            continue
        carried = subject
        filled["subject"] = subject
        complaints = _check_values(filled, subject, board)   # STEP 5 — the VALUES only
        try:
            move = Move(text=claim, **filled)                # STEP 4 — the key. Computed.
        except ValueError as exc:
            turns.append(Turn(claim, subject, filled, None, complaints + [str(exc)]))
            continue
        turns.append(Turn(claim, subject, filled, move, complaints))

    moves = [t.move for t in turns if t.move]
    if not moves:
        return Outcome(request, turns, None, BLOCK,
                       ["nothing in this request named a thing the lab has"], [])

    sig = fold(moves)                                        # STEP 6 — the FOLD
    verdict, asks = judge(sig, turns)                        # STEP 7 — the PATTERN
    program = [build(m) for m in moves] if verdict != BLOCK else []   # STEP 8 — EMIT
    return Outcome(request, turns, sig, verdict, asks, program)


def _check_values(filled: Dict[str, object], subject: str, board: Board) -> List[str]:
    """STEP 5 — gates 1 and 2, narrowed to what they are actually for.

    THE SHAPE IS NOT IN QUESTION HERE. It was computed. All that can be wrong is a value,
    and there are only two ways for a value to be wrong: it was not in the request, or the
    world cannot hold it.
    """
    out: List[str] = []
    for slot in ("filter", "except"):
        for attr, value in (filled.get(slot) or {}).items():
            if attr not in board.filterable(subject):
                out.append(f"{subject} has no attribute {attr!r}")
                continue
            allowed = board.values(subject, attr)
            if allowed and value not in allowed:
                out.append(f"{subject}.{attr} cannot be {value!r} — it must be one of {allowed}")
    for attr, value in (filled.get("target") or {}).items():
        if attr not in board.settable(subject):
            why = ("it is OBSERVED, so it can be asked but never demanded"
                   if attr in board.observable(subject) else "nothing can set it")
            out.append(f"{subject}.{attr} is not settable — {why}")
        else:
            allowed = board.values(subject, attr)
            if allowed and value not in allowed:
                out.append(f"{subject}.{attr} cannot be set to {value!r} — one of {allowed}")
    if filled.get("fact") and filled["fact"] not in board.observable(subject):
        out.append(f"{subject} has no fact {filled['fact']!r} to ask")
    if filled.get("count"):
        comparator, n = filled["count"]
        if not isinstance(n, int):
            out.append(f"a count must be a whole number, not {n!r}")
    return out


def judge(sig: Signature, turns: List[Turn]) -> tuple:
    """STEP 7 — gates 3 and 4 over the FOLDED pattern.

    Everything here reads the signature, never the request. Gate 3 asks whether the pattern
    is legal; gate 4 asks whether what is left is worth serving. Neither supplies an answer
    — the standing rule is that we cannot know what the operator wanted, so an ambiguity is
    a question and never a repair.
    """
    asks: List[str] = []
    fatal = False

    for turn in turns:
        if turn.complaints:
            asks.extend(turn.complaints)
            fatal = True

    if sig.cyclic:
        asks.append("these clauses disagree about what has to happen first")
        fatal = True

    for i in sig.set_aside:
        move = sig.moves[i]
        carved = ", ".join(f"{k}={v}" for k, v in (move.filled.get("except") or {}).items())
        asks.append(f"you set {carved} aside and nothing else says what happens to it — "
                    "leave it alone, or did you mean to say?")

    if len(sig.moves) > 1 and not sig.joins:
        asks.append("these clauses make things and never connect them — "
                    "did you mean them joined, or apart?")

    if fatal:
        return BLOCK, asks
    return (BOUNCE if asks else SERVE), asks


# ── a filler that needs no model, so the pipeline's own logic can be tested ────────────
def table_filler(answers: Dict[str, Dict[str, object]]) -> Filler:
    """Answers looked up by claim text. Lets the pipeline be exercised without a GPU."""
    def fill(claim: str, offers: Dict[str, object]) -> Dict[str, object]:
        return dict(answers.get(claim.strip(), {}))
    return fill


def show(outcome: Outcome) -> None:
    import json
    print(f"\n  “{outcome.request}”")
    for n, turn in enumerate(outcome.turns, 1):
        mark = turn.move.mnemonic if turn.move else "—"
        key = turn.move.key if turn.move else "—"
        print(f"    turn {n}  {mark:<30} k={key:<6} “{turn.claim}”")
        for c in turn.complaints:
            print(f"            ⇐ {c}")
    if outcome.signature:
        sig = outcome.signature
        print(f"    FOLD    {sig.fingerprint}  {sig.mnemonic}")
        for e in sig.joins:
            print(f"            join {e.kind} on {e.on}")
        if sig.residual:
            print(f"            residual moves (cannot be resolved before the run): "
                  f"{[i + 1 for i in sig.residual]}")
    print(f"    {outcome.verdict}")
    for a in outcome.asks:
        print(f"      ask: {a}")
    for g in outcome.program:
        print(f"      goal {json.dumps(g, sort_keys=True)}")
