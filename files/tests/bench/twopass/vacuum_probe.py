"""CAN THE MODEL SEE THESE PHENOMENA AT ALL? — the harness-vs-model question, in a vacuum.

    PYTHONPATH=. python3 -m tests.bench.twopass.vacuum_probe --framing move --runs 3
    PYTHONPATH=. python3 -m tests.bench.twopass.vacuum_probe --framing describe --runs 3

    ⚠ NEEDS THE MODEL LOADED. `ollama stop llama3.1:8b` was run to free the GPU; the first
      call will pay a reload. Rule V4: never run this and a suite at the same time.

# ⇒⇒ THE QUESTION THIS ANSWERS, AND IT IS THE OPERATOR'S

> *"make sure is something any LLM needs to know, as well as some of the other stuff we
> encountered today, so i am wondering if it can identify them in a vacuum — or is our harness
> capturing it wrong?"*

Two very different worlds, and everything we build next depends on which one we are in:

    IT CAN, IN A VACUUM      then the pipeline is LOSING something the model already has, and
                             the fix is in the harness — a question asked at the wrong moment,
                             or an answer discarded downstream.
    IT CANNOT                then no prompt will retrieve it, and every one of these must be
                             computed from the request's own markers, as `mood_of` already is.

⇒ **AND THE TWO FRAMINGS ARE THE DIAGNOSTIC, NOT A STYLE CHOICE.** Rule W7b was measured
  repeatedly: a question whose answer DESCRIBES its own understanding degrades, while one whose
  answer is a CHOICE FROM A CLOSED SET performs. *"what does 'it' refer to?"* -> *"the request
  itself"*, 0/3; *"what has to be done?"* -> the right two steps, 3/3.

  So a gap between the arms is itself the finding: **describe-low + move-high means the model
  HAS the distinction and cannot narrate it**, which is precisely the shape that made
  anchor-and-scan work.

# ⇒ NOT ONE SENTENCE HERE IS FROM THE CORPUS, AND THAT IS A RULE NOT A PREFERENCE

[[gorgon-prompt-examples-get-copied]]: a prompt illustrated with a corpus phrase had the
EXAMPLE come back as the answer, voiding a whole day's measurement. These are all ordinary
operations English, none of it in the 14 rungs — which is also the operator's other point:
*"right now we are doing the rungs BUT in the real world it might differ."*

# ⇒ SEALED BEFORE RUNNING (rule V5)

Every `want` below is written before a single call is made. If a later commit edits one to make
a run pass, that is the failure this file exists to make visible.
"""
import argparse
from collections import Counter
from typing import Dict, List, NamedTuple


class Case(NamedTuple):
    tag: str
    phenomenon: str
    sentence: str
    question: str
    options: List[str]
    want: str
    why: str


