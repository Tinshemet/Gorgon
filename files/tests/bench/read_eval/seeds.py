"""seeds.py — BUILD ORDER #4: the human-written seeds, authored as TEXT, never as offsets.

    PYTHONPATH=. python3 -m tests.bench.read_eval.seeds              # build + validate + count
    PYTHONPATH=. python3 -m tests.bench.read_eval.seeds --emit       # write cases/seeds.jsonl
    PYTHONPATH=. python3 -m tests.bench.read_eval.seeds --show cs    # print a stratum's gold

# ⇒⇒ AUTHORED AS TEXT BECAUSE HAND-TYPED OFFSETS ARE HAND-TYPED BUGS

A seed names its spans by their WORDS — `objects=["the web vm"]` — and the builder computes
the offsets and runs every emitted case through `schema.validate`. The one thing a human
cannot reliably do (count characters) is the one thing the machine does; the one thing the
machine cannot do (decide what a competent reader extracts) stays human. A repeated phrase
picks its occurrence explicitly: `("stop", 2)`.

# ⇒⇒ ⚠ EVERY GOLD LABEL HERE IS **UNVERIFIED** UNTIL THE OPERATOR REVIEWS IT

The spec is explicit: a human reviews every label. These are DRAFTS by the assistant —
plausible, validated for FORM, and worth nothing as ground truth until reviewed (build order
#5 is the review workflow). Nothing may be scored against this file before that.
⇒ AND A1 IS NOT HERE. The sealed held-out set stays sealed; seeding from it would spend it.

# ⇒ THE GOLD CONVENTIONS, DECIDED ONCE SO FIFTY SEEDS DO NOT DECIDE THEM FIFTY WAYS

  · A BARE PRONOUN IS NOT A SPAN. *"create a vm named alpha and launch it"* — the reading is
    that launch applies to alpha's vm, so the ATTACHMENT points both actions at the one span.
    Extracting `it` as an object would be marking the pointer instead of the thing.
  · AN EXCEPTION IS ITS OWN OBJECT, ROLE `excluded` — RULED BY THE OPERATOR 08-18, replacing
    the earlier one-span convention. *"every vm except the db vm"* is TWO spans: the set
    (patient) and the carve-out (excluded), and the excluded one scores a hit only when the
    reading does NOT act on it — which bills the deadliest misreading directly.
  · A CONDITION IS NOT AN ACTION. *"IF alpha IS STOPPED, launch it"* has one action. A reader
    emitting `stop` there hallucinated an operation out of a description of the world.
  · AN ADJUNCT'S VERB IS NOT AN ACTION. *"stop the vms TO FREE UP MEMORY"* has one action —
    extracting `free up` as a second step is the exact failure this stratum exists to catch.
  · A NAMED THING IN A CONDITION/ADJUNCT IS STILL A SPAN, unattached. *"launch beta only if
    THE LAB NETWORK is up"* — the network is extracted, attached to nothing.
  · A SUBORDINATE CLAUSE WHOSE SUBJECT IS *YOU* AND WHOSE VERB IS AN ACT IS AN INSTRUCTION —
    generalised from the operator's ba-0004 reject (08-18). *"after YOU HAVE CHECKED the
    others"* marks `checked` as an action on `the others`; *"after THE JOB FINISHES"* does
    not mark `finishes`, because the world is doing it, not you. The subject decides.
  · SELF-CORRECTION OVERRIDES — the SPEC'S rule, adopted for gold. *"restart the web vm, no
    wait, the db one"* extracts ONLY `the db one`; both targets is a hard failure. ⚠ The
    seam's ROUTE behaviour (report and ask, never substitute) is unchanged by this: gold
    grades what the READ should settle on, and asking remains the route's business.
  · VALUES ARE OBJECT SPANS. *"give alpha 4 cores and 8gb"* — `4 cores` and `8gb` are
    arguments of give, exactly as the spec treats a pasted path: an argument, not junk.

# ⇒ THE EDGE RULINGS, from the 08-18 full audit — all already true of the gold below:
#
#   · SEQUENCE IS NOT TRIGGER. A trigger is a WORLD condition/time that starts an act
#     ("after the job finishes"). Ordering between two INSTRUCTED acts — "then", "after you
#     have checked" — is SEQUENCE, and v1.2 does not mark it (V2-LEDGER item 5). ba-0004 and
#     mc-0001 therefore carry no trigger, deliberately.
#   · `TELL ME` BEFORE AN INTERROGATIVE COMPLEMENT IS THE QUESTION'S WRAPPER, NOT AN ACT —
    the operator's cc-0003 rejects, both of them. "tell me if X" asks what "did X?" asks;
    the complement is the explicit QUERY act and the wrapper marks nothing. (`show me the
    logs` is different: `show` acts on a THING and stays an action.)
  · A COURTESY FORMULA MARKS NOTHING, even when clause-shaped. cc-0001's "when you get a
#     chance" is grammatically a when-clause and carries NO trigger, no action, no span —
#     treating politeness as content is the measured 7/7 escalation defect, and the eval must
#     not reward it from the other direction.
#   · A BARE / INDEFINITE MASS NOUN IN A WORLD-CLAUSE IS NOT A SPAN. "free up MEMORY" names
#     no identifiable thing; "THE lab network" / "THE job" / "alpha" do. Definiteness decides,
#     which is still the grammar deciding.
#   · INSIDE AN EVIDENCE SPAN, NOTHING IS SEPARATELY MARKED. diag-0002's symptom mentions
#     "the network"; the evidence is opaque testimony, and decomposing testimony is the same
#     mistake as reading inside the operator's quotes.

# ⇒ ⚠ ONE GOLD THE SCHEMA CANNOT SAY, LEFT OUT RATHER THAN FORCED

*"stop alpha or beta"* — the reading is a CHOICE, one of the two. `attachments` can say BOTH
and can say ONE, and either would be a wrong key. Shoving it into the wrong shape teaches the
eval to reward a misreading (the measured defect was `[stop beta, stop beta]`). It enters the
set when the schema can carry an `exclusive` marker — a version bump, not a quiet field.
"""
import json
import os
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from .schema import CLEAN, STRATA, validate

