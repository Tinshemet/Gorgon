"""THE REAL TEST — hand the model a request it has never seen and watch it spew the number.

    PYTHONPATH=. python3 -m tests.bench.formula.filling            # the held-out set
    PYTHONPATH=. python3 -m tests.bench.formula.filling --rungs    # the fourteen rungs

The operator, 2026-08-07: *"the real test for the formula is to get a response it's not
familiar with, and see it spew the number. Honestly the formula is a type of AI model
itself, but smaller."*

Everything before this file measured the FORMULA — whether nine slots can say a thing, and
whether the fold is well behaved. Those are questions about arithmetic and they were always
going to come out clean once the arithmetic was right. THIS asks the only question that can
still fail: **will the model fill slots it is handed?**

WHAT IS DIFFERENT FROM EVERY PREVIOUS PROMPT ATTEMPT, and why this is not the lever that
has failed five times ([[gorgon-offering-is-not-using]]):

  * the model is never shown a shape, a keyword, or a data structure. No `count`, no
    `every`, no `select`. Those words are not in the prompt and cannot come back.
  * it is shown ONLY the slots the manifest permits for this kind, with the closed value
    sets spelled out. A slot the world cannot honour is not mentioned, so it cannot be
    chosen — SUBTRACTIVE, which is the only kind of schema move that has ever worked.
  * it answers ONE claim at a time. Staged lowering, whose measured mechanism is branch
    count.

The failure modes it can still have are exactly two, and both are attributable: a WRONG
VALUE (gate 1 and gate 2 already catch those at zero false alarms) and a WRONG SLOT.

# ⇒⇒ THE RESULT, AND IT IS A FAILURE: 0 OF 14 FINAL KEYS MATCHED

Run over all fourteen rungs end to end, the model's fills reproduced the correct final key
ZERO times. Not one. The isolated probes above were clean and the whole pipeline is not, so
the gap is somewhere between them and it is mine, not the model's:

    rung  1   correct S·F·C[eq]  -> model S·T
    rung 11   correct S·? ▸ S·F·T -> model S           (nothing filled at all)
    rung 12   correct S·F·M      -> model S
    rung  9   correct S·C[min]·P[reach] -> BLOCKED, no move survived

TWO CAUSES ARE VISIBLE AND NEITHER IS THE DESIGN:

  1 **THE PER-TURN PROMPTS LOST THE BOARD.** `_offered()` is still written and is no longer
    sent — the rewrite to one-question-per-turn dropped it, so each turn now sees only the
    bare sentence and its enum. That is `built-and-never-called` AGAIN, in code written to
    demonstrate the fix for a different instance of it.

  2 **CREATION VERBS BIAS TO `must_become`.** "create a vm named alpha" wants
    which_ones=name:alpha + how_many=(eq,1) and the model answers must_become. The
    contrastive pair that rescued `network=dmz` is the same pair that mis-sorts a creation,
    because "create" genuinely sounds like something becoming true.

⇒ SO THE HONEST STATE IS: the FORMULA is measured and sound (31/31, 293/293, commutative,
  order recovered). THE FILLING IS NOT WORKING at request scale and the numbers above are
  what that looks like. Do not quote the isolated 10/10 as if it were a system result.
"""
import argparse
import json
from typing import Dict, List, Optional

from planner.formula.fold import fold
from planner.formula.holdout import HELD_OUT
from planner.formula.legal import Board
from planner.formula.pipeline import Outcome, run, show
from planner.formula.slots import Move

_PROMPT = """You are filling in a form about one sentence. Answer only what the sentence says.

Answer EVERY question. Where the sentence does not answer one, give an empty list (or null)
— do not guess, do not invent a name, and do not carry anything over from what you know.

  what kind of thing is this about?
  which ones? (conditions that pick them out)
  which ones are excluded?
  how many should there be, and is that exactly / at least / at most?
  what must become true of them?
  what should we go and check about them?
  what new thing should be made for each one?
  what is it copied from?

Use only the words offered to you."""


