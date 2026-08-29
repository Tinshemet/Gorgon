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
# ⇒ v3 — THE CLOSING STRATA (operator-scoped 08-20: learned patterns + the
#   structure_map's open holes; v3 is the LAST release and closes the READ saga)
V3_STRATA = ("identifiers", "units", "possessive", "alternatives",
             "reduced-relative", "apposition", "cause", "purpose", "concession",
             "magnitude", "manner", "learned-words", "self-address",
             "ordinals", "fallback", "pairwise", "negated-query", "schedules",
             "superlatives", "naming-lists", "quoted-values", "audit", "capability", "preference",
             # v3.1 (operator, 08-22: "i want to cover everything") — the corpus holes the
             # structure_map and coverage_map named and no stratum held
             "null-turn", "indirect-orders", "tense-person", "deferred-time",
             "conditional-branches", "partitives",
             # v2.3 — the class the operator named: "only understandable by the fact of the
             # previous turns" (08-22). READ is blind; RESOLVE supplies the state.
             "turn-dependent", "difficulty")
STRATA = SPEC_STRATA + EARNED_STRATA + V3_STRATA

NOISE = ("terse", "typos", "no-punct", "voice", "fused", "embedded-junk", "code-switch",
         "list-form", "shouting")        # v3.1: the structure_map's two SURFACE classes
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
#   ⇒ **v2.0 roles — RULED 08-21 (V2-LEDGER #11 per-seed rulings):**
#     `reference` — an apposition CO-NAMES the patient ("alpha, the jumpbox"): scanned
#     and expressed, bound to the same referent, never a second thing. The reader is
#     scored on the equivalence the apposition-as-teaching harvest depends on.
#     `beneficiary` — for-whom ("a network for the test vms"): a silently dropped
#     purpose qualifier (the linguistic sweep's measured gap) becomes a visible miss.
#     A beneficiary expresses for-whom; it never infers extra acts.
#   ⇒ **v2.6 — `selector` (RULED 08-23, ATTRIBUTES ARE LEAVES, ledger #17):** an attribute
#     value that RESTRICTS the patient — `the vm at 10.0.0.5`, `every vm with over 6gb of
#     ram` — is its own span like any other leaf; `selector` says it picks the thing rather
#     than being given to it (`value`). One rule for every attribute value a class owns;
#     a token no class owns (`8g:77q`) is not a leaf and stays in the phrase. Operator:
#     *"wouldn't this make sense that 10.0.0.5 is a different span since it's an attribute?"*
# v3.1 (operator 2026-08-25): a selector/anchor/value may carry a KIND — WHAT it filters or
# assigns by. `status` is oracle-evaluated (the world reports it — decision 6).
MEMBER_KINDS = ("temporal", "status", "magnitude", "identifier", "attribute", "entity")

# v3.1 (operator 2026-08-26): a TRIGGER decomposes — the last blob. Its KIND, and its own
# self-contained sub-spans (subject + condition), mirroring the main clause.
TRIGGER_KINDS = ("conditional", "temporal", "fallback", "coordination")

# v3.1 (operator 2026-08-26): a QUERY decomposes too — its `ask` object carries the wh-TYPE
# (what it seeks) and the wh-word as a sub-span. A DIAGNOSIS (report) carries a `finding`.
QUERY_KINDS = ("identity", "selection", "object-ref", "reason", "count", "amount",
               "polar", "manner", "time", "place")
DIAGNOSIS_KINDS = ("state", "event", "progress")
# v3.1 (operator 2026-08-26): an EVIDENCE clause decomposes like a finding — a reason/report.
EVIDENCE_KINDS = ("state", "event", "progress", "purpose", "outcome")
# v3.1 (operator 2026-08-26): a MANNER channel decomposes too.
MANNER_KINDS = ("sequential", "simultaneous", "duration", "scope")

