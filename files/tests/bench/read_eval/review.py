"""review.py — BUILD ORDER #5: the operator verifies every gold label, one keypress each.

    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl        # review
    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl --status
    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl --freeze v1
    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl --rank     # a 2nd person

# ⇒⇒ WHAT THE TOOL RECORDS, AND WHAT IT DELIBERATELY DOES NOT DO

It records VERDICTS — accept · reject-with-reason — never edits. The seed file is the single
source of the gold ([[gorgon-storage-home]]-style SSOT): a wrong label is FIXED IN `seeds.py`
and re-emitted, not patched here, or the JSONL and its source drift apart and the next --emit
silently undoes the review. A rejection's note says what was wrong; the fix happens at the
source; the case comes back PENDING because its content changed.

# ⇒ A VERDICT IS BOUND TO THE BYTES IT JUDGED

Each verdict stores a hash of the case (sentence + gold, canonical JSON). If the case changes
after review — a re-emit, an offset shift, a reworded sentence — the verdict goes STALE and
the case returns to pending with the old note shown. **An approval of last week's gold is not
an approval of today's**, which is the fixture-moved-and-the-check-did-not lesson
(2026-08-17) applied to review.

# ⇒ THE DISPLAY: the sentence with its gold PAINTED ON, then the structure

    stop [the web vm]₀ and launch [the db vm]₁          objects in cyan · evidence yellow
    actions underlined · attachments listed as  action -> objects
    restart [the vms]₀ ⟨one at a time⟩m                  channels magenta: ⟨…⟩t trigger · ⟨…⟩m manner
    outcome: NONE · store: word=grubnash, kind=vm        an empty reading says why; the mock is shown
    context: expecting=yes-no · hint [answer-shaped] …   v2.3: what RESOLVE supplied, what READ answers
    mood [deference] 'when you have a sec'               v2.4: the turn's stance, carried as evidence too

Keys:  a accept · r reject (asks one line: why) · s skip for now · u undo last · q quit.
Progress is saved after EVERY key — quitting mid-run loses nothing.

# ⇒ --freeze IS BUILD ORDER #6'S DOOR, AND IT IS STRICT

`--freeze v1` writes `cases/v1.jsonl` from cases that are ACCEPTED with a FRESH hash — all of
them, or it refuses and says which are not. A frozen release is immutable except via explicit
commit with a note (the spec's own rule), so the freeze also writes `v1.review.json` beside it
— the verdicts as the audit trail of who approved what. Both are committed DELIBERATELY.

# ⇒ --rank IS A DIFFERENT PERSON'S JOB, AND THE FLAG KEEPS THE TWO APART

Without the flag the command CERTIFIES (the operator: accept/reject). With `--rank` it ranks
DIFFICULTY (a second person, 1-10: would a reader find this hard or ambiguous?) — the
readability axis agreed 08-22; the structural axis is computed from the gold and is nobody's
to rank. The roles are split on purpose: the one who signed the gold does not grade how hard
it was, and the one who grades has seen nothing. So the rank loop is BLIND BY CONSTRUCTION:
  · it never opens `.review.json` — no verdict, no note, no STALE banner
  · it shows the sentence UNPAINTED plus what the reader is given (`context`, `store`) —
    never the gold, never the stratum/noise/source/id (the id prefix names the stratum)
  · the queue is in a fixed shuffled order, so a stratum's cases do not arrive as a run
  · ranks land in `<cases>.rank.json`, bound to the hash of WHAT WAS SHOWN — a reworded
    sentence stales its rank; a re-emitted gold does not, the rater never saw it
One rater means no agreement number; if a second ever joins, keep scores per rater — a
contested difficulty is a finding about the sentence, not noise to average away.

# ⇒ THE TWIN FAST PATH (dormant until expansion lands)

A noised case whose `pair_id` twin is already ACCEPTED shows the twin's sentence beside its
own — the gold is inherited, so the question shrinks to "is the noise faithful?". The spec
expects these to verify several times faster; nothing else about the flow changes.
"""
import hashlib
import json
import os
import re
import sys
from typing import Dict, List, Optional

from .schema import load, validate

BOLD, DIM, CYAN, YELLOW, UL, OFF = ("\x1b[1m", "\x1b[2m", "\x1b[36m", "\x1b[33m",
                                    "\x1b[4m", "\x1b[0m")
MAGENTA = "\x1b[35m"          # an action's CHANNELS (trigger · manner) — v2.0 gold
CHANNELS = ("trigger", "manner")