# ── THE PHENOMENA, EACH ON A SENTENCE THE CORPUS HAS NEVER SEEN ───────────────────────
CASES: List[Case] = [
    # 1 · MOOD — a goal to hold, or an action to perform
    Case("mood-1", "mood", "make sure the cache is warm",
         "Is this asking you to perform an action now, or to bring about a state and keep it "
         "true?", ["perform an action", "bring about a state"], "bring about a state",
         "the operator's own example, on a sentence that is not the corpus's"),
    Case("mood-2", "mood", "warm the cache",
         "Is this asking you to perform an action now, or to bring about a state and keep it "
         "true?", ["perform an action", "bring about a state"], "perform an action",
         "THE CONTROL. If both come back the same the model is not reading mood at all"),

    # 2 · LIGHT VERB — is the noun the thing, or the action
    Case("light-1", "light-verb", "take a backup of the database",
         "In this sentence, is 'backup' the name of a thing that already exists, or the name "
         "of the action being requested?",
         ["a thing that already exists", "the action being requested"],
         "the action being requested", "the light verb empties into the noun"),
    Case("light-2", "light-verb", "delete the backup from last Friday",
         "In this sentence, is 'backup' the name of a thing that already exists, or the name "
         "of the action being requested?",
         ["a thing that already exists", "the action being requested"],
         "a thing that already exists", "THE CONTROL — a contentful verb leaves the noun a thing"),

    # 3 · EFFECTED vs AFFECTED — the create/use fork, on one verb
    Case("effect-1", "effected-affected", "take a photo of the room",
         "Does the photo exist before this is done, or does it come into being because of it?",
         ["it exists already", "it comes into being"], "it comes into being",
         "effected object"),
    Case("effect-2", "effected-affected", "take the photo from the drawer",
         "Does the photo exist before this is done, or does it come into being because of it?",
         ["it exists already", "it comes into being"], "it exists already",
         "affected object — SAME VERB, opposite answer"),

    # 4 · DISTRIBUTIVE vs COLLECTIVE
    Case("dist-1", "distributive", "put the servers in a rack",
         "Does this mean one rack holding all of them, or a separate rack for each?",
         ["one rack for all of them", "a separate rack for each"], "one rack for all of them",
         "unmarked plural defaults to COLLECTIVE"),
    Case("dist-2", "distributive", "put each server in a rack",
         "Does this mean one rack holding all of them, or a separate rack for each?",
         ["one rack for all of them", "a separate rack for each"], "a separate rack for each",
         "`each` is the overt distributive marker"),

    # 5 · RECIPROCITY — how many relations
    Case("recip-1", "reciprocity", "have the nodes trust each other",
         "Does this describe something true of each node on its own, or something that must "
         "hold between PAIRS of nodes?",
         ["true of each node on its own", "between pairs of nodes"], "between pairs of nodes",
         "`each other` is a quantifier over pairs, not a property"),
    Case("recip-2", "reciprocity", "have the nodes report their status",
         "Does this describe something true of each node on its own, or something that must "
         "hold between PAIRS of nodes?",
         ["true of each node on its own", "between pairs of nodes"],
         "true of each node on its own", "THE CONTROL"),

    # 6 · SPECIFIC vs NON-SPECIFIC INDEFINITE — the operator's parked gate 3 case
    Case("spec-1", "specificity", "find a free port and bind to it",
         "Does 'a free port' mean one particular port the speaker has in mind, or any port "
         "that turns out to qualify?",
         ["one particular port", "any port that qualifies"], "any port that qualifies",
         "non-specific indefinite"),
    Case("spec-2", "specificity", "archive a report and email it to me",
         "Could 'a report' here mean either an existing report or one this action creates?",
         ["yes, it is ambiguous", "no, it is clear"], "yes, it is ambiguous",
         "THE OPERATOR'S CASE. If the model sees the ambiguity, gate 3 can ask about it"),

    # 7 · DEFINITE DESCRIPTION — existence AND uniqueness are presupposed
    Case("def-1", "definiteness", "restart the proxy",
         "What does this take for granted about how many proxies there are?",
         ["that there is exactly one", "that there are several", "nothing at all"],
         "that there is exactly one", "uniqueness presupposition — Russell/Strawson"),
    Case("def-2", "definiteness", "restart a proxy",
         "What does this take for granted about how many proxies there are?",
         ["that there is exactly one", "that there are several", "nothing at all"],
         "nothing at all", "THE CONTROL — an indefinite presupposes no uniqueness"),

    # 8 · NEGATION SCOPE — none, or not-all
    Case("neg-1", "negation-scope", "do not restart every worker",
         "Does this forbid restarting any worker at all, or only forbid restarting all of them?",
         ["forbids restarting any", "only forbids restarting all of them"],
         "only forbids restarting all of them",
         "negation over a universal — the reading that silently inverts a program"),

    # 9 · RELATIVE vs ABSOLUTE MEASURE
    Case("degree-1", "relative-measure", "give it two more cores",
         "Is 'two' the number it should end up with, or the number to add to what it has?",
         ["the number it ends up with", "the number to add"], "the number to add",
         "a relative measure — the manifest has only ABSOLUTE setters, so this silently doubles "
         "as an absolute one"),

    # 10 · VAGUE QUANTIFIER — no exact count exists
    Case("vague-1", "vague-quantifier", "restart most of the workers",
         "Does 'most' name an exact number?", ["yes", "no"], "no",
         "there is no count to compute — this must become a question, never a guess"),
]

