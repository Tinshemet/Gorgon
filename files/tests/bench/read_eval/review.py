"""review.py — BUILD ORDER #5: the operator verifies every gold label, one keypress each.

    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl        # review
    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl --status
    PYTHONPATH=. python3 -m tests.bench.read_eval.review cases/seeds.jsonl --freeze v1

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

Keys:  a accept · r reject (asks one line: why) · s skip for now · u undo last · q quit.
Progress is saved after EVERY key — quitting mid-run loses nothing.

# ⇒ --freeze IS BUILD ORDER #6'S DOOR, AND IT IS STRICT

`--freeze v1` writes `cases/v1.jsonl` from cases that are ACCEPTED with a FRESH hash — all of
them, or it refuses and says which are not. A frozen release is immutable except via explicit
commit with a note (the spec's own rule), so the freeze also writes `v1.review.json` beside it
— the verdicts as the audit trail of who approved what. Both are committed DELIBERATELY.

# ⇒ THE TWIN FAST PATH (dormant until expansion lands)

A noised case whose `pair_id` twin is already ACCEPTED shows the twin's sentence beside its
own — the gold is inherited, so the question shrinks to "is the noise faithful?". The spec
expects these to verify several times faster; nothing else about the flow changes.
"""
import hashlib
import json
import os
import sys
from typing import Dict, List, Optional

from .schema import load, validate

BOLD, DIM, CYAN, YELLOW, UL, OFF = ("\x1b[1m", "\x1b[2m", "\x1b[36m", "\x1b[33m",
                                    "\x1b[4m", "\x1b[0m")


def _hash(case: dict) -> str:
    body = json.dumps({"sentence": case["sentence"], "gold": case["gold"]},
                      sort_keys=True)
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
        verb = case["gold"]["actions"][at["action"]]["text"]
        objs = " + ".join(
            f"{spans[ix]['text']!r}" + (f" ({role})" if role else "")
            for ix, role in members_of(at))
        print(f"      {verb!r} -> {objs}")
    acts_attached = {at["action"] for at in case["gold"]["attachments"]}
    for i, a in enumerate(case["gold"]["actions"]):
        if i not in acts_attached:
            print(f"      {a['text']!r} -> (nothing)")
    for a in case["gold"]["actions"]:
        if a.get("trigger"):
            print(f"      {a['text']!r} STARTS WHEN: {a['trigger']['text']!r}")
    v = verdicts.get(case["id"])
    if v and state_of(case, verdicts) == "STALE":
        print(f"    {YELLOW}⚠ STALE — judged {v['verdict']!r} but the gold has changed "
              f"since. Note then: {v.get('note') or '—'}{OFF}")


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
        else:
            print(f"  {DIM}a / r / s / u / q{OFF}")
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
              "[--status | --freeze <name>] | --practice")
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
    if "--freeze" in argv:
        return freeze(cases, path, argv[argv.index("--freeze") + 1])
    if "--status" in argv:
        return status(cases, path)
    return review(cases, path)


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