CASES_DIR = os.path.join(os.path.dirname(__file__), "cases")
Text = Union[str, Tuple[str, int]]            # "the web vm" · ("stop", 2) = 2nd occurrence


class Seed(NamedTuple):
    id: str
    stratum: str
    sentence: str
    objects: List[Text]
    actions: List[Text]
    attach: Dict[int, List[int]]              # action index -> span indices
    evidence: List[Text] = []
    queries: List[int] = []                   # indices into `actions` that are QUERY acts
    rules: List[int] = []                     # indices into `actions` that are RULE acts
    reports: List[int] = []                   # indices into `actions` that are REPORT acts
    triggers: Dict[int, Text] = {}            # action index -> the clause that STARTS it
    source: str = "seed"                      # "real-failure" where a documented defect said it
    note: str = ""


def _at(sentence: str, spec: Text, what: str) -> Tuple[int, int]:
    text, occurrence = (spec, 1) if isinstance(spec, str) else spec
    low, needle, at = sentence.lower(), text.lower(), -1
    for _ in range(occurrence):
        at = low.find(needle, at + 1)
        if at < 0:
            raise SystemExit(f"{what}: {text!r} (occurrence {occurrence}) "
                             f"not in {sentence!r}")
    return at, at + len(text)


def build(seed: Seed) -> dict:
    spans = []
    for spec in seed.objects:
        start, end = _at(seed.sentence, spec, seed.id)
        spans.append({"text": seed.sentence[start:end], "start": start, "end": end,
                      "type": "object"})
    for spec in seed.evidence:
        start, end = _at(seed.sentence, spec, seed.id)
        spans.append({"text": seed.sentence[start:end], "start": start, "end": end,
                      "type": "evidence"})
    actions = []
    for i, spec in enumerate(seed.actions):
        start, end = _at(seed.sentence, spec, seed.id)
        act = {"text": seed.sentence[start:end], "start": start, "end": end}
        if i in seed.triggers:
            ts, te = _at(seed.sentence, seed.triggers[i], seed.id)
            act["trigger"] = {"text": seed.sentence[ts:te], "start": ts, "end": te}
        if i in seed.queries:
            act["kind"] = "query"
        if i in seed.rules:
            act["kind"] = "rule"
        if i in seed.reports:
            act["kind"] = "report"
        actions.append(act)
    # v1.1 — a member may be a plain index or {"span": i, "role": "..."}; passed through,
    # the schema validates the role vocabulary and the one-patient rule
    attachments = [{"action": a, "objects": list(objs)}
                   for a, objs in sorted(seed.attach.items())]
    return {"id": seed.id, "stratum": seed.stratum, "noise": CLEAN, "pair_id": None,
            "source": seed.source, "sentence": seed.sentence,
            "gold": {"spans": spans, "actions": actions, "attachments": attachments}}


