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
         ["the vms"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["they are stuck"],
         note="RULED 08-22 (certification): 'you do need to carry the evidence to stop "
              "because its a future reference' — the because-clause is the SYMPTOM, "
              "evidence by the certified convention, and it is CARRIED by the act, "
              "not left beside it"),
    Seed("ca-0002", "cause", "restart alpha because it won't answer",
         ["alpha"], ["restart"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["it won't answer"],
         note="RULED 08-22: carried — 'an important reference, regardless if its used "
              "as part of the operator'"),

    # ══ concession — an exception the operator already thought about ═════════════════
    Seed("co-0001", "concession", "stop the test vms even though alpha is busy",
         ["the test vms"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["alpha is busy"],
         note="RULED 08-21: testimony on a bystander, NEVER an excluded-role — 'even "
              "though' pre-empts an objection, it removes no one ('except' is v2's "
              "excluded role, already covered). RULED 08-22 (certification, LEDGER "
              "#12): the bystander is NOT an object — 'drop the other object since "
              "its irrelevant to the main cause' — it lives INSIDE the evidence, "
              "which is the whole clause 'alpha is busy', carried by the act and "
              "FILED as cross-turn evidence, not acted upon. Supersedes v1 adj-0003 "
              "(same sentence, alpha extracted, no evidence)"),
    Seed("co-0002", "concession", "launch the fleet even though the lab network is slow",
         ["the fleet"], ["launch"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["the lab network is slow"],
         note="RULED 08-22 (LEDGER #12), the operator's own shape: 'stop vmA because "
              "networkA is slow' becomes stop -> vmA + evidence 'networkA is slow', "
              "FILED -> 'networkA is slow' (cross-turn evidence, not acted upon). "
              "The bystander network is inside the testimony, not an object"),

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
         ["the db vm"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         mood=[("deference", "when you have a sec")], evidence=["when you have a sec"],
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
         ["the lab vms"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         mood=[("phatic", "good morning")], evidence=["good morning"],
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
         ["create", "add"],
         {0: [0, 1],
          1: [{"span": 2, "role": "patient"}, {"span": 1, "role": "destination"}]},
         note="the operator's own sentence — a THEME generator plus a compound: one "
              "create distributing two mints (plain members, no direction claimed), "
              "then an add. RULED 08-22: 'add does not have a patient and a "
              "destination, its supposed to be a put-on-network request' — so the add "
              "is DIRECTED like pw-0002: 'those vms' (within-sentence anaphora) is the "
              "patient, and 'it' is the bare pronoun resolved to its antecedent, the "
              "network span, as destination (the bare-pronoun rule: point at the "
              "thing, never at the pointer — fb-0001's 'kill it' → alpha)"),

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
         ["alpha"], ["restart"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["it won't answer"],
         noise="embedded-junk", pair_id="ca-0002",
         note="junk between patient and cause-clause — outside every span; the "
              "evidence still binds"),
    # ═══════════════════════════════════════════════════════════════════════════════════
    # ══ v3.1 — THE CORPUS HOLES (operator, 08-22: "i want to cover everything … READ
    # ══ should be able to parse 95%+ of english"). Six strata the structure_map and
    # ══ coverage_map named and no gold held. Every RULING NEEDED is a docket item.
    # ═══════════════════════════════════════════════════════════════════════════════════

    # ══ null-turn — the reading is NOTHING, and that is the certified answer ══════════
    #   Zero golds existed for a sentence the reader must produce nothing from. This is the
    #   stratum the courtesy hazard, the polite-order family and the commitment rest on:
    #   the reader's SILENCE is the correct output, and until now nothing proved it.
    Seed("nt-0001", "null-turn", "ok, got it", [], [], {}, outcome="none",
         note="ACKNOWLEDGEMENT (coverage_map hole) — flavour species A2; no thing, no act. "
              "RULED 08-22: 'acknowledgment only carries resolution when the issue is "
              "diagnosis/query, meaning only when INFORMATION is the topic' — with no "
              "context supplied there is no information issue in play, so this is a plain "
              "acknowledgement and stays `none`. Its control is td-0010, the same bytes "
              "under an answered query, which IS testimony"),
    Seed("nt-0002", "null-turn", "thanks, that worked", [], [], {},
         evidence=["thanks", "that worked"], outcome="testimony",
         mood=[("closure", "thanks")],
         note="RULED 08-22 (LEDGER #14): 'should be treated as testimony, a subset of "
              "evidence which are user input' — RESOLUTION: the system's act succeeded, a "
              "fact the issue ledger files (D3's Issues.answers()). The evidence is "
              "UNATTACHED and legal only because the outcome says so: the act it reports "
              "on belongs to the previous turn, and 'that' is a cross-turn pointer with no "
              "span (the bare-pronoun rule + LAST is out of scope)"),
    Seed("nt-0003", "null-turn", "oh it's really hot in here", [], [], {}, outcome="none",
         note="UNRELATED — species B: a proposition about a world that is not ours"),
    Seed("nt-0004", "null-turn", "asdjhasjdbhasd", [], [], {}, outcome="none",
         note="NOISE — species C: carries nothing at all"),
    Seed("nt-0005", "null-turn", "please!!", [], [],
         {}, evidence=["please!!"], outcome="testimony",
         mood=[("frustration", "please!!")],
         note="RULED 08-22: 'ambigius / mood indector for rage/desperation' — and then "
              "'mood should be its own channel because it is important to ALSO provide it "
              "as evidence', so it rides the v2.4 MOOD channel and the same span is carried "
              "as evidence. THE SPECIES, and the taxonomy settles the ambiguity itself: "
              "rage would be A4 HOSTILITY, but A4 requires an AIMED slur and there is none "
              "here — so both rage and desperation land in A3 FRUSTRATION, which says a "
              "PRIOR ATTEMPT FAILED (a diagnosis context, D1). ⚠ RULING NEEDED if that "
              "boundary is wrong. The word is A1 deference; the FORCE is what is read — "
              "which is the direct countermeasure to the 7/7 measured hazard where a "
              "courtesy word was resolved into intent"),
    Seed("nt-0006", "null-turn", "i'll add the labels myself tomorrow", [], [],
         {}, evidence=["i'll add the labels myself tomorrow"], outcome="testimony",
         note="RULED 08-22: testimony — 'evidence for a user resolved'. The OPERATOR says "
              "THEY will act, so a reader that emits add_label has taken an act nobody "
              "asked for; the fact that the user took it is what the ledger files. The "
              "whole clause is the testimony (co-0001's convention: evidence is the WHOLE "
              "clause). 'the labels' still names an attribute, not a thing — no span"),
    Seed("nt-0007", "null-turn", "i'll stop alpha myself", ["alpha"], [],
         {}, evidence=["i'll stop alpha myself"], outcome="testimony",
         note="RULED 08-22: testimony, same as nt-0006 — with a lab object, which still "
              "detects (id-0001-cs's ruling). The act is the operator's, not Gorgon's; the "
              "evidence span covers the object it names, which is legal (only SAME-type "
              "spans may not overlap)"),
    Seed("nt-0008", "null-turn", "asdjhasjdbhasd the vms", ["the vms"], [], {},
         outcome="reject",
         hint=("inexpressible",
               "the verb slot holds a keyboard — no closed class expresses it, and no store "
               "could teach it either"),
         note="RULING NEEDED: a keyboard in the VERB slot with a lab object — species C "
              "(noise) in a licensing slot. Drafted REJECT like the foreign verb (the slot "
              "decides, the closed classes do not grow); vs `grubnash the vms`, which is "
              "species D (UNKNOWN) and BOUNCES with a question because the store may know it"),
    Seed("nt-0009", "turn-dependent", "stop neither alpha nor beta", [], [],
         {}, outcome="context-needed",
         hint=("possible-reference",
               "'stop neither' may be a PROHIBITION (a rule: do not stop these) or an "
               "ORDER TO ABANDON an act already under way — which one depends on whether "
               "something is running"),
         context={"from": "resolve", "heading": "unknown", "waited_response": False},
         note="RULED 08-22: 'this is a rule, asking the AI not to stop something, or could "
              "be an action, asking the AI to stop their action, this is context "
              "dependent' — so it is not null, it is TURN-DEPENDENT. The context supplied "
              "here is deliberately EMPTY of heading: even with RESOLVE speaking, this "
              "state does not settle it, and READ says so rather than guessing"),

    # ══ turn-dependent — READ IS BLIND, AND SAYS SO (operator ruling, LEDGER #14) ══════
    #   *"they are only understandable by the fact of the previous turns"*. The corpus
    #   declares BOTH hints: `context` is what RESOLVE supplies (inbound), `hint` is what
    #   READ writes for ROUTE (outbound) — AFTER chunking, BEFORE it decides what it is
    #   looking at, so the hint records what a piece COULD be before the reading commits to
    #   what it IS (operator's correction, 08-22). Nothing is dropped for being vague — *"an unrelated 'check' is processed as if it is important, ALL are"*.
    #   ⚠ RULING NEEDED, whole-stratum: is a hint written on EVERY turn, or only where READ
    #   is uncertain? Drafted: only where it carries information ROUTE cannot recompute.
    #   ⚠ RULING NEEDED: these come in WITH/WITHOUT-context pairs and `pair_id` cannot link
    #   them (a clean case never points — that mechanism is for noise twins). Should pairing
    #   generalise to a context pair, or does the note carry it?
    Seed("td-0001", "turn-dependent", "yes", [], [], {},
         evidence=["yes"], outcome="testimony",
         context={"from": "resolve", "expecting": "yes-no", "about": "the plan"},
         hint=("answer-shaped", "a bare polarity answer, and a y/n was expected — this "
                                "settles the pending question"),
         note="THE OPERATOR'S OWN SHAPE (08-22): 'context message from RESOLVE: expecting a "
              "y/n answer from user about a plan · user: yes -> yes (evidence)'. The "
              "expectation is what makes a one-word turn legal AND EXTRACTABLE"),
    Seed("td-0002", "turn-dependent", "no", [], [], {},
         evidence=["no"], outcome="testimony",
         context={"from": "resolve", "expecting": "yes-no", "about": "the plan"},
         hint=("answer-shaped", "a bare polarity answer, negative — the pending plan is "
                                "declined"),
         note="the negative arm of td-0001; polarity is read by the closed class "
              "(reading_answers.NEGATION), never by the model"),
    Seed("td-0003", "turn-dependent", "yeah", [], [], {},
         evidence=["yeah"], outcome="testimony",
         context={"from": "resolve", "expecting": "yes-no", "about": "the plan"},
         hint=("answer-shaped", "'yeah' is an affirmation here because an answer was "
                                "waited on; with nothing pending it is a backchannel"),
         note="⚠ THE ISO DEFECT, NAMED (operator, 08-22): the 'yeah's from a week ago were "
              "'both tunal and required context of previous messages to make sense'. "
              "`reading_answers.AFFIRMATION` holds 'yeah'; `iso.BACKCHANNEL` holds its "
              "tonal siblings — and NO reader can settle which one it is alone. The "
              "context does. Pairs with td-0004"),
    Seed("td-0004", "turn-dependent", "yeah", [], [], {}, outcome="context-needed",
         hint=("answer-shaped", "'yeah' with nothing pending — an affirmation of something, "
                                "or a backchannel; READ cannot tell and does not guess"),
         note="THE CONTROL for td-0003: same bytes, NO expectation supplied, and the "
              "reading changes. This pair is the whole argument for the loop — a reader "
              "that answers the same for both is guessing on one of them"),
    Seed("td-0005", "turn-dependent", "check", [], [], {}, outcome="context-needed",
         hint=("possible-reference", "a lone 'check' could be a reference to a previous "
                                     "response — or an order to check something unnamed"),
         note="THE OPERATOR'S OWN EXAMPLE (08-22): 'an unrelated check is processed as if "
              "it is important, ALL are — its processed under context-needed and will be "
              "resolved at ROUTE to determine if its a reference, or not. The READ is "
              "blind here but it is given a hint based on rules.' Nothing is dropped"),
    Seed("td-0006", "turn-dependent", "hey, check", [], [], {}, outcome="context-needed",
         mood=[("phatic", "hey")], evidence=["hey"],
         context={"from": "resolve", "waited_response": True},
         hint=("possible-reference", "the user is asking about a follow-up to previous "
                                     "responses"),
         note="THE OPERATOR'S WORKED EXAMPLE, verbatim: \"'hey, check' is virtually the "
              "same as a lone 'check' … RESOLVE HINT: awaiting a response · READ HINT: 'the "
              "user is asking about a follow-up to previous responses' -> ROUTE: REFUSE, no "
              "reference found to a response worth checking / ACCEPT, routing a RESOLVE -> "
              "RESOLVE: action approved.\" The greeting is flavour and marks nothing; the "
              "WAITED RESPONSE is what sharpens the same hint td-0005 gives blind"),
    Seed("td-0007", "turn-dependent", "stop that", [], ["stop"], {},
         context={"from": "resolve", "heading": "a plan was just proposed",
                  "waited_response": True},
         hint=("possible-reference", "'that' points at the act just proposed — the target "
                                     "is in the previous turn, not this one"),
         note="AN ORDER WITH A CROSS-TURN TARGET, made legal by the context. The act is "
              "read; its object is NOT in this sentence, so the attachment is empty and "
              "'that' gets no span (the bare-pronoun rule: point at the thing, and the "
              "thing is not here). Resolving it is LAST's, which stays out of scope — "
              "READ's job is to produce the act and SAY where the target lives"),
    Seed("td-0008", "turn-dependent", "whats next", [], ["whats next"], {}, queries=[0],
         context={"from": "resolve", "heading": "a plan is part-run", "waited_response": False},
         hint=("possible-reference", "asks about the state of something already under way — "
                                     "the referent is the running plan"),
         note="a QUERY whose subject is the session itself, not the lab — audit's kin, and "
              "it produces (the query act) rather than bouncing"),
    Seed("td-0010", "turn-dependent", "ok, got it", [], [],
         {}, evidence=["got it"], outcome="testimony",
         context={"from": "resolve", "heading": "a query was just answered",
                  "topic": "information", "waited_response": True},
         hint=("answer-shaped", "an acknowledgement of INFORMATION — the question that was "
                                "open is now closed"),
         note="RULED 08-22: 'acknowledgment only carries resolution when the issue is "
              "diagnosis/query, meaning ONLY WHEN INFORMATION IS THE TOPIC'. So the same "
              "bytes are testimony here and a plain acknowledgement in nt-0001: the "
              "difference is entirely in the state RESOLVE supplies, which is the loop's "
              "whole claim. Evidence is 'got it' — the receipt, not the courtesy. RULING "
              "NEEDED: the counterpart NOT drafted is 'ok, got it' after an ACT, which by "
              "this ruling is `none` — its own case, or does nt-0001 carry it?"),
    Seed("td-0009", "turn-dependent", "lets continue", [], [], {}, outcome="context-needed",
         hint=("unreadable-alone", "'continue' names no act and no object — nothing in this "
                                   "turn survives without knowing what was under way"),
         note="the operator's second vague example: 'check', 'lets continue' are USUALLY "
              "TOO VAGUE. Distinct from td-0005: 'check' could be an order in its own "
              "right, 'lets continue' cannot — nothing is nameable, which is why the hint "
              "kind differs"),

    # ══ indirect-orders — the measured 0/14 family, an order by another mechanism ═══════
    Seed("io-0001", "indirect-orders", "i need alpha stopped",
         ["alpha"], ["stopped"], {0: [0]},
         note="nominalised order — the PARTICIPLE is the act, the patient precedes it. "
              "RULING NEEDED: is the verb span 'stopped' or 'need alpha stopped'"),
    Seed("io-0002", "indirect-orders", "alpha needs to be stopped",
         ["alpha"], ["stopped"], {0: [0]},
         note="passive with a deontic — the patient is the SUBJECT; order, not report"),
    Seed("io-0003", "indirect-orders", "would you mind stopping alpha?",
         ["alpha"], ["stopping"], {0: [0]},
         note="polite order in question form — a REFUSABLE order (cap-0002's ruling), the "
              "gerund is the act. RULING NEEDED: query kind (like 'can you check') or "
              "plain act — drafted as the ACT, because 'mind' asks consent for an act, "
              "not for information"),
    Seed("io-0004", "indirect-orders", "let's stop alpha",
         ["alpha"], ["stop"], {0: [0]},
         note="hortative — 'let's' is an opener with a first-person marker; the order stands"),
    Seed("io-0005", "indirect-orders", "we should stop alpha",
         ["alpha"], ["stop"], {0: [0]},
         note="deontic 'should' — an order by obligation, not a rule (no 'never'/'always')"),
    Seed("io-0006", "indirect-orders", "alpha should be stopped",
         ["alpha"], ["stopped"], {0: [0]},
         note="deontic passive — same act as io-0005 with the patient as subject"),
    Seed("io-0007", "indirect-orders", "it would be great if alpha were down",
         ["alpha"], ["were down"], {0: [0]},
         note="subjunctive ACHIEVE — a state asked for, no verb of acting at all. RULING "
              "NEEDED: the act span of a state-achieve ('were down' drafted); mood_of "
              "should read ACHIEVE and the step is derived downstream"),

    # ══ tense-person — the verb form decides order vs report ═════════════════════════
    Seed("tp-0001", "tense-person", "i stopped alpha",
         ["alpha"], ["stopped"], {0: [0]}, reports=[0],
         note="first-person PAST — a REPORT of the operator's own act; the ledger files it, "
              "nothing runs. A reader that emits stop_vm acts on a past"),
    Seed("tp-0002", "tense-person", "alpha stopped",
         ["alpha"], ["stopped"], {0: [0]}, reports=[0],
         note="intransitive past — a state change OBSERVED; report, not order"),
    Seed("tp-0003", "tense-person", "alpha was stopped yesterday",
         ["alpha"], ["was stopped"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["yesterday"], reports=[0],
         note="RULED 08-22 (THE TENSE RULE, LEDGER #14): 'yesterday is a sensitive "
              "temporal reference … its not a temporal trigger but a reference, every day "
              "is a temporal trigger for example — PAST ACTION ARE EVIDENCE AND FUTURE ARE "
              "TRIGGERS, usually'. So the past reference is an EVIDENCE span carried by "
              "the report; the deferred-time stratum's future phrases stay TRIGGERS. "
              "Unmarked, the report reads as a timeless state"),
    Seed("tp-0004", "tense-person", "alpha is stopping",
         ["alpha"], ["is stopping"], {0: [0]}, reports=[0],
         note="progressive — a state IN PROGRESS, observed; report"),
    Seed("tp-0005", "tense-person", "i just stopped alpha, launch beta",
         ["alpha", "beta"], ["stopped", "launch"], {0: [0], 1: [1]}, reports=[0],
         note="a report AND an order in one sentence — the clause split must keep them "
              "apart: the past is filed, the imperative runs"),

    # ══ deferred-time — one-shot time and duration (the linguistic sweep's own finding) ═
    #   `schedules` covers recurrence; "stop every vm at 9pm" RUNS NOW today. A discarded
    #   time qualifier is a wrong CHOICE, not padding.
    Seed("dt-0001", "deferred-time", "stop every vm at 9pm",
         ["every vm"], ["stop"], {0: [0]}, triggers={0: "at 9pm"},
         note="one-shot CLOCK — the trigger channel carries it (like 'every night')"),
    Seed("dt-0002", "deferred-time", "snapshot alpha in 10 minutes",
         ["alpha"], ["snapshot"], {0: [0]}, triggers={0: "in 10 minutes"},
         note="relative delay — a trigger on the clock from now"),
    Seed("dt-0003", "deferred-time", "launch beta tomorrow morning",
         ["beta"], ["launch"], {0: [0]}, triggers={0: "tomorrow morning"},
         note="deictic day + part — temporal.DEICTIC reads 'tomorrow'; the trigger is the "
              "whole phrase"),
    Seed("dt-0004", "deferred-time", "stop alpha for an hour",
         ["alpha"], ["stop"], {0: [0]}, manner={0: "for an hour"},
         note="DURATION — stop, and launch again after an hour: one act with a bounded "
              "extent, the reverse act derived downstream. RULING NEEDED: duration is "
              "drafted on the MANNER channel (execution control: how long), not trigger "
              "(when); the derived launch is RESOLVE's, not READ's"),

    # ══ conditional-branches — the other branch: unless · otherwise · both ═════════════
    Seed("cb-0001", "conditional-branches", "stop alpha unless it is the jumpbox",
         ["alpha"], ["stop"], {0: [0]}, triggers={0: "unless it is the jumpbox"},
         note="negative condition — a trigger whose polarity is inverted; the act is the "
              "same. 'the jumpbox' is a predicate nominal, not an object (apposition's kin)"),
    Seed("cb-0002", "conditional-branches",
         "if alpha is up, snapshot it, otherwise launch it",
         ["alpha"], ["snapshot", "launch"], {0: [0], 1: [0]},
         triggers={0: "if alpha is up", 1: "otherwise"},
         note="the ELSE branch — two acts on one referent under complementary triggers; "
              "'otherwise' is the trigger word of the second (its condition is the "
              "negation of the first, RESOLVE's to expand). Both 'it' are bare pronouns "
              "-> the one span"),
    Seed("cb-0003", "conditional-branches", "stop both alpha and beta, not just one",
         ["alpha", "beta"], ["stop"], {0: [0, 1]}, manner={0: "not just one"},
         note="RULED 08-22: \"'not just one' is ambigius since it could mean launch both or "
              "if you cant launch one dont launch the other as well — this is for ROUTE or "
              "resolve but SHOULD BE TAGGED ANYWAY as 'procedure control', like 'one at a "
              "time'\". So it rides the MANNER channel (mn-0001's channel): READ carries "
              "the control faithfully, the two readings are settled downstream"),
    Seed("cb-0004", "conditional-branches",
         "if alpha is down restart it, and if that doesn't help, tell me",
         ["alpha"], ["restart", "tell me"], {0: [0], 1: [0]},
         triggers={0: "if alpha is down", 1: "if that doesn't help"}, queries=[1],
         note="a condition AND a fallback on one referent, the fallback a QUERY (report "
              "back) — the chain's shape, certified at READ"),

    # ══ partitives — how many of the set, and a number that is a name ════════════════
    Seed("pt-0001", "partitives", "stop two of the lab vms",
         ["two of the lab vms"], ["stop"], {0: [0]},
         note="numeric partitive — the spec stays WHOLE (naming-spec ruling: a generator, "
              "not a list); which two is RESOLVE's"),
    Seed("pt-0002", "partitives", "stop all but two of the vms",
         ["all but two of the vms"], ["stop"], {0: [0]},
         note="count carve-out with NO named exclusion — whole span. RULING NEEDED: the "
              "excluded role needs a thing; a COUNT cannot be excluded, so the span stays "
              "one (vs 'every vm except db', two spans)"),
    Seed("pt-0003", "partitives", "stop any vm", ["any vm"], ["stop"], {0: [0]},
         note="'any' — one, unspecified; a scope word the UNIVERSAL class holds but whose "
              "reading is ONE, not ALL. RULING NEEDED: any = one of (RESOLVE picks)"),
    Seed("pt-0004", "partitives", "stop half of the vms", ["half of the vms"], ["stop"],
         {0: [0]}, note="fraction partitive — PARTIAL class; whole span"),
    Seed("pt-0005", "partitives", "stop vm 3", ["vm 3"], ["stop"], {0: [0]},
         note="a NUMBER AS A NAME — 'vm 3' is one named thing; contrast pt-0006"),
    Seed("pt-0006", "partitives", "stop 3 vms", ["3 vms"], ["stop"], {0: [0]},
         note="a number as a COUNT — the position decides (enumerator before the noun)"),

    Seed("sa-0002-cs", "self-address", "בוקר טוב, stop the lab vms",
         ["the lab vms"], [], {},
         outcome="reject",
         hint=("unsupported-language",
               "the sentence mixes languages — Gorgon reads English; ask the operator to "
               "restate it in one language"),
         noise="code-switch", pair_id="sa-0002",
         note="RULED 08-22, AND IT SUPERSEDES THE SLOT READING (ledger #12 said foreign "
              "FLAVOUR passes through): 'sa-0002-cs should ALSO be rejected as it contains "
              "a different language and therefor NO MATTER WHAT it should also be automatic "
              "reject … all sentences containing a different language get ASK automatically "
              "with the note basically telling them that the project does not support "
              "multi-language sentences.' THE REASON: 'the other language isnt supported, "
              "WE CANT ORACLE IT, and we value SAFETY MORE THAN CONVENIENCE' — no scaffold, "
              "no certified gold, no reviewer who can read it, so nothing could tell us "
              "whether the reading was right, and an uncheckable reading that ACTS is what "
              "the seal pattern exists to refuse. The rule is about the SENTENCE, not the "
              "slot — and "
              "this case PROVES it: the English half is a complete, legal order and it still "
              "does not fire. The object NP still detects (id-0001-cs's convention); no act "
              "is produced; no mood either — `בוקר טוב` cannot be READ as phatic, the closed "
              "classes do not grow. ⚠ RULING NEEDED: a NAME in another script (a vm called "
              "אלפא) — #12 said names pass through the slot; does the sentence rule swallow "
              "that too?"),
    Seed("id-0001-cs", "identifiers", "תעצור את the vm at 10.0.0.5",
         ["the vm at 10.0.0.5"], [], {},
         noise="code-switch", pair_id="id-0001", outcome="reject",
         hint=("unsupported-language",
               "the sentence mixes languages — Gorgon reads English; the verb is not "
               "expressible and the sentence is not restatable without the operator"),
         note="RULED 08-22 (LEDGER #12, extended by #16 — the rule is now about the "
              "SENTENCE, not the slot): 'an automatic REJECT, since the verb is "
              "inexpressible' — Gorgon reads English by declaration; a foreign token in "
              "a licensing slot is REJECTED, never bounced with a question, never "
              "translated. The object NP still detects. The control for the declaration"),
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

