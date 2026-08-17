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
  · AN EXCEPTION LIVES INSIDE ITS SPAN. *"every vm except the db vm"* is ONE object — the
    boundary metric is exactly the test of whether a reader keeps the carve-out attached.
  · A CONDITION IS NOT AN ACTION. *"IF alpha IS STOPPED, launch it"* has one action. A reader
    emitting `stop` there hallucinated an operation out of a description of the world.
  · AN ADJUNCT'S VERB IS NOT AN ACTION. *"stop the vms TO FREE UP MEMORY"* has one action —
    extracting `free up` as a second step is the exact failure this stratum exists to catch.
  · A NAMED THING IN A CONDITION/ADJUNCT IS STILL A SPAN, unattached. *"launch beta only if
    THE LAB NETWORK is up"* — the network is extracted, attached to nothing.
  · SELF-CORRECTION OVERRIDES — the SPEC'S rule, adopted for gold. *"restart the web vm, no
    wait, the db one"* extracts ONLY `the db one`; both targets is a hard failure. ⚠ The
    seam's ROUTE behaviour (report and ask, never substitute) is unchanged by this: gold
    grades what the READ should settle on, and asking remains the route's business.
  · VALUES ARE OBJECT SPANS. *"give alpha 4 cores and 8gb"* — `4 cores` and `8gb` are
    arguments of give, exactly as the spec treats a pasted path: an argument, not junk.

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
    for spec in seed.actions:
        start, end = _at(seed.sentence, spec, seed.id)
        actions.append({"text": seed.sentence[start:end], "start": start, "end": end})
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
         "label the red vms and launch the blue ones",
         ["the red vms", "the blue ones"], ["label", "launch"], {0: [0], 1: [1]}),

    # ══ buried-args — the argument far from its verb ═════════════════════════════════
    Seed("ba-0001", "buried-args", "stop the vms on the lab network",
         ["the vms on the lab network"], ["stop"], {0: [0]}),
    Seed("ba-0002", "buried-args",
         "delete the snapshots older than a week on the backup store",
         ["the snapshots older than a week on the backup store"], ["delete"], {0: [0]}),
    Seed("ba-0003", "buried-args",
         "put on the lab network every vm carrying the prod label",
         ["the lab network", "every vm carrying the prod label"], ["put"], {0: [0, 1]},
         note="fronted argument — the object arrives before the thing it is done to"),
    Seed("ba-0004", "buried-args",
         "the web vm, after you have checked the others, restart it",
         ["the web vm"], ["restart"], {0: [0]},
         note="topicalised object + interposed clause; `it` points back, no span"),

    # ══ anaphora — within one sentence ═══════════════════════════════════════════════
    Seed("ana-0001", "anaphora", "create a vm named alpha and launch it",
         ["a vm named alpha"], ["create", "launch"], {0: [0], 1: [0]}),
    Seed("ana-0002", "anaphora",
         "stop every vm and snapshot the ones that are still running",
         ["every vm", "the ones that are still running"], ["stop", "snapshot"],
         {0: [0], 1: [1]}),
    Seed("ana-0003", "anaphora", "create two vms and put them on the dmz network",
         ["two vms", "the dmz network"], ["create", "put"], {0: [0], 1: [0, 1]}),
    Seed("ana-0004", "anaphora",
         "clone the golden image into three vms and label them test",
         ["the golden image", "three vms", "test"], ["clone", "label"],
         {0: [0, 1], 1: [1, 2]}),

    # ══ negation — the exception lives inside the span ═══════════════════════════════
    Seed("neg-0001", "negation", "stop every vm except the db vm",
         ["every vm except the db vm"], ["stop"], {0: [0]}),
    Seed("neg-0002", "negation", "don't stop the web vm, stop the db vm",
         ["the db vm"], [("stop", 2)], {0: [0]}, source="real-failure",
         note="the FIRST stop is negated — extracting it as an action is the failure"),
    Seed("neg-0003", "negation",
         "launch everything but the vms carrying the test label",
         ["everything but the vms carrying the test label"], ["launch"], {0: [0]}),
    Seed("neg-0004", "negation", "stop every vm that is not running",
         ["every vm that is not running"], ["stop"], {0: [0]}, source="real-failure",
         note="measured 08-16: read as {status: running} — the OPPOSITE set"),

    # ══ conditionals — a condition is not an action ══════════════════════════════════
    Seed("cond-0001", "conditionals", "if alpha is stopped, launch it",
         ["alpha"], ["launch"], {0: [0]}, source="real-failure",
         note="`stopped` is a state test; emitting stop_vm here is hallucination"),
    Seed("cond-0002", "conditionals", "when the backup finishes, snapshot the db vm",
         ["the db vm"], ["snapshot"], {0: [0]}),
    Seed("cond-0003", "conditionals", "launch beta only if the lab network is up",
         ["beta", "the lab network"], ["launch"], {0: [0]},
         note="the network is extracted and attached to NOTHING — it is a condition's noun"),
    Seed("cond-0004", "conditionals", "if the web vm is down, restart it",
         ["the web vm"], ["restart"], {0: [0]}),

    # ══ multi-clause — several requests in one string ════════════════════════════════
    Seed("mc-0001", "multi-clause", "stop alpha. then launch beta.",
         ["alpha", "beta"], ["stop", "launch"], {0: [0], 1: [1]}),
    Seed("mc-0002", "multi-clause", "list the vms. anyway, is alpha running?",
         ["the vms", "alpha"], ["list"], {0: [0]}, source="real-failure",
         note="topic shift — the question is a SECOND request; its noun is still extracted"),
    Seed("mc-0003", "multi-clause",
         "create a vm named web, put it on the dmz, and snapshot it",
         ["a vm named web", "the dmz"], ["create", "put", "snapshot"],
         {0: [0], 1: [0, 1], 2: [0]}),
    Seed("mc-0004", "multi-clause",
         "check the db vm's disk. if it is full, delete the oldest snapshot.",
         ["the db vm's disk", "the oldest snapshot"], ["check", "delete"],
         {0: [0], 1: [1]}),

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
         ["the vms", "staging"], ["label"], {0: [0, 1]},
         note="the VALUE is corrected — `test` must not be extracted"),

    # ══ qualifiers — earned 2026-08-18: a value with a modifier the phrase must carry ═
    Seed("qual-0001", "qualifiers", "give alpha 4 cores and 8gb",
         ["alpha", "4 cores", "8gb"], ["give"], {0: [0, 1, 2]}, source="real-failure",
         note="measured: the whole sentence read as None — `give` is a light verb"),
    Seed("qual-0002", "qualifiers", "stop the biggest vm",
         ["the biggest vm"], ["stop"], {0: [0]}, source="real-failure"),
    Seed("qual-0003", "qualifiers", "stop most of the vms",
         ["most of the vms"], ["stop"], {0: [0]}),
    Seed("qual-0004", "qualifiers", "stop the vms one at a time",
         ["the vms"], ["stop"], {0: [0]},
         note="the manner phrase binds the ACT — extracting it as an object is a failure"),
    Seed("qual-0005", "qualifiers", "snapshot every vm at 21:30",
         ["every vm"], ["snapshot"], {0: [0]},
         note="the clock is a qualifier of the act; it is not an object"),
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

    # ══ diagnosis — earned 2026-08-18; D1, the thesis. Evidence spans, no imperative ═
    Seed("diag-0001", "diagnosis", "vm2 is not working, it boots to a blue screen",
         ["vm2"], [], {}, evidence=["it boots to a blue screen"],
         source="real-failure"),
    Seed("diag-0002", "diagnosis", "the web vm keeps dropping off the network",
         ["the web vm"], [], {}, evidence=["keeps dropping off the network"]),
    Seed("diag-0003", "diagnosis",
         "alpha won't start and the log says 'cannot allocate memory'",
         ["alpha"], [], {}, evidence=["won't start", "cannot allocate memory"],
         source="real-failure",
         note="the QUOTES are the operator's boundary marks, not evidence — the gold span is "
              "the inner text, the same rule the quoted-value fix wrote on 08-16"),
    Seed("diag-0004", "diagnosis",
         "something is wrong with the dmz network, pings time out",
         ["the dmz network"], [], {}, evidence=["pings time out"]),

    # ══ cross-cutting — earned 2026-08-18: the vocab-list boundaries ═════════════════
    Seed("cc-0001", "cross-cutting", "when you get a chance, stop the test vms",
         ["the test vms"], ["stop"], {0: [0]}, source="real-failure",
         note="courtesy must not read as an action — `get` here is 7/7 the ACHIEVE trap"),
    Seed("cc-0002", "cross-cutting", "make sure the lab network exists",
         ["the lab network"], ["make sure"], {0: [0]},
         note="`make` alone is a leak word; `make sure` is the whole verb"),
    Seed("cc-0003", "cross-cutting",
         "go over the event log and tell me if the db vm restarted",
         ["the event log", "the db vm"], ["go over", "tell"], {0: [0], 1: [1]},
         note="`go` in a phrasal verb; `restarted` is a question's content, not an action"),
    Seed("cc-0004", "cross-cutting",
         "put the notes from the meeting in the shared folder",
         ["the notes from the meeting", "the shared folder"], ["put"], {0: [0, 1]},
         note="`from` inside a noun phrase — the leak word is not a role marker here"),
    Seed("cc-0005", "cross-cutting", "spin down the render vms after the job finishes",
         ["the render vms"], ["spin down"], {0: [0]},
         note="phrasal `spin down`; `finishes` belongs to the temporal adjunct"),
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
