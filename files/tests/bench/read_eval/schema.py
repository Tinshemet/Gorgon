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
`--selfcheck` proves the validator CAN fail: a battery of deliberately broken records, each
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

# ── v1.1: ARGUMENT ROLES, because a role swap was invisible (operator, mid-review 08-18:
#   *"we can only get the recall side, not the precision"*). An attachment's members may be
#   role-tagged — {"span": 1, "role": "patient"} — and a reading that puts the network onto
#   the vms is then a SCORED miss instead of a perfect score. V2-LEDGER item 3, taken early
#   because it blinded the eval on exactly the confidently-wrong class it exists to bill.
#     patient      the thing acted upon — exactly ONE per tagged attachment
#     destination  where it goes · source  where it comes from · value  what it is set to
#   ⇒ A PLAIN INT MEMBER REMAINS LEGAL — single-argument attachments carry no direction, so
#     45 of 53 cases keep their bytes and the operator's verdicts on them stay FRESH.
#   ⇒ MIXED FORMS IN ONE ATTACHMENT ARE A FAULT: half-tagged direction is untestable.
#   ⇒ **`excluded` — THE OPERATOR'S RULING, mid-review 08-18:** *"the exception should be
#     its own object: 'every vm' - 'db vm'."* An exception is not part of the set's name, it
#     is a SECOND thing with a relation — which is the seam's own model (`Declared.excludes`
#     travels with the set). And it bills the deadliest misreading DIRECTLY: an excluded
#     member scores a hit only when the reading does NOT act on it. One span could not say
#     that; a reader stopping db along with everything else still overlapped the big span.
ROLES = ("patient", "destination", "source", "value", "excluded")

# ── v1.3: QUERY ACTS (operator, mid-review 08-18: mc-0002's second clause is "a dropped
#   clause, that is a query"). A question is a THIRD of the sentence taxonomy — order ·
#   question · statement — and v1.2 could only mark imperative verbs, so *"is alpha
#   running?"* flattened to a stray unattached span and reading the question scored the
#   same as ignoring it. An action entry may carry `kind: "query"`: its span is the
#   INTERROGATIVE CLAUSE (grammar still decides — there is no imperative verb to bracket,
#   so the clause itself is the act), attached to what it asks about.
#   And v1.3b, closing the taxonomy: `kind: "rule"` — the statement that LEGISLATES.
#   *"never delete the db vm"* is a PROHIBITION, not an instruction to delete; reading it as
#   an order is a catastrophic flip, and the seam's own reading (a rule quantifies over TIME,
#   `speech_act.DECLARATION`) existed with nothing to bill it. A rule act is never executed:
#   an operation emitted from a rule clause is a hallucination BY DEFINITION.
ACTION_KINDS = ("instruct", "query", "rule")

# ── v1.2: ACTION TRIGGERS (V2-LEDGER item 4, taken mid-review 08-18 at the operator's
#   instruction — the second time the flattening fought the reviewer in one pass). An action
#   may carry `trigger`: the offsets of the clause that STARTS it — "if alpha is stopped",
#   "when the backup finishes", "after the job finishes", "at 21:30". What to do and what
#   starts it are the seam's own split (`temporal.read`, `iso.is_condition`); without this
#   field a reader that captures the condition and one that discards it scored the same,
#   while the discarded qualifier is a live defect ("stop every vm at 9pm" runs NOW).

CASE_KEYS = {"id", "stratum", "noise", "pair_id", "source", "sentence", "gold"}
GOLD_KEYS = {"spans", "actions", "attachments"}


