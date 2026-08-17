"""read_eval_buckets.py — BUILD ORDER #1 OF THE READ EVAL: bucket what already bleeds.

    PYTHONPATH=. python3 -m tests.bench.read_eval_buckets            # the report
    PYTHONPATH=. python3 -m tests.bench.read_eval_buckets --check    # mapping integrity
    PYTHONPATH=. python3 -m tests.bench.read_eval_buckets --cases    # free real-failure seeds

# ⇒⇒ WHAT THIS IS FOR — the spec's first step, 2026-08-18

The read-eval spec says: *"Weight strata by bucketing the existing failure log FIRST — build/
expand the buckets that actually bleed."* This file IS that bucketing. It walks the two curated
failure inventories the project already keeps — `issue_map.ISSUES` (every known issue, by level
and family) and `structure_map.MAP` (39 ways a sentence is built, run live) — and sorts every
READ-relevant row into the spec's own vocabulary:

    STRATA   the spec's eight — clean-single · coordination · buried-args · anaphora ·
             negation · conditionals · multi-clause · self-correction — PLUS THE FOUR THIS
             REPORT'S FIRST RUN EARNED (ruled 2026-08-18): qualifiers · adjunct-clauses ·
             diagnosis · cross-cutting. `read_eval.schema` owns the list.
    NOISE    terse · typos · no-punct · voice · embedded-junk · code-switch

# ⇒ THE MAPPING IS DECLARED, NEVER INFERRED

Both inventories are CLOSED, CURATED lists — so a hand-written mapping is admissible under the
same licence as every other declared table here ([[gorgon-declare-dont-infer]]). No keyword
matching: a keyword matcher over open English is the exact thing the project bans, and it would
misfile the first issue whose name reads unlike its meaning.

⇒ ⚠ **AND THE MAPPING IS TOTAL, BOTH WAYS, OR `--check` FAILS.** Every source row must be
  mapped and every mapped key must exist in its source. An issue added tomorrow BREAKS the
  check until somebody decides its bucket — a forced decision, never a silent drop, which is
  the UNKNOWN-is-never-filtered rule applied to our own bookkeeping.

# ⇒ TWO BUCKETS THE SPEC DOES NOT HAVE, AND WHY THEY ARE REPORTED RATHER THAN HIDDEN

    OUT-OF-SCOPE     cross-turn rows. The eval reads ONE string; a case whose gold cannot be
                     determined by a human from the sentence alone is excluded BY THE SPEC
                     (§3 rule 1 — that is gate territory). They are counted, not discarded:
                     they are the cross-turn backlog wearing its real size.
    NO-SPEC-BUCKET   rows that are read-relevant but fit no spec stratum — the qualifier
                     family (units, superlative, manner), the sentence types (diagnosis,
                     commissive, suggestion), the cross-cutting causes (vocab lists, courtesy).
                     ⇒ **THIS LIST IS THE OPERATOR'S DECISION QUEUE**: each row either earns a
                       stratum (the way self-correction earned one in the spec), folds into an
                       existing one, or is explicitly deferred. Hiding them would repeat
                       DialogBank — scoring well by not looking.

# ⇒ ⚠ NOISE PROPORTIONS: THERE IS NO USAGE LOG OF SENTENCES, AND THE REPORT SAYS SO

The spec says *"proportions from logs, not guesses"* — and `~/.gorgon/events.log` holds TOOL
CALLS (`{"tool": "launch_vm", ...}`), not the operator's sentences. Nothing on this machine
records what was TYPED. So the spec's declared fallback applies — ~40% clean / 60% noise,
weighted toward terse+typos — and it is printed as an ASSUMPTION, never as a measurement.
⇒ The fix is upstream and cheap: log the raw request string at the door. Until then every
  noise proportion is provisional.
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

from .issue_map import ISSUES, READ
from .structure_map import MAP

# ── the vocabulary — OWNED BY `read_eval.schema`, the eval's contract. This file only
#   consumes it, so a stratum earned or retired changes exactly one place.
#   ⇒ THE RULING, 2026-08-18, off this report's own decision queue: *"qualifiers and
#     adjunct-clauses earn strata, diagnosis too, as well as cross-cutting causes."* The four
#     clusters below the spec's eight are therefore STRATA now, not residue.
from .read_eval.schema import NOISE, STRATA
OUT = "OUT-OF-SCOPE"          # cross-turn / dialogue — excluded by the spec itself
RESIDUE = "NO-SPEC-BUCKET"    # read-relevant, no spec stratum — the decision queue

BUCKETS = STRATA + NOISE + (OUT, RESIDUE)


# ── structure_map rows -> bucket. Keyed by the row's NAME, checked against MAP. ──────
STRUCTURE_BUCKET: Dict[str, str] = {
    "determiner": "clean-single",
    "cardinal": "clean-single",
    "count comparator": "clean-single",
    "declared attribute value": "clean-single",
    "member list": "coordination",
    "relative clause": "buried-args",         # the argument sits behind a subordinate clause
    "exception": "negation",                  # the spec names "everything except" as negation
    "reciprocal": "anaphora",                 # pronoun-headed set inside one clause
    "magnitude comparative": "qualifiers",
    "superlative": "qualifiers",
    "units": "qualifiers",
    "possessive": "qualifiers",
    "prepositional filter": "buried-args",    # attachment: does `on lab` bind the vms or the verb?
    "reduced relative": "buried-args",
    "apposition": RESIDUE,               # still in the queue
    "negated filter": "negation",
    "coordination": "coordination",
    "temporal subordination": "conditionals",  # `whenever` is the conditional's temporal arm
    "clock adjunct": "qualifiers",
    "conditional": "conditionals",
    "purpose": "adjunct-clauses",
    "cause": "adjunct-clauses",
    "concession": "adjunct-clauses",
    "alternative": "coordination",            # `or` is coordination with a choice — see the seed
    "comparison across clauses": "adjunct-clauses",
    "anaphora, same turn": "anaphora",
    "anaphora, cross turn": OUT,              # gold undeterminable from the sentence — spec §3.1
    "ellipsis, cross turn": OUT,
    "repair": "self-correction",
    "topic shift": "multi-clause",            # two independent requests in ONE string — in scope
    "answer to our question": OUT,            # dialogue, not a request
    "casing": "no-punct",
    "typo": "typos",
    "contraction": RESIDUE,                   # standard English, not degradation — not noise
    "multi-sentence": "multi-clause",
    "fragment": "terse",                      # the spec's own example of terse IS a fragment
    "bullet list": "terse",
    "pasted data": "embedded-junk",
    "identifiers and paths": "embedded-junk",
}

# ── issue_map READ rows -> bucket. ROUTE/RESOLVE rows are the eval's explicit non-goal. ──
ISSUE_BUCKET: Dict[str, str] = {
    "anaphora across turns": OUT,
    "ellipsis across turns": OUT,
    "feedback direction": OUT,
    "turn management": OUT,
    "partner correction": OUT,
    "conditionality": "conditionals",
    "partiality": "qualifiers",
    "certainty": "qualifiers",
    "magnitude": "qualifiers",
    "superlative": "qualifiers",
    "units": "qualifiers",
    "manner constraint": "qualifiers",
    "one-off clock time": "qualifiers",
    "diagnosis": "diagnosis",                 # ⚠ D1, THE THESIS — a stratum of its own now
    "resolution": RESIDUE,
    "evidence": "embedded-junk",
    "commissive": RESIDUE,
    "suggestion": RESIDUE,
    "self-correction": "self-correction",
    "retraction": "self-correction",
    "produces nothing -> GREETING": "clean-single",
    "negation -> the opposite set": "negation",
    "`if` -> teaching": "conditionals",
    "universal anywhere -> legislation": "clean-single",
    "an attribute -> a machine": "cross-cutting",
    "a bare `sorry` -> a repair": "self-correction",
    "`or` read as `and`": "coordination",
    "_operation_words leak": "cross-cutting",
    "ACHIEVE_MARKERS": "cross-cutting",
    "intent markers grant authority": RESIDUE,  # -> spec §4 register variation (overly polite)
    "flavour needs a teacher": RESIDUE,
    "drop the row / forgive the word": "cross-cutting",
    "one propose(), written twice": "cross-cutting",
}


# ── what remains in the queue after the 2026-08-18 ruling — NOT ruled on, still open:
RESIDUE_CLUSTER: Dict[str, str] = {
    # SENTENCE TYPES minus diagnosis — the operator promoted diagnosis alone
    "resolution": "sentence-types", "commissive": "sentence-types",
    "suggestion": "sentence-types",
    # REGISTER — the spec already has a home: §4 register variation, not a stratum
    "intent markers grant authority": "register (spec §4)",
    "flavour needs a teacher": "register (spec §4)",
    "contraction": "register (spec §4)",
    # SMALL
    "apposition": "small",
}


class Row(NamedTuple):
    bucket: str
    name: str
    example: str
    bleeds: bool        # OPEN issue, or a structure hole/partial — the weight signal
    seed: bool          # carries a sentence usable as a real-failure case
    provenance: str     # issue_map · structure_map
    state: str          # OPEN/FIXED/DECLINED/PARKED · ok/PARTIAL/HOLE


def rows() -> List[Row]:
    out: List[Row] = []
    for f in MAP:
        state = "HOLE" if not f.reads_it else ("PARTIAL" if f.partial else "ok")
        out.append(Row(STRUCTURE_BUCKET[f.name], f.name, f.example,
                       bleeds=(not f.reads_it) or f.partial,
                       seed=bool(f.example), provenance="structure_map", state=state))
    for i in ISSUES:
        if i.level != READ:
            continue                          # the eval is read-only — spec §9
        out.append(Row(ISSUE_BUCKET[i.name], i.name, i.what,
                       bleeds=i.state == "OPEN",
                       seed=i.state in ("OPEN", "FIXED"), provenance="issue_map",
                       state=i.state))
    return out


def weights() -> Dict[str, Tuple[int, int]]:
    """bucket -> (bleeding, total). The bleeding count is the build-order signal."""
    got: Dict[str, Tuple[int, int]] = {b: (0, 0) for b in BUCKETS}
    for r in rows():
        bleed, total = got[r.bucket]
        got[r.bucket] = (bleed + (1 if r.bleeds else 0), total + 1)
    return got


def check() -> List[str]:
    """Total, both ways, or say exactly what is not."""
    faults: List[str] = []
    map_names = {f.name for f in MAP}
    issue_names = {i.name for i in ISSUES if i.level == READ}
    for key in STRUCTURE_BUCKET:
        if key not in map_names:
            faults.append(f"STRUCTURE_BUCKET maps {key!r}, which structure_map does not have")
    for name in map_names:
        if name not in STRUCTURE_BUCKET:
            faults.append(f"structure_map row {name!r} is UNMAPPED — decide its bucket")
    for key in ISSUE_BUCKET:
        if key not in issue_names:
            faults.append(f"ISSUE_BUCKET maps {key!r}, which issue_map does not have at READ")
    for name in issue_names:
        if name not in ISSUE_BUCKET:
            faults.append(f"issue_map READ row {name!r} is UNMAPPED — decide its bucket")
    for key, bucket in list(STRUCTURE_BUCKET.items()) + list(ISSUE_BUCKET.items()):
        if bucket not in BUCKETS:
            faults.append(f"{key!r} -> {bucket!r}, which is not a declared bucket")
    # the residue clustering is total the same way — one decision per row, none silent
    residue_names = {k for k, v in list(STRUCTURE_BUCKET.items()) + list(ISSUE_BUCKET.items())
                     if v == RESIDUE}
    for name in residue_names:
        if name not in RESIDUE_CLUSTER:
            faults.append(f"residue row {name!r} has no cluster — decide it")
    for key in RESIDUE_CLUSTER:
        if key not in residue_names:
            faults.append(f"RESIDUE_CLUSTER names {key!r}, which is not a residue row")
    return faults


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    bad = check()
    if bad:
        print("\n".join(f"  ✗ {b}" for b in bad))
        return 1
    if "--check" in argv:
        print("  the bucketing is total, both ways — 0 faults")
        return 0

    all_rows = rows()
    if "--cases" in argv:
        print("\n  FREE REAL-FAILURE SEEDS — sentence · bucket · where it came from\n")
        for r in sorted(all_rows, key=lambda r: (r.bucket, r.name)):
            if r.seed and r.bucket not in (OUT,):
                print(f"    [{r.bucket:15}] {r.example[:64]!r}")
                print(f"    {'':17} {r.name} · {r.provenance} · {r.state}")
        return 0

    got = weights()
    print("\n  STRATUM WEIGHTS — build the buckets that bleed (spec: 50–80 cases each)\n")
    ordered = sorted(STRATA, key=lambda b: -got[b][0])
    for b in ordered:
        bleed, total = got[b]
        bar = "█" * bleed
        floor = "spec floor 50 — must still saturate" if bleed == 0 else \
            f"suggest {min(80, 50 + 10 * bleed)}"
        print(f"    {b:16} {bleed:2} bleeding of {total:2} known   {bar:6} {floor}")

    print("\n  NOISE — evidence per type, and ⚠ THE PROPORTIONS ARE AN ASSUMPTION:")
    print("  events.log records TOOL CALLS, not sentences. Nothing logs what was TYPED, so")
    print("  the spec default stands — ~40% clean / 60% noise, weighted terse+typos.")
    print("  ⇒ the cheap fix is upstream: log the raw request string at the door.\n")
    for b in NOISE:
        bleed, total = got[b]
        note = "no evidence either way" if total == 0 else f"{bleed} bleeding of {total} known"
        print(f"    {b:16} {note}")

    outs = [r for r in all_rows if r.bucket == OUT]
    res = [r for r in all_rows if r.bucket == RESIDUE]
    print(f"\n  OUT-OF-SCOPE ({len(outs)}) — cross-turn; the spec itself excludes these (§3.1).")
    print(f"  They are the cross-turn backlog wearing its real size, not deleted work.")
    print(f"\n  ⇒⇒ NO-SPEC-BUCKET ({len(res)}) — THE OPERATOR'S DECISION QUEUE, one choice per")
    print(f"     CLUSTER: earn a stratum · fold into one · defer explicitly.\n")
    clusters: Dict[str, List[Row]] = {}
    for r in res:
        clusters.setdefault(RESIDUE_CLUSTER[r.name], []).append(r)
    for cluster in sorted(clusters, key=lambda c: -sum(1 for r in clusters[c] if r.bleeds)):
        members = clusters[cluster]
        bleeding = sum(1 for r in members if r.bleeds)
        print(f"    ── {cluster}  ({bleeding} bleeding of {len(members)})")
        for r in sorted(members, key=lambda r: (not r.bleeds, r.name)):
            mark = "⬜" if r.bleeds else "✅"
            flag = "   ⚠ D1 — THE THESIS" if r.name == "diagnosis" else ""
            print(f"       {mark} {r.name:28} {r.example[:40]!r}{flag}")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