ROLES = ("patient", "destination", "source", "value", "excluded", "evidence",
         "reference", "beneficiary", "selector",
         # v3.1 (operator 2026-08-25, corpus decomposition): a comparison/condition
         # operator (`over`, `more than`, `stuck at boot`), a temporal reference
         # (`last week`, `a month`), and a creation/possession participle (`taken`).
         "conditional", "anchor", "ownership",
         # v3.1b: `self` — a UNIQUE reference to Gorgon (`you`), always resolving to the
         # agent itself; distinct from `reference` (`it`/`that`, ambiguous, needs a referent)
         "self",
         # v3.1c (operator 2026-08-25): selection over the SET's membership — `quantifier`
         # (two of · half of · any · all but · none), and `ordinal` — RANK the set and pick
         # ONE (produces a singular): first/last/second (by position) AND biggest/oldest
         # (superlative, by an attribute; ranking key in the vector adj:sup). Distinct from
         # `selector`, which FILTERS by an attribute value and may match many.
         "quantifier", "ordinal",
         # v3.1d: `operator` — a reference to the HUMAN user (`i`), the mirror of `self`
         # (Gorgon). Marks a testimony's subject: the act is the operator's, not Gorgon's.
         "operator",
         "seek")   # the wh-word of a query — what it seeks

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
#   And v1.4 — the operator on diag-0001: *"it should be at least 'diagnosis' -> vm2 +
#   'it boots to a blue screen' (testimony)"*. A diagnosis must PRODUCE: `kind: "report"` —
#   the act is the asserting clause (the clause-is-the-act rule, same as query), and its
#   attachment BINDS the patient to the testimony (ledger item 7, taken): exactly one
#   `patient`, the rest role `evidence`. Ops never absorb under a report — acting on a
#   symptom description is the delete_vm-from-"is not working" defect, billed.
ACTION_KINDS = ("instruct", "query", "rule", "report",
                # v3.1 (operator 08-25): META-CONTROL — governs the INTERACTION (pacing,
                # order, session flow), not the lab. Standalone (`lets continue`) or via the
                # `pacing` channel on another act. (`testimony` kind RETIRED 08-26: a user
                # report is EVIDENCE + frame(testimony), not an action.)
                "meta-control")

# ── v1.2: ACTION TRIGGERS (V2-LEDGER item 4, taken mid-review 08-18 at the operator's
#   instruction — the second time the flattening fought the reviewer in one pass). An action
#   may carry `trigger`: the offsets of the clause that STARTS it — "if alpha is stopped",
#   "when the backup finishes", "after the job finishes", "at 21:30". What to do and what
#   starts it are the seam's own split (`temporal.read`, `iso.is_condition`); without this
#   field a reader that captures the condition and one that discards it scored the same,
#   while the discarded qualifier is a live defect ("stop every vm at 9pm" runs NOW).

# ── v2.0: ACTION MANNER (V2-LEDGER #11 schema ruling 1, RULED 08-21 — *"a way to
#   control how the procedure acts … not a meta control but more about how the pipeline
#   is handled — so it should be expressed"*). An action may carry `manner`: the offsets
#   of the clause that says HOW its execution runs — "one at a time", "all at once".
#   The act's second CONTROL channel beside `trigger` (when-control · how-control); on a
#   plural patient the constraint lands on the DERIVED LOOP at lowering. Never
#   meta-control: confirmation/verification/authority stay the gates' territory.
#
# ── v2.0: THE PER-CASE STORE (V2-LEDGER #11 schema ruling 2, RULED 08-21). A case may
#   carry `store`: a POPULATED mock the runner seeds into a THROWAWAY archive before
#   read_case — several entries across kinds PLUS red herrings (four decoy classes:
#   near-miss same kind · sounds similar · name overlap, different meaning · unrelated
#   filler). Selection under distraction is the measurement — correctness · relevancy ·
#   inference. Certifying the case RATIFIES the mock, decoys included. Entries are flat
#   primitive facts; their deeper shape belongs to the stores, not this schema.

CASE_KEYS = {"id", "stratum", "noise", "pair_id", "source", "sentence", "gold"}
OPTIONAL_KEYS = {"store", "outcome", "context", "vector"}

# ── v2.2: THE OUTCOME — an empty reading is a STATEMENT, not an omission (operator, 08-22) ─
#
#   Until now every gold had at least a span or an act, so "the reader must produce NOTHING"
#   was never certified — and that is the reading the courtesy hazard, the polite-order
#   family, the commitment ("i'll do it myself") and the foreign verb all depend on. A case
#   with NO actions must now SAY why:
#       none    the turn is not a program — flavour, acknowledgement, unrelated, noise, a
#               commitment by the operator, a prohibition (the spared object has no span)
#       reject  a licensing slot holds something no closed class can express — the foreign
#               verb (id-0001-cs: "automatic REJECT, since the verb is inexpressible")
#   Spans are free in both: the object NP still detects (the ruling on id-0001-cs).
#       testimony  the turn carries a FACT and no program — "a subset of evidence which are
#               user input" (operator 08-22): "thanks, that worked" is the system's act
#               resolved, "i'll stop alpha myself" is the user resolving it. Both are facts
#               the issue ledger files (D3's Issues.answers()). Evidence may be UNATTACHED
#               here and only here — declared, not omitted.
#       context-needed  the turn is only readable against the previous one. *"an unrelated
#               'check' is processed as if it is important, ALL are … READ is blind here"* —
#               nothing is dropped for being vague; ROUTE decides whether a reference exists.
OUTCOMES = ("none", "reject", "testimony", "context-needed", "acknowledge")
GOLD_KEYS = {"spans", "actions", "attachments"}
OPTIONAL_GOLD_KEYS = {"hint", "mood", "frame"}