def members_of(attachment: dict):
    """Every attachment member as (span_index, role_or_None) — THE one parser of both forms.

    Written here so runner, review and seeds read an attachment identically — the
    same-rule-on-two-paths defect ([[gorgon-detector-not-producer-again]] era) pre-empted.
    """
    out = []
    for member in attachment.get("objects", ()):
        if isinstance(member, dict):
            out.append((member.get("span"), member.get("role")))
        else:
            out.append((member, None))
    return out


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
        known = {"text", "start", "end", "trigger", "kind"}
        for extra in set(act) - known:
            faults.append(f"{cid}: actions[{i}]: unknown key {extra!r}")
        if "kind" in act and act["kind"] not in ACTION_KINDS:
            faults.append(f"{cid}: actions[{i}]: kind {act['kind']!r} is not one of "
                          f"{ACTION_KINDS}")
        slim = {k: v for k, v in act.items() if k not in ("trigger", "kind")}
        faults += _offsets(f"{cid}: actions[{i}]", slim, sentence, typed=False)
        if "trigger" in act:
            trig = act["trigger"]
            if not isinstance(trig, dict):
                faults.append(f"{cid}: actions[{i}]: trigger is not an object")
            else:
                faults += _offsets(f"{cid}: actions[{i}].trigger", trig, sentence,
                                   typed=False)

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
        if not isinstance(objs, list):
            faults.append(f"{where}: objects is not a list")
            continue
        members = members_of(att)
        indices = [m[0] for m in members]
        if any(not isinstance(ix, int) or not (0 <= ix < len(spans)) for ix in indices):
            faults.append(f"{where}: objects {objs!r} reference spans that do not exist")
            continue
        if len(set(indices)) != len(indices):
            faults.append(f"{where}: objects repeat an index")
        # v1.1 roles: all-or-none per attachment, roles from the closed set, ONE patient
        tagged = [role for _ix, role in members if role is not None]
        if tagged:
            if len(tagged) != len(members):
                faults.append(f"{where}: mixed tagged and untagged members — "
                              f"half-tagged direction is untestable")
            for role in tagged:
                if role not in ROLES:
                    faults.append(f"{where}: role {role!r} is not one of {ROLES}")
            if sum(1 for r in tagged if r == "patient") != 1:
                faults.append(f"{where}: a tagged attachment needs exactly one patient")
        for member in objs:
            if isinstance(member, dict) and set(member) != {"span", "role"}:
                faults.append(f"{where}: a tagged member is exactly {{span, role}}")
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

    planted = [0]

    def broken(mutate, expect: str):
        planted[0] += 1
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
    # v1.1 roles — the validator must refuse each way a tag can lie
    broken(lambda c: c["gold"]["attachments"][0].__setitem__(
        "objects", [{"span": 0, "role": "vibes"}]), "not one of")
    broken(lambda c: c["gold"]["attachments"][0].__setitem__(
        "objects", [{"span": 0, "role": "patient"}, 1]), "mixed tagged and untagged")
    broken(lambda c: c["gold"]["attachments"][0].__setitem__(
        "objects", [{"span": 0, "role": "patient"}, {"span": 1, "role": "patient"}]),
        "exactly one patient")
    broken(lambda c: c["gold"]["attachments"][0].__setitem__(
        "objects", [{"span": 0, "role": "destination"}]), "exactly one patient")
    # v1.2 triggers — lying offsets and stowaway keys must both refuse
    broken(lambda c: c["gold"]["actions"][0].__setitem__(
        "trigger", {"text": "nope", "start": 0, "end": 4}), "gold says")
    broken(lambda c: c["gold"]["actions"][0].__setitem__(
        "trigger", {"text": "restart", "start": 0, "end": 7, "why": "x"}), "unknown key")
    broken(lambda c: c["gold"]["actions"][0].__setitem__("kind", "musing"), "not one of")

    noised = _good()
    noised.update(id="coord-0001n", noise="typos", pair_id="ghost-0000")
    planted[0] += 1
    got = validate([_good(), noised])
    if not any("names no case" in f for f in got):
        problems.append(f"expected the dangling pair fault, got {got or 'NOTHING'}")
    return problems if problems else ["PLANTED=%d" % planted[0]]


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selfcheck" in argv:
        got = selfcheck()
        if got and not got[0].startswith("PLANTED="):
            print("\n".join(f"  ✗ {b}" for b in got))
            return 1
        n = got[0].split("=")[1] if got else "?"
        print(f"  the validator catches all {n} planted faults, and passes the good case")
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