SEEDS: List[Seed] = [
    # ══ clean-single — the baseline; must saturate ═══════════════════════════════════
    Seed("cs-0001", "clean-single", "create a vm named alpha",
         ["a vm named alpha"], ["create"], {0: [0]}),
    Seed("cs-0002", "clean-single", "stop the web vm",
         ["the web vm"], ["stop"], {0: [0]}),
    Seed("cs-0003", "clean-single", "delete the snapshot called nightly",
         ["the snapshot called nightly"], ["delete"], {0: [0]}),
    Seed("cs-0004", "clean-single", "launch every stopped vm",
         ["every stopped vm"], ["launch"], {0: [0]}),
    Seed("cs-0005", "clean-single", "list the networks",
         ["the networks"], ["list"], {0: [0]}),

    Seed("cs-0006", "clean-single", "is alpha running?",
         ["alpha"], ["is alpha running"], {0: [0]}, queries=[0],
         note="a bare status query — the third sentence type, finally in the set"),
    Seed("cs-0007", "clean-single", "which vms are stopped?",
         ["which vms"], ["which vms are stopped"], {0: [0]}, queries=[0],
         note="the operator's catch: the query PRODUCES A SET, and the first gold (no object "
              "span) billed the seam's correct set-reading as a hallucination. The wh-NP is "
              "the span — `which` stays in like `every` does — and the asked property "
              "(`stopped`) stays unmarked, exactly parallel to cs-0006's `running`"),

    # ══ coordination — shared and distributed attachment ═════════════════════════════
    Seed("coord-0001", "coordination", "restart the web vm and the db vm",
         ["the web vm", "the db vm"], ["restart"], {0: [0, 1]}),
    Seed("coord-0002", "coordination",
         "create a network called lab and a vm named web",
         ["a network called lab", "a vm named web"], ["create"], {0: [0, 1]}),
    Seed("coord-0003", "coordination", "stop alpha, beta and gamma",
         ["alpha", "beta", "gamma"], ["stop"], {0: [0, 1, 2]}),
    Seed("coord-0004", "coordination",
         "snapshot the web vm and the db vm then stop both",
         ["the web vm", "the db vm"], ["snapshot", "stop"],
         {0: [0, 1], 1: [0, 1]},
         note="`both` refers — the attachment carries it, no span for the pro-form"),
    Seed("coord-0005", "coordination",
         "label the red vms 'ready' and launch the blue ones",
         ["the red vms", "ready", "the blue ones"], ["label", "launch"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}], 1: [2]},
         note="disambiguated at the v2 freeze, the operator's ruling: the model guessed a "
              "label value 'right' given no context, and that does not give it a pass — "
              "'it's a test issue'. The sentence now names the value"),

    # ══ buried-args — the argument far from its verb ═════════════════════════════════
    Seed("ba-0001", "buried-args", "stop the vms on the lab network",
         ["the vms on the lab network"], ["stop"], {0: [0]}),
    Seed("ba-0002", "buried-args",
         "delete the snapshots older than a week on the backup store",
         ["the snapshots older than a week on the backup store"], ["delete"], {0: [0]}),
    Seed("ba-0003", "buried-args",
         "put on the lab network every vm carrying the prod label",
         ["the lab network", "every vm carrying the prod label"], ["put"],
         {0: [{"span": 1, "role": "patient"}, {"span": 0, "role": "destination"}]},
         note="fronted argument — the object arrives before the thing it is done to"),
    Seed("ba-0004", "buried-args",
         "the web vm, after you have checked the others, restart it",
         ["the web vm", "the others"], ["checked", "restart"], {0: [1], 1: [0]},
         triggers={1: "after you have checked the others"},
         note="TWO operator rulings meet here: the you-subject clause is an instructed act "
              "(08-18), AND it TRIGGERS the restart (08-19, superseding ledger item 5 for "
              "after-clauses — 'restart should happen AFTER the AI is done checking'). "
              "Consistent with you-is-the-agent: the trigger fires on the agent's own "
              "completed act, a future ledger event. Bare `then` remains unmarked sequence"),

    # ══ anaphora — within one sentence ═══════════════════════════════════════════════
    Seed("ana-0001", "anaphora", "create a vm named alpha and launch it",
         ["a vm named alpha"], ["create", "launch"], {0: [0], 1: [0]}),
    Seed("ana-0002", "anaphora",
         "stop every vm and snapshot the ones that are still running",
         ["every vm", "the ones that are still running"], ["stop", "snapshot"],
         {0: [0], 1: [1]}),
    Seed("ana-0003", "anaphora", "create two vms and put them on the dmz network",
         ["two vms", "the dmz network"], ["create", "put"],
         {0: [0], 1: [{"span": 0, "role": "patient"}, {"span": 1, "role": "destination"}]}),
    Seed("ana-0004", "anaphora",
         "clone the golden image into three vms and label them test",
         ["the golden image", "three vms", "test"], ["clone", "label"],
         {0: [{"span": 0, "role": "source"}, {"span": 1, "role": "patient"}],
          1: [{"span": 1, "role": "patient"}, {"span": 2, "role": "value"}]}),

    # ══ negation — the exception lives inside the span ═══════════════════════════════
    Seed("neg-0001", "negation", "stop every vm except the db vm",
         ["every vm", "the db vm"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "excluded"}]},
         note="the operator's ruling: the exception is its OWN object — scored inverted, "
              "a hit only when nothing acts on it"),
    Seed("neg-0002", "negation", "don't stop the web vm, stop the db vm",
         ["the db vm"], [("stop", 2)], {0: [0]}, source="real-failure",
         note="the FIRST stop is negated — extracting it as an action is the failure"),
    Seed("neg-0003", "negation",
         "launch everything but the vms carrying the test label",
         ["everything", "the vms carrying the test label"], ["launch"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "excluded"}]}),
    Seed("neg-0004", "negation", "stop every vm that is not running",
         ["every vm that is not running"], ["stop"], {0: [0]}, source="real-failure",
         note="measured 08-16: read as {status: running} — the OPPOSITE set"),

    # ══ conditionals — a condition is not an action ══════════════════════════════════
    Seed("cond-0001", "conditionals", "if alpha is stopped, launch it",
         ["alpha"], ["launch"], {0: [0]}, triggers={0: "if alpha is stopped"},
         source="real-failure",
         note="`stopped` is a state test; emitting stop_vm here is hallucination"),
    Seed("cond-0002", "conditionals", "when the backup finishes, snapshot the db vm",
         ["the backup", "the db vm"], ["snapshot"], {0: [1]},
         triggers={0: "when the backup finishes"},
         note="`the backup` is a named thing in a WORLD clause — a span, attached to "
              "nothing; `finishes` is the world's verb, not an instruction"),
    Seed("cond-0003", "conditionals", "launch beta only if the lab network is up",
         ["beta", "the lab network"], ["launch"], {0: [0]},
         triggers={0: "only if the lab network is up"},
         note="the network is extracted and attached to NOTHING — it is a condition's noun"),
    Seed("cond-0004", "conditionals", "if the web vm is down, restart it",
         ["the web vm"], ["restart"], {0: [0]}, triggers={0: "if the web vm is down"}),

    Seed("cond-0005", "conditionals", "if the backup failed, tell me which vms it skipped",
         ["the backup", "which vms"], ["which vms it skipped"],
         {0: [1]}, queries=[0], triggers={0: "if the backup failed"},
         note="same rule as cc-0003: `tell me` is the question's wrapper, dropped; the query "
              "act carries the TRIGGER (answer when the backup fails), attaches to its "
              "wh-NP; the filter `it skipped` is ledger item 2"),

    # ══ multi-clause — several requests in one string ════════════════════════════════
    Seed("mc-0001", "multi-clause", "stop alpha. then launch beta.",
         ["alpha", "beta"], ["stop", "launch"], {0: [0], 1: [1]}),
    Seed("mc-0002", "multi-clause", "list the vms. anyway, is alpha running?",
         ["the vms", "alpha"], ["list", "is alpha running"], {0: [0], 1: [1]},
         queries=[1], source="real-failure",
         note="topic shift — the question is a SECOND request, marked as a QUERY act whose "
              "span is the interrogative clause"),
    Seed("mc-0003", "multi-clause",
         "create a vm named web, put it on the dmz, and snapshot it",
         ["a vm named web", "the dmz"], ["create", "put", "snapshot"],
         {0: [0], 1: [{"span": 0, "role": "patient"}, {"span": 1, "role": "destination"}],
          2: [0]}),
    Seed("mc-0004", "multi-clause",
         "check the db vm's disk. if it is full, delete the oldest snapshot.",
         ["the db vm's disk", "the oldest snapshot"], ["check", "delete"],
         {0: [0], 1: [1]}, triggers={1: "if it is full"}),

    # ══ self-correction — the SPEC's override rule; both targets is a hard failure ═══
    Seed("sc-0001", "self-correction", "restart the web vm, no wait, the db one",
         ["the db one"], ["restart"], {0: [0]}, source="real-failure"),
    Seed("sc-0002", "self-correction", "stop alpha — sorry, i meant beta",
         ["beta"], ["stop"], {0: [0]}, source="real-failure"),
    Seed("sc-0003", "self-correction",
         "snapshot the db vm, scratch that, snapshot the web vm",
         ["the web vm"], [("snapshot", 2)], {0: [0]},
         note="the whole first clause is overridden, verb included"),
    Seed("sc-0004", "self-correction", "label the vms test, er, staging",
         ["the vms", "staging"], ["label"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="the VALUE is corrected — `test` must not be extracted"),

    # ══ qualifiers — earned 2026-08-18: a value with a modifier the phrase must carry ═
    Seed("qual-0001", "qualifiers", "give alpha 4 cores and 8gb",
         ["alpha", "4 cores", "8gb"], ["give"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "value"}]}, source="real-failure",
         note="measured: the whole sentence read as None — `give` is a light verb"),
    Seed("qual-0002", "qualifiers", "stop the biggest vm",
         ["the biggest vm"], ["stop"], {0: [0]}, source="real-failure"),
    Seed("qual-0003", "qualifiers", "stop most of the vms",
         ["most of the vms"], ["stop"], {0: [0]}),
    Seed("qual-0004", "qualifiers", "stop the vms one at a time",
         ["the vms"], ["stop"], {0: [0]},
         note="the manner phrase binds the ACT — extracting it as an object is a failure"),
    Seed("qual-0005", "qualifiers", "snapshot every vm at 21:30",
         ["every vm"], ["snapshot"], {0: [0]}, triggers={0: "at 21:30"},
         note="the clock is a qualifier of the act — carried as its TRIGGER"),
    Seed("qual-0006", "qualifiers", "delete alpha's snapshots",
         ["alpha's snapshots"], ["delete"], {0: [0]},
         note="possession — the owner stays inside the span"),

    # ══ adjunct-clauses — earned 2026-08-18: modifies, never orders ══════════════════
    Seed("adj-0001", "adjunct-clauses", "stop the vms to free up memory",
         ["the vms"], ["stop"], {0: [0]},
         note="PURPOSE — `free up` as a second action is the exact failure"),
    Seed("adj-0002", "adjunct-clauses", "restart the db vm because it is stuck",
         ["the db vm"], ["restart"], {0: [0]}),
    Seed("adj-0003", "adjunct-clauses", "stop the test vms even though alpha is busy",
         ["the test vms", "alpha"], ["stop"], {0: [0]},
         note="CONCESSION — alpha extracted, attached to nothing"),
    Seed("adj-0004", "adjunct-clauses", "stop more vms than you started",
         ["more vms than you started"], ["stop"], {0: [0]},
         note="COMPARISON — the standard stays inside the span"),

    Seed("cc-0006", "cross-cutting", "never delete the db vm",
         ["the db vm"], ["never delete"], {0: [0]}, rules=[0],
         note="a PROHIBITION — the frequency adverb makes it a rule; an op emitted from "
              "this clause is a hallucination by definition"),
    Seed("cc-0007", "cross-cutting", "treat prod as read-only",
         ["prod", "read-only"], ["treat"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]}, rules=[0],
         note="the door-key control — a standing rule, not an act to run now"),
    Seed("cc-0008", "cross-cutting", "every vm must carry a label",
         ["every vm", "a label"], ["must carry"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]}, rules=[0],
         note="deontic legislation — universal subject + must; a rule about future state"),

    # ══ diagnosis — earned 2026-08-18; D1, the thesis. Evidence spans, no imperative ═
    Seed("diag-0001", "diagnosis", "vm2 is not working, it boots to a blue screen",
         ["vm2"], ["vm2 is not working"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"},
              {"span": 2, "role": "evidence"}]},
         evidence=["is not working", "it boots to a blue screen"],
         reports=[0], source="real-failure",
         note="the operator's ruling, twice: every malfunction predicate is testimony, AND "
              "the diagnosis must PRODUCE — the report act binds patient to testimony"),
    Seed("diag-0002", "diagnosis", "the web vm keeps dropping off the network",
         ["the web vm"], ["the web vm keeps dropping off the network"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["keeps dropping off the network"], reports=[0]),
    Seed("diag-0003", "diagnosis",
         "alpha won't start and the log says 'cannot allocate memory'",
         ["alpha"], ["alpha won't start"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"},
              {"span": 2, "role": "evidence"}]},
         evidence=["won't start", "cannot allocate memory"],
         reports=[0], source="real-failure",
         note="the QUOTES are the operator's boundary marks, not evidence — the gold span is "
              "the inner text, the same rule the quoted-value fix wrote on 08-16"),
    Seed("diag-0004", "diagnosis",
         "something is wrong with the dmz network, pings time out",
         ["the dmz network"], ["something is wrong with the dmz network"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"},
              {"span": 2, "role": "evidence"}]},
         evidence=["something is wrong", "pings time out"], reports=[0],
         note="same rule as diag-0001: the generic complaint is testimony too"),

    # ══ cross-cutting — earned 2026-08-18: the vocab-list boundaries ═════════════════
    Seed("cc-0001", "cross-cutting", "when you get a chance, stop the test vms",
         ["the test vms"], ["stop"], {0: [0]}, source="real-failure",
         note="courtesy must not read as an action — `get` here is 7/7 the ACHIEVE trap"),
    Seed("cc-0002", "cross-cutting", "make sure the lab network exists",
         ["the lab network"], ["make sure"], {0: [0]},
         note="`make` alone is a leak word; `make sure` is the whole verb"),
    Seed("cc-0003", "cross-cutting",
         "go over the event log and tell me if the db vm restarted",
         ["the event log", "the db vm"], ["go over", "if the db vm restarted"],
         {0: [0], 1: [1]}, queries=[1],
         note="the operator's second reject fixed the dangler: `tell me` is the QUESTION'S "
              "WRAPPER, not an act — 'tell me if X' asks what 'did X?' asks. The query act "
              "IS the production; nothing attaches to nothing"),
    Seed("cc-0004", "cross-cutting",
         "put the notes from the meeting in the shared folder",
         ["the notes from the meeting", "the shared folder"], ["put"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "destination"}]},
         note="`from` inside a noun phrase — the leak word is not a role marker here"),
    Seed("cc-0005", "cross-cutting", "spin down the render vms after the job finishes",
         ["the render vms", "the job"], ["spin down"], {0: [0]},
         triggers={0: "after the job finishes"},
         note="phrasal `spin down`; `the job` is a named thing in the adjunct — a span, "
              "unattached; `finishes` is the world's verb"),
]


