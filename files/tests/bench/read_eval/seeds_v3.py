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
    # ⇒ 08-23, ATTRIBUTES ARE LEAVES — RULED: A SELECTING VALUE IS A LEAF TOO (schema v2.6,
    #   role `selector`). `the vm at 10.0.0.5` is `the vm` + `10.0.0.5`, exactly as the
    #   assigned `a vm` + `4 cores`; the role says it PICKS the thing rather than being given
    #   to it. ba-0001's convention stands for THINGS: `the vms on the lab network` keeps `the
    #   lab network` inside because a network is a thing the lab keeps, not a leaf value.
    Seed("id-0001", "identifiers", "stop the vm at 10.0.0.5",
         ["the vm", "10.0.0.5"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "selector", "kind": "identifier"}]},
         note="RULED 08-23: a selecting identifier is its own span (role selector); "
              "`at` is the preposition that makes it a selector, context not value"),
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
         ["the vm", "7f3k-2210"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "selector", "kind": "identifier"}]},
         note="RULED 08-23: selector leaf; `with serial` is the attribute word, context"),
    Seed("id-0005", "identifiers", "stop the vm at 8g:77q",
         ["the vm", "8g:77q"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "selector", "kind": "identifier"}]},
         note="RULED 08-23 (ledger #20): '8g:77q is an attribute the same way an ip is, so it "
              "should be treated the same' — a token in the selector slot is an attribute "
              "value, its own span, whether or not a class declares its shape; the OWNER "
              "decides: an ip is accepted into `where`, this is refused and the operator is "
              "asked which attribute it is. (#17b's 'stays in the phrase' clause overturned; "
              "the old downstream was a capability BOUNCE, now an ASK.)"),

    # ══ units — quantity + unit paired to a declared attribute ═══════════════════════
    Seed("un-0001", "units", "give the db vm 16gb of memory",
         ["the db vm", "16gb"], ["give"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="the unit names the attribute (gb -> memory_mb through the class); the "
              "value span is the quantity+unit token, bare — coord-0005's convention"),
    Seed("un-0002", "units", "create a vm with 4 cores and 8gb of ram",
         ["a vm", "4 cores", "8gb"], ["create"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "value"}]},
         note="RULED 08-21: 'each value should be scored indpendently' — spec values "
              "CARVED OUT: patient is the minted kind, every literal value its own "
              "value-role span. 08-23 (ATTRIBUTES ARE LEAVES): the value is the "
              "NUMBER + UNIT the owner scrutinises — `8gb`, as un-0001's `16gb`; "
              "`of ram` is the attribute word, context not value. (Naming specs are "
              "leaves too now — see nl-0001)"),
    Seed("un-0003", "units", "set the cpu of the web vm to 4 cores",
         ["the web vm", "4 cores"], ["set"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="partitive-of over an ATTRIBUTE — `the cpu of X` names X's attribute, "
              "never a second thing"),
    Seed("un-0004", "units", "how much memory does alpha have?",
         ["memory", "alpha"], ["how much memory does alpha have"],
         {0: [{"span": 0, "role": "value"}, {"span": 1, "role": "patient"}]}, queries=[0],
         note="RULED 08-24 (ledger #21): the have-frame is the genitive asked — owner "
              "patient, leaf VALUE (id-0002's precedent: the asked predicate is a value, "
              "never a selector — a selector PICKS the thing, here the thing is named). "
              "Asked-ness is flagged by the query action + the reading's `predicate`, "
              "nothing new. The AMOUNT is the produced answer, unspanned."),

    # ══ possessive — the genitive is a reference, and the reference is the target ════
    Seed("po-0001", "possessive", "delete alpha's snapshots",
         ["alpha", "snapshots"], ["delete"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="RULED 08-23 (ledger #19): 'X's snapshot' — snapshot is a VALUE, its own "
              "span; X is its owner, the patient. The genitive is owner + leaf, like "
              "`the cpu of X` (un-0003) — never one NP. (Earlier gold kept the whole NP "
              "and matched the reader; both were wrong.)"),
    Seed("po-0002", "possessive", "list the web vm's snapshots",
         ["the web vm", "snapshots"], ["list"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]}),
    Seed("po-0003", "possessive", "snapshot beta's disk",
         ["beta", "disk"], ["snapshot"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]}),
    Seed("po-0004", "possessive", "how many snapshots does alpha have?",
         ["snapshots", "alpha"], ["how many snapshots does alpha have"],
         {0: [{"span": 0, "role": "value"}, {"span": 1, "role": "patient"}]}, queries=[0],
         note="RULED 08-24 (ledger #21): `alpha's snapshots` (#19) worn as a question — "
              "owner patient, leaf VALUE; the COUNT is produced, never spanned"),

    # ══ alternatives — or-coordination: the read records BOTH, choosing is route's ═══
    Seed("al-0001", "alternatives", "stop alpha or beta",
         ["alpha", "beta"], ["stop"], {0: [0, 1]},
         triggers={0: ("or", "coordination", [])},
         note="RULED 08-21: 'score both — the or is scored like a trigger since "
              "boolean operators are triggers; the decision is at RESOLVE, not ROUTE'. "
              "No alternation flag: both members score, the operator rides the trigger "
              "channel, the world satisfies one member at resolve"),
    Seed("al-0002", "alternatives", "launch the web vm or the db vm, whichever is stopped",
         ["the web vm", "the db vm"], ["launch"], {0: [0, 1]},
         triggers={0: ("whichever is stopped", "conditional", [("whichever", "selector", None, None), ("stopped", "selector", "status", None)])},
         note="the whichever-clause IS the condition — the trigger channel carries it "
              "(the al-0001 ruling unifies the family); choosing is RESOLVE's"),

    # ══ reduced-relative — the relativizer elided, the filter remains ════════════════
    Seed("rr-0001", "reduced-relative", "stop the vms running on lab",
         ["the vms", "running", "lab"], ["stop"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "selector", "kind": "status"},
              {"span": 2, "role": "selector", "kind": "entity"}]},
         note="RULED 08-25 (operator, mid-grading — reject of an accidental accept): a "
              "reduced relative DECOMPOSES, it is not one blob. 'the vms' is the patient; "
              "'running' is the STATUS filter (a status value that selects — its own span, "
              "vector state=status:running); 'lab' from 'on lab' is the network as a "
              "DESTINATION. Supersedes the 'keep the NP whole' reading. "
              "⇒ 'running' is a GROUNDED selector, not opaque: status is a declared OBSERVED "
              "attribute (attr_values running/stopped; the `alive`/guest_ping fact ANSWERS it, "
              "three-valued — decision 6). READ spans it and marks the attribute; RESOLVE "
              "satisfies it from the Active Library, else probes into the findings ledger "
              "(the book keeper). The dual sourcing is RESOLVE's, downstream of this gold."),
    Seed("rr-0002", "reduced-relative", "delete the snapshots taken last week",
         ["the snapshots", "last week"], ["delete"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "selector", "kind": "temporal"}]},
         note="RULED 08-25 (operator, revised): 'the snapshots' patient; 'taken' is "
              "OWNERSHIP (the creation/possession participle, its own span); 'last week' is "
              "a temporal ANCHOR, not a selector — the reference the age is pinned to"),
    Seed("rr-0003", "reduced-relative", "restart the vms stuck at boot",
         ["the vms", "stuck at boot"], ["restart"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "selector", "kind": "status"}]},
         note="RULED 08-25 (operator, revised): 'the vms' patient; 'stuck at boot' is a "
              "CONDITION/status kept as ONE symptom span — role CONDITIONAL, not selector"),

    # ══ apposition — a rename in flight, the archive's own X-is-Y ════════════════════
    Seed("ap-0001", "apposition", "alpha, the jumpbox, is down",
         ["alpha", "the jumpbox"], ["is down"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "reference", "refers": "alpha"},
              {"span": 2, "role": "evidence"}]},
         reports=[0], evidence=["is down"],
         note="RULED 08-21: 'the renames are scanned as well but are treated as "
              "refernces' — the apposition IS expressed, bound to the SAME referent "
              "with a reference role. One patient; the reader is scored on the "
              "equivalence the apposition-as-teaching harvest depends on"),
    Seed("ap-0002", "apposition", "stop the jumpbox, alpha",
         ["the jumpbox", "alpha"], ["stop"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "reference", "refers": "the jumpbox"}]},
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

    # ══ purpose — the reason GIVEN with the act: diagnosis, reversed ═════════════════
    # ⇒ OPERATOR 08-24, closing the one hole the 08-16 sweep named: "purpose is
    #   constructed from 2 things which are already implemented in a 'sibling',
    #   diagnosis, but on the other way around: we have a request and evidence/rule …
    #   this a ledger entry, with a request attached, it actually a good way to teach
    #   ROUTE and RESOLVE, human makes decision and gives evidence for it … 'why is vm3
    #   stopped?' -> 'vm3 was stopped due to it being idle, reverse the decision?'"
    #   The to-clause is EVIDENCE by the certified 08-22 convention (cause's mirror),
    #   carried by the act — the future why-answer's source. Cross-turn use is ROUTE's.
    Seed("pu-0001", "purpose", "stop the idle vms to free memory",
         ["the idle vms"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["to free memory"],
         note="the operator's own sentence — the decision and its reason in one breath; "
              "dropping the to-clause is the silent-qualifier defect (08-16), the act "
              "must CARRY it"),
    Seed("pu-0002", "purpose", "snapshot the db vm so we can roll back",
         ["the db vm"], ["snapshot"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["so we can roll back"],
         note="`so (that)` — the second purpose marker; the reason names a FUTURE use, "
              "not a present symptom, which is exactly diagnosis reversed"),
    Seed("pu-0003", "purpose", "delete the old snapshots to save space",
         ["the old snapshots"], ["delete"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "evidence"}]},
         evidence=["to save space"],
         note="a DESTRUCTIVE act with its justification attached — the ledger entry the "
              "operator described, written at request time"),

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
         ["every vm", "over", "6gb"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "conditional"},
              {"span": 2, "role": "selector", "kind": "magnitude"}]},
         note="RULED 08-25 (operator): decompose — 'every vm' patient, 'over' CONDITIONAL "
              "(the comparator, its own span now, not just context), '6gb' the selector it "
              "governs. Supersedes the 08-23 comparator-as-context reading."),
    Seed("mg-0002", "magnitude", "list the vms with more than 2 cores",
         ["the vms", "more than", "2 cores"], ["list"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "conditional"},
              {"span": 2, "role": "selector", "kind": "magnitude"}]},
         note="RULED 08-25: 'the vms' patient, 'more than' CONDITIONAL, '2 cores' selector"),
    Seed("mg-0003", "magnitude", "delete the snapshots older than a month",
         ["the snapshots", "older than", "a month"], ["delete"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "conditional"},
              {"span": 2, "role": "anchor", "kind": "temporal"}]},
         note="RULED 08-25 (operator): 'the snapshots' patient; 'older than' together is the "
              "CONDITIONAL (the whole comparator, mg-0001/0002 shape); 'a month' the temporal "
              "ANCHOR it measures against. age > a month is the world's to compute at RESOLVE"),

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
         ["the db vm", "you"], ["stop"],
         {0: [{"span": 0, "role": "patient"}]}, frame=[("you", "meta")],
         pacing={0: "when you have a sec"},
         mood=[("deference", "when you have a sec")],
         note="RULED 08-25 (operator): NOT evidence — a META-CONTROL of PACING. 'when you "
              "have a sec' carries hidden info (the user believes Gorgon is BUSY) + a defer "
              "directive ('do it when free'), an order-of-operations control, not a lab "
              "command. Rides the stop as the `pacing` channel; 'you' is the SELF-reference "
              "the condition hangs on (the anchor); fold.priority=deferrable is the signal "
              "ROUTE reads. Deference mood stays as the tone. Contrast sa-0002 (pure fluff).",
         store=[{"phrase": "when you have a sec", "is": "courtesy", "ratified": True},
                {"phrase": "in a sec", "is": "duration", "ratified": True},
                {"word": "tomato", "kind": "fruit", "ratified": True}]),

    # ══ self-address — 'you' is the agent; it must never become a thing ══════════════
    Seed("sa-0001", "self-address", "can you check the web vm?",
         ["you", "the web vm"], ["check"],
         {0: [{"span": 1, "role": "patient"}]}, queries=[0], frame=[("you", "meta")],
         note="RULED 08-26 (operator): span 'you' (frame meta) and 'check' (the queried "
              "verb — a capability query, like cap-0001/au-0001); 'the web vm' the patient"),
    Seed("sa-0002", "self-address", "good morning, stop the lab vms",
         ["the lab vms"], ["stop"],
         {0: [{"span": 0, "role": "patient"}]},
         mood=[("phatic", "good morning")],
         note="RULED 08-25 (operator): 'good morning' is pure FLUFF — a phatic mood and "
              "NOTHING else. NOT evidence (it carries no info about the system). Contrast "
              "lw-0003, where 'when you have a sec' DOES carry info (agent is busy)."),

    # ══ ordinals — selection by ORDER, a closed class nothing reads ══════════════════
    Seed("or-0001", "ordinals", "stop the first vm",
         ["vm", "first"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "ordinal"}]},
         note="RULED 08-21: 'we keep it — again resolve issue'. The ordinal stays "
              "INSIDE the span: one selector NP, verbatim; the attr-class TYPE "
              "licenses the ordering axis and the world orders and picks at RESOLVE"),
    Seed("or-0002", "ordinals", "delete the last snapshot",
         ["snapshot", "last"], ["delete"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "ordinal"}]}),
    Seed("or-0003", "ordinals", "restart the second one",
         ["one", "second"], ["restart"],
         {0: [{"span": 0, "role": "reference"}, {"span": 1, "role": "ordinal"}]}),

    # ══ fallback — act-anaphora: `that` names the ACT, failure-contingent order ══════
    Seed("fb-0001", "fallback", "stop alpha, and if that fails, kill it",
         ["alpha", "that", "it"], ["stop", "kill"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "reference", "refers": "stop"}],
          1: [{"span": 2, "role": "reference", "refers": "alpha"}]},
         triggers={1: ("if that fails", "conditional", [("that", "reference", None, "stop"), ("fails", "selector", "status", None)])},
         note="RULED 08-25 (operator): TWO references of different kinds — 'that' references "
              "the ACTION (stopping alpha), recorded on action 0 (stop) it points back to; "
              "'it' references the OBJECT alpha, the kill's target. Object-reference vs "
              "action-reference, same role. Supersedes the no-span bare-pronoun rule here."),
    Seed("fb-0002", "fallback", "launch the db vm, and if that doesn't work, restart the host",
         ["the db vm", "the host", "that"], ["launch", "restart"],
         {0: [{"span": 0, "role": "patient"}],
          1: [{"span": 1, "role": "patient"},
              {"span": 2, "role": "reference", "refers": "launch"}]},
         triggers={1: ("if that doesn't work", "conditional", [("that", "reference", None, "launch"), ("doesn't work", "selector", "status", None)])}),

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
         ["which vms", "not running"], ["which vms are not running"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "selector", "kind": "status"}]},
         queries=[0],
         note="RULED 08-25 (operator): decompose the QUERY — 'which vms' the patient (the "
              "sought set), 'not running' the status SELECTOR (status != running). The asked "
              "PROPERTY is now a span, not dropped; the answer-shape (members) stays in the "
              "v4 vector. Supersedes 'the asked property stays unmarked'."),
    Seed("nq-0002", "negated-query", "is alpha not responding?",
         ["alpha", "not responding"], ["is alpha not responding"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "selector", "kind": "status"}]},
         queries=[0],
         note="RULED 08-25 (operator): 'alpha' patient; 'not responding' is STATUS, a status "
              "SELECTOR (same shape as nq-0001 'not running') — not a symptom/conditional"),

    # ══ schedules — recurrence as a standing trigger (temporal.RECURRENCE, offsetless
    #    today exactly as the clock was) ═══════════════════════════════════════════════
    Seed("sch-0001", "schedules", "snapshot the db vm every night",
         ["the db vm"], ["snapshot"], {0: [0]},
         triggers={0: ("every night", "temporal", [("night", "anchor", "temporal", None)])},
         note="the recurrence is the trigger — clock_tail's sibling, RECURRENCE arm; "
              "today it has no offset reader, so this seed holds the slot open exactly "
              "as qual-0005 held the clock's"),
    Seed("sch-0002", "schedules", "check the lab network every 2 hours",
         ["the lab network"], ["check"], {0: [0]},
         triggers={0: ("every 2 hours", "temporal", [("2 hours", "anchor", "temporal", None)])}),

    # ══ superlatives — an ORDERING over an attribute (attr classes license it) ═══════
    Seed("sup-0001", "superlatives", "stop the biggest vm",
         ["vm", "biggest"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "ordinal"}]},
         note="RULED 08-25 (operator): a superlative is an ORDINAL — rank the set, pick one "
              "(same operation as first/last, ranking key is an ATTRIBUTE not a position; "
              "vector adj:sup carries the key). 'biggest' ordinal, 'vm' patient. NOT a "
              "selector (a selector filters, may be many; an ordinal produces a singular)."),
    Seed("sup-0002", "superlatives", "delete the oldest snapshot of alpha",
         ["alpha", "snapshot", "oldest"], ["delete"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "ordinal"}]},
         note="RULED 08-24 (ledger #23): 'delete is the verb, oldest is an attribute/"
              "adjective, snapshot is a value inside of alpha and alpha is the patient' — "
              "the of-genitive is #19's other spelling, and the leaf span is the BARE "
              "leaf; `oldest` is a fact about its own word (vector class adj:sup, no "
              "declared axis — RESOLVE asks the world which attribute orders it). "
              "sup-0001 is untouched: a superlative on a THING stays in the thing's "
              "span (08-21, or-0001)."),

    # ══ naming-lists — one act MINTING several names ═════════════════════════════════
    # ⇒ 08-23, ATTRIBUTES ARE LEAVES — RULED: A NAME IS A LEAF. A name assigned at creation
    #   is a value of its own (role value, attribute name), scrutinised by the owner; a name
    #   that REFERS (`stop alpha`) stays in its phrase. Read together with 08-21's "a naming
    #   spec is one generative unit": a LITERAL name is a leaf per name (a · b · c); a
    #   GENERATOR spec is itself the leaf — ONE value span (`1-5`, `after musicians`) the
    #   owner runs. The names it mints still never exist as bytes.
    Seed("nl-0001", "naming-lists", "create three vms named a, b and c",
         ["three vms", ("a", 3), "b", ("c", 2)], ["create"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "value"}, {"span": 3, "role": "value"}]},
         note="RULED 08-21: naming specs are often GENERATORS. RULED 08-23: a name is a "
              "LEAF — three literal names, three value spans, the patient is the minted "
              "kind alone"),
    Seed("nl-0002", "naming-lists", "create two networks called front and back",
         ["two networks", "front", "back"], ["create"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "value"}]}),
    Seed("nl-0003", "naming-lists", "create 5 vms named 1-5",
         ["5 vms", "1-5"], ["create"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
         note="the operator's own sentence — a RANGE generator: no five name spans "
              "exist; the SPEC is the leaf, one value span, and the generator runs "
              "where the owner runs it"),
    Seed("nl-0004", "naming-lists",
         "create 3 vms named after musicians and a network called the stadium "
         "and add those vms to it",
         ["3 vms", "after musicians", "a network", "the stadium", "those vms", "it"],
         ["create", "add"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"},
              {"span": 2, "role": "patient"}, {"span": 3, "role": "value"}],
          1: [{"span": 4, "role": "reference", "refers": "3 vms"},
              {"span": 5, "role": "reference", "refers": "a network"}]},
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
         ["you"], ["run"],
         {}, queries=[0], frame=[("you", "meta")],
         note="coverage_map ⚠⚠: events.log is the arbiter and no sentence reaches it. "
              "NO object spans — the question is about the agent's ledger, not a lab "
              "thing; any lab op emitted from it scores hallucinated. Pairs with "
              "self-address: 'you' is the agent"),
    Seed("au-0002", "audit", "what changed in the lab today?",
         ["changed", "the lab", "today"], ["what changed in the lab today"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "selector", "kind": "entity"},
              {"span": 2, "role": "selector", "kind": "temporal"}]},
         queries=[0],
         note="RULED 08-25 (operator): decompose the query — 'changed' is the PATIENT (what "
              "is being asked about; the verb spans it, no noun to grab), 'the lab' the "
              "SELECTOR (changes related to the lab), 'today' the temporal ANCHOR"),

    # ══ capability — CAN-you generic vs CAN-you polite order ═════════════════════════
    Seed("cap-0001", "capability", "can you create networks?",
         ["you", "networks"], ["create"],
         {0: [{"span": 1, "role": "patient"}]}, queries=[0], frame=[("you", "meta")],
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
         ["the lab network", "the new vms"], ["prefer"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "beneficiary"}]},
         meta_controls=[0],
         note="RULED 08-25 (operator): a preference is a META-CONTROL expressing an ORDERING "
              "('prefer X' = 'try X first') — soft/defeasible, ROUTE weighs it. 'prefer' the "
              "meta-control act; 'the lab network' patient (the preferred thing), 'the new "
              "vms' beneficiary (the for-X scope, cap-0002's convention). Was one rule blob."),
    Seed("pr-0002", "preference", "i'd rather use the smaller profile",
         ["i", "profile", "smaller"], ["use"],
         {0: [{"span": 1, "role": "patient"},
              {"span": 2, "role": "selector", "kind": "magnitude"}]},
         frame=[("i", "testimony")],
         meta_controls=[0],
         note="RULED 08-25 (operator): preference = META-CONTROL ordering ('i'd rather' = "
              "try-first). 'i' operator, 'use' the meta-control act, 'profile' patient; "
              "'smaller' is a SELECTOR — a COMPARATIVE (-er) is relational (smaller than "
              "what?), it FILTERS like 'older than a month', unlike a superlative which is "
              "an ordinal that ranks-and-picks (vector adj:cmp vs adj:sup)."),

    # ══ hand-authored noise twins — embedded-junk + code-switch (RULED 08-21: build) ══
    # Mechanical noisers cannot invent junk placement or another language, so these
    # twins are authored by hand and certified like any case. The slot decides junk;
    # the closed classes do not grow.
    Seed("po-0001-ej", "possessive", "delete adsfk alpha's snapshots",
         ["alpha", "snapshots"], ["delete"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "value"}]},
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
    Seed("nt-0001", "null-turn", "ok, got it", [], [], {}, outcome="acknowledge",
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
         {}, evidence=["please!!"], outcome="none",
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
    Seed("nt-0007", "null-turn", "i'll stop alpha myself",
         ["i'll", "stop alpha"], [],
         {}, outcome="testimony", frame=[("i'll", "testimony")],
         evidence=["stop alpha"],
         note="RULED 08-25 (operator): decompose the testimony — \"i'll\" the OPERATOR, "
              "'stop' a testimony act (the user will do it themselves, Gorgon does NOT), "
              "'alpha' the patient. Was one evidence blob; now decomposed. The act is the "
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
    Seed("nt-0009", "turn-dependent", "stop neither alpha nor beta",
         ["neither", "alpha", "beta"], ["stop"],
         {0: [{"span": 0, "role": "quantifier"}, {"span": 1, "role": "excluded"},
              {"span": 2, "role": "excluded"}]},
         hint=("prohibition", "the rule is: do NOT stop alpha and beta"),
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
    Seed("td-0004", "turn-dependent", "yeah", [], [], {}, outcome="none",
         evidence=["yeah"], mood=[("affirmation", "yeah")],
         hint=("answer-shaped", "'yeah' with nothing pending — bland (no pretext). With a "
                                "confirmation in context it is BOTH acknowledge AND "
                                "affirmation (operator 08-25); RESOLVE decides on the pretext"),
         note="THE CONTROL for td-0003: same bytes, NO expectation supplied, and the "
              "reading changes. This pair is the whole argument for the loop — a reader "
              "that answers the same for both is guessing on one of them"),
    Seed("td-0005", "turn-dependent", "check", [], ["check"], {}, outcome="context-needed",
         hint=("possible-reference", "a lone 'check' could be a reference to a previous "
                                     "response — or an order to check something unnamed"),
         note="THE OPERATOR'S OWN EXAMPLE (08-22): 'an unrelated check is processed as if "
              "it is important, ALL are — its processed under context-needed and will be "
              "resolved at ROUTE to determine if its a reference, or not. The READ is "
              "blind here but it is given a hint based on rules.' Nothing is dropped"),
    Seed("td-0006", "turn-dependent", "hey, check", [], ["check"], {}, outcome="context-needed",
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
    Seed("td-0007", "turn-dependent", "stop that", ["that"], ["stop"],
         {0: [{"span": 0, "role": "reference"}]},
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
    Seed("td-0009", "turn-dependent", "lets continue", ["lets"], ["continue"],
         {}, meta_controls=[0], frame=[("lets", "meta")],
         outcome="context-needed",
         hint=("possible-reference", "'lets continue' is a META-CONTROL of session flow — "
                                     "resume what was under way; 'continue' names no lab act "
                                     "and its referent is a prior turn"),
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
         ["you", "alpha"], ["stopping"],
         {0: [{"span": 1, "role": "patient"}]}, frame=[("you", "meta")],
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
         ["alpha", "were down"], ["were down"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "value", "kind": "status"}]},
         note="RULED 08-25 (operator): 'were down' is a STATUS, same as 'down' in 'is vm2 "
              "down?' (legal, down=stopped) — grammatically similar, just add 'were' to the "
              "span. 'alpha' patient, 'were down' the status SELECTOR (vector state="
              "status=stopped already marks it); the achieve step is derived downstream."),

    # ══ tense-person — the verb form decides order vs report ═════════════════════════
    Seed("tp-0001", "tense-person", "i stopped alpha",
         ["i", "stopped alpha"], [],
         {}, outcome="testimony", frame=[("i", "testimony")],
         evidence=["stopped alpha"],
         note="RULED 08-26 (operator): a testimony is EVIDENCE, not an action — the user "
              "REPORTS their own act, the AI records it, never runs it. 'i' frame(testimony), "
              "'stopped alpha' evidence. The `testimony` action kind is RETIRED."),
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
         ["i", "stopped alpha", "beta"], ["launch"],
         {0: [{"span": 2, "role": "patient"}]}, frame=[("i", "testimony")],
         evidence=["stopped alpha"],
         note="RULED 08-25: testimony ('i' operator + 'stopped' testimony act + 'alpha' "
              "patient) AND a real order ('launch beta') in one sentence — kept apart"),

    # ══ deferred-time — one-shot time and duration (the linguistic sweep's own finding) ═
    #   `schedules` covers recurrence; "stop every vm at 9pm" RUNS NOW today. A discarded
    #   time qualifier is a wrong CHOICE, not padding.
    Seed("dt-0001", "deferred-time", "stop every vm at 9pm",
         ["every vm"], ["stop"], {0: [0]}, triggers={0: ("at 9pm", "temporal", [("9pm", "anchor", "temporal", None)])},
         note="one-shot CLOCK — the trigger channel carries it (like 'every night')"),
    Seed("dt-0002", "deferred-time", "snapshot alpha in 10 minutes",
         ["alpha"], ["snapshot"], {0: [0]}, triggers={0: ("in 10 minutes", "temporal", [("10 minutes", "anchor", "temporal", None)])},
         note="relative delay — a trigger on the clock from now"),
    Seed("dt-0003", "deferred-time", "launch beta tomorrow morning",
         ["beta"], ["launch"], {0: [0]}, triggers={0: ("tomorrow morning", "temporal", [("tomorrow morning", "anchor", "temporal", None)])},
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
         ["alpha"], ["stop"], {0: [0]}, triggers={0: ("unless it is the jumpbox", "conditional", [("it", "reference", None, "alpha"), ("the jumpbox", "selector", "entity", None)])},
         note="negative condition — a trigger whose polarity is inverted; the act is the "
              "same. 'the jumpbox' is a predicate nominal, not an object (apposition's kin)"),
    Seed("cb-0002", "conditional-branches",
         "if alpha is up, snapshot it, otherwise launch it",
         ["alpha", ("it", 1), ("it", 2)], ["snapshot", "launch"],
         {0: [{"span": 0, "role": "patient"},
              {"span": 1, "role": "reference", "refers": "alpha"}],
          1: [{"span": 0, "role": "patient"},
              {"span": 2, "role": "reference", "refers": "alpha"}]},
         triggers={0: ("if alpha is up", "conditional", [("alpha", "patient", None, None), ("up", "selector", "status", None)]), 1: ("otherwise", "fallback", [])},
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
         ["alpha", "it", "that"], ["restart", "tell me"],
         {0: [{"span": 1, "role": "reference", "refers": "alpha"}],
          1: [{"span": 2, "role": "reference", "refers": "restart"}]},
         triggers={0: ("if alpha is down", "conditional", [("alpha", "patient", None, None), ("down", "selector", "status", None)]), 1: ("if that doesn't help", "conditional", [("that", "reference", None, "restart"), ("doesn't help", "selector", "status", None)])}, queries=[1],
         note="a condition AND a fallback on one referent, the fallback a QUERY (report "
              "back) — the chain's shape, certified at READ"),

    # ══ partitives — how many of the set, and a number that is a name ════════════════
    Seed("pt-0001", "partitives", "stop two of the lab vms",
         ["vms", "lab", "two of the"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "destination"},
              {"span": 2, "role": "quantifier"}]},
         note="numeric partitive — the spec stays WHOLE (naming-spec ruling: a generator, "
              "not a list); which two is RESOLVE's"),
    Seed("pt-0002", "partitives", "stop all but two of the vms",
         ["vms", "all but two of"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "quantifier"}]},
         note="count carve-out with NO named exclusion — whole span. RULING NEEDED: the "
              "excluded role needs a thing; a COUNT cannot be excluded, so the span stays "
              "one (vs 'every vm except db', two spans)"),
    Seed("pt-0003", "partitives", "stop any vm", ["vm", "any"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "quantifier"}]},
         note="'any' — one, unspecified; a scope word the UNIVERSAL class holds but whose "
              "reading is ONE, not ALL. RULING NEEDED: any = one of (RESOLVE picks)"),
    Seed("pt-0004", "partitives", "stop half of the vms", ["vms", "half of"], ["stop"],
         {0: [{"span": 0, "role": "patient"}, {"span": 1, "role": "quantifier"}]},
         note="RULED 08-25: 'vms' patient, 'half of' quantifier"),
    Seed("pt-0005", "partitives", "stop vm 3", ["vm 3"], ["stop"], {0: [0]},
         note="a NUMBER AS A NAME — 'vm 3' is one named thing; contrast pt-0006"),
    Seed("pt-0006", "partitives", "stop 3 vms", ["3 vms"], ["stop"], {0: [0]},
         note="a number as a COUNT — the position decides (enumerator before the noun)"),

    Seed("sa-0002-cs", "self-address", "בוקר טוב, stop the lab vms",
         ["the lab vms"], ["stop"], {0: [0]},
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
         ["the vm", "10.0.0.5"], [], {},
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
    # ⇒ schema v3.0 (operator 08-24): every case carries its COMPUTED per-word vector —
    #   the third gold layer, certified by exception in review ([[vectors.py]])
    from .vectors import attach
    attach(cases)
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