DESCRIBE_PROMPT = ("Read the sentence and answer the question about it in one short phrase. "
                   "Explain what the sentence means.")

MOVE_PROMPT = ("Read the sentence and answer the question by choosing exactly one of the "
               "options offered. Choose only from the options.")


def _schema(options: List[str], framing: str) -> dict:
    if framing == "move":
        return {"type": "object", "additionalProperties": False, "required": ["answer"],
                "properties": {"answer": {"type": "string", "enum": list(options)}}}
    # ⇒ THE DESCRIBE ARM IS DELIBERATELY OPEN. Closing it would make the arms differ only in
    #   wording, and the whole point is to measure what an OPEN answer costs.
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string"}}}


def ask(case: Case, framing: str, model=None, temp: float = 0.0, timeout: int = 180):
    from engines.channel import constrained
    prompt = MOVE_PROMPT if framing == "move" else DESCRIBE_PROMPT
    payload = f"the sentence: {case.sentence}\n\nthe question: {case.question}"
    if framing == "move":
        payload += "\n\nthe options: " + " | ".join(case.options)
    try:
        got = constrained(prompt, payload, _schema(case.options, framing),
                          model=model, temp=temp, timeout=timeout) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<failed: {type(exc).__name__}>"


def scores(answer, case: Case, framing: str) -> bool:
    """In the MOVE arm this is equality. In DESCRIBE it is generous on purpose.

    ⇒ **THE DESCRIBE ARM IS GRADED LENIENTLY AND THAT PROTECTS THE FINDING.** If it is graded
      strictly and scores low, the result is unreadable — did the model lack the distinction,
      or merely phrase it unexpectedly? Marking it correct whenever the answer CONTAINS the
      key words means a low score can only mean the distinction is absent.
    """
    if not answer or str(answer).startswith("<failed"):
        return False
    said = str(answer).lower()
    if framing == "move":
        return said.strip() == case.want.lower()
    key = [w for w in case.want.lower().split() if len(w) > 3]
    return any(w in said for w in key) if key else case.want.lower() in said


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--framing", default="move", choices=("move", "describe", "both"))
    ap.add_argument("--runs", type=int, default=3, help="rule V3 — never diagnose from n=1")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    framings = ("move", "describe") if args.framing == "both" else (args.framing,)
    tally: Counter = Counter()
    by_phenomenon: Dict[str, Counter] = {}

    print("=" * 100)
    print(f"CAN THE MODEL SEE THESE IN A VACUUM?  framings={','.join(framings)}  n={args.runs}")
    print("=" * 100)

    for case in CASES:
        print(f"\n{case.tag:<9} [{case.phenomenon}] “{case.sentence}”")
        print(f"          want: {case.want}   ({case.why})")
        for framing in framings:
            hits = 0
            for _ in range(args.runs):
                answer = ask(case, framing, model=args.model)
                ok = scores(answer, case, framing)
                hits += ok
                print(f"          {framing:<9} {'ok  ' if ok else 'MISS'} {str(answer)[:66]}")
            tally[framing] += hits
            tally[f"{framing}_total"] += args.runs
            slot = by_phenomenon.setdefault(case.phenomenon, Counter())
            slot[framing] += hits
            slot[f"{framing}_total"] += args.runs

    print(f"\n{'=' * 100}")
    for framing in framings:
        print(f"  {framing:<10} {tally[framing]}/{tally[f'{framing}_total']}")
    print()
    for phenomenon, slot in sorted(by_phenomenon.items()):
        line = "   ".join(f"{f} {slot[f]}/{slot[f'{f}_total']}" for f in framings)
        print(f"  {phenomenon:<20} {line}")
    print("\n  READ IT THIS WAY:")
    print("    move HIGH, describe LOW  -> the model HAS the distinction and cannot narrate it.")
    print("                                Our harness is asking at the wrong moment.")
    print("    both LOW                 -> it is not there to retrieve. Compute it from the")
    print("                                request's markers, as `mood_of` already does.")
    print("    both HIGH                -> the pipeline is discarding an answer it was given.")


if __name__ == "__main__":
    main()
