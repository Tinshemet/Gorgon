"""schema.py — BUILD ORDER #2: the case format, and the validator that keeps gold honest.

    PYTHONPATH=. python3 -m tests.bench.read_eval.schema <cases.jsonl>     # validate a file
    PYTHONPATH=. python3 -m tests.bench.read_eval.schema --selfcheck       # can it FAIL?

# ⇒⇒ ONE RECORD PER CASE, JSONL, EXACTLY THE SPEC'S SHAPE

    {"id": "coord-0042n", "stratum": "coordination", "noise": "typos",
     "pair_id": "coord-0042", "source": "real-failure",
     "sentence": "restrat the web vm adn the db vm then snapshot both",
     "gold": {"spans":       [{"text": "the web vm", "start": 8, "end": 18,
                               "type": "object"}, …],
              "actions":     [{"text": "restrat", "start": 0, "end": 7}, …],
              "attachments": [{"action": 0, "objects": [0, 1]}, …]}}

Character offsets are the ground truth — `sentence[start:end] == text`, verified, every span,
every action. Gold references the sentence AS WRITTEN: a typo'd span is the gold span WITH its
typo. Noise lives in the input only; if a human cannot determine the frame, the case does not
belong here at all (that is gate territory — spec §3.1).

# ⇒⇒ THE STRATA — the spec's eight, PLUS THE FOUR THE BUCKETING EARNED

The operator, 2026-08-18, on `read_eval_buckets`' decision queue: *"qualifiers and
adjunct-clauses earn strata, diagnosis too, as well as cross-cutting causes."* The bucketing
found the spec's strata catch 7 bleeding rows while 21 bled outside them — these four are where
the project ACTUALLY fails, promoted exactly the way `self-correction` earned its place in the
spec (it changes gold, so it is a stratum, not a tag):

    qualifiers       a value with a modifier the phrase must carry — units, superlative,
                     partiality, manner, clock. *"give alpha 4 cores and 8gb"*
    adjunct-clauses  a second clause that MODIFIES, never orders — purpose, cause,
                     concession, comparison. *"stop the vms to free up memory"* — extracting
                     `free up memory` as a second ACTION is the failure these cases exist for
    diagnosis        ⚠ D1, THE THESIS. *"vm2 is not working, it boots to a blue screen"* —
                     the object and its EVIDENCE, no imperative anywhere
    cross-cutting    the vocab-list boundaries — a sentence where `make`/`get`/`put` is NOT an
                     operation, a courtesy phrase that must not escalate intent. These cases
                     exist to catch the closed-list leaks that surface in every other stratum

⇒ NOT promoted, still in the queue: resolution · commissive · suggestion (sentence-types minus
  diagnosis), register (the spec already owns it as §4 variation), apposition.

# ⇒ SPAN TYPES — `object` and `evidence`, and why there are two

`object` is a thing the request is ABOUT. `evidence` is what the operator is SHOWING us — the
quoted error, the symptom clause — the seam's own long-standing distinction (`quoted_clauses`:
read as a value it becomes a machine name; read as nothing it is the most important part of
the sentence, discarded). Diagnosis cases are mostly evidence spans, and embedded-junk noise
cases are OBJECT spans by the spec's explicit rule: a pasted path is an argument, not junk.
⇒ An attachment maps an ACTION to objects. A diagnosis case with no imperative has
  `actions: []`, `attachments: []` — span detection and boundaries still score; attachment
  simply has nothing to say there. The evidence→object link is NOT in this schema; if scoring
  it ever matters, that is a schema version bump, not a quiet extra field.

# ⇒⇒ THE VALIDATOR REFUSES WHAT IT DOES NOT KNOW

Unknown top-level or gold keys are FAULTS, not extensions — a typo'd field name must fail
loudly, never ride along unread (the suite-not-asserting defect, applied to data). And
`--selfcheck` proves the validator CAN fail: fourteen deliberately broken records, each
asserting its own specific fault fires. A validator nobody has seen fail is the exact mistake
`seam_determinism` exists to stop making twice.

# ⇒ PAIRING — noised -> clean, many-to-one, one direction only

A noised case's `pair_id` names its clean twin; the twin is `noise: "clean"`, same stratum,
and its own `pair_id` is null. Clean cases never point anywhere — a cycle or a chain would
make the degradation report double-count. Unpaired noised cases are legal (null).
"""
import json
from typing import Dict, List, Optional

# ── the vocabulary. ONE source of truth — the bucketing report imports THESE. ────────
SPEC_STRATA = ("clean-single", "coordination", "buried-args", "anaphora", "negation",
               "conditionals", "multi-clause", "self-correction")
EARNED_STRATA = ("qualifiers", "adjunct-clauses", "diagnosis", "cross-cutting")
STRATA = SPEC_STRATA + EARNED_STRATA

NOISE = ("terse", "typos", "no-punct", "voice", "embedded-junk", "code-switch")
CLEAN = "clean"
SOURCES = ("seed", "seed-expansion", "real-failure")
SPAN_TYPES = ("object", "evidence")

