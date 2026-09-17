"""build_cases.py — THE CLAUSE-CUT SPEC, and its gold, written from ENGLISH.

⇒⇒ **`_first_cut`'S DOCSTRING DESCRIBES EIGHT RULES. A DESCRIPTION IS NOT A SPEC.** It says where
a cut is licensed and says nothing about where one is FORBIDDEN, and the forbidden half is the
whole risk: a restored comma splits a clause, and a clause split in the wrong place loses a span,
an act, or an attachment. The v2 price for having no comma at all was 7 spans, 4 acts and 10
attachments; the price for putting one in the wrong place has never been measured, because a
corpus written from the code would only ever confirm the code.

⇒ **SO THE GOLD COMES FROM ENGLISH, RULE BY RULE, AS A PAIR.** For each of the eight, the
construction it exists to catch, and the construction where the SAME closed-class words appear
and English has no boundary. The second half is where the number lives.

⇒⇒ THE SPEC — eight licences, each with what it must refuse:

    1  A LEADING COURTESY LITERAL closes at the literal's end.
       cut     `when you get a chance stop alpha`      ->  after `chance`
       refuse  the literal is closed; nothing else may claim to be one

    2  A MID-CLAUSE WRAPPER opens its own clause.
       cut     `stop alpha tell me when it is down`    ->  before `tell`
       refuse  `tell me which vms are up`  — a wrapper at position 0 is the clause, not
               a second one, and cutting at 0 would cut nothing off

    3  `anyway` RELEASES WHAT STANDS BEHIND IT — and is set off on BOTH sides.
       cut     `stop alpha anyway restart beta`        ->  before `anyway` AND before
               `restart`. The first freeze's gold named one cut; two is the English, so the
               GOLD was wrong and the rule was right (corrected 2026-09-17).
       refuse  nothing to refuse — `anyway` is a single closed word with one job

    4  A MID-CLAUSE CONDITION HEAD ({if, unless} + EVENTS) opens a subordinate.
       cut     `restart alpha if it is down`           ->  before `if`
       refuse  `tell me if the db restarted`  — whether-`if` ASKS, it does not condition
       refuse  `three vms named after musicians`  — a NAMING CUE before the head makes it
               a naming spec, one leaf, not a temporal clause

    5  A PIECE-INITIAL CONDITION HEAD's subordinate ends after its PREDICATE.
       cut     `if alpha is stopped launch it`         ->  before `launch`
       refuse  `if the biggest vm on the lab network is stopped restart it` must cut ONLY
               after `stopped` — a long subject may never fake the boundary, and nothing
               cuts before the predicate has been seen

    6  A SECOND IMPERATIVE is its own clause.
       cut     `dont stop the web vm stop the db vm`   ->  before the second `stop`
       refuse  `how many machines carry the fleet label`  — a QUESTION SKIN is never cut:
               the wh/aux frame governs the whole clause and `carry the` is no imperative
               inside it
       refuse  `check the disk usage`  — one imperative is one clause

    7  A TESTIMONY PREDICATE releases its elaboration.
       cut     `vm2 is not working it boots to a bluescreen`  ->  before `it`
       refuse  fewer than three words remaining is no elaboration — no vote, no cut
       refuse  **`put cant on the dmz network`** — an IMPERATIVE is not testimony. Found by
               the random-English sweep on 2026-09-17: one survivor in 3000 sentences, and
               it was this rule reading an operator's order as a report about a thing.

    8  A GOAL HEAD's complement is a CLAUSE, not an object.
       refuse  `make sure exactly three vms carry the prod label` — the noun phrase after
               the head is a SUBJECT and the first base-form op after it is its PREDICATE.
               A cut here loses `label=prod` and leaves `count(vm)=3`: the DELETION shape,
               language benchmark rung 7. This rule exists only to REFUSE.

⇒ THE GOLD IS THE WORD A CUT PRECEDES, never an offset. `merge_cut_points` returns absolute
  offsets; a gold written in offsets would break on every rewording and would tempt whoever
  fixed it to read the answer off the code.

⇒ OUT OF SCOPE AND SAID SO, from `_first_cut`'s own note: bare-name lists without commas
  (scan's NP reading) and value respeaks without commas (self_repair's). Named, not forgotten.

Usage:  PYTHONPATH=. python3 -m tests.bench.cut_eval.build_cases
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cases.jsonl")

CASES: list = []


def case(rule: int, bucket: str, text: str, before: list, why: str) -> None:
    """`before` — the words each restored comma must precede, in order. Empty = no cut."""
    CASES.append({"id": f"c{rule}-{len([c for c in CASES if c['rule'] == rule]) + 1:02d}",
                  "rule": rule, "bucket": bucket, "text": text, "before": before, "why": why})


# 1 · a leading courtesy literal
case(1, "must_cut", "when you get a chance stop alpha", ["stop"],
     "the courtesy literal closes at its own end; the order behind it is its own clause")
case(1, "must_cut", "if you get a chance restart the web vm", ["restart"],
     "the other declared courtesy literal, same shape")

# 2 · a mid-clause wrapper
case(2, "must_cut", "stop alpha tell me when it is down", ["tell"],
     "a WRAPPER mid-clause opens its own clause")
case(2, "must_not_cut", "tell me which vms are up", [],
     "a wrapper at position 0 IS the clause — cutting at 0 cuts nothing off")
case(2, "must_not_cut", "let me know which vms are up", [],
     "the other declared wrapper, also clause-initial")

# 3 · anyway
# ⇒ TWO CUTS, NOT ONE — GOLD CORRECTED 2026-09-17. The first freeze named one cut and the rule
#   produced two; `stop alpha, anyway, restart beta` is the English, so the GOLD was wrong and
#   the rule was right. Recorded rather than quietly amended: a corpus whose author silently
#   retro-fits its answers to the code measures the code against itself, which is the one thing
#   this whole eval exists to avoid.
case(3, "must_cut", "stop alpha anyway restart beta", ["anyway", "restart"],
     "`anyway` releases what stands behind it — the word is set off on BOTH sides, so the "
     "clause behind it opens too")

# 4 · a mid-clause condition head
case(4, "must_cut", "restart alpha if it is down", ["if"],
     "a mid-clause condition head opens a subordinate; cut in front of it")
case(4, "must_cut", "stop the web vm unless it is the last one", ["unless"],
     "`unless` is the other declared head")
case(4, "must_not_cut", "tell me if the db vm restarted", [],
     "whether-`if` ASKS and does not condition — the host word before it is the guard")
case(4, "must_not_cut", "let me know if alpha is up", [],
     "the same whether-`if`, behind the other wrapper host")
case(4, "must_not_cut", "create three vms named after musicians", [],
     "a NAMING CUE before the head makes this a naming spec, one leaf (ledger #17)")

# 5 · a piece-initial condition head
case(5, "must_cut", "if alpha is stopped launch it", ["launch"],
     "the subordinate ends after its predicate; the imperative behind it is its own clause")
case(5, "must_cut", "unless the db vm is running restart it", ["restart"],
     "same shape behind `unless`")
case(5, "must_not_cut", "if the biggest vm on the lab network is stopped", [],
     "a long subject may not fake a boundary, and no imperative follows the predicate")
case(5, "must_not_cut", "when you get a chance", [],
     "a subordinate's own content cannot open an imperative before its predicate")

# 6 · a second imperative
case(6, "must_cut", "dont stop the web vm stop the db vm", ["stop the db"],
     "a second base-form operation word taking a determiner object is its own clause")
case(6, "must_cut", "restart the web vm snapshot the db vm", ["snapshot"],
     "two bare imperatives, no punctuation between them")
case(6, "must_not_cut", "check the disk usage", [],
     "one imperative is one clause")
case(6, "must_not_cut", "how many machines carry the fleet label", [],
     "a QUESTION SKIN is never cut — the wh frame governs the whole clause and `carry the` "
     "is no imperative inside it")
case(6, "must_not_cut", "did you stop the web vm", [],
     "an AUXILIARY opening inverts and asks; the frame governs the whole clause")
case(6, "must_not_cut", "stop the web vm on the lab network", [],
     "a prepositional tail is not a second imperative")

# 7 · a testimony predicate
case(7, "must_cut", "vm2 is not working it boots to a bluescreen", ["it"],
     "a testimony predicate releases its elaboration; three or more words remain")
case(7, "must_not_cut", "the web vm is not working", [],
     "nothing follows the predicate — no elaboration, no cut")
case(7, "must_not_cut", "alpha is down now", [],
     "fewer than three words remain behind the predicate — no vote, no cut")
# ⚠ THE CASE THE RANDOM SWEEP FOUND, 2026-09-17
case(7, "must_not_cut", "put cant on the dmz network", [],
     "an IMPERATIVE is not testimony. The only survivor of 3000 random English sentences: "
     "`put cant on` was read as a predicate and `the dmz network` as its elaboration, "
     "splitting an operator's order in half")
case(7, "must_not_cut", "put web on the dmz network", [],
     "the same order with a real machine name — the control for the case above")

# 8 · a goal head — this rule exists only to REFUSE
case(8, "must_not_cut", "make sure exactly three vms carry the prod label", [],
     "the noun phrase after a GOAL head is a SUBJECT and the base-form op after it is its "
     "PREDICATE. A cut loses `label=prod` and leaves `count(vm)=3` — the deletion shape, "
     "language benchmark rung 7 (2026-08-22)")
case(8, "must_not_cut", "ensure every vm carries the fleet label", [],
     "the second declared goal head, same shape")
case(8, "must_not_cut", "verify that the db vm holds a snapshot", [],
     "the third, with an explicit complementiser")


def main() -> None:
    os.makedirs(HERE, exist_ok=True)
    with open(OUT, "w") as f:
        for c in CASES:
            f.write(json.dumps(c) + "\n")
    from collections import Counter
    print(f"wrote {len(CASES)} cases -> {OUT}")
    for k, v in sorted(Counter(c["bucket"] for c in CASES).items()):
        print(f"  {k:<14}{v:>4}")
    print("  by rule: " + "  ".join(
        f"{r}:{n}" for r, n in sorted(Counter(c["rule"] for c in CASES).items())))


if __name__ == "__main__":
    main()
