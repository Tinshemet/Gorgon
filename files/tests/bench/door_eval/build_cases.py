"""build_cases.py — the front door's gold, written from the CONTRACT and frozen before it runs.

⇒⇒ **THE GOLD IS WRITTEN BLIND, AND THAT IS THE WHOLE METHOD.** A corpus built by running the
door and recording what it did would have "whatever it currently does" as its gold, and scoring
against it would measure nothing — the door would be graded against itself and could never fail.
So every `expect` below is derived from the module's stated contract and the operator's rulings,
with the door NOT run, and the file is frozen before a single case is scored. What comes out is a
DISAGREEMENT LIST, and each disagreement is one of two things: a door defect, or a gold error.
The operator rules on which. That is the seal pattern ([[gorgon-the-seal-pattern]]) at the size
this surface needs.

⇒ **WHERE AGREEMENT IS CHEAP AND WHERE IT IS NOT — say it rather than let a number hide it.**
  · `must_repair` pauses and phrase typos are MECHANICAL: the contract states the rule in one
    line ("dropped with its separator"; "the odd word >=4 letters at Damerau distance 1"), so the
    gold is a re-reading of a rule and agreement is expected. These cases price RECALL, not
    judgement — they catch a repair that stopped firing, nothing subtler.
  · `must_not_touch` and `ambiguous` are JUDGEMENT. `forgot it` is one edit from the retraction
    `forget it` and is an ordinary English sentence; `made that` is one edit from `make that`.
    The module's own docstring names this as accepted residual risk. Whether the door is allowed
    to eat them is a RULING, not a measurement, and these are the cases worth an operator's time.

⇒ THE THREE BUCKETS, and each answers a different question:

    must_repair      RECALL       junk the door is supposed to remove
    must_not_touch   PRECISION    text it must return byte-identical  <- the safety axis
    ambiguous        CALIBRATION  cases where the right answer is to ASK, not to guess

⇒ EVERY CASE CARRIES ITS `why`, naming the ruling or the closed set it comes from, so a
  disagreement can be adjudicated without re-deriving why the case exists.

⇒⇒ **`_split_pass` IS SCORED, AND ITS GOLD COMES FROM AN AUTHORITY OUTSIDE GORGON.** The first
  build skipped it: which fusions "hide a closed word" looked like a rule that lives in code, so
  deriving cases would have meant writing gold from what the door does. Re-reading the function's
  own docstring settles it — *"an UNKNOWN token that splits into two known words is read apart"*.
  **UNKNOWN is the whole contract, and a real English word is not an unknown token.** So:

    must_repair      a fused token that is NOT a word, built from closed words (`stopthe`)
    must_not_touch   a real English WORD that happens to decompose (`stopping`, `antiseptic`)

  The `must_not_touch` half is adjudicated by `/usr/share/dict/american-english` — an authority
  with no knowledge of this project — and the words are inlined here rather than read at build
  time so the corpus stays portable and frozen.

⇒⇒ ONE PASS IS STILL NOT COVERED, AND SAYING SO IS THE POINT.

    4   N3 comma restore — the cut points come from `pass2.merge_cut_points`, whose rule is a
                        body of code rather than a stated contract. Deriving cases would be the
                        circle this file exists to avoid. Closing it means first writing that
                        rule down as a spec, which is its own piece of work.

  A number from this corpus is a number about SIX of the door's seven passes, and must be quoted
  that way.

Usage:  PYTHONPATH=. python3 -m tests.bench.door_eval.build_cases       # writes cases.jsonl
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cases.jsonl")

CASES: list = []


# ⇒ DISTINCT PREFIXES. `bucket[:2]` gave `must_repair` and `must_not_touch` the SAME prefix, so
#   `mu-0052` named two different cases and a disagreement could not be cited unambiguously.
#   Found 2026-09-17 by reading the score output rather than by any check — worth a check.
_PREFIX = {"must_repair": "mr", "must_not_touch": "mn", "ambiguous": "am"}


def case(bucket: str, text: str, expect: str, why: str, ask: str = "") -> None:
    CASES.append({"id": f"{_PREFIX[bucket]}-{len([c for c in CASES if c['bucket'] == bucket]) + 1:04d}",
                  "bucket": bucket, "text": text, "expect": expect, "ask": ask, "why": why})


# ── must_repair · FILLED PAUSES ──────────────────────────────────────────────────────────────
# `iso.FILLED_PAUSE` = er erm ehm um uhm uh eh hmm hm. The contract: dropped WITH one adjacent
# separator. Front and mid take the separator AFTER; a pause at the very end takes the one BEFORE.
for _p in ("um", "uh", "erm", "hmm", "eh", "er", "ehm", "uhm", "hm"):
    case("must_repair", f"{_p}, stop alpha", "stop alpha",
         f"FILLED_PAUSE {_p!r} at clause front, dropped with its comma+space")
for _p in ("um", "uh", "erm", "hmm", "eh"):
    case("must_repair", f"stop {_p} alpha", "stop alpha",
         f"FILLED_PAUSE {_p!r} mid-clause, dropped with the space after it")
for _p in ("um", "uh", "erm", "hmm"):
    case("must_repair", f"stop alpha {_p}", "stop alpha",
         f"FILLED_PAUSE {_p!r} at the very end, dropped with the space BEFORE it")

# ── must_repair · TYPO INSIDE A CLOSED-SET PHRASE (stage 2) ──────────────────────────────────
# Every other word exact; the odd word >=4 letters at Damerau distance 1 from a phrase word that
# is also >=4. Phrases from self_repair.CORRECTIONS/RETRACTIONS and speech_act.WRAPPERS/COURTESY.
for _bad, _good, _phrase in (
    ("no wati, stop alpha",              "no wait, stop alpha",              "no wait"),
    ("i mesnt alpha",                    "i meant alpha",                    "i meant"),
    ("i maen alpha",                     "i mean alpha",                     "i mean"),
    ("mkae that beta",                   "make that beta",                   "make that"),
    ("make thta beta",                   "make that beta",                   "make that"),
    ("not thta one",                     "not that one",                     "not that"),
    ("or rathr beta",                    "or rather beta",                   "or rather"),
    ("wati no, stop beta",               "wait no, stop beta",               "wait no"),
    ("cancle that",                      "cancel that",                      "cancel that"),
    ("belya that",                       "belay that",                       "belay that"),
    ("forgte it",                        "forget it",                        "forget it"),
    ("ignroe that",                      "ignore that",                      "ignore that"),
    ("scracth that",                     "scratch that",                     "scratch that"),
    ("disregrad that",                   "disregard that",                   "disregard that"),
    ("nevre mind",                       "never mind",                       "never mind"),
    ("as you wree",                      "as you were",                      "as you were"),
    ("tlel me which vms are up",         "tell me which vms are up",         "tell me"),
    ("let me knwo when it is up",        "let me know when it is up",        "let me know"),
    ("wehn you get a chance, stop alpha", "when you get a chance, stop alpha", "when you get a chance"),
    ("if you get a chnace, stop alpha",  "if you get a chance, stop alpha",  "if you get a chance"),
):
    case("must_repair", _bad, _good, f"stage 2: one typo'd word inside the closed phrase {_phrase!r}")

# ── must_not_touch · A TYPO'D NAME IS THE NAME ───────────────────────────────────────────────
# Operator's rule, structural: every candidate is drawn from a closed set, so a name can never BE
# one. These names are not in any closed class and must survive byte-identical.
for _n in ("alpah", "grubnsah", "zortlan", "xqvim", "plonkard", "vurmish"):
    case("must_not_touch", f"stop {_n}", f"stop {_n}",
         f"a typo'd or unknown NAME ({_n!r}) is the name — never a repair candidate")
for _n in ("web-01", "foo-bar", "db-7", "lab-core-2"):
    case("must_not_touch", f"stop {_n}", f"stop {_n}",
         f"UNDECLARED hyphenated name {_n!r} — the separator pass opens only KNOWN closed words")
for _n in ("bteA", "myVM", "webServer"):
    case("must_not_touch", f"stop {_n}", f"stop {_n}",
         f"camelCase {_n!r} is an identifier — a code shape, named not rewritten")

# ── must_not_touch · QUOTES ARE OPAQUE ───────────────────────────────────────────────────────
for _q, _d in (("'no wati um'", "a typo'd marker AND a filled pause, both inside quotes"),
               ('"um erm uh"', "nothing but filled pauses, inside double quotes"),
               ("'i mesnt it'", "a typo'd correction phrase inside quotes"),
               ("`forgte it`", "a typo'd retraction inside backticks"),
               ("'alpah'", "a typo'd name inside quotes")):
    case("must_not_touch", f"label alpha {_q}", f"label alpha {_q}",
         f"evidence is opaque testimony — {_d}")

# ── must_not_touch · CODE SHAPES ARE NAMED, NEVER REWRITTEN ──────────────────────────────────
for _s, _k in (("--all-the-vms", "flag"), ("--no-color", "flag"), ("-xzf", "flag"),
               ("/etc/web/temp.cfg", "path"), ("/var/log/qemu.log", "path"),
               ("~/.gorgon/workspace", "path")):
    case("must_not_touch", f"stop alpha {_s}", f"stop alpha {_s}",
         f"{_k} {_s!r} is a code shape — recognised, left byte-identical (ruling 2026-09-07/14)")

# ── must_not_touch · THE PRECISION TRAPS ─────────────────────────────────────────────────────
# ⚠ THE CASES THAT MATTER MOST. Each is an ordinary English sentence one edit from a marker
# phrase, in marker position. The module names this as accepted residual risk; these price it.
for _t, _near in (("no want, stop alpha",        "no wait"),
                  ("forgot it, stop alpha",      "forget it"),
                  ("made that beta",             "make that"),
                  ("never find the vm",          "never mind"),
                  ("i meat alpha",               "i mean / i meant"),
                  ("or rather beta",             "(exact phrase, must NOT be re-repaired)"),
                  ("tall me which vms are up",   "tell me"),
                  ("as you were told",           "as you were")):
    case("must_not_touch", _t, _t,
         f"PRECISION TRAP: a real sentence one edit from {_near!r} in marker position")

# ── must_not_touch · A MULTI-EDIT STRETCH PASSES THROUGH ─────────────────────────────────────
# Operator ruling 2026-09-14: only a SINGLE declared corruption print is actionable.
for _t in ("that's great, stop the db", "the grate vm is down", "i thnkk alpha is up"):
    case("must_not_touch", _t, _t,
         "a multi-edit stretch is neither repaired nor asked about (ruling 2026-09-14)")

# ── must_not_touch · A REAL WORD IN A CLOSED CLASS IS NEVER REPAIRED ─────────────────────────
for _t in ("nope, stop alpha", "lets stop alpha", "move alpha to lab", "ever stop alpha"):
    case("must_not_touch", _t, _t,
         "a word declared in ANY closed class is a real word and is never repaired (2026-09-08)")

# ── must_repair · SEPARATOR-JOINED CLOSED WORDS (pass 0a) ────────────────────────────────────
# Contract: a hyphen/underscore joining KNOWN CLOSED words is a fusion separator, opened to a
# space; an UNDECLARED name is never broken (those live in must_not_touch above). Single-char
# swap, so the result is the same length as the input.
for _bad, _good in (
    ("do-not-stop-alpha",      "do not stop alpha"),
    ("do_not_stop_alpha",      "do not stop alpha"),
    ("is-the-vm-up",           "is the vm up"),
    ("stop-the-vm",            "stop the vm"),
    ("all-of-them",            "all of them",),
    ("restart-it-and-stop-beta", "restart it and stop beta"),
):
    case("must_repair", _bad, _good,
         "pass 0a: every joined token is a KNOWN closed word, so the separator is a fusion")

# ── must_repair · SINGLE-WORD RECOGNITION, THE SLOTS N2 DECLARES (stage 3) ───────────────────
# The four slots are stated in the module docstring, so the gold is the RULE, not the door:
#   opener  -> the next word is a noun      pronoun -> the previous word is an operation verb
#   verb    -> clause-initial position      noun    -> an opener within the two words before it
for _bad, _good, _slot in (
    ("eveyr vm on lab",              "every vm on lab",              "opener, next word is a noun"),
    ("create two vms and put thrm on lab",
     "create two vms and put them on lab",                           "pronoun, previous word is a verb"),
    ("stop the netwrk",              "stop the network",             "noun, an opener stands before it"),
    ("restart the dmz netwrk",       "restart the dmz network",       "noun, opener two words back"),
    ("is alpha rynning",             "is alpha running",             "status, after a copula"),
    ("stop the runnin vms",          "stop the running vms",         "status, pre-nominal before a kind"),
):
    case("must_repair", _bad, _good, f"stage 3 (N2 sim check): {_slot}")

# ── must_repair · FUSED TOKENS THAT ARE NOT WORDS (pass 0b, `_split_pass`) ───────────────────
# The contract's own word is UNKNOWN. None of these is an English word; each is two closed words
# run together, which is exactly what the pass exists to open. Constructed here from the closed
# sets rather than copied from the module's comments, so they are not the door's own examples
# handed back to it.
for _bad, _good in (
    ("stopthe web vm",        "stop the web vm"),
    ("onthe lab network",     "on the lab network"),
    ("isnot running",         "is not running"),
    ("ifalpha is stopped, restart it", "if alpha is stopped, restart it"),
    ("the testvms",           "the test vms"),
):
    case("must_repair", _bad, _good,
         "pass 0b: an UNKNOWN token (not an English word) made of two closed words")

# ⇒ `restartalpha` IS NOT HERE, and the reason is a finding. `restart` is absent from
#   `_operation_words` entirely — not in `ops`, not in `known`, and neither is `reboot` — so the
#   door has nothing to split toward and nothing to repair `restrt` toward either. That resolves
#   the module docstring's claim that "`restrt` measured as recoverable": it survives because the
#   VOCABULARY lacks the word, not because verbs are exempt. Whether a common operation verb
#   belongs in the closed sets is an OPERATOR question, so no case asserts an answer.

# ── must_not_touch · A REAL WORD IS NOT AN UNKNOWN TOKEN ─────────────────────────────────────
# ⚠⚠ THE BUCKET THE 2026-09-17 SWEEP EXISTS FOR. Each of these is in
# `/usr/share/dict/american-english`. The pass's contract says it opens an UNKNOWN token; a word
# in the dictionary is known to English whether or not Gorgon has enumerated it, so every one of
# these must come back byte-identical. The first six are the ones an operator will actually type.
for _w in ("stopping", "startup", "markup", "takeover", "runoff", "runaway",
           "somewhere", "nowhere", "somehow", "everywhere", "insure", "beat",
           "theme", "notable", "meat", "cabinet", "merchants", "antiseptic",
           "animator", "novelties", "shadowbox", "nonmembers", "understate", "backer"):
    case("must_not_touch", f"stop the {_w} vm", f"stop the {_w} vm",
         f"{_w!r} is an English word (system dictionary) — not an UNKNOWN token, never split")
# and in the frames where the damage was actually observed, not just the sweep frame
for _t in ("the web vm is stopping",
           "check the startup scripts",
           "there is nowhere to put it",
           "beat the deadline",
           "the markup is wrong"):
    case("must_not_touch", _t, _t,
         "a real English word in a natural operator sentence — observed damaged 2026-09-17")

# ── must_not_touch · THE MANIFEST'S OWN MISSPELLING MUST NOT BE PROPAGATED ───────────────────
case("must_not_touch", "stop the boxes vm", "stop the boxes vm",
     "`boxes` is correct English; `boxs` is a MISSPELLING in the manifest's noun set, and the "
     "door 'corrects' the right spelling into it (2026-09-17). The defect is the manifest's, "
     "but the door must not propagate it.")

case("must_not_touch", "restrt alpha", "restrt alpha",
     "`restart` is absent from `_operation_words`, so there is no candidate to repair toward. "
     "This case pins TODAY's behaviour; if `restart` is ever added to the closed sets it must "
     "move to must_repair, and this line is where that decision becomes visible.")

# ── ambiguous · THE RIGHT ANSWER IS TO ASK ───────────────────────────────────────────────────
for _t, _why in (
    ("did you eveyr stop it",
     "`eveyr` fits `every` only before a NOUN; no slot votes here, so nothing fires"),
    ("stpped alpha",
     "`stpped` explains `stopped` AND `stepped` at one print each — a tie is an ask"),
):
    case("ambiguous", _t, _t, _why, ask="ambiguous-or-silent")


def main() -> None:
    os.makedirs(HERE, exist_ok=True)
    with open(OUT, "w") as f:
        for c in CASES:
            f.write(json.dumps(c) + "\n")
    from collections import Counter
    n = Counter(c["bucket"] for c in CASES)
    print(f"wrote {len(CASES)} cases -> {OUT}")
    for k, v in sorted(n.items()):
        print(f"  {k:<16}{v:>4}")


if __name__ == "__main__":
    main()