def emit() -> List[dict]:
    cases = [build(s) for s in SEEDS]
    faults = validate(cases)
    if faults:
        raise SystemExit("\n".join(f"  ✗ {f}" for f in faults))
    return cases


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    cases = emit()

    if "--show" in argv:
        prefix = argv[argv.index("--show") + 1]
        for c in cases:
            if c["id"].startswith(prefix):
                print(f"\n  {c['id']}  {c['sentence']!r}")
                for s in c["gold"]["spans"]:
                    print(f"      {s['type']:9} [{s['start']:3},{s['end']:3})  {s['text']!r}")
                for a in c["gold"]["actions"]:
                    print(f"      action    [{a['start']:3},{a['end']:3})  {a['text']!r}")
                for at in c["gold"]["attachments"]:
                    print(f"      attach    action {at['action']} -> {at['objects']}")
        return 0

    if "--emit" in argv:
        os.makedirs(CASES_DIR, exist_ok=True)
        path = os.path.join(CASES_DIR, "seeds.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for c in cases:
                fh.write(json.dumps(c) + "\n")
        print(f"  {len(cases)} cases -> {path}   ⚠ UNVERIFIED until the operator reviews")
        return 0

    by = {}
    for c in cases:
        by[c["stratum"]] = by.get(c["stratum"], 0) + 1
    print(f"  {len(cases)} seeds, all valid, every stratum populated:")
    for s in STRATA:
        print(f"    {s:16} {by.get(s, 0)}")
    real = sum(1 for c in cases if c["source"] == "real-failure")
    print(f"  {real} carry source=real-failure — a documented defect said the sentence")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