def _hash(case: dict) -> str:
    # ⇒ THE SEAL BINDS EVERYTHING JUDGED. Found 08-22: `store` (v2.0) and `outcome` (v2.2)
    #   were outside the hash, so a changed mock or a changed outcome never staled a
    #   verdict — "an accept ratifies the store, decoys included" was a sentence, not a
    #   binding. Now it is a binding; the cases carrying a store go STALE once, by design.
    judged = {"sentence": case["sentence"], "gold": case["gold"]}
    for extra in ("store", "outcome", "context", "vector"):   # ADDITIVE: a case without them keeps its hash
        if extra in case:
            judged[extra] = case[extra]
    body = json.dumps(judged, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def _verdicts_path(cases_path: str) -> str:
    return os.path.splitext(cases_path)[0] + ".review.json"


def load_verdicts(cases_path: str) -> Dict[str, dict]:
    path = _verdicts_path(cases_path)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_verdicts(cases_path: str, verdicts: Dict[str, dict]) -> None:
    with open(_verdicts_path(cases_path), "w", encoding="utf-8") as fh:
        json.dump(verdicts, fh, indent=1, sort_keys=True)


def state_of(case: dict, verdicts: Dict[str, dict]) -> str:
    """pending · accepted · rejected · STALE (judged, then the bytes changed)."""
    v = verdicts.get(case["id"])
    if not v:
        return "pending"
    if v.get("hash") != _hash(case):
        return "STALE"
    return v.get("verdict", "pending")


def painted(case: dict) -> str:
    """The sentence with gold painted on — every boundary visible at a glance."""
    sentence = case["sentence"]
    marks = []          # (start, end, open, close)
    for i, s in enumerate(case["gold"]["spans"]):
        colour = CYAN if s["type"] == "object" else YELLOW
        marks.append((s["start"], s["end"], f"{colour}[", f"]{DIM}{i}{OFF}"))
    for a in case["gold"]["actions"]:
        marks.append((a["start"], a["end"], UL, OFF))
        # The channels ride the action, not the span list — unpainted they were INVISIBLE,
        # and two manner golds were rejected for "missing" what they carried (08-22).
        for ch in CHANNELS:
            if a.get(ch):
                marks.append((a[ch]["start"], a[ch]["end"],
                              f"{MAGENTA}⟨", f"⟩{DIM}{ch[0]}{OFF}"))
    out, at = [], 0
    for start, end, open_, close in sorted(marks):
        if start < at:                        # overlapping action/object — paint sequentially
            continue
        out += [sentence[at:start], open_, sentence[start:end], close]
        at = end
    out.append(sentence[at:])
    return "".join(out)


def show(case: dict, verdicts: Dict[str, dict], by_id: Dict[str, dict]) -> None:
    print(f"\n{BOLD}{case['id']}{OFF}  {case['stratum']} · {case['noise']} · "
          f"{case['source']}")
    print(f"    {painted(case)}")
    pid = case.get("pair_id")
    if pid and pid in by_id and state_of(by_id[pid], verdicts) == "accepted":
        print(f"    {DIM}twin (accepted): {by_id[pid]['sentence']}{OFF}")
        print(f"    {DIM}gold is inherited — the question is only: is the noise "
              f"faithful?{OFF}")
    from .schema import members_of
    spans = case["gold"]["spans"]
    for at in case["gold"]["attachments"]:
        act = case["gold"]["actions"][at["action"]]
        tag = {"query": " (QUERY)", "rule": " (RULE)",
               "report": " (DIAGNOSIS)"}.get(act.get("kind") or "", "")
        def _memtag(at, ix, role):
            for o in at.get("objects", ()):
                if isinstance(o, dict) and o.get("span") == ix:
                    k = f":{o['kind']}" if o.get("kind") else ""
                    r = f"->{o['refers']}" if o.get("refers") is not None else ""
                    return f" ({role}{k}{r})" if role else ""
            return f" ({role})" if role else ""
        objs = " + ".join(
            f"{spans[ix]['text']!r}" + _memtag(at, ix, role)
            for ix, role in members_of(at))
        print(f"      {act['text']!r}{tag} -> {objs}{_channels(act)}")
    acts_attached = {at["action"] for at in case["gold"]["attachments"]}
    for i, a in enumerate(case["gold"]["actions"]):
        if i not in acts_attached:
            print(f"      {a['text']!r} -> (nothing){_channels(a)}")
    # v2.3: THE INBOUND HINT — what RESOLVE supplied. Shown FIRST, because the reading
    #   below is only correct UNDER it (operator 08-22: "READ is fed by RESOLVE").
    if case.get("context"):
        print(f"      {MAGENTA}context:{OFF} " + " · ".join(
            f"{k}={v}" for k, v in case["context"].items()))
    # v3.0: THE VECTOR — every cell judged with the case; flip a wrong one with `f`.
    #   Compact: only words that earned cells; the fold last (it is a FUNCTION of the
    #   words — a fold flip rules the fold RULE, not this one case).
    vec = case.get("vector")
    if vec:
        for wi, w in enumerate(vec["words"]):
            cells = w["cells"]
            if not cells:
                continue
            body = " · ".join(
                f"{d}={','.join(v) if isinstance(v, list) else v}"
                for d, v in sorted(cells.items()))
            print(f"      {DIM}w{wi:<2}{OFF} {w['w']:14} {body}")
        print(f"      {DIM}fold{OFF} " + " · ".join(
            f"{d}={v}" for d, v in sorted(vec["fold"].items())))
    # v2.2: the OUTCOME of an empty reading is part of the gold — shown, so it is judged
    if case.get("outcome"):
        print(f"      {MAGENTA}outcome: {case['outcome'].upper()}{OFF}  "
              f"{DIM}(no act is the reading — is that right?){OFF}")
    # v3.1: THE FRAME — speech-act participants (i=user, you=agent), not verb arguments.
    for f in case["gold"].get("frame") or []:
        txt = case["gold"]["spans"][f["span"]]["text"]
        print(f"      {MAGENTA}frame:{OFF} {txt!r} = {f['party']}")
    # v2.4: THE MOOD CHANNEL — a span with a species, carried as evidence too.
    for m in case["gold"].get("mood") or []:
        print(f"      {MAGENTA}mood [{m['kind']}]{OFF} {m['text']!r}")
    # v2.3: THE OUTBOUND HINT — what READ writes for ROUTE. The `kind` is scored; the
    #   `says` gloss is ratified by this accept and never string-matched.
    if case["gold"].get("hint"):
        h = case["gold"]["hint"]
        print(f"      {MAGENTA}hint [{h['kind']}]{OFF} {h['says']}")
    # v2.0: the store is ratified by the accept — shown, so it is judged
    if case.get("store"):
        print(f"      {DIM}store:{OFF} " + " · ".join(
            ", ".join(f"{k}={v}" for k, v in e.items()) for e in case["store"]))
    # The STALE banner — orphaned behind `_channels`'s return in f125461 (found 08-23), so
    # every STALE case was re-judged with its old note INVISIBLE. It lives at the end of
    # `show`, where it was.
    v = verdicts.get(case["id"])
    if v and state_of(case, verdicts) == "STALE":
        print(f"    {YELLOW}⚠ STALE — judged {v['verdict']!r} but the gold has changed "
              f"since. Note then: {v.get('note') or '—'}{OFF}")


def _channels(act: dict) -> str:
    """The action's trigger/manner, listed beside its objects — part of the gold judged."""
    return "".join(f"  {MAGENTA}{ch}: {act[ch]['text']!r}{OFF}"
                   for ch in CHANNELS if act.get(ch))


def review(cases: List[dict], cases_path: str) -> int:
    if not sys.stdin.isatty():
        print("  review is interactive — run it in a terminal")
        return 2
    verdicts = load_verdicts(cases_path)
    by_id = {c["id"]: c for c in cases}
    queue = [c for c in cases if state_of(c, verdicts) in ("pending", "STALE")]
    print(f"  {len(queue)} to review of {len(cases)} "
          f"({sum(1 for c in cases if state_of(c, verdicts) == 'accepted')} accepted, "
          f"{sum(1 for c in cases if state_of(c, verdicts) == 'rejected')} rejected)")
    print(f"  {DIM}a accept · r reject · s skip · u undo last · q quit — saved every key{OFF}")
    history: List[str] = []
    at = 0
    while at < len(queue):
        case = queue[at]
        show(case, verdicts, by_id)
        try:
            key = input(f"  [{at + 1}/{len(queue)}] > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if key == "q":
            break
        elif key == "s":
            at += 1
        elif key == "u" and history:
            gone = history.pop()
            verdicts.pop(gone, None)
            save_verdicts(cases_path, verdicts)
            at = max(0, at - 1)
            print(f"  {DIM}undid {gone}{OFF}")
        elif key == "a":
            verdicts[case["id"]] = {"verdict": "accepted", "hash": _hash(case), "note": ""}
            save_verdicts(cases_path, verdicts)
            history.append(case["id"])
            at += 1
        elif key == "r":
            note = input("      why (one line, goes to seeds.py's author): ").strip()
            verdicts[case["id"]] = {"verdict": "rejected", "hash": _hash(case),
                                    "note": note}
            save_verdicts(cases_path, verdicts)
            history.append(case["id"])
            at += 1
        elif key == "f" and case.get("vector"):
            # ⇒ v3.0: FLIP A CELL — the per-cell reject (operator 08-24: "WHICH WORDS FLIP
            #   IT THE WRONG WAY"). Machine-readable, so the fix lands where the cell was
            #   computed; several flips stack on one case. `w3.kind=network why...`,
            #   `fold.mood=ACHIEVE why...` — empty input finishes the case as rejected.
            flips = []
            while True:
                line = input("      flip (wN.dim=value why · empty=done): ").strip()
                if not line:
                    break
                m = re.match(r"^(w\d+|fold)\.([a-z]+)\s*=\s*(\S+)\s*(.*)$", line)
                if not m:
                    print(f"      {DIM}form: w3.kind=network the head is the net{OFF}")
                    continue
                flips.append({"at": m.group(1), "dim": m.group(2),
                              "to": m.group(3), "why": m.group(4).strip()})
            if flips:
                verdicts[case["id"]] = {
                    "verdict": "rejected", "hash": _hash(case), "flips": flips,
                    "note": "; ".join(f"{f['at']}.{f['dim']}→{f['to']}" for f in flips)}
                save_verdicts(cases_path, verdicts)
                history.append(case["id"])
                at += 1
        else:
            print(f"  {DIM}a accept · r reject · f flip cells · s / u / q{OFF}")
    return status(cases, cases_path)


def status(cases: List[dict], cases_path: str) -> int:
    verdicts = load_verdicts(cases_path)
    counts: Dict[str, int] = {}
    for c in cases:
        s = state_of(c, verdicts)
        counts[s] = counts.get(s, 0) + 1
    print(f"\n  {len(cases)} cases: " + " · ".join(
        f"{n} {s}" for s, n in sorted(counts.items())))
    rejected = [(c["id"], verdicts[c["id"]].get("note", ""))
                for c in cases if state_of(c, verdicts) == "rejected"]
    if rejected:
        print("  rejected — fix in seeds.py and re-emit:")
        for cid, note in rejected:
            print(f"    {cid:14} {note or '(no note)'}")
    return 0


def freeze(cases: List[dict], cases_path: str, name: str) -> int:
    verdicts = load_verdicts(cases_path)
    not_ready = [(c["id"], state_of(c, verdicts)) for c in cases
                 if state_of(c, verdicts) != "accepted"]
    if not_ready:
        print(f"  ✗ refusing to freeze — {len(not_ready)} case(s) not accepted-and-fresh:")
        for cid, s in not_ready[:20]:
            print(f"      {cid:14} {s}")
        return 1
    out = os.path.join(os.path.dirname(os.path.abspath(cases_path)), f"{name}.jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c) + "\n")
    audit = os.path.join(os.path.dirname(os.path.abspath(cases_path)),
                         f"{name}.review.json")
    with open(audit, "w", encoding="utf-8") as fh:
        json.dump(verdicts, fh, indent=1, sort_keys=True)
    print(f"  froze {len(cases)} accepted cases -> {out}")
    print(f"  audit trail          -> {audit}")
    print(f"  ⇒ commit BOTH deliberately — a frozen release changes only via an explicit "
          f"commit with a note")
    return 0


# ── rank: the second person's loop — blind, 1-10, its own file ─────────────────────
RANK_KEYS = tuple(str(n) for n in range(1, 11))


def _rank_hash(case: dict) -> str:
    """Binds the rank to WHAT THE RATER SAW: sentence + context + store. NOT the gold —
    the rater never saw it, so a re-emitted gold must not stale a difficulty score."""
    shown = {"sentence": case["sentence"]}
    for extra in ("context", "store"):
        if extra in case:
            shown[extra] = case[extra]
    body = json.dumps(shown, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def _ranks_path(cases_path: str) -> str:
    return os.path.splitext(cases_path)[0] + ".rank.json"


def load_ranks(cases_path: str) -> Dict[str, dict]:
    path = _ranks_path(cases_path)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_ranks(cases_path: str, ranks: Dict[str, dict]) -> None:
    with open(_ranks_path(cases_path), "w", encoding="utf-8") as fh:
        json.dump(ranks, fh, indent=1, sort_keys=True)


def rank_state_of(case: dict, ranks: Dict[str, dict]) -> str:
    """unranked · ranked · STALE (ranked, then the shown bytes changed)."""
    r = ranks.get(case["id"])
    if not r:
        return "unranked"
    if r.get("hash") != _rank_hash(case):
        return "STALE"
    return "ranked"


def rank_order(cases: List[dict]) -> List[dict]:
    """A fixed shuffle by id-hash: the same order every run (resumable), but never the
    file's order — which groups a stratum's cases together and would hand the rater a
    difficulty class by position."""
    return sorted(cases, key=lambda c: hashlib.sha256(c["id"].encode()).hexdigest())


def show_for_rank(case: dict) -> None:
    """The sentence as a reader meets it — unpainted — and only what the reader is given."""
    print(f"\n    {BOLD}{case['sentence']}{OFF}")
    if case.get("context"):
        print(f"      {DIM}context:{OFF} " + " · ".join(
            f"{k}={v}" for k, v in case["context"].items()))
    if case.get("store"):
        print(f"      {DIM}store:{OFF} " + " · ".join(
            ", ".join(f"{k}={v}" for k, v in e.items()) for e in case["store"]))


def rank(cases: List[dict], cases_path: str) -> int:
    if not sys.stdin.isatty():
        print("  rank is interactive — run it in a terminal")
        return 2
    ranks = load_ranks(cases_path)
    queue = [c for c in rank_order(cases) if rank_state_of(c, ranks) in ("unranked", "STALE")]
    print(f"  {len(queue)} to rank of {len(cases)} "
          f"({sum(1 for c in cases if rank_state_of(c, ranks) == 'ranked')} ranked)")
    print(f"  {DIM}1-10 how hard or ambiguous would a reader find this? "
          f"(1 trivial · 10 a person would get it wrong){OFF}")
    print(f"  {DIM}s skip · u undo last · q quit — saved every key{OFF}")
    history: List[str] = []
    at = 0
    while at < len(queue):
        case = queue[at]
        show_for_rank(case)
        try:
            key = input(f"  [{at + 1}/{len(queue)}] > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if key == "q":
            break
        elif key == "s":
            at += 1
        elif key == "u" and history:
            gone = history.pop()
            ranks.pop(gone, None)
            save_ranks(cases_path, ranks)
            at = max(0, at - 1)
            print(f"  {DIM}undid the last rank{OFF}")
        elif key in RANK_KEYS:
            ranks[case["id"]] = {"rank": int(key), "hash": _rank_hash(case)}
            save_ranks(cases_path, ranks)
            history.append(case["id"])
            at += 1
        else:
            print(f"  {DIM}1-10 / s / u / q{OFF}")
    return rank_status(cases, cases_path)


def rank_status(cases: List[dict], cases_path: str) -> int:
    """Coverage and the distribution — never joined to verdicts or results here; that join
    is the analyst's step, after both files are complete."""
    ranks = load_ranks(cases_path)
    counts: Dict[str, int] = {}
    hist: Dict[int, int] = {}
    for c in cases:
        s = rank_state_of(c, ranks)
        counts[s] = counts.get(s, 0) + 1
        if s == "ranked":
            r = ranks[c["id"]]["rank"]
            hist[r] = hist.get(r, 0) + 1
    print(f"\n  {len(cases)} cases: " + " · ".join(
        f"{n} {s}" for s, n in sorted(counts.items())))
    if hist:
        print("  difficulty: " + " · ".join(f"{r}:{hist[r]}" for r in sorted(hist)))
    return 0


# ── practice: five throwaway cases, three with PLANTED faults, and an answer key ─────
def _practice_cases() -> List[dict]:
    """Schema-valid, semantically judged — two right, three planted wrong. NOT the eval."""
    def case(cid, sentence, spans, actions, attachments):
        return {"id": cid, "stratum": "clean-single", "noise": "clean", "pair_id": None,
                "source": "seed", "sentence": sentence,
                "gold": {"spans": spans, "actions": actions, "attachments": attachments}}
    return [
        case("practice-1", "create a vm named practice",
             [{"text": "a vm named practice", "start": 7, "end": 26, "type": "object"}],
             [{"text": "create", "start": 0, "end": 6}], [{"action": 0, "objects": [0]}]),
        case("practice-2", "stop the web vm",
             [{"text": "web vm", "start": 9, "end": 15, "type": "object"}],
             [{"text": "stop", "start": 0, "end": 4}], [{"action": 0, "objects": [0]}]),
        case("practice-3", "stop alpha and snapshot it",
             [{"text": "alpha", "start": 5, "end": 10, "type": "object"}],
             [{"text": "stop", "start": 0, "end": 4}], [{"action": 0, "objects": [0]}]),
        case("practice-4", "if beta is down, restart it",
             [{"text": "beta", "start": 3, "end": 7, "type": "object"}],
             [{"text": "down", "start": 11, "end": 15},
              {"text": "restart", "start": 17, "end": 24}],
             [{"action": 1, "objects": [0]}]),
        case("practice-5", "label the web vm and stop the db vm",
             [{"text": "the web vm", "start": 6, "end": 16, "type": "object"},
              {"text": "the db vm", "start": 26, "end": 35, "type": "object"}],
             [{"text": "label", "start": 0, "end": 5}, {"text": "stop", "start": 21, "end": 25}],
             [{"action": 0, "objects": [1]}, {"action": 1, "objects": [0]}]),
    ]


PRACTICE_KEY = {
    "practice-1": ("a", "correct — one action, one object, boundaries right"),
    "practice-2": ("r", "PLANTED: boundary — the span drops `the`; the object is "
                        "`the web vm`, not `web vm`"),
    "practice-3": ("r", "PLANTED: missing — `snapshot` is a second action, attached to "
                        "alpha through `it`, and the gold does not have it"),
    "practice-4": ("r", "PLANTED: hallucinated action — `down` is a CONDITION, a state "
                        "the world is in, not something you are told to do"),
    "practice-5": ("r", "PLANTED: attachments crossed — label points at the db vm and "
                        "stop at the web vm, the reverse of the sentence"),
}


def practice() -> int:
    """The review loop on throwaway cases, then the answer key against your verdicts."""
    import tempfile
    cases = _practice_cases()
    bad = validate(cases)
    if bad:
        print("\n".join(f"  ✗ {b}" for b in bad))
        return 1
    print(f"{BOLD}  PRACTICE — five cases, some carry a planted fault. Judge each one:{OFF}")
    print(f"  {DIM}accept what a competent reader would extract; reject anything missing, "
          f"extra,\n  or mis-bracketed. Your verdicts here touch nothing.{OFF}")
    with tempfile.TemporaryDirectory() as tmp:
        scratch = os.path.join(tmp, "practice.jsonl")
        with open(scratch, "w", encoding="utf-8") as fh:
            for c in cases:
                fh.write(json.dumps(c) + "\n")
        review(cases, scratch)
        verdicts = load_verdicts(scratch)
    print(f"\n{BOLD}  THE ANSWER KEY{OFF}")
    right = 0
    for cid, (want, why) in PRACTICE_KEY.items():
        got = verdicts.get(cid, {}).get("verdict", "(not judged)")
        want_word = "accept" if want == "a" else "reject"
        ok = got == ("accepted" if want == "a" else "rejected")
        right += 1 if ok else 0
        mark = "✓" if ok else "✗"
        print(f"  {mark} {cid}: should {want_word} — {why}")
        if not ok:
            print(f"      you said: {got}")
    print(f"\n  {right}/{len(PRACTICE_KEY)}. "
          + ("Ready — run the real file the same way." if right == len(PRACTICE_KEY) else
             "Re-run --practice if you want another pass; the real set can wait."))
    return 0


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--practice" in argv:
        return practice()
    path = next((a for a in argv if not a.startswith("--")), None)
    if not path:
        print("usage: python3 -m tests.bench.read_eval.review <cases.jsonl> "
              "[--status | --freeze <name> | --rank [--status]] | --practice")
        return 2
    if not os.path.isabs(path):
        here = os.path.dirname(os.path.abspath(__file__))
        path = path if os.path.exists(path) else os.path.join(here, path)
    cases = load(path)
    bad = validate(cases)
    if bad:
        print("\n".join(f"  ✗ {b}" for b in bad))
        print("  the case file is not valid — nothing to review until it is")
        return 1
    if "--rank" in argv:
        # the second person's door: nothing past this line reads a verdict
        return rank_status(cases, path) if "--status" in argv else rank(cases, path)
    if "--freeze" in argv:
        return freeze(cases, path, argv[argv.index("--freeze") + 1])
    if "--status" in argv:
        return status(cases, path)
    return review(cases, path)


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
