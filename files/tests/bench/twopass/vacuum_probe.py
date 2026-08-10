"""CAN THE MODEL SEE THESE PHENOMENA AT ALL? — the harness-vs-model question, in a vacuum.

    PYTHONPATH=. python3 -m tests.bench.twopass.vacuum_probe --runs 3

    ⚠ NEEDS THE MODEL. Rule V4: never run this and a suite at the same time.

# ⇒⇒ THE QUESTION, AND IT IS THE OPERATOR'S

> *"make sure is something any LLM needs to know... i am wondering if it can identify them in a
> vacuum — or is our harness capturing it wrong?"*

    IT CAN, IN A VACUUM   the pipeline is LOSING something the model already has; fix the harness
    IT CANNOT             no prompt retrieves it; compute it from markers, as `mood_of` does

# ⇒⇒ THE FIRST RUN IS VOID, AND THE REASON IS THE WHOLE POINT OF RE-READING IT

Run 1 (2026-08-09) reported move 39/51 · describe 39/51. **That number is withdrawn.** Reading
the cases underneath the summary showed TWO defects, both mine, and both fatal to it:

    "warm the cache"      describe -> "perform an action"     CORRECT
                          move     -> "bring about a state"   WRONG

  ⇒ **THE OPTIONS FLIPPED A RIGHT ANSWER INTO A WRONG ONE.** Same model, same sentence. The
    binary was a FALSE DICHOTOMY — every action brings about a state — so *"warm the cache"* is
    a defensible member of both options and the model had no way to divide them. It answered
    the same for both sentences, and the CONTROL is what exposed it.

    "restart the proxy"   describe -> "one"                   graded MISS

  ⇒ **THE GRADER MARKED A CORRECT ANSWER WRONG.** It looked for words longer than three
    characters from *"that there is exactly one"* — `that`, `there`, `exactly` — and `one`
    contains none of them. Substring grading cannot grade a short right answer.

**The operator saw it before the data did:** *"there is no way an AI doesn't know what 'make
sure' means, so i am afraid we touched something."* We had.

# ⇒ WHAT CHANGED, NAMED SO IT CANNOT LOOK LIKE SOFTENING (rule V5)

**A key may not be edited to make a run pass. These are edits to BROKEN QUESTIONS**, and each
is recorded with what it was:

  * `mood` — options were *perform an action / bring about a state*, which do not partition.
    Now: **is the ACTION named, or only the END STATE?** *"warm the cache"* names the action;
    *"make sure the cache is warm"* names only the state and leaves the action open. That is
    the distinction the pipeline actually needs, and it divides cleanly.
  * `recip-2` — the control sentence *"have the nodes report their status"* is genuinely
    ambiguous (report to WHOM? possibly each other). Replaced with one that cannot be read as
    pairwise. The KEY is unchanged.
  * `def-2` — the key was *"nothing at all"*, which is wrong: *"restart a proxy"* does
    presuppose at least one exists. The question conflated EXISTENCE with UNIQUENESS. Now it
    asks only about uniqueness, where the two articles genuinely differ.

# ⇒ AND OPTION ORDER IS MEASURED RATHER THAN AVERAGED AWAY

This project has already measured enum ORDER moving answers — one entry moved from front to
back doubled exact matches and removed every spurious step. So the move arm runs each case
BOTH WAYS, forward and reversed. **A case that answers differently by order has been decided by
position rather than by meaning**, and that is reported as its own column rather than hidden in
an average.

# ⇒ THE DESCRIBE ARM IS JUDGED, NOT SUBSTRING-MATCHED

A second model call asks whether the free answer MEANS THE SAME as the key — a closed yes/no,
which is the form this project has measured as reliable. Every raw answer is printed regardless,
so the judge can be overruled by eye.
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


CASES: List[Case] = [
    # 1 · MOOD — is the ACTION named, or only the END STATE? (options rebuilt, see header)
    Case("mood-1", "mood", "make sure the cache is warm",
         "Does this sentence name the action to carry out, or does it name only the end state "
         "and leave the action open?",
         ["it names the action to carry out", "it names only the end state"],
         "it names only the end state", "the operator's own example"),
    Case("mood-2", "mood", "warm the cache",
         "Does this sentence name the action to carry out, or does it name only the end state "
         "and leave the action open?",
         ["it names the action to carry out", "it names only the end state"],
         "it names the action to carry out",
         "THE CONTROL. Run 1 answered these two identically and the control caught it"),

    # 2 · LIGHT VERB
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

    # 3 · EFFECTED vs AFFECTED
    Case("effect-1", "effected-affected", "take a photo of the room",
         "Does the photo exist before this is done, or does it come into being because of it?",
         ["it exists already", "it comes into being"], "it comes into being", "effected"),
    Case("effect-2", "effected-affected", "take the photo from the drawer",
         "Does the photo exist before this is done, or does it come into being because of it?",
         ["it exists already", "it comes into being"], "it exists already",
         "affected — SAME VERB, opposite answer"),

    # 4 · DISTRIBUTIVE vs COLLECTIVE
    Case("dist-1", "distributive", "put the servers in a rack",
         "Does this mean one rack holding all of them, or a separate rack for each?",
         ["one rack for all of them", "a separate rack for each"], "one rack for all of them",
         "unmarked plural defaults to COLLECTIVE"),
    Case("dist-2", "distributive", "put each server in a rack",
         "Does this mean one rack holding all of them, or a separate rack for each?",
         ["one rack for all of them", "a separate rack for each"], "a separate rack for each",
         "`each` is the overt distributive marker"),

    # 5 · RECIPROCITY  (control sentence replaced — see header)
    Case("recip-1", "reciprocity", "have the nodes trust each other",
         "Does this describe something true of each node on its own, or something that must "
         "hold between PAIRS of nodes?",
         ["true of each node on its own", "between pairs of nodes"], "between pairs of nodes",
         "`each other` quantifies over pairs"),
    Case("recip-2", "reciprocity", "have the nodes write their uptime to a log file",
         "Does this describe something true of each node on its own, or something that must "
         "hold between PAIRS of nodes?",
         ["true of each node on its own", "between pairs of nodes"],
         "true of each node on its own",
         "THE CONTROL, rewritten: the old one asked nodes to REPORT, which can be read as "
         "reporting to one another"),

    # 6 · SPECIFIC vs NON-SPECIFIC INDEFINITE
    Case("spec-1", "specificity", "find a free port and bind to it",
         "Does 'a free port' mean one particular port the speaker already has in mind, or any "
         "port that turns out to qualify?",
         ["one particular port", "any port that qualifies"], "any port that qualifies",
         "non-specific indefinite"),
    Case("spec-2", "specificity", "archive a report and email it to me",
         "Could 'a report' here mean either a report that already exists or one this action "
         "creates?", ["yes, it could mean either", "no, only one reading is possible"],
         "yes, it could mean either",
         "THE OPERATOR'S PARKED GATE 3 CASE. If the model sees the ambiguity, gate 3 can ask"),

    # 7 · DEFINITENESS — uniqueness ONLY (key corrected, see header)
    Case("def-1", "definiteness", "restart the proxy",
         "Does this sentence take for granted that there is only ONE proxy?",
         ["yes, only one", "no, there could be several"], "yes, only one",
         "uniqueness presupposition — Russell/Strawson"),
    Case("def-2", "definiteness", "restart a proxy",
         "Does this sentence take for granted that there is only ONE proxy?",
         ["yes, only one", "no, there could be several"], "no, there could be several",
         "THE CONTROL — an indefinite presupposes existence but NOT uniqueness, which is what "
         "run 1's key got wrong"),

    # 8 · NEGATION SCOPE
    Case("neg-1", "negation-scope", "do not restart every worker",
         "Does this forbid restarting any worker at all, or only forbid restarting all of them?",
         ["forbids restarting any", "only forbids restarting all of them"],
         "only forbids restarting all of them", "negation over a universal"),

    # 9 · RELATIVE vs ABSOLUTE MEASURE
    Case("degree-1", "relative-measure", "give it two more cores",
         "Is 'two' the number it should end up with, or the number to add to what it has?",
         ["the number it ends up with", "the number to add"], "the number to add",
         "the manifest has only ABSOLUTE setters, so this silently becomes absolute"),

    # 10 · VAGUE QUANTIFIER
    Case("vague-1", "vague-quantifier", "restart most of the workers",
         "Does 'most' name an exact number?", ["yes", "no"], "no",
         "no count exists to compute — this must become a question"),
]

# ── SECOND BLOCK · THE SAME PHENOMENA IN DIFFERENT GRAMMAR ────────────────────────────
#
# ⇒ **ONE SENTENCE PER PHENOMENON MEASURES A SENTENCE, NOT A PHENOMENON.** The operator:
#   *"run it a few times, with different grammar and sentences."* These vary the construction —
#   passive, subordinate clause, question form, a different light verb — so a result that turns
#   on one phrasing shows up as a split rather than as a score.
CASES += [
    Case("mood-3", "mood", "the queue should be empty before the job starts",
         "Does this sentence name the action to carry out, or does it name only the end state "
         "and leave the action open?",
         ["it names the action to carry out", "it names only the end state"],
         "it names only the end state", "modal `should` instead of `make sure`"),
    Case("mood-4", "mood", "empty the queue before the job starts",
         "Does this sentence name the action to carry out, or does it name only the end state "
         "and leave the action open?",
         ["it names the action to carry out", "it names only the end state"],
         "it names the action to carry out", "CONTROL, same clause structure"),
    Case("light-3", "light-verb", "run a health check on the gateway",
         "In this sentence, is 'check' the name of a thing that already exists, or the name of "
         "the action being requested?",
         ["a thing that already exists", "the action being requested"],
         "the action being requested", "a different light verb — `run`"),
    Case("effect-3", "effected-affected", "write a summary of the incident",
         "Does the summary exist before this is done, or does it come into being because of it?",
         ["it exists already", "it comes into being"], "it comes into being",
         "a contentful creator verb, not a light one"),
    Case("effect-4", "effected-affected", "email the summary to the team",
         "Does the summary exist before this is done, or does it come into being because of it?",
         ["it exists already", "it comes into being"], "it exists already", "CONTROL"),
    Case("dist-3", "distributive", "the reports were filed in a folder",
         "Does this mean one folder holding all of them, or a separate folder for each?",
         ["one folder for all of them", "a separate folder for each"],
         "one folder for all of them", "PASSIVE voice, unmarked plural"),
    Case("dist-4", "distributive", "file every report in its own folder",
         "Does this mean one folder holding all of them, or a separate folder for each?",
         ["one folder for all of them", "a separate folder for each"],
         "a separate folder for each", "`its own` as the distributive marker, not `each`"),
    Case("recip-3", "reciprocity", "the services must be able to reach one another",
         "Does this describe something true of each service on its own, or something that must "
         "hold between PAIRS of services?",
         ["true of each service on its own", "between pairs of services"],
         "between pairs of services", "`one another`, and a modal"),
    Case("spec-3", "specificity", "pick a mirror and download from it",
         "Does 'a mirror' mean one particular mirror the speaker already has in mind, or any "
         "mirror that turns out to qualify?",
         ["one particular mirror", "any mirror that qualifies"], "any mirror that qualifies",
         "a different light-ish verb"),
    Case("def-3", "definiteness", "the certificate expires on Friday",
         "Does this sentence take for granted that there is only ONE certificate?",
         ["yes, only one", "no, there could be several"], "yes, only one",
         "a definite in a STATEMENT rather than a command"),
    Case("neg-2", "negation-scope", "all the workers should not be restarted",
         "Does this forbid restarting any worker at all, or only forbid restarting all of them?",
         ["forbids restarting any", "only forbids restarting all of them"],
         "forbids restarting any",
         "`all ... not` — the OPPOSITE scope from `not ... every`, on the same two words"),
    Case("degree-2", "relative-measure", "double the memory on that host",
         "Is the new amount stated outright, or does it depend on what the host has now?",
         ["stated outright", "depends on what it has now"], "depends on what it has now",
         "a multiplier rather than `more`"),
    Case("vague-2", "vague-quantifier", "restart a few of the workers",
         "Does 'a few' name an exact number?", ["yes", "no"], "no",
         "a different vague quantifier"),
]

DESCRIBE_PROMPT = ("Read the sentence and answer the question about it in one short phrase.")
MOVE_PROMPT = ("Read the sentence and answer the question by choosing exactly one of the "
               "options offered. Choose only from the options.")
JUDGE_PROMPT = ("Two answers to the same question are given. Say whether they mean the same "
                "thing. Ignore wording, length and phrasing entirely.")


def _enum_schema(options: List[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": list(options)}}}


def _open_schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string"}}}


def _call(prompt, payload, schema, model, timeout=180):
    from engines.channel import constrained
    try:
        got = constrained(prompt, payload, schema, model=model, temp=0.0, timeout=timeout) or {}
        return got.get("answer")
    except Exception as exc:
        return f"<failed: {type(exc).__name__}>"


def ask_move(case: Case, reversed_order: bool, model=None):
    options = list(reversed(case.options)) if reversed_order else list(case.options)
    payload = (f"the sentence: {case.sentence}\n\nthe question: {case.question}"
               f"\n\nthe options: " + " | ".join(options))
    return _call(MOVE_PROMPT, payload, _enum_schema(options), model)


def ask_describe(case: Case, model=None):
    payload = f"the sentence: {case.sentence}\n\nthe question: {case.question}"
    return _call(DESCRIBE_PROMPT, payload, _open_schema(), model)


def judged_same(answer, want: str, question: str, model=None) -> bool:
    """Does the free answer MEAN the key? A closed yes/no, judged by the model.

    ⇒ Substring matching graded *"one"* as a miss against *"that there is exactly one"*, which
      is how run 1 scored the definiteness cases at zero while the model was answering
      correctly. A judge cannot make that particular mistake; every raw answer is printed
      anyway so it can be overruled by eye.
    """
    if not answer or str(answer).startswith("<failed"):
        return False
    payload = (f"the question that was asked: {question}\n\n"
               f"answer A: {answer}\n\nanswer B: {want}")
    got = _call(JUDGE_PROMPT, payload, _enum_schema(["yes, the same", "no, different"]), model)
    return got == "yes, the same"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="rule V3 — never diagnose from n=1")
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", default=None, help="one phenomenon")
    args = ap.parse_args()

    tally: Counter = Counter()
    by_phenomenon: Dict[str, Counter] = {}
    order_split: List[str] = []

    print("=" * 104)
    print(f"CAN THE MODEL SEE THESE IN A VACUUM?  n={args.runs}  "
          f"(move runs BOTH option orders; describe is model-judged)")
    print("=" * 104)

    for case in CASES:
        if args.only and case.phenomenon != args.only:
            continue
        print(f"\n{case.tag:<9} [{case.phenomenon}] “{case.sentence}”")
        print(f"          want: {case.want}")
        fwd = rev = desc = 0
        for _ in range(args.runs):
            a = ask_move(case, False, args.model)
            b = ask_move(case, True, args.model)
            d = ask_describe(case, args.model)
            ok_a, ok_b = a == case.want, b == case.want
            ok_d = judged_same(d, case.want, case.question, args.model)
            fwd += ok_a
            rev += ok_b
            desc += ok_d
            print(f"          forward  {'ok  ' if ok_a else 'MISS'} {str(a)[:52]}")
            print(f"          reversed {'ok  ' if ok_b else 'MISS'} {str(b)[:52]}")
            print(f"          describe {'ok  ' if ok_d else 'MISS'} {str(d)[:52]}")
        if fwd != rev:
            order_split.append(f"{case.tag} (forward {fwd}/{args.runs}, reversed {rev}/{args.runs})")
        for key, hit in (("forward", fwd), ("reversed", rev), ("describe", desc)):
            tally[key] += hit
            tally[f"{key}_total"] += args.runs
            slot = by_phenomenon.setdefault(case.phenomenon, Counter())
            slot[key] += hit
            slot[f"{key}_total"] += args.runs

    print(f"\n{'=' * 104}")
    for key in ("forward", "reversed", "describe"):
        print(f"  {key:<10} {tally[key]}/{tally[f'{key}_total']}")
    print()
    for phenomenon, slot in sorted(by_phenomenon.items()):
        print(f"  {phenomenon:<20} " + "   ".join(
            f"{k} {slot[k]}/{slot[f'{k}_total']}" for k in ("forward", "reversed", "describe")))
    print(f"\n  DECIDED BY OPTION ORDER RATHER THAN MEANING: {order_split or 'none'}")
    print("\n  READ IT THIS WAY:")
    print("    all three HIGH   -> the model HAS it. Any pipeline failure is OURS.")
    print("    all three LOW    -> not there to retrieve. Compute it from the markers.")
    print("    order split      -> that case measured nothing; the options decided it.")


if __name__ == "__main__":
    main()