def _schema(offers: Dict[str, object]) -> Dict[str, object]:
    """A grammar built from THIS kind's legal moves. Never a fixed schema.

    Where the manifest declares a closed set the schema is an enum, so an illegal value is
    not merely rejected afterwards — it cannot be decoded in the first place.

    ⇒ EVERY FIELD IS REQUIRED, AND MEASURED SO. With optional fields the 8B model returned
      `{}` — a valid completion, and the shortest one, so a grammar that permits it gets it.
      Making the same fields required, with an EMPTY LIST as the way to say "the sentence
      does not answer this", turned that same request into a clean fill on the first draw.
      It is the `pattern: ^\\$` lesson again: a grammar that cannot refuse has no teeth.
    """
    attrs = list(offers.get("filter") or [])
    settable = list(offers.get("target") or [])

    def pairs(allowed: List[str]) -> Dict[str, object]:
        return {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["attribute", "value"],
                "properties": {
                    "attribute": ({"type": "string", "enum": allowed} if allowed
                                  else {"type": "string"}),
                    "value": {"type": ["string", "boolean", "integer"]},
                },
            },
        }

    props: Dict[str, object] = {
        "which_ones": pairs(attrs),
        "excluded": pairs(attrs),
        # nullable rather than absent: the model must decide, and saying "no number" is an
        # answer it has to give rather than a field it can walk past.
        "how_many": {
            "type": ["object", "null"], "additionalProperties": False,
            "required": ["number", "at"],
            "properties": {
                "number": {"type": "integer"},
                "at": {"type": "string", "enum": list(offers.get("count") or ["eq"])},
            },
        },
        "must_become": pairs(settable),
    }
    # the remaining slots are arrays of a closed set — empty means "the sentence says none".
    for name, values in (("go_and_check", offers.get("fact")),
                         ("make_one_each", offers.get("makes")),
                         ("they_must_all", offers.get("predicate"))):
        if values:
            props[name] = {"type": "array", "items": {"type": "string", "enum": list(values)}}
    if offers.get("source"):
        props["copied_from"] = {"type": ["string", "null"]}
    return {"type": "object", "additionalProperties": False,
            "required": sorted(props), "properties": props}


def _offered(offers: Dict[str, object]) -> str:
    """The legal moves, in words. This is the board handed to the model."""
    lines = [f"the thing: {offers['subject']}"]
    closed = offers.get("_closed_values") or {}
    if offers.get("filter"):
        lines.append("conditions you may use: " + ", ".join(offers["filter"]))
    for attr, values in closed.items():
        lines.append(f"  {attr} can only be: {', '.join(values)}")
    if offers.get("target"):
        lines.append("things you may require: " + ", ".join(offers["target"]))
    if offers.get("fact"):
        lines.append("things you may go and check: " + ", ".join(offers["fact"]))
    if offers.get("makes"):
        lines.append("things you may make one of per member: " + ", ".join(offers["makes"]))
    return "\n".join(lines)


NOT_SAID = "no"


def _pairs_schema(allowed: List[str]) -> Dict[str, object]:
    return {
        "type": "object", "additionalProperties": False, "required": ["answer"],
        "properties": {"answer": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["attribute", "value"],
                "properties": {
                    "attribute": {"type": "string", "enum": allowed},
                    "value": {"type": ["string", "boolean", "integer"]},
                },
            },
        }},
    }


def _pick_schema(allowed: List[str]) -> Dict[str, object]:
    # NOT_SAID FIRST, deliberately. The eight-field form degenerated to picking the first
    # enum member for every sentence; putting the refusal first means that failure, if it
    # returns, shows up as a silent flood of `no` rather than a flood of plausible answers.
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": [NOT_SAID] + list(allowed)}}}


def _turns_for(offers: Dict[str, object]) -> List[tuple]:
    """ONE QUESTION PER TURN, and only the questions this kind can legally answer.

    ⇒ THIS IS THE WHOLE MEASUREMENT OF 2026-08-07. The same model, the same sentences:
        eight fields in one call  -> the SAME answer for every sentence. It stopped reading
                                     and returned the first enum member each time.
        two fields in one call    -> clean.
        one question per call     -> 10 of 10 correct, with the refusal listed FIRST so the
                                     positional bias was ruled out rather than assumed.
      The operator's own framing had it right — *"make the AI fill the formula EACH TURN,
      using staged lowering"* — and collapsing that into one call is what broke it.
    """
    attrs = list(offers.get("filter") or [])
    out: List[tuple] = []
    if attrs and offers.get("target"):
        # ASKED TOGETHER, ON PURPOSE, AND MEASURED SO. These two are the only pair in the
        # form that DISAMBIGUATE EACH OTHER — one is what is already true and picks the set
        # out, the other is what is not true yet and must become so. Asked alone, each came
        # back empty; asked as a contrastive pair, both filled. One-question-per-turn is the
        # rule; a question that needs a foil is one question.
        out.append((
            "_which_and_must",
            "which_ones  = the conditions that pick out WHICH ones the sentence is about "
            "(already true of them)\n"
            "must_become = what the sentence says should BECOME true of them (not true yet)\n"
            "Use an empty list where the sentence gives none.",
            {"type": "object", "additionalProperties": False,
             "required": ["which_ones", "must_become"],
             "properties": {"which_ones": _pairs_schema(attrs)["properties"]["answer"],
                            "must_become": _pairs_schema(list(offers["target"]))
                            ["properties"]["answer"]}},
        ))
    elif attrs:
        out.append((
            "which_ones",
            "List the conditions the sentence uses to pick out WHICH ones it is about. "
            "Only conditions actually stated. If it is about all of them, answer with an "
            "empty list.",
            _pairs_schema(attrs),
        ))
    if attrs:
        out.append((
            "excluded",
            "List anything the sentence explicitly EXCLUDES or sets aside — the 'except X' "
            "part. If nothing is excluded, answer with an empty list.",
            _pairs_schema(attrs),
        ))
    out.append((
        "how_many",
        "If the sentence says HOW MANY there should be, give the number and whether that is "
        "exactly, at least, or at most. If it gives no number, answer null.",
        {"type": "object", "additionalProperties": False, "required": ["answer"],
         "properties": {"answer": {
             "type": ["object", "null"], "additionalProperties": False,
             "required": ["number", "at"],
             "properties": {"number": {"type": "integer"},
                            "at": {"type": "string",
                                   "enum": list(offers.get("count") or ["eq"])}}}}},
    ))
    if offers.get("fact"):
        out.append((
            "fact",
            "Answer with the thing to check ONLY if the sentence asks us to go and find out "
            f"something we do not already know. Otherwise answer {NOT_SAID!r}.",
            _pick_schema(list(offers["fact"])),
        ))
    if offers.get("makes"):
        out.append((
            "makes",
            "Answer with the thing to create ONLY if the sentence says a NEW one should be "
            f"made for each member. Otherwise answer {NOT_SAID!r}.",
            _pick_schema(list(offers["makes"])),
        ))
    if offers.get("predicate"):
        out.append((
            "predicate",
            "Answer 'reach' ONLY if the sentence says they must all be able to reach or ping "
            f"each other. Otherwise answer {NOT_SAID!r}.",
            _pick_schema(list(offers["predicate"])),
        ))
    if offers.get("source"):
        out.append((
            "source",
            "If the sentence says these are COPIED or CLONED from something, name what they "
            "are copied from. Otherwise answer null.",
            {"type": "object", "additionalProperties": False, "required": ["answer"],
             "properties": {"answer": {"type": ["string", "null"]}}},
        ))
    return out


