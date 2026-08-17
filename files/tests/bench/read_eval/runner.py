"""runner.py — BUILD ORDER #3: feed cases, capture both passes, score, write results.

    PYTHONPATH=. python3 -m tests.bench.read_eval.runner <cases.jsonl>          # the eval
    PYTHONPATH=. python3 -m tests.bench.read_eval.runner <cases.jsonl> --limit 20
    PYTHONPATH=. python3 -m tests.bench.read_eval.runner --smoke                # wiring proof

# ⇒⇒ WHAT IS RUN — THE REAL SEAM, NOT A REPLICA

    pass 1   `pass1.run_scanned(sentence)`            -> Declared rows (the OBJECT spans)
    pass 2   `pass2.operations_by_clause(...)`        -> [(clause, Operation)] (the ACTIONS,
                                                         and the attachment via `on`)

Both passes call the model exactly as production does. Every case is a different sentence, so
every call is COLD — the warm-path artifact `seam_determinism` documents cannot occur here by
construction. Temp 0; where a number matters, run the file 3x and compare, never re-run one
case ([[gorgon-seed-dependence]]).

# ⇒ HOW OUR SHAPES MEET THE SPEC'S GOLD, AND TWO HONEST MISMATCHES

**Objects.** A Declared row's `span` is text; the case's gold is offsets. The runner recovers
offsets by locating the span in the sentence — first occurrence, which is the same convention
`scan` itself uses. Matching gold<->predicted is greedy best-overlap; DETECTION credits >=50%
token overlap (the spec's threshold, reported); BOUNDARY is exact-match rate and token F1.

**Actions.** ⚠ The seam NEVER EMITS A VERB SPAN — pass 2 answers with a manifest OPERATOR
(`stop_vm`), not the sentence's word (`halt`). So a gold action is scored DETECTED when an
operation was emitted from the clause that CONTAINS the gold verb's offsets, and action
boundary metrics are **reported as not-measured** rather than faked at 100%. If verb offsets
ever matter, that is seam work (emit them), never runner work (guess them).

**Attachment.** Gold maps action -> objects. Predicted: the operation's `on` is a handle; the
symbol table maps handle -> row -> matched gold span. Scored per (action, object) pair, and —
the spec's own rule — ONLY over correctly-detected spans, so pass 2 is never billed for pass
1's misses. `value` (a second declared name) is checked as an object of the same action.

# ⇒ PER-PASS ATTRIBUTION IS STRUCTURAL, NOT DIAGNOSED

    detection / boundary miss            -> pass 1  (it marks spans)
    attachment miss on correct spans     -> pass 2  (it slots them)
    hallucinated span                    -> pass 1 · hallucinated action -> pass 2

# ⇒ THE RESULTS FILE IS VERSIONED, ONE PER RUN, RAW MATERIAL INCLUDED

`results/<git-sha>-<utc>.json` — config, per-case intermediates (rows, operations, matches),
per-stratum x per-noise table, paired degradation. The intermediates are the point: a failing
case can be re-read from the file without re-running the model, which is the export_failures
lesson (diagnose from the artifact, not from memory of it).

# ⇒ `--smoke` IS A WIRING PROOF, NOT AN EVAL

Three hand-labelled sentences run end to end. It exists because a runner nobody has run is
the built-and-never-called defect wearing a new name. Its cases are NOT the eval set and its
numbers mean nothing beyond "every stage executed and scored".
"""
import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Tuple

from .schema import CLEAN, NOISE, STRATA, load, validate

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
OVERLAP = 0.5                     # the spec's detection threshold, reported with every table


# ── offsets and overlap ──────────────────────────────────────────────────────────────
def _find(sentence: str, text: str) -> Optional[Tuple[int, int]]:
    """First occurrence, case-blind — the same convention `scan` uses to place a span."""
    at = sentence.lower().find(str(text).strip().lower())
    return None if at < 0 else (at, at + len(str(text).strip()))


def _locate(sentence: str, text: str) -> Optional[Tuple[int, int]]:
    """`_find`, then a token-sequence walk for text the seam has NORMALISED.

    ⇒ FOUND ON THE SMOKE'S THIRD SENTENCE: `clauses_of` rewrites *"the web vm and the db vm"*
      to *"the web vm, the db vm"*, so the clause string no longer occurs in the sentence and
      exact find returns nothing — which silently made every action UNDETECTABLE in any
      coordinated clause. The walk matches the clause's TOKENS in order instead; punctuation
      and the rewritten conjunction fall out on both sides.
    """
    got = _find(sentence, text)
    if got:
        return got
    import re
    want = re.findall(r"[\w:']+", str(text).lower())
    have = [(m.group(0).lower(), m.start(), m.end())
            for m in re.finditer(r"[\w:']+", sentence)]
    if not want:
        return None
    for start_at in range(len(have)):
        if have[start_at][0] != want[0]:
            continue
        at, last = start_at, start_at
        ok = True
        for token in want[1:]:
            at = next((j for j in range(at + 1, len(have)) if have[j][0] == token), None)
            if at is None:
                ok = False
                break
            last = at
        if ok:
            return (have[start_at][1], have[last][2])
    return None