# ── v2.3: THE TWO HINTS — how READ, ROUTE and RESOLVE talk (operator, 2026-08-22) ────────
#
#   *"READ is fed by RESOLVE … RESOLVE dictates that the next answer is a 'yes or no'
#   question meaning a READ 'yes' is legal AND EXTRACTABLE. READ -> ROUTE -> RESOLVE is a
#   feedback loop that interact with eachother through WHAT MESSAGES ARE LEGAL AT WHAT
#   STATE."* Two channels, opposite directions, and the corpus declares both:
#
#     INBOUND   `context` — the case-level state RESOLVE supplies (waited-response · mood ·
#               current heading). Data, exactly like `store` is data for the world; the
#               certification ratifies it. This is NOT cross-turn resolution (still out of
#               scope, LAST): nothing is resolved across turns, one fact is SUPPLIED.
#     OUTBOUND  `gold.hint` — what READ WRITES for ROUTE, so that "we can investigate if it
#               made the right call and ROUTE gets more context". PLACEMENT, ruled by the
#               operator: *"AFTER chunking, BEFORE it makes a decision about what it is
#               looking at"* — the clause split has run, nothing has been typed yet. The
#               hint records what a piece COULD be before the reading commits to what it IS,
#               which is what makes a wrong commitment auditable instead of invisible. The
#               same lesson gate 1 paid for in the other direction: WHERE a check runs
#               decides what it can still see (3 catches vs 32).
#
#   A hint is {kind, says}: `kind` is closed and SCORED, `says` is the gloss — shown at
#   certification, ratified by the accept, never string-matched (a free-text match would be
#   a judgement call wearing a number).
#   ⚠ THE KIND VOCABULARY IS DRAFTED, NOT RULED — the operator closes it.
HINT_KINDS = ("possible-reference",     # may point at a previous turn's act or answer
              "answer-shaped",          # reads as a response to a question (polarity/choice)
              "unreadable-alone",       # nothing in the turn survives without the context
              # v2.5 — the two REFUSALS, because a reject that says nothing is a silence and
              #   the whole point is that the operator is told WHY:
              "unsupported-language",   # the sentence mixes languages — Gorgon reads English
              "inexpressible",          # a licensing slot holds what no closed class expresses
              "prohibition")            # v3.1: a negative rule — `neither X nor Y` reads as
                                        #   "do NOT act on these" (all objects excluded)
# ⇒ `mood` was briefly a hint kind and GRADUATED the same night — see MOOD_KINDS below. One
#   fact, one home: a free-text gloss and a closed channel for the same thing is the
#   twin-owner defect this project keeps refusing.