CASE_KEYS = {"id", "stratum", "noise", "pair_id", "source", "sentence", "gold"}
GOLD_KEYS = {"spans", "actions", "attachments"}


def _offsets(where: str, item: dict, sentence: str, typed: bool) -> List[str]:
    """The one check that keeps gold honest: the offsets must reproduce the text."""
    faults = []
    for key in ("text", "start", "end"):
        if key not in item:
            return [f"{where}: missing {key!r}"]
    start, end, text = item["start"], item["end"], item["text"]
    if not isinstance(start, int) or not isinstance(end, int) or not isinstance(text, str):
        return [f"{where}: text/start/end are not str/int/int"]
    if not (0 <= start < end <= len(sentence)):
        faults.append(f"{where}: offsets [{start},{end}) outside the sentence")
    elif sentence[start:end] != text:
        faults.append(f"{where}: sentence[{start}:{end}] is "
                      f"{sentence[start:end]!r}, gold says {text!r}")
    if typed and item.get("type") not in SPAN_TYPES:
        faults.append(f"{where}: type {item.get('type')!r} is not one of {SPAN_TYPES}")
    known = {"text", "start", "end"} | ({"type"} if typed else set())
    for extra in set(item) - known:
        faults.append(f"{where}: unknown key {extra!r}")
    return faults


def validate_case(case: dict) -> List[str]:
    """Every fault in one record, named precisely. Pairing is checked at file level."""
    faults: List[str] = []
    cid = case.get("id") or "<no id>"

    for extra in set(case) - CASE_KEYS:
        faults.append(f"{cid}: unknown key {extra!r} — the schema does not ride along")
    for missing in CASE_KEYS - set(case):
        faults.append(f"{cid}: missing {missing!r}")
    if faults:
        return faults

    if not isinstance(case["id"], str) or not case["id"].strip():
        faults.append(f"{cid}: id must be a non-empty string")
    if case["stratum"] not in STRATA:
        faults.append(f"{cid}: stratum {case['stratum']!r} is not declared")
    if case["noise"] not in (CLEAN,) + NOISE:
        faults.append(f"{cid}: noise {case['noise']!r} is not declared")
    if case["source"] not in SOURCES:
        faults.append(f"{cid}: source {case['source']!r} is not declared")
    if not isinstance(case["sentence"], str) or not case["sentence"].strip():
        faults.append(f"{cid}: sentence is empty")
    if case["pair_id"] is not None and not isinstance(case["pair_id"], str):
        faults.append(f"{cid}: pair_id must be a string or null")

    gold = case["gold"]
    if not isinstance(gold, dict):
        return faults + [f"{cid}: gold is not an object"]
    for extra in set(gold) - GOLD_KEYS:
        faults.append(f"{cid}: gold has unknown key {extra!r}")
    for missing in GOLD_KEYS - set(gold):
        faults.append(f"{cid}: gold is missing {missing!r}")
    if any(f.startswith(f"{cid}: gold") for f in faults):
        return faults

    sentence = case["sentence"] if isinstance(case["sentence"], str) else ""
    spans, actions = gold["spans"], gold["actions"]
    for i, span in enumerate(spans):
        faults += _offsets(f"{cid}: spans[{i}]", span, sentence, typed=True)
    for i, act in enumerate(actions):
        faults += _offsets(f"{cid}: actions[{i}]", act, sentence, typed=False)

    # same-type spans must not overlap — two golds claiming one character is an authoring slip
    placed = [(s["start"], s["end"], s.get("type"), i) for s in spans
              if isinstance(s.get("start"), int) and isinstance(s.get("end"), int)]
    for a in range(len(placed)):
        for b in range(a + 1, len(placed)):
            s1, e1, t1, i1 = placed[a]
            s2, e2, t2, i2 = placed[b]
            if t1 == t2 and s1 < e2 and s2 < e1:
                faults.append(f"{cid}: spans[{i1}] and spans[{i2}] overlap ({t1})")

    seen_actions = set()
    for i, att in enumerate(gold["attachments"]):
        where = f"{cid}: attachments[{i}]"
        if set(att) != {"action", "objects"}:
            faults.append(f"{where}: must be exactly {{action, objects}}")
            continue
        act = att["action"]
        if not isinstance(act, int) or not (0 <= act < len(actions)):
            faults.append(f"{where}: action {act!r} is out of bounds")
        elif act in seen_actions:
            faults.append(f"{where}: action {act} attached twice — one entry per action")
        else:
            seen_actions.add(act)
        objs = att["objects"]
        if not isinstance(objs, list) or any(
                not isinstance(o, int) or not (0 <= o < len(spans)) for o in objs):
            faults.append(f"{where}: objects {objs!r} reference spans that do not exist")
        elif len(set(objs)) != len(objs):
            faults.append(f"{where}: objects repeat an index")
    return faults


