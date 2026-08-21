"""seeds_v3.py — THE CLOSING STRATA (drafted 2026-08-20 night, operator certifies before use).

v3 = the LAST release (operator-scoped): learned patterns + the structure_map's open
holes, growing the corpus toward ~300. Twenty-three new strata. Every gold below follows
the certified conventions (grammar decides · a span is verbatim bytes · the exception is
its own object · a query produces · every malfunction predicate is testimony).

⇒⇒ THE 08-21 MORNING RULINGS LANDED HERE (V2-LEDGER #11 carries every decision in the
   operator's words). The two schema questions were TAKEN: `manner` is the act's second
   control channel (offsets, scored like triggers) and `store` carries a POPULATED
   per-case mock — four decoy classes, selection under distraction, certification
   ratifies the mock decoys included. Every RULING NEEDED note below was replaced by
   the ruling it received. Hand-authored embedded-junk/code-switch twins close the file.
"""
from typing import Dict, List, Optional

from .seeds import Seed, Text, build  # the same shapes; v1/v2 seeds stay untouched
from .schema import validate

SEEDS_V3: List[Seed] = [
    # ══ identifiers — typed values the stores taught (ip/mac/serial mocks) ═══════════
    Seed("id-0001", "identifiers", "stop the vm at 10.0.0.5",
         ["the vm at 10.0.0.5"], ["stop"], {0: [0]},
         note="an identifier in a restrictive PP is part of the NP, exactly as "
              "'the vms on the lab network' is (ba-0001's convention)"),
    Seed("id-0002", "identifiers", "which vm has mac aa:bb:cc:dd:ee:ff?",
         ["which vm", "aa:bb:cc:dd:ee:ff"], ["which vm has mac aa:bb:cc:dd:ee:ff"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         queries=[0],
         note="RULED 08-21: 'mark it as a query — since we have the value but not the "
              "key' — a REVERSE LOOKUP: the given value is the query's input argument "
              "(value role), the wh-NP is the asked side. cs-0007 refined: an asked "
              "PREDICATE stays unmarked; a given VALUE is expressed"),
    Seed("id-0003", "identifiers", "give the web vm the ip 10.0.0.7",
         ["the web vm", "10.0.0.7"], ["give"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="identifier as ASSIGNED value — the attribute-class thesis, write side"),
    Seed("id-0004", "identifiers", "stop the vm with serial 7f3k-2210",
         ["the vm with serial 7f3k-2210"], ["stop"], {0: [0]}),
    Seed("id-0005", "identifiers", "stop the vm at 8g:77q",
         ["the vm at 8g:77q"], ["stop"], {0: [0]},
         note="an identifier shape NO class declares — the read keeps the span whole; "
              "the BOUNCE (a class with no reader) is downstream and deliberate "
              "([[gorgon-attribute-classes]]: unknown-noun ASK becomes capability BOUNCE)"),

    # ══ units — quantity + unit paired to a declared attribute ═══════════════════════
    Seed("un-0001", "units", "give the db vm 16gb of memory",
         ["the db vm", "16gb"], ["give"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="the unit names the attribute (gb -> memory_mb through the class); the "
              "value span is the quantity+unit token, bare — coord-0005's convention"),
    Seed("un-0002", "units", "create a vm with 4 cores and 8gb of ram",
         ["a vm", "4 cores", "8gb of ram"], ["create"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "value"}]},
         note="RULED 08-21: 'each value should be scored indpendently' — spec values "
              "CARVED OUT: patient is the minted kind, every literal value its own "
              "value-role span. (The line vs naming specs: literal values carve; a "
              "generative naming spec stays whole — see nl-0001)"),
    Seed("un-0003", "units", "set the cpu of the web vm to 4 cores",
         ["the web vm", "4 cores"], ["set"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="partitive-of over an ATTRIBUTE — `the cpu of X` names X's attribute, "
              "never a second thing"),
    Seed("un-0004", "units", "how much memory does alpha have?",
         ["alpha"], ["how much memory does alpha have"], {0: [0]}, queries=[0]),

    # ══ possessive — the genitive is a reference, and the reference is the target ════
    Seed("po-0001", "possessive", "delete alpha's snapshots",
         ["alpha's snapshots"], ["delete"], {0: [0]},
         note="structure_map hole: the apostrophe survives tokenisation and the name "
              "was lost — the span is the whole genitive NP; alpha is its owner READ"),
    Seed("po-0002", "possessive", "list the web vm's snapshots",
         ["the web vm's snapshots"], ["list"], {0: [0]}),
    Seed("po-0003", "possessive", "snapshot beta's disk",
         ["beta's disk"], ["snapshot"], {0: [0]}),
    Seed("po-0004", "possessive", "how many snapshots does alpha have?",
         ["alpha"], ["how many snapshots does alpha have"], {0: [0]}, queries=[0],
         note="the genitive relation asked interrogatively — the COUNT is produced"),

    # ══ alternatives — or-coordination: the read records BOTH, choosing is route's ═══
    Seed("al-0001", "alternatives", "stop alpha or beta",
         ["alpha", "beta"], ["stop"], {0: [0, 1]},
         triggers={0: "or"},
         note="RULED 08-21: 'score both — the or is scored like a trigger since "
              "boolean operators are triggers; the decision is at RESOLVE, not ROUTE'. "
              "No alternation flag: both members score, the operator rides the trigger "
              "channel, the world satisfies one member at resolve"),
    Seed("al-0002", "alternatives", "launch the web vm or the db vm, whichever is stopped",
         ["the web vm", "the db vm"], ["launch"], {0: [0, 1]},
         triggers={0: "whichever is stopped"},
         note="the whichever-clause IS the condition — the trigger channel carries it "
              "(the al-0001 ruling unifies the family); choosing is RESOLVE's"),

    # ══ reduced-relative — the relativizer elided, the filter remains ════════════════
    Seed("rr-0001", "reduced-relative", "stop the vms running on lab",
         ["the vms running on lab"], ["stop"], {0: [0]},
         note="structure_map hole: same filter as 'the vms that are running on lab', "
              "relativizer elided — the reader keys on the relativizer today"),
    Seed("rr-0002", "reduced-relative", "delete the snapshots taken last week",
         ["the snapshots taken last week"], ["delete"], {0: [0]}),
    Seed("rr-0003", "reduced-relative", "restart the vms stuck at boot",
         ["the vms stuck at boot"], ["restart"], {0: [0]}),

    # ══ apposition — a rename in flight, the archive's own X-is-Y ════════════════════
    Seed("ap-0001", "apposition", "alpha, the jumpbox, is down",
         ["alpha", "the jumpbox"], ["is down"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "reference"},
              {"span": 2, "role": "evidence"}]},
         reports=[0], evidence=["is down"],
         note="RULED 08-21: 'the renames are scanned as well but are treated as "
              "refernces' — the apposition IS expressed, bound to the SAME referent "
              "with a reference role. One patient; the reader is scored on the "
              "equivalence the apposition-as-teaching harvest depends on"),
    Seed("ap-0002", "apposition", "stop the jumpbox, alpha",
         ["the jumpbox", "alpha"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "reference"}]},
         note="imperative apposition, same ruling mirrored — `alpha` co-names the "
              "patient as a reference"),

    # ══ cause — a symptom wearing a subordinate clause (D1's kin) ════════════════════
    Seed("ca-0001", "cause", "stop the vms because they are stuck",
         ["the vms"], ["stop"], {0: [0]}, evidence=["they are stuck"],
         note="every malfunction predicate is testimony — the because-clause is the "
              "SYMPTOM, evidence by the certified convention; the act stands alone"),
    Seed("ca-0002", "cause", "restart alpha because it won't answer",
         ["alpha"], ["restart"], {0: [0]}, evidence=["it won't answer"]),

    # ══ concession — an exception the operator already thought about ═════════════════
    Seed("co-0001", "concession", "stop the test vms even though alpha is busy",
         ["the test vms", "alpha"], ["stop"], {0: [0]}, evidence=["is busy"],
         note="RULED 08-21: testimony on a bystander, NEVER an excluded-role — 'even "
              "though' pre-empts an objection, it removes no one ('except' is v2's "
              "excluded role, already covered). Resolve/route test material later; "
              "a concession never grants"),
    Seed("co-0002", "concession", "launch the fleet even though the lab network is slow",
         ["the fleet", "the lab network"], ["launch"], {0: [0]},
         evidence=["is slow"]),

    # ══ magnitude — comparison over an attribute, the closed comparator class ════════
    Seed("mg-0001", "magnitude", "stop every vm with over 6gb of ram",
         ["every vm with over 6gb of ram"], ["stop"], {0: [0]},
         note="read 08-16 as (gt, 6, gb, memory_mb); the span is the filtered NP whole"),
    Seed("mg-0002", "magnitude", "list the vms with more than 2 cores",
         ["the vms with more than 2 cores"], ["list"], {0: [0]}),
    Seed("mg-0003", "magnitude", "delete the snapshots older than a month",
         ["the snapshots older than a month"], ["delete"], {0: [0]}),

    # ══ manner — HOW binds this request only, and dropping it changes what runs ══════
    Seed("mn-0001", "manner", "restart the vms one at a time",
         ["the vms"], ["restart"], {0: [0]},
         manner={0: "one at a time"},
         note="RULED 08-21 (schema ruling 1): manner is EXPRESSED — the act's second "
              "control channel, how-execution-is-handled; the derived loop inherits "
              "it at lowering as serial pacing"),
    Seed("mn-0002", "manner", "stop the lab vms all at once",
         ["the lab vms"], ["stop"], {0: [0]},
         manner={0: "all at once"}),

    # ══ learned-words — the stores teach, the reader picks it up (SCHEMA QUESTION 2) ═
    Seed("lw-0001", "learned-words", "stop the grubnash",
         ["the grubnash"], ["stop"], {0: [0]},
         store=[{"word": "grubnash", "kind": "vm", "ratified": True},
                {"word": "grubnash", "kind": "network", "ratified": False},
                {"word": "grubnest", "kind": "vm", "ratified": True},
                {"word": "tomato", "kind": "fruit", "ratified": True}],
         note="RULED 08-21 (schema ruling 2): a POPULATED store — the target plus "
              "three decoy classes (name overlap unratified · near-miss/sounds-similar "
              "· unrelated filler). Selection under distraction is the measurement; "
              "certifying this case ratifies the mock, decoys included"),
    Seed("lw-0002", "learned-words", "spin up a fresh grubnash next to alpha",
         ["a fresh grubnash", "alpha"], ["spin up"], {0: [0, 1]},
         store=[{"word": "grubnash", "kind": "vm", "ratified": True},
                {"word": "grubnash", "kind": "network", "ratified": False},
                {"word": "grubnest", "kind": "vm", "ratified": True},
                {"word": "tomato", "kind": "fruit", "ratified": True}],
         note="the taught word in a creation frame, same populated mock as lw-0001"),
    Seed("lw-0003", "learned-words", "when you have a sec, stop the db vm",
         ["the db vm"], ["stop"], {0: [0]},
         store=[{"phrase": "when you have a sec", "is": "courtesy", "ratified": True},
                {"phrase": "in a sec", "is": "duration", "ratified": True},
                {"word": "tomato", "kind": "fruit", "ratified": True}],
         note="a TAUGHT courtesy literal (retires the archive-debt pattern), with a "
              "sounds-similar decoy of a DIFFERENT meaning beside it. Courtesy marks "
              "nothing, exactly as certified"),

    # ══ self-address — 'you' is the agent; it must never become a thing ══════════════
    Seed("sa-0001", "self-address", "can you check the web vm?",
         ["the web vm"], ["can you check the web vm"], {0: [0]}, queries=[0],
         note="'you' is the agent ([[gorgon-you-is-the-agent]]): the read only FLAGS "
              "the pronoun — the gold check is that no 'you' row exists (a row would "
              "score hallucinated). Routing stays post-READ, as ruled"),
    Seed("sa-0002", "self-address", "good morning, stop the lab vms",
         ["the lab vms"], ["stop"], {0: [0]},
         note="a greeting marks nothing — flavour is one kind, not the genus"),

    # ══ ordinals — selection by ORDER, a closed class nothing reads ══════════════════
    Seed("or-0001", "ordinals", "stop the first vm",
         ["the first vm"], ["stop"], {0: [0]},
         note="RULED 08-21: 'we keep it — again resolve issue'. The ordinal stays "
              "INSIDE the span: one selector NP, verbatim; the attr-class TYPE "
              "licenses the ordering axis and the world orders and picks at RESOLVE"),
    Seed("or-0002", "ordinals", "delete the last snapshot",
         ["the last snapshot"], ["delete"], {0: [0]}),
    Seed("or-0003", "ordinals", "restart the second one",
         ["the second one"], ["restart"], {0: [0]}),

    # ══ fallback — act-anaphora: `that` names the ACT, failure-contingent order ══════
    Seed("fb-0001", "fallback", "stop alpha, and if that fails, kill it",
         ["alpha"], ["stop", "kill"], {0: [0], 1: [0]},
         triggers={1: "if that fails"},
         note="`that` refers to the STOP — an act, not a thing; the kill is TRIGGERED "
              "by its failure. No span for the act-anaphor (the bare-pronoun rule, one "
              "level up)"),
    Seed("fb-0002", "fallback", "launch the db vm, and if that doesn't work, restart the host",
         ["the db vm", "the host"], ["launch", "restart"], {0: [0], 1: [1]},
         triggers={1: "if that doesn't work"}),

    # ══ pairwise — coordination with DIFFERENT values per conjunct ═══════════════════
    Seed("pw-0001", "pairwise", "label web 'ready' and db 'hold'",
         ["web", "ready", "db", "hold"], ["label", "label"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}],
          1: [{"span": 2, "role": "patient"}, {"span": 3, "role": "value"}]},
         note="RULED 08-21: the two-acts shape is BLESSED — one verb, one act per "
              "conjunct pair, all sharing the verb's offsets; the elided verb is "
              "real, just unspoken. The one-patient rule stands untouched"),
    Seed("pw-0002", "pairwise", "put web on lab and db on dmz",
         ["web", "lab", "db", "dmz"], ["put", "put"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "destination"}],
          1: [{"span": 2, "role": "patient"}, {"span": 3, "role": "destination"}]},
         note="same shape as pw-0001, destination flavour"),
    Seed("pw-0003", "pairwise", "label alpha 'up', beta 'down' and gamma 'hold'",
         ["alpha", "up", "beta", "down", "gamma", "hold"],
         ["label", "label", "label"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}],
          1: [{"span": 2, "role": "patient"}, {"span": 3, "role": "value"}],
          2: [{"span": 4, "role": "patient"}, {"span": 5, "role": "value"}]},
         note="coverage per the ruling ('cover not just one case but a few') — the "
              "three-conjunct chain: one verb, three acts"),
    Seed("pw-0004", "pairwise", "give web 4 cores and db 8gb",
         ["web", "4 cores", "db", "8gb"], ["give", "give"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}],
          1: [{"span": 2, "role": "patient"}, {"span": 3, "role": "value"}]},
         note="coverage — unit-value flavour: pairwise composed with the units stratum"),

    # ══ negated-query — negation composed with the interrogative ═════════════════════
    Seed("nq-0001", "negated-query", "which vms are not running?",
         ["which vms"], ["which vms are not running"], {0: [0]}, queries=[0],
         note="cs-0007's convention + negation: the asked property (negated) stays "
              "unmarked; the wh-NP is the span"),
    Seed("nq-0002", "negated-query", "is alpha not responding?",
         ["alpha"], ["is alpha not responding"], {0: [0]}, queries=[0]),

    # ══ schedules — recurrence as a standing trigger (temporal.RECURRENCE, offsetless
    #    today exactly as the clock was) ═══════════════════════════════════════════════
    Seed("sch-0001", "schedules", "snapshot the db vm every night",
         ["the db vm"], ["snapshot"], {0: [0]},
         triggers={0: "every night"},
         note="the recurrence is the trigger — clock_tail's sibling, RECURRENCE arm; "
              "today it has no offset reader, so this seed holds the slot open exactly "
              "as qual-0005 held the clock's"),
    Seed("sch-0002", "schedules", "check the lab network every 2 hours",
         ["the lab network"], ["check"], {0: [0]},
         triggers={0: "every 2 hours"}),

    # ══ superlatives — an ORDERING over an attribute (attr classes license it) ═══════
    Seed("sup-0001", "superlatives", "stop the biggest vm",
         ["the biggest vm"], ["stop"], {0: [0]},
         note="structure_map ⚠⚠: a superlative needs an ordering — the attribute "
              "class's TYPE (count/quantity = orderable) is what licenses (max, "
              "memory_mb). Span whole, like every filtered NP"),
    Seed("sup-0002", "superlatives", "delete the oldest snapshot of alpha",
         ["the oldest snapshot of alpha"], ["delete"], {0: [0]}),

    # ══ naming-lists — one act MINTING several names ═════════════════════════════════
    Seed("nl-0001", "naming-lists", "create three vms named a, b and c",
         ["three vms named a, b and c"], ["create"], {0: [0]},
         note="RULED 08-21: ONE span carrying the mints — naming specs are often "
              "GENERATORS (ranges, themes), not lists; the names may not exist as "
              "bytes at all. Literal values carve (un-0002); a naming spec is one "
              "generative unit — mints happen where the generator runs"),
    Seed("nl-0002", "naming-lists", "create two networks called front and back",
         ["two networks called front and back"], ["create"], {0: [0]}),
    Seed("nl-0003", "naming-lists", "create 5 vms named 1-5",
         ["5 vms named 1-5"], ["create"], {0: [0]},
         note="the operator's own sentence — a RANGE generator: no five name spans "
              "exist; the spec stays whole and the generator runs downstream"),
    Seed("nl-0004", "naming-lists",
         "create 3 vms named after musicians and a network called the stadium "
         "and add those vms to it",
         ["3 vms named after musicians", "a network called the stadium", "those vms"],
         ["create", "add"], {0: [0, 1], 1: [2]},
         note="the operator's own sentence — a THEME generator plus a compound: one "
              "create distributing two mints (plain members, no direction claimed), "
              "then an add whose 'those vms' is within-sentence anaphora; 'it' is the "
              "bare pronoun, no span (the bare-pronoun rule)"),

    # ══ quoted-values — a value with SPACES stays one value ══════════════════════════
    Seed("qv-0001", "quoted-values", "label the web vm 'do not touch'",
         ["the web vm", "do not touch"], ["label"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="the quoted value contains a NEGATION and an op word — the quotes are "
              "structural: nothing inside them is read as language (evidence-opacity's "
              "little sibling, write side)"),
    Seed("qv-0002", "quoted-values", "call the new network 'staging east'",
         ["the new network", "staging east"], ["call"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]}),

    # ══ audit — a question about OUR OWN behaviour, never sent at the lab ════════════
    Seed("au-0001", "audit", "what did you just run?",
         [], ["what did you just run"], {}, queries=[0],
         note="coverage_map ⚠⚠: events.log is the arbiter and no sentence reaches it. "
              "NO object spans — the question is about the agent's ledger, not a lab "
              "thing; any lab op emitted from it scores hallucinated. Pairs with "
              "self-address: 'you' is the agent"),
    Seed("au-0002", "audit", "what changed in the lab today?",
         [], ["what changed in the lab today"], {}, queries=[0],
         note="same family, the lab-shaped skin — still an events.log question"),

    # ══ capability — CAN-you generic vs CAN-you polite order ═════════════════════════
    Seed("cap-0001", "capability", "can you create networks?",
         [], ["can you create networks"], {}, queries=[0],
         note="BARE PLURAL, no determiner = a question about ABILITY — no object, no "
              "create op (one emitted scores hallucinated). The twin below is the "
              "adversary"),
    Seed("cap-0002", "capability", "can you create a network for the test vms?",
         ["a network", "the test vms"], ["create"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "beneficiary"}]},
         note="SINGULAR INDEFINITE = the polite order (0/14 measured). RULED 08-21: "
              "the beneficiary role is TAKEN — a dropped purpose qualifier becomes a "
              "visible miss — and a polite order is a REFUSABLE order: the read "
              "produces it faithfully, ROUTE decides its fate"),

    # ══ preference — a SOFT standing constraint; reads as a RULE act ═════════════════
    Seed("pr-0001", "preference", "prefer the lab network for the new vms",
         ["the lab network", "the new vms"],
         ["prefer the lab network for the new vms"], {0: [0, 1]}, rules=[0],
         note="a preference LEGISLATES softly — the clause is the act (the rules "
              "convention); weighting it against a hard rule is route's, never read's"),
    Seed("pr-0002", "preference", "i'd rather use the smaller profile",
         ["the smaller profile"], ["i'd rather use the smaller profile"],
         {0: [0]}, rules=[0],
         note="coverage_map's preference hole — 'i'd rather' is a closed preference "
              "marker; the superlative inside the span rides the superlatives stratum"),

    # ══ hand-authored noise twins — embedded-junk + code-switch (RULED 08-21: build) ══
    # Mechanical noisers cannot invent junk placement or another language, so these
    # twins are authored by hand and certified like any case. The slot decides junk;
    # the closed classes do not grow.
    Seed("po-0001-ej", "possessive", "delete adsfk alpha's snapshots",
         ["alpha's snapshots"], ["delete"], {0: [0]},
         noise="embedded-junk", pair_id="po-0001",
         note="keyboard mash in a CLOSED position — junk between verb and NP joins no "
              "span (the slot decides); the same bytes in a naming slot would be a "
              "legal mint"),
    Seed("ca-0002-ej", "cause", "restart alpha adsfk because it won't answer",
         ["alpha"], ["restart"], {0: [0]}, evidence=["it won't answer"],
         noise="embedded-junk", pair_id="ca-0002",
         note="junk between patient and cause-clause — outside every span; the "
              "evidence still binds"),
    Seed("sa-0002-cs", "self-address", "בוקר טוב, stop the lab vms",
         ["the lab vms"], ["stop"], {0: [0]},
         noise="code-switch", pair_id="sa-0002",
         note="a greeting in another language marks nothing — same gold as the clean "
              "twin; flavour is one kind, not the genus"),
    Seed("id-0001-cs", "identifiers", "תעצור את the vm at 10.0.0.5",
         ["the vm at 10.0.0.5"], [], {},
         noise="code-switch", pair_id="id-0001",
         note="the VERB is foreign — no producer fires, and the closed classes do not "
              "grow (RULED): gold says the UNKNOWN bounce — no acts, no attachments; "
              "the object NP still detects. The bounce IS the correct answer"),
]


def emit() -> List[dict]:
    """Build every v3 seed and refuse to hand over anything the schema rejects."""
    cases = [build(s) for s in SEEDS_V3]
    faults = validate(cases)
    if faults:
        raise SystemExit("\n".join(f"  ✗ {f}" for f in faults))
    return cases


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import json
    import os
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    cases = emit()
    if "--emit" in argv:
        path = os.path.join(os.path.dirname(__file__), "cases", "v3-draft.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for case in cases:
                fh.write(json.dumps(case, ensure_ascii=False) + "\n")
        print(f"  {len(cases)} case(s) -> {path}")
    else:
        print(f"  {len(cases)} case(s), 0 faults (--emit writes cases/v3-draft.jsonl)")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())