def _tokens_at(sentence: str, start: int, end: int) -> List[Tuple[int, int]]:
    import re
    return [(m.start() + start, m.end() + start)
            for m in re.finditer(r"[\w:']+", sentence[start:end])]


def _token_overlap(sentence: str, a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """Shared tokens / gold tokens — a token counts when the other side covers it fully."""
    gold = _tokens_at(sentence, *a)
    if not gold:
        return 0.0
    hit = sum(1 for s, e in gold if b[0] <= s and e <= b[1])
    return hit / len(gold)


def _f1(sentence: str, gold: Tuple[int, int], got: Tuple[int, int]) -> float:
    g = set(_tokens_at(sentence, *gold))
    p = set(_tokens_at(sentence, *got))
    if not g or not p:
        return 0.0
    shared = len(g & p)
    if not shared:
        return 0.0
    precision, recall = shared / len(p), shared / len(g)
    return 2 * precision * recall / (precision + recall)


# ── one case through both passes ─────────────────────────────────────────────────────
def read_case(sentence: str, board=None) -> dict:
    """The seam's whole reading of one sentence, with everything the scorer needs kept."""
    from planner.formula.legal import Board
    from orchestrator.seam import pass1 as P1, pass2 as P2

    board = board or Board()
    rows = P1.run_scanned(sentence, board=board)
    table = P2.symbol_table(rows, board)
    steps = P2.operations_by_clause(sentence, rows, board=board)

    by_handle = {s.handle: i for i, s in enumerate(table)}
    predicted_spans = []
    for i, row in enumerate(rows):
        where = _find(sentence, row.span or row.name)
        predicted_spans.append({"row": i, "span": row.span, "kind": row.object_type,
                                "where": dict(row.where or {}),
                                "start": where[0] if where else None,
                                "end": where[1] if where else None})
    operations = []
    for clause, op in steps:
        at = _locate(sentence, clause)
        operations.append({"clause": clause,
                           "clause_start": at[0] if at else None,
                           "clause_end": at[1] if at else None,
                           "operator": op.operator, "on": op.on, "value": op.value,
                           "on_row": by_handle.get(op.on),
                           "value_row": by_handle.get(op.value)})
    return {"rows": predicted_spans, "operations": operations}


# ── scoring one case against its gold ────────────────────────────────────────────────
def score_case(case: dict, reading: dict) -> dict:
    sentence = case["sentence"]
    gold_spans = case["gold"]["spans"]
    gold_actions = case["gold"]["actions"]
    predicted = [p for p in reading["rows"] if p["start"] is not None]

    # objects: greedy best-overlap, one predicted span per gold span
    taken: set = set()
    span_match: List[Optional[int]] = []          # gold index -> predicted row index
    detection = boundary_exact = 0
    f1_total = 0.0
    for g in gold_spans:
        best, best_ov = None, 0.0
        for j, p in enumerate(predicted):
            if j in taken:
                continue
            ov = _token_overlap(sentence, (g["start"], g["end"]), (p["start"], p["end"]))
            if ov > best_ov:
                best, best_ov = j, ov
        if best is not None and best_ov >= OVERLAP:
            taken.add(best)
            span_match.append(predicted[best]["row"])
            detection += 1
            exact = (predicted[best]["start"], predicted[best]["end"]) == (g["start"], g["end"])
            boundary_exact += 1 if exact else 0
            f1_total += _f1(sentence, (g["start"], g["end"]),
                            (predicted[best]["start"], predicted[best]["end"]))
        else:
            span_match.append(None)
    hallucinated_spans = len(predicted) - len(taken)

    # ── actions: an operation is ABSORBED by the gold action it serves, or hallucinated.
    #
    # ⇒⇒ THE SMOKE FORCED THIS SHAPE, twice in three sentences:
    #   · `restart` has no manifest operator, so pass 2 legitimately decomposed it into
    #     stop_vm + launch_vm per machine — FOUR operations serving ONE gold action. Counting
    #     ops one-to-one billed a correct expansion as three hallucinations.
    #   · pass 2's per-clause ask leaked the OTHER clause's steps (stop_vm emitted from the
    #     launch clause — despite `operations_by_clause`'s own docstring). Those target rows
    #     the clause's action does not attach, so absorption refuses them and they are
    #     counted hallucinated — which is exactly what they are.
    #
    #   An op is absorbed by gold action g when its clause CONTAINS g's verb AND every row it
    #   targets is one of g's attached objects (through the span match). Detection = at least
    #   one absorbed op; anything absorbed by nothing is hallucinated.
    attached_rows: Dict[int, set] = {}
    for att in case["gold"]["attachments"]:
        attached_rows[att["action"]] = {
            span_match[obj] for obj in att["objects"] if span_match[obj] is not None}
    absorbed: Dict[int, List[int]] = {}
    hallucinated_actions = 0
    for k, op in enumerate(reading["operations"]):
        home = None
        for gi, g in enumerate(gold_actions):
            if op["clause_start"] is None:
                continue
            if not (op["clause_start"] <= g["start"] and g["end"] <= op["clause_end"]):
                continue
            targets = {op["on_row"], op["value_row"]} - {None}
            if targets and targets <= attached_rows.get(gi, set()):
                home = gi
                break
        if home is None:
            hallucinated_actions += 1
        else:
            absorbed.setdefault(home, []).append(k)
    action_hits = [gi in absorbed for gi in range(len(gold_actions))]

    # attachment: per (action, object) pair, ONLY over detected spans — pass 2 never pays
    # for pass 1's miss. Hit when any absorbed op of that action targets the matched row.
    att_total = att_hit = 0
    for att in case["gold"]["attachments"]:
        gi = att["action"]
        if not (0 <= gi < len(action_hits)) or not action_hits[gi]:
            continue
        op_rows = set()
        for k in absorbed.get(gi, []):
            op = reading["operations"][k]
            op_rows |= {op["on_row"], op["value_row"]} - {None}
        for obj in att["objects"]:
            if span_match[obj] is None:
                continue                        # pass 1 missed the span — not pass 2's bill
            att_total += 1
            if span_match[obj] in op_rows:
                att_hit += 1

    return {"gold_spans": len(gold_spans), "detected": detection,
            "boundary_exact": boundary_exact, "boundary_f1": round(f1_total, 3),
            "gold_actions": len(gold_actions), "actions_detected": sum(action_hits),
            "attach_total": att_total, "attach_hit": att_hit,
            "hallucinated_spans": hallucinated_spans,
            "hallucinated_actions": hallucinated_actions,
            "pass1_misses": len(gold_spans) - detection,
            "pass2_misses": att_total - att_hit}


# ── aggregation ──────────────────────────────────────────────────────────────────────
def _cell() -> Dict[str, float]:
    return {k: 0 for k in ("cases", "gold_spans", "detected", "boundary_exact",
                           "boundary_f1", "gold_actions", "actions_detected",
                           "attach_total", "attach_hit", "hallucinated_spans",
                           "hallucinated_actions")}


def aggregate(scored: List[Tuple[dict, dict]]) -> dict:
    by_stratum: Dict[str, dict] = {}
    by_noise: Dict[str, dict] = {}
    overall = _cell()
    for case, s in scored:
        for table, key in ((by_stratum, case["stratum"]), (by_noise, case["noise"])):
            cell = table.setdefault(key, _cell())
            for target in (cell, overall) if table is by_stratum else (cell,):
                target["cases"] += 1
                for k in s:
                    if k in target:
                        target[k] += s[k]
    return {"overall": overall, "by_stratum": by_stratum, "by_noise": by_noise}


def degradation(scored: List[Tuple[dict, dict]]) -> List[dict]:
    """Paired cases: the clean twin's detection rate minus the noised one's, per pair."""
    by_id = {c["id"]: (c, s) for c, s in scored}
    out = []
    for case, s in scored:
        pid = case.get("pair_id")
        if not pid or pid not in by_id:
            continue
        twin_case, twin_s = by_id[pid]
        def rate(x):
            return x["detected"] / x["gold_spans"] if x["gold_spans"] else 1.0
        out.append({"pair": pid, "noise": case["noise"], "stratum": case["stratum"],
                    "clean": round(rate(twin_s), 3), "noised": round(rate(s), 3),
                    "delta": round(rate(twin_s) - rate(s), 3)})
    return out


# ── the run ──────────────────────────────────────────────────────────────────────────
def run(cases: List[dict], limit: Optional[int] = None) -> dict:
    from planner.formula.legal import Board
    board = Board()
    picked = cases[:limit] if limit else cases
    scored: List[Tuple[dict, dict]] = []
    details = []
    for n, case in enumerate(picked, start=1):
        reading = read_case(case["sentence"], board)
        s = score_case(case, reading)
        scored.append((case, s))
        details.append({"id": case["id"], "reading": reading, "score": s})
        print(f"  [{n}/{len(picked)}] {case['id']:20} "
              f"spans {s['detected']}/{s['gold_spans']} · "
              f"actions {s['actions_detected']}/{s['gold_actions']} · "
              f"attach {s['attach_hit']}/{s['attach_total']} · "
              f"halluc {s['hallucinated_spans']}+{s['hallucinated_actions']}")
    return {"config": {"overlap_threshold": OVERLAP, "temp": 0,
                       "action_boundary": "NOT MEASURED — the seam emits operators, "
                                          "not verb spans"},
            "aggregate": aggregate(scored),
            "degradation": degradation(scored),
            "cases": details}


def write_results(report: dict) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10,
                             cwd=os.path.dirname(__file__)).stdout.strip() or "nogit"
    except Exception:
        sha = "nogit"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    path = os.path.join(RESULTS_DIR, f"{sha}-{stamp}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    return path


def _table(report: dict) -> str:
    lines = ["", f"  PER-STRATUM (detection threshold {OVERLAP:.0%} token overlap; action "
                 f"boundaries NOT measured)", ""]
    header = f"    {'stratum':18} {'cases':>5} {'detect':>7} {'exact':>6} {'attach':>7} {'halluc':>7}"
    lines.append(header)
    agg = report["aggregate"]
    for name in list(STRATA) + [CLEAN] + list(NOISE):
        source = agg["by_stratum"] if name in STRATA else agg["by_noise"]
        if name not in source:
            continue
        c = source[name]
        det = f"{c['detected']}/{c['gold_spans']}" if c["gold_spans"] else "—"
        exact = f"{c['boundary_exact']}/{c['detected']}" if c["detected"] else "—"
        att = f"{c['attach_hit']}/{c['attach_total']}" if c["attach_total"] else "—"
        hal = c["hallucinated_spans"] + c["hallucinated_actions"]
        lines.append(f"    {name:18} {c['cases']:>5} {det:>7} {exact:>6} {att:>7} {hal:>7}")
    if report["degradation"]:
        lines.append("\n  PAIRED DEGRADATION (clean minus noised, span detection)")
        for d in report["degradation"]:
            lines.append(f"    {d['pair']:20} {d['noise']:14} {d['stratum']:16} "
                         f"{d['clean']:.0%} -> {d['noised']:.0%}  (Δ {d['delta']:+.0%})")
    return "\n".join(lines)


# ── the smoke: three hand-labelled sentences, end to end. A WIRING PROOF ONLY. ───────
def _smoke_cases() -> List[dict]:
    def case(cid, stratum, noise, pair, sentence, spans, actions, attachments):
        return {"id": cid, "stratum": stratum, "noise": noise, "pair_id": pair,
                "source": "seed", "sentence": sentence,
                "gold": {"spans": spans, "actions": actions, "attachments": attachments}}
    s1 = "create a vm named alpha"
    s2 = "stop every vm that is running and launch the vm named web"
    s3 = "restart the web vm and the db vm"
    return [
        case("smoke-0001", "clean-single", CLEAN, None, s1,
             [{"text": "a vm named alpha", "start": 7, "end": 23, "type": "object"}],
             [{"text": "create", "start": 0, "end": 6}],
             [{"action": 0, "objects": [0]}]),
        case("smoke-0002", "multi-clause", CLEAN, None, s2,
             [{"text": "every vm that is running", "start": 5, "end": 29, "type": "object"},
              {"text": "the vm named web", "start": 41, "end": 57, "type": "object"}],
             [{"text": "stop", "start": 0, "end": 4},
              {"text": "launch", "start": 34, "end": 40}],
             [{"action": 0, "objects": [0]}, {"action": 1, "objects": [1]}]),
        case("smoke-0003", "coordination", CLEAN, None, s3,
             [{"text": "the web vm", "start": 8, "end": 18, "type": "object"},
              {"text": "the db vm", "start": 23, "end": 32, "type": "object"}],
             [{"text": "restart", "start": 0, "end": 7}],
             [{"action": 0, "objects": [0, 1]}]),
    ]


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--smoke" in argv:
        cases = _smoke_cases()
        bad = validate(cases)
        if bad:
            print("\n".join(f"  ✗ {b}" for b in bad))
            return 1
        print("  SMOKE — a wiring proof, not an eval. Its numbers mean nothing beyond "
              "'every stage executed'.\n")
    else:
        path = next((a for a in argv if not a.startswith("--")), None)
        if not path:
            print("usage: python3 -m tests.bench.read_eval.runner <cases.jsonl> "
                  "[--limit N] | --smoke")
            return 2
        cases = load(path)
        bad = validate(cases)
        if bad:
            print("\n".join(f"  ✗ {b}" for b in bad))
            print(f"\n  the case file is not valid — refusing to run on broken gold")
            return 1
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    report = run(cases, limit=limit)
    print(_table(report))
    where = write_results(report)
    print(f"\n  results -> {where}")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