# ── v2.4: MOOD IS A CHANNEL OF ITS OWN (operator, 2026-08-22) ────────────────────────────
#
#   *"mood should be its own channel i think because it is important to ALSO PROVIDE IT AS
#   EVIDENCE."* Two claims, and the second is the checkable one:
#     1  A CHANNEL, not a hint — the flavour taxonomy already names eight species and each
#        says something operational: deference -> low urgency, the request may be refused ·
#        closure -> the LAST thing succeeded, a resolution · frustration -> a prior attempt
#        FAILED, a diagnosis context (D1) · hostility -> aimed; an insult IS an act ·
#        hedge -> low commitment, confirm more · urgency -> NOT pure flavour, it collides
#        with the temporal reader · phatic -> the session is opening or closing ·
#        filler -> the request may be INCOMPLETE, a reason to wait rather than read.
#     2  ALSO EVIDENCE — a mood span is a fact about the speaker, and downstream files it.
#        So: EVERY MOOD SPAN MUST ALSO BE AN EVIDENCE SPAN, at the same offsets. Enforced.
#   A mood is {kind, text, start, end} — a span with a species, like a trigger is a span on
#   an act. `gold.mood` is a LIST: a turn may carry two ("ugh, please…" is frustration AND
#   deference), and the reading must not have to choose.
MOOD_KINDS = ("deference", "closure", "frustration", "hostility",
              "hedge", "urgency", "phatic", "filler",
              "affirmation")   # v3.1: yeah/ok/yes — usually ack + affirm together


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

    for extra in set(case) - CASE_KEYS - OPTIONAL_KEYS:
        faults.append(f"{cid}: unknown key {extra!r} — the schema does not ride along")
    for missing in CASE_KEYS - set(case):
        faults.append(f"{cid}: missing {missing!r}")
    if faults:
        return faults

    # v2.2 outcome: declared from the closed set; checked against the actions below
    if "outcome" in case and case["outcome"] not in OUTCOMES:
        faults.append(f"{cid}: outcome {case['outcome']!r} is not one of {OUTCOMES}")

    # v3.0 vector (operator 08-24): the per-word decomposition + the fold — COMPUTED by
    #   the emitter, certified by exception. Words must mirror the sentence token for
    #   token; cells and fold keys come from the declared dimensions, nothing rides along.
    if "vector" in case:
        import re as _re
        vec = case["vector"]
        from .vectors import FOLD_DIMENSIONS, WORD_DIMENSIONS
        toks = [m.group(0) for m in _re.finditer(r"\S+", case["sentence"])]
        words = (vec or {}).get("words") if isinstance(vec, dict) else None
        if not isinstance(vec, dict) or not isinstance(words, list):
            faults.append(f"{cid}: vector is not {{words, fold}}")
        elif [w.get("w") for w in words] != toks:
            faults.append(f"{cid}: vector words do not mirror the sentence tokens")
        else:
            for wi, w in enumerate(words):
                for k in set(w.get("cells") or {}) - set(WORD_DIMENSIONS):
                    faults.append(f"{cid}: vector word {wi} has unknown dimension {k!r}")
            for k in set(vec.get("fold") or {}) - set(FOLD_DIMENSIONS):
                faults.append(f"{cid}: vector fold has unknown dimension {k!r}")

    # v2.3 context: the INBOUND hint — a flat, non-empty declaration of the prior state
    if "context" in case:
        ctx = case["context"]
        if not isinstance(ctx, dict) or not ctx:
            faults.append(f"{cid}: context must be a non-empty object")
        else:
            for key, value in ctx.items():
                if not isinstance(value, (str, int, float, bool)) or value is None:
                    faults.append(f"{cid}: context[{key!r}] must be flat — the state is "
                                  f"declared, never nested")

    # v2.0 store: flat primitive facts, non-empty — certification ratifies the mock
    if "store" in case:
        store = case["store"]
        if not isinstance(store, list) or not store:
            faults.append(f"{cid}: store must be a non-empty list")
        else:
            for i, entry in enumerate(store):
                if not isinstance(entry, dict) or not entry:
                    faults.append(f"{cid}: store[{i}] must be a non-empty object")
                    continue
                for k, v in entry.items():
                    if not isinstance(k, str) or not isinstance(v, (str, int, bool)):
                        faults.append(f"{cid}: store[{i}].{k}: entries are flat "
                                      f"str/int/bool facts")

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
    for extra in set(gold) - GOLD_KEYS - OPTIONAL_GOLD_KEYS:
        faults.append(f"{cid}: gold has unknown key {extra!r}")
    for missing in GOLD_KEYS - set(gold):
        faults.append(f"{cid}: gold is missing {missing!r}")
    if any(f.startswith(f"{cid}: gold") for f in faults):
        return faults

    sentence = case["sentence"] if isinstance(case["sentence"], str) else ""
    spans, actions = gold["spans"], gold["actions"]
    for i, span in enumerate(spans):
        # v3.1: an evidence span may carry a decomposition (kind + sub-spans) — slim those
        # out of the offset check, validate them separately
        slim = ({k: v for k, v in span.items() if k not in ("kind", "spans")}
                if isinstance(span, dict) and span.get("type") == "evidence" else span)
        faults += _offsets(f"{cid}: spans[{i}]", slim, sentence, typed=True)
        if isinstance(span, dict) and span.get("type") == "evidence":
            if "kind" in span and span["kind"] not in EVIDENCE_KINDS:
                faults.append(f"{cid}: spans[{i}] evidence kind {span['kind']!r} is not "
                              f"one of {EVIDENCE_KINDS}")
            for k, sub in enumerate(span.get("spans", [])):
                w = f"{cid}: spans[{i}].spans[{k}]"
                slimsub = {x: v for x, v in sub.items() if x not in ("role", "kind", "refers")}
                faults += _offsets(w, slimsub, sentence, typed=False)
                if sub.get("role") not in ROLES:
                    faults.append(f"{w}: role {sub.get('role')!r} is not one of {ROLES}")
                if "kind" in sub and sub["kind"] not in MEMBER_KINDS:
                    faults.append(f"{w}: kind {sub['kind']!r} is not one of {MEMBER_KINDS}")
                if "refers" in sub and not (isinstance(sub["refers"], str) and sub["refers"].strip()):
                    faults.append(f"{w}: refers must be the referent's words")
    for i, act in enumerate(actions):
        known = {"text", "start", "end", "trigger", "kind", "manner", "pacing", "ask", "finding"}
        for extra in set(act) - known:
            faults.append(f"{cid}: actions[{i}]: unknown key {extra!r}")
        if "kind" in act and act["kind"] not in ACTION_KINDS:
            faults.append(f"{cid}: actions[{i}]: kind {act['kind']!r} is not one of "
                          f"{ACTION_KINDS}")
        slim = {k: v for k, v in act.items() if k not in ("trigger", "kind", "manner", "pacing", "ask", "finding")}
        faults += _offsets(f"{cid}: actions[{i}]", slim, sentence, typed=False)
        for channel in ("trigger", "manner", "pacing", "ask", "finding"):
            if channel in act:
                clause = act[channel]
                if not isinstance(clause, dict):
                    faults.append(f"{cid}: actions[{i}]: {channel} is not an object")
                    continue
                # v3.1: a trigger/manner/pacing has clause TEXT; ask/finding are pure
                # {kind, spans} decomposition objects with no text of their own.
                if channel not in ("ask", "finding"):
                    slimch = {k: v for k, v in clause.items() if k not in ("kind", "spans")}
                    faults += _offsets(f"{cid}: actions[{i}].{channel}", slimch, sentence,
                                       typed=False)
                _kset = {"trigger": TRIGGER_KINDS, "ask": QUERY_KINDS,
                         "finding": DIAGNOSIS_KINDS, "manner": MANNER_KINDS}.get(channel)
                if _kset is not None and "kind" in clause and clause["kind"] not in _kset:
                    faults.append(f"{cid}: actions[{i}].{channel} kind {clause['kind']!r} "
                                  f"is not one of {_kset}")
                for k, sub in enumerate(clause.get("spans", []) if _kset is not None else []):
                    w = f"{cid}: actions[{i}].{channel}.spans[{k}]"
                    slim = {x: v for x, v in sub.items() if x not in ("role", "kind", "refers")}
                    faults += _offsets(w, slim, sentence, typed=False)
                    if sub.get("role") not in ROLES:
                        faults.append(f"{w}: role {sub.get('role')!r} is not one of {ROLES}")
                    if "kind" in sub and sub["kind"] not in MEMBER_KINDS:
                        faults.append(f"{w}: kind {sub['kind']!r} is not one of {MEMBER_KINDS}")
                    if "refers" in sub and not (isinstance(sub["refers"], str)
                                                and sub["refers"].strip()):
                        faults.append(f"{w}: refers must be the referent's words")

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
        # a span may carry DISTINCT roles in one attachment — a DUAL TYPE (operator 2026-08-29:
        # a diagnosis like `stuck at boot` is EVIDENCE by nature and a SELECTOR by use). Only an
        # exact (index, role) duplicate is a fault.
        if len(set(members)) != len(members):
            faults.append(f"{where}: objects repeat an (index, role) pair")
        # v1.1 roles: all-or-none per attachment, roles from the closed set, ONE patient
        tagged = [role for _ix, role in members if role is not None]
        if tagged:
            if len(tagged) != len(members):
                faults.append(f"{where}: mixed tagged and untagged members — "
                              f"half-tagged direction is untestable")
            for role in tagged:
                if role not in ROLES:
                    faults.append(f"{where}: role {role!r} is not one of {ROLES}")
            # v3.1: the ACTED-ON subject is one `patient`, OR — when there is no patient —
            # one `reference` (a pronoun `it`/`that` filling the slot). A `reference`
            # ALONGSIDE a patient is an appositive (apposition: `alpha, the jumpbox`), which
            # is why patient==1 passes regardless of references. `self` (you) is the
            # addressee, orthogonal. A QUERY may have ZERO acted-on (the answer is sought,
            # not given).
            patients = sum(1 for r in tagged if r == "patient")
            refs = sum(1 for r in tagged if r == "reference")
            act_i = att.get("action")
            is_query = (isinstance(act_i, int) and 0 <= act_i < len(gold["actions"])
                        and gold["actions"][act_i].get("kind") == "query")
            if is_query:
                if patients > 1:
                    faults.append(f"{where}: a query takes at most one patient")
            elif patients >= 1:
                pass                                  # >=1 patient: a compound create (a
                                                      # naming list) makes several; a
                                                      # reference beside one is appositive
            elif patients == 0 and refs >= 1:
                pass                                  # pronoun(s) fill the subject slot
                                                      # (nl-0004 add: `those vms` + `it`)
            elif patients == 0 and refs == 0 and any(r == "excluded" for r in tagged):
                pass                                  # a PROHIBITION (neither X nor Y): all
                                                      # excluded, nothing is acted on
            elif (patients == 0 and refs == 0 and any(r == "self" for r in tagged)
                  and isinstance(act_i, int) and 0 <= act_i < len(gold["actions"])
                  and gold["actions"][act_i].get("kind") == "meta-control"):
                pass                                  # a META-CONTROL on self (`lets
                                                      # continue`): governs the session, no
                                                      # lab object
            else:
                faults.append(f"{where}: a tagged attachment needs exactly one patient "
                              f"(or, with none, one reference)")
        for member in objs:
            if isinstance(member, dict):
                extra = set(member) - {"span", "role", "kind", "refers"}
                if extra:
                    faults.append(f"{where}: a tagged member has unknown key {extra!r}")
                if "kind" in member and member["kind"] not in MEMBER_KINDS:
                    faults.append(f"{where}: member kind {member['kind']!r} is not one of "
                                  f"{MEMBER_KINDS}")
                if "refers" in member:
                    ref = member["refers"]
                    if not (isinstance(ref, str) and ref.strip()):
                        faults.append(f"{where}: refers {ref!r} must be the referent's "
                                      f"words (a non-empty string)")

    # v2.4 mood: a span with a species, and it must ALSO be evidence (the operator's rule)
    if "mood" in gold:
        moods = gold["mood"]
        if not isinstance(moods, list) or not moods:
            faults.append(f"{cid}: mood must be a non-empty list — absent means none")
        else:
            evidence_at = {(sp.get("start"), sp.get("end")) for sp in gold.get("spans") or []
                           if sp.get("type") == "evidence"}
            for i, m in enumerate(moods):
                where = f"{cid}: mood[{i}]"
                if not isinstance(m, dict):
                    faults.append(f"{where}: not an object")
                    continue
                for extra in set(m) - {"kind", "text", "start", "end"}:
                    faults.append(f"{where}: unknown key {extra!r}")
                if m.get("kind") not in MOOD_KINDS:
                    faults.append(f"{where}: kind {m.get('kind')!r} is not one of {MOOD_KINDS}")
                slim = {k: v for k, v in m.items() if k != "kind"}
                faults += _offsets(where, slim, case["sentence"], typed=False)
                # v3.1: a PHATIC greeting or an AFFIRMATION is pure mood — no info — so
                # it is NOT also evidence (operator 08-25: 'good morning'/'yeah' mark
                # nothing). A mood the PACING channel already carries (a deference softener
                # `when you have a sec`, filed as a meta-control) is likewise not evidence.
                # Every other mood species still carries as evidence (08-22).
                pacing_at = {(a["pacing"]["start"], a["pacing"]["end"])
                             for a in gold.get("actions", []) if isinstance(a, dict)
                             and isinstance(a.get("pacing"), dict)}
                if (m.get("kind") not in ("phatic", "affirmation")
                        and (m.get("start"), m.get("end")) not in evidence_at
                        and (m.get("start"), m.get("end")) not in pacing_at):
                    faults.append(f"{where}: mood is not carried as evidence — the operator's "
                                  f"rule (08-22) is that a mood span is ALSO an evidence span "
                                  f"at the same offsets, so downstream can file it")

    # v3.1 FRAME (operator 08-25): the speech-act participants — `i`/`you` are NOT verb
    # arguments, they are WHO is speaking. `i` = user (leans testimony), `you` = agent
    # (leans meta). Each entry names a span and its party.
    if "frame" in gold:
        fr = gold["frame"]
        if not isinstance(fr, list) or not fr:
            faults.append(f"{cid}: frame is not a non-empty list")
        else:
            for j, f in enumerate(fr):
                if not isinstance(f, dict) or set(f) != {"span", "party"}:
                    faults.append(f"{cid}: frame[{j}] is exactly {{span, party}}")
                    continue
                if not (isinstance(f["span"], int) and 0 <= f["span"] < len(spans)):
                    faults.append(f"{cid}: frame[{j}] span out of range")
                if f["party"] not in ("testimony", "meta", "request"):
                    faults.append(f"{cid}: frame[{j}] party {f['party']!r} is not "
                                  f"testimony/meta/request")

    # v2.3 hint: closed kind, free gloss — the OUTBOUND half of the loop
    if "hint" in gold:
        hint = gold["hint"]
        if not isinstance(hint, dict) or set(hint) != {"kind", "says"}:
            faults.append(f"{cid}: hint is exactly {{kind, says}}")
        else:
            if hint["kind"] not in HINT_KINDS:
                faults.append(f"{cid}: hint kind {hint['kind']!r} is not one of {HINT_KINDS}")
            if not isinstance(hint["says"], str) or not hint["says"].strip():
                faults.append(f"{cid}: hint says nothing — the gloss is what a human ratifies")
    # A context-needed turn MUST hint; that is the whole point of the outcome — READ is
    # blind, so what it hands ROUTE is a question, never a silence.
    if case.get("outcome") == "context-needed" and "hint" not in gold:
        faults.append(f"{cid}: outcome 'context-needed' with no hint — READ must say what it "
                      f"suspects, or ROUTE has nothing to resolve")
    # v2.5: A REJECT MUST SAY WHY. The operator's rule (08-22) is that a rejected sentence
    #   comes back as an ASK carrying the reason — "the project does not support
    #   multi-language sentences". A refusal with no reason is a silence, and a silence is
    #   the one thing this seam is not allowed to answer with.
    if case.get("outcome") == "reject" and "hint" not in gold:
        faults.append(f"{cid}: outcome 'reject' with no hint — a refusal must carry the "
                      f"reason the operator is shown")
    # Testimony is evidence: it must carry one.
    if case.get("outcome") == "testimony" and not any(
            sp.get("type") == "evidence" for sp in gold.get("spans") or []):
        faults.append(f"{cid}: outcome 'testimony' with no evidence span — testimony IS "
                      f"evidence (operator 08-22), so it must carry the fact it reports")

    # v2.2: NO ACTIONS <=> AN OUTCOME. An empty reading must say why, and a declared
    #   outcome must not come with an act — "none" that acts is a contradiction, "reject"
    #   that acts is the licence hole this field exists to close.
    if not actions and "outcome" not in case:
        faults.append(f"{cid}: no actions and no outcome — an empty reading needs "
                      f"'outcome': 'none' or 'reject'")
    # v3.1 (operator 08-25): the VERB is always read — a `reject`/`context-needed`/
    #   `testimony` outcome may coexist with the act it spans (the act is read, the outcome
    #   governs whether it RUNS). Only `none` — a genuinely empty reading — forbids an act.
    if actions and case.get("outcome") == "none":
        faults.append(f"{cid}: outcome 'none' declares no act, but "
                      f"{len(actions)} action(s) are gold")

    # v2.1 (RULED 08-22, certification of v3): EVIDENCE IS CARRIED. A symptom clause is
    # testimony FOR an act — "carry the evidence to stop because it's a future reference".
    # An evidence span nothing attaches to is a painted-but-orphaned reading: the reviewer
    # shows it in yellow and the action line never mentions it. Five v3 golds had exactly
    # that (ca-0001/2, co-0001/2, ca-0002-ej); every frozen set already obeys this.
    carried = {ix for att in gold["attachments"] if isinstance(att, dict)
               and isinstance(att.get("objects"), list)
               for ix, _role in members_of(att)}
    # ⇒ v2.4 THE EXCEPTION, GENERALISED: **an actless turn has nothing to attach evidence
    #   TO.** First written for `testimony` alone; the mood channel exposed the rest — "hey,
    #   check" is context-needed, carries a phatic mood, and therefore evidence, with no act
    #   in sight. Requiring attachment there is incoherent, not strict. Every case the
    #   original v2.1 rule caught (ca-0001, co-0001…) HAD an act, so this is strictly the
    #   same rule stated correctly.
    if not actions:
        carried = carried | {i for i, sp in enumerate(spans) if sp.get("type") == "evidence"}
    # v3.1 (08-26): a TESTIMONY frame carries its evidence — a user REPORT (`i stopped
    # alpha`) is evidence the frame owns, even beside a real command (`launch beta`)
    if any(f.get("party") == "testimony" for f in gold.get("frame", [])):
        carried = carried | {i for i, sp in enumerate(spans) if sp.get("type") == "evidence"}
    # a PHATIC mood ('hey') is a session-opener, not evidence FOR an act (v3.1): its span
    # need not attach even when a verb is present beside it (`hey, check`)
    phatic_at = {(m.get("start"), m.get("end")) for m in gold.get("mood", [])
                 if isinstance(m, dict) and m.get("kind") == "phatic"}
    carried = carried | {i for i, sp in enumerate(spans)
                         if (sp.get("start"), sp.get("end")) in phatic_at}
    for i, span in enumerate(spans):
        if span.get("type") == "evidence" and i not in carried:
            faults.append(f"{cid}: spans[{i}] is evidence nothing carries — attach it "
                          f"with role 'evidence'")
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
    # v3.1: two patients is now LEGAL (a compound create); instead, an unknown member kind
    # and a bad `refers` must both refuse
    broken(lambda c: c["gold"]["attachments"][0]["objects"].__setitem__(
        0, {"span": 0, "role": "selector", "kind": "wat"}), "member kind")
    broken(lambda c: c["gold"]["attachments"][0]["objects"].__setitem__(
        0, {"span": 0, "role": "reference", "refers": 99}), "referent's words")
    broken(lambda c: c["gold"]["attachments"][0].__setitem__(
        "objects", [{"span": 0, "role": "destination"}]), "exactly one patient")
    # v1.2 triggers — lying offsets and stowaway keys must both refuse
    broken(lambda c: c["gold"]["actions"][0].__setitem__(
        "trigger", {"text": "nope", "start": 0, "end": 4}), "gold says")
    broken(lambda c: c["gold"]["actions"][0].__setitem__(
        "trigger", {"text": "restart", "start": 0, "end": 7, "why": "x"}), "unknown key")
    broken(lambda c: c["gold"]["actions"][0].__setitem__("kind", "musing"), "not one of")
    # v2.0 manner + store — each new door must also refuse
    broken(lambda c: c["gold"]["actions"][0].__setitem__(
        "manner", {"text": "nope", "start": 0, "end": 4}), "gold says")
    broken(lambda c: c["gold"]["actions"][0].__setitem__(
        "manner", {"text": "restart", "start": 0, "end": 7, "why": "x"}), "unknown key")
    # v2.4 mood — a wrong species, a lying offset, and an unfiled mood must all refuse
    broken(lambda c: c["gold"].__setitem__("mood", [{"kind": "smug", "text": "restart",
                                                     "start": 0, "end": 7}]), "not one of")
    broken(lambda c: c["gold"].__setitem__("mood", [{"kind": "deference", "text": "nope",
                                                     "start": 0, "end": 4}]), "gold says")
    broken(lambda c: c["gold"].__setitem__("mood", [{"kind": "deference", "text": "restart",
                                                     "start": 0, "end": 7}]),
           "not carried as evidence")
    broken(lambda c: c["gold"].__setitem__("mood", []), "non-empty list")
    # v2.3 hint + context — the outbound half must not lie either
    broken(lambda c: c["gold"].__setitem__("hint", {"kind": "vibes", "says": "x"}),
           "not one of")
    broken(lambda c: c["gold"].__setitem__("hint", {"kind": "possible-reference"}),
           "exactly {kind, says}")
    broken(lambda c: c["gold"].__setitem__("hint",
           {"kind": "possible-reference", "says": "  "}), "says nothing")
    broken(lambda c: c.__setitem__("context", {}), "non-empty object")
    broken(lambda c: (c.__setitem__("outcome", "reject"),
                      c["gold"].__setitem__("actions", []),
                      c["gold"].__setitem__("attachments", [])), "must carry the reason")
    broken(lambda c: c.__setitem__("context", {"expecting": ["y", "n"]}), "must be flat")
    # v2.2 outcome — the three ways an empty reading can lie
    broken(lambda c: c.__setitem__("outcome", "vibes"), "not one of")
    broken(lambda c: c.__setitem__("outcome", "none"), "declares no act")
    broken(lambda c: (c["gold"].__setitem__("actions", []),
                      c["gold"].__setitem__("attachments", [])), "needs 'outcome'")
    # v2.1 evidence is carried — an orphaned evidence span must refuse
    broken(lambda c: c["gold"]["spans"].append(
        {"text": "and", "start": 19, "end": 22, "type": "evidence"}), "nothing carries")
    broken(lambda c: c.__setitem__("store", []), "non-empty list")
    broken(lambda c: c.__setitem__("store", [{}]), "non-empty object")
    broken(lambda c: c.__setitem__("store", [{"word": ["nested"]}]), "flat")

    enriched = _good()
    enriched["store"] = [{"word": "grubnash", "kind": "vm", "ratified": True}]
    enriched["gold"]["actions"][0]["manner"] = {"text": "the web vm",
                                                "start": 8, "end": 18}
    if validate([enriched]):
        problems.append(f"the store+manner case FAILED: {validate([enriched])}")

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