def model_filler(model: str = None, temp: float = 0.0, timeout: int = 300,
                 record: Optional[List] = None):
    """A filler that asks the real model for VALUES only — one question at a time."""
    from engines.channel import constrained

    def fill(claim: str, offers: Dict[str, object]) -> Dict[str, object]:
        raw: Dict[str, object] = {}
        for slot, question, schema in _turns_for(offers):
            prompt = (f"{question}\n\nAnswer only from the sentence. Do not guess, do not "
                      f"invent a name, and do not use anything you know about {offers['subject']}s "
                      f"in general.")
            try:
                got = constrained(prompt, f"the sentence: {claim}", schema,
                                  model=model, temp=temp, timeout=timeout) or {}
            except Exception as exc:
                raw[slot] = f"call failed: {type(exc).__name__}"
                continue
            if slot == "_which_and_must":
                raw["which_ones"] = got.get("which_ones")
                raw["must_become"] = got.get("must_become")
            else:
                raw[slot] = got.get("answer")
        if record is not None:
            record.append((claim, raw))
        return _to_slots(raw)

    return fill


def _to_slots(got: Dict[str, object]) -> Dict[str, object]:
    """The turns' answers become slots. NOTHING HERE CHOOSES A SHAPE — it is a rename."""
    out: Dict[str, object] = {}
    for answered, slot in (("which_ones", "filter"), ("excluded", "except"),
                           ("must_become", "target")):
        pairs = {c["attribute"]: c["value"] for c in (got.get(answered) or [])
                 if isinstance(c, dict) and "attribute" in c}
        if pairs:
            out[slot] = pairs
    how = got.get("how_many")
    if isinstance(how, dict) and how.get("number") is not None:
        out["count"] = (str(how.get("at") or "eq"), int(how["number"]))
    for slot in ("fact", "makes", "predicate", "source"):
        value = got.get(slot)
        if (not value or not isinstance(value, str)
                or value.strip().lower() in {NOT_SAID, "null", "none", "n/a", "-"}):
            continue
        out[slot] = (value, None) if slot == "makes" else value
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rungs", action="store_true", help="the fourteen rungs instead")
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", type=int, default=None)
    args = ap.parse_args()

    if args.rungs:
        from tests.bench.rungs import RUNGS
        jobs = [(r.n, r.goal, None) for r in RUNGS]
    else:
        jobs = [(h.n, h.request, h) for h in HELD_OUT]
    if args.only:
        jobs = [j for j in jobs if j[0] == args.only]

    board = Board()
    print("=" * 100)
    print("THE MODEL FILLS THE FORM — it is never shown a shape, a keyword, or a structure")
    print("=" * 100)
    for n, request, held in jobs:
        record: List = []
        outcome = run(request, model_filler(model=args.model, record=record), board=board)
        tag = f" [{held.verdict}]" if held else ""
        print(f"\n{'─' * 100}\n{n:>3}{tag}")
        show(outcome)
        for claim, raw in record:
            print(f"      raw “{claim}” -> {json.dumps(raw, sort_keys=True, default=str)}")


if __name__ == "__main__":
    main()
