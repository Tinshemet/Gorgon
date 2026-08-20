"""seeds_v3.py — THE CLOSING STRATA (drafted 2026-08-20 night, operator certifies before use).

v3 = the LAST release (operator-scoped): learned patterns + the structure_map's open
holes, growing the corpus toward ~300. Twelve new strata. Every gold below follows the
certified conventions (grammar decides · a span is verbatim bytes · the exception is its
own object · a query produces · every malfunction predicate is testimony); where a
convention does not yet COVER the shape, the note names the RULING NEEDED and the draft
takes the conservative reading.

⇒⇒ TWO SCHEMA QUESTIONS RIDE WITH THIS FILE (the operator rules before the freeze):
   1. MANNER — "one at a time" is read (right-stopped) but the gold cannot SAY it.
      Proposal: `manner: Dict[int, Text]` on Seed/case, scored like triggers.
   2. STORE — learned-words cases need per-case mock store state (an encyclopedia/
      archive entry the reader may consult). Proposal: `store: List[dict]` on the case;
      the runner seeds a THROWAWAY Archive before read_case. Nothing routes until a
      person signs it — these mocks are ratified BY the operator certifying the case.
"""
from typing import Dict, List

from .seeds import Seed, Text  # the same shapes; v1/v2 seeds stay untouched

SEEDS_V3: List[Seed] = [
    # ══ identifiers — typed values the stores taught (ip/mac/serial mocks) ═══════════
    Seed("id-0001", "identifiers", "stop the vm at 10.0.0.5",
         ["the vm at 10.0.0.5"], ["stop"], {0: [0]},
         note="an identifier in a restrictive PP is part of the NP, exactly as "
              "'the vms on the lab network' is (ba-0001's convention)"),
    Seed("id-0002", "identifiers", "which vm has mac aa:bb:cc:dd:ee:ff?",
         ["which vm"], ["which vm has mac aa:bb:cc:dd:ee:ff"], {0: [0]}, queries=[0],
         note="RULING NEEDED: cs-0007 leaves the asked property unmarked; here the mac "
              "is a FILTER VALUE, not the produced set — same treatment drafted"),
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
         ["a vm with 4 cores and 8gb of ram"], ["create"], {0: [0]},
         note="RULING NEEDED: a creation SPEC — descriptor-with keeps the values inside "
              "the NP (ba-0001 family), or do spec values get value-role spans?"),
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
         note="RULING NEEDED: an alternative means ONE of them — the read records both "
              "members; whether gold needs an `alternation` flag (schema) or the "
              "attachment suffices is the operator's call. Drafted as plain members"),
    Seed("al-0002", "alternatives", "launch the web vm or the db vm, whichever is stopped",
         ["the web vm", "the db vm"], ["launch"], {0: [0, 1]},
         note="the whichever-clause CONDITIONS the choice — reads as the selector"),

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
         ["alpha"], ["is down"], {0: [0]}, reports=[0],
         evidence=["is down"],
         note="RULING NEEDED: the apposition 'the jumpbox' RENAMES alpha — the "
              "archive's `X is a Y` in another skin. Draft keeps it OUT of gold spans "
              "(a rename is a teaching, not a second thing); is that the ruling?"),
    Seed("ap-0002", "apposition", "stop the jumpbox, alpha",
         ["the jumpbox"], ["stop"], {0: [0]},
         note="imperative apposition — same question mirrored: `alpha` renames"),

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
         note="RULING NEEDED: the concession names a STATE of a bystander — drafted as "
              "testimony evidence on alpha; is a concession ever an excluded-role?"),
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
         note="SCHEMA QUESTION 1: the manner is read (right-stopped off the span) but "
              "gold cannot SAY it — proposal: manner={0: 'one at a time'}, scored like "
              "triggers. Drafted without until the operator rules"),
    Seed("mn-0002", "manner", "stop the lab vms all at once",
         ["the lab vms"], ["stop"], {0: [0]}),

    # ══ learned-words — the stores teach, the reader picks it up (SCHEMA QUESTION 2) ═
    Seed("lw-0001", "learned-words", "stop the grubnash",
         ["the grubnash"], ["stop"], {0: [0]},
         note="STORE: [{word: grubnash, kind: vm, ratified: true}] — with the entry the "
              "kindless row TYPES; without it the same sentence asks. The pair of "
              "readings is the measurement"),
    Seed("lw-0002", "learned-words", "spin up a fresh grubnash next to alpha",
         ["a fresh grubnash", "alpha"], ["spin up"], {0: [0, 1]},
         note="STORE as lw-0001 — the taught word in a creation frame"),
    Seed("lw-0003", "learned-words", "when you have a sec, stop the db vm",
         ["the db vm"], ["stop"], {0: [0]},
         note="STORE: [{phrase: 'when you have a sec', is: courtesy}] — a TAUGHT "
              "courtesy literal; retires the archive-debt pattern (two hand literals "
              "today). Courtesy marks nothing, exactly as certified"),

    # ══ self-address — 'you' is the agent; it must never become a thing ══════════════
    Seed("sa-0001", "self-address", "can you check the web vm?",
         ["the web vm"], ["can you check the web vm"], {0: [0]}, queries=[0],
         note="'you' is the agent ([[gorgon-you-is-the-agent]]): the read only FLAGS "
              "the pronoun — the gold check is that no 'you' row exists (a row would "
              "score hallucinated). Routing stays post-READ, as ruled"),
    Seed("sa-0002", "self-address", "good morning, stop the lab vms",
         ["the lab vms"], ["stop"], {0: [0]},
         note="a greeting marks nothing — flavour is one kind, not the genus"),
]