def validate(cases: List[dict]) -> List[str]:
    """The whole file: every record, plus identity and pairing across records."""
    faults: List[str] = []
    for case in cases:
        faults += validate_case(case)

    ids: Dict[str, dict] = {}
    for case in cases:
        cid = case.get("id")
        if isinstance(cid, str) and cid in ids:
            faults.append(f"{cid}: id appears twice")
        elif isinstance(cid, str):
            ids[cid] = case

    for case in cases:
        cid, pid = case.get("id") or "<no id>", case.get("pair_id")
        if pid is None:
            continue
        if case.get("noise") == CLEAN:
            faults.append(f"{cid}: a clean case never points at a twin — pairing is one-way")
            continue
        twin = ids.get(pid)
        if twin is None:
            faults.append(f"{cid}: pair_id {pid!r} names no case in this file")
            continue
        if twin.get("noise") != CLEAN:
            faults.append(f"{cid}: twin {pid!r} is not clean — noised->noised is not a pair")
        if twin.get("stratum") != case.get("stratum"):
            faults.append(f"{cid}: twin {pid!r} is a different stratum")
    return faults


def load(path: str) -> List[dict]:
    """JSONL, one case per non-empty line. A parse error names its line and stops."""
    out: List[dict] = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as err:
                raise SystemExit(f"{path}:{n}: not JSON — {err}")
    return out


# ── the selfcheck: a validator that cannot fail validates nothing ────────────────────
def _good() -> dict:
    return {"id": "coord-0001", "stratum": "coordination", "noise": CLEAN,
            "pair_id": None, "source": "seed",
            "sentence": "restart the web vm and the db vm then snapshot both",
            "gold": {"spans": [
                        {"text": "the web vm", "start": 8, "end": 18, "type": "object"},
                        {"text": "the db vm", "start": 23, "end": 32, "type": "object"}],
                     "actions": [
                        {"text": "restart", "start": 0, "end": 7},
                        {"text": "snapshot", "start": 38, "end": 46}],
                     "attachments": [{"action": 0, "objects": [0, 1]},
                                     {"action": 1, "objects": [0, 1]}]}}


def selfcheck() -> List[str]:
    """Fourteen broken records; each must trip its OWN fault. Silence anywhere is the bug."""
    problems: List[str] = []

    if validate([_good()]):
        problems.append(f"the known-good case FAILED: {validate([_good()])}")

    def broken(mutate, expect: str):
        case = _good()
        mutate(case)
        got = validate([case])
        if not any(expect in f for f in got):
            problems.append(f"expected a fault containing {expect!r}, got {got or 'NOTHING'}")

    broken(lambda c: c.__setitem__("stratum", "vibes"), "not declared")
    broken(lambda c: c.__setitem__("noise", "smudged"), "not declared")
    broken(lambda c: c.__setitem__("source", "dreamt"), "not declared")
    broken(lambda c: c.__setitem__("bonus", 1), "unknown key")
    broken(lambda c: c["gold"].__setitem__("extra", []), "unknown key")
    broken(lambda c: c["gold"]["spans"][0].__setitem__("start", 9), "gold says")
    broken(lambda c: c["gold"]["spans"][0].__setitem__("end", 99), "outside the sentence")
    broken(lambda c: c["gold"]["spans"][0].__setitem__("type", "thing"), "not one of")
    broken(lambda c: c["gold"]["attachments"][0].__setitem__("action", 7), "out of bounds")
    broken(lambda c: c["gold"]["attachments"][0].__setitem__("objects", [0, 5]),
           "do not exist")
    broken(lambda c: c["gold"]["attachments"].append({"action": 0, "objects": [1]}),
           "attached twice")
    broken(lambda c: c["gold"]["spans"].append(
        {"text": "web vm and", "start": 12, "end": 22, "type": "object"}), "overlap")
    broken(lambda c: c.__setitem__("pair_id", "coord-0001"),
           "a clean case never points")

    noised = _good()
    noised.update(id="coord-0001n", noise="typos", pair_id="ghost-0000")
    got = validate([_good(), noised])
    if not any("names no case" in f for f in got):
        problems.append(f"expected the dangling pair fault, got {got or 'NOTHING'}")
    return problems


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selfcheck" in argv:
        bad = selfcheck()
        if bad:
            print("\n".join(f"  ✗ {b}" for b in bad))
            return 1
        print("  the validator catches all fourteen planted faults, and passes the good case")
        return 0
    path = next((a for a in argv if not a.startswith("--")), None)
    if not path:
        print("usage: python3 -m tests.bench.read_eval.schema <cases.jsonl> | --selfcheck")
        return 2
    cases = load(path)
    faults = validate(cases)
    if faults:
        print("\n".join(f"  ✗ {f}" for f in faults))
        print(f"\n  {len(faults)} fault(s) in {len(cases)} case(s)")
        return 1
    strata = {}
    for c in cases:
        strata[c["stratum"]] = strata.get(c["stratum"], 0) + 1
    print(f"  {len(cases)} case(s), 0 faults")
    for s in STRATA:
        if s in strata:
            print(f"    {s:16} {strata[s]}")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
