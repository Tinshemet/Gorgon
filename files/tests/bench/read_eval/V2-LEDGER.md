# WHAT THE v1 SCHEMA CANNOT SAY — the version-bump ledger

Three golds v1 cannot express, each found while authoring or reviewing the first 53. Every
one is a DELIBERATE omission, recorded here rather than forced into the wrong shape — a wrong
key TEACHES the misreading it encodes. None of these blocks the v1 freeze; each is a schema
version bump with its own review pass when taken.

## 1 · THE EXCLUSIVE CHOICE (found authoring, 2026-08-18)

*"stop alpha or beta"* is ONE of the two. `attachments` can say BOTH and can say ONE, and
either key is wrong — the measured defect this would guard was `[stop beta, stop beta]`.
⇒ v2: an `exclusive: true` marker on an attachment whose objects are alternatives.
⇒ Until then: no `or`-choice sentences in the set. Left out, not mislabelled.

## 2 · CONDITIONS INSIDE A SPAN (operator, during review, 2026-08-18)

*"the snapshots older than a week on the backup store"* is one span, and the gold says
nothing about `{age: > 1 week}` or `{store: backup}` — the inside-the-bracket reading that
`conditions_from` performs and the whole MultiWOZ episode measured. v1 grades OUTER
boundaries and attachment only; condition extraction is tested nowhere in this eval.
⇒ v2: an optional `conditions` object on a span. Roughly doubles authoring + review cost —
  priced, not free, which is why it is not a quiet field now.
⇒ **THE SHARPEST MOTIVATOR (operator, 08-18, on cs-0007):** *"which vms are stopped?"* — the
  wh-query's ANSWER IS the set the condition defines — 'vms which stopped', the operator's
  own correction: the NOUN is the base set and the PREDICATE the filter ({kind: vm} +
  {status: stopped}), not a pre-labeled kind. v1 marks `[which vms]`
  and the filter vanishes, so a reader that captures `{status: stopped}` and one that reads a
  bare noun score the same — on a sentence whose entire point is the filter. The polar twin
  (cs-0006) flattens safely; the wh form is where item 2 bites hardest.
⇒ **AND THE ENSURE-VERB'S TARGET STATE IS THE SAME FAMILY (operator, 08-18, cc-0002):**
  *"make sure the lab network EXISTS"* — a hidden-achieve clause whose target predicate is
  unmarked, exactly as the wh-filter is. v2 form: `[the lab network] + {exists: true}`. The
  ACHIEVE/ENSURE label itself stays route territory; the STATE is readable structure.

## 4 · ACTION TRIGGERS — ✅ TAKEN as v1.2, same day

*"after/before are triggers for decomp technically."* Right: these words do not MODIFY a
sentence, they SPLIT it — *what to do* + *what starts it* — which is the seam's own model
(`temporal.py` reads WHAT STARTS IT; the door routes procedure/routine/trigger by exactly
this). v1 gold flattens the split: the act is marked, the world-clause verb is not, named
things get unattached spans. So a reader that captures the trigger and one that discards it
SCORE THE SAME — and the discarded qualifier is a measured live defect (*"stop every vm at
9pm"* runs NOW, [[gorgon-linguistic-sweep]]).
⇒ v2: a `trigger` field on an action — `{"action": 0, "trigger": {"start": …, "end": …}}` —
  the clause's offsets, nothing more. Scoring: trigger detected/attached like an object.
⇒ Same family as item 2 (both are qualifiers the gold cannot carry): conditions qualify the
  SPAN side, triggers qualify the ACTION side. Take them in one schema bump.

## 3 · ARGUMENT ROLES — ✅ TAKEN as v1.1, same day

*"put on the lab network every vm carrying the prod label"* — the vm is the THEME, the
network the DESTINATION, and the attachment says only that both belong to `put`.
⇒ ⚠ (historical — billed since v1.1) **A ROLE SWAP WAS INVISIBLE TO v1.0.** A reading that puts the network onto the vms scores
  identically to the correct one. That failure class is real (rung 3's
  `add_vm_to_network(web, lab)` vs `(lab, web)`) and unbilled until v2.
⇒ v2: roles on attachment members — `{"action": 0, "objects": [{"span": 1, "role": "theme"},
  {"span": 0, "role": "destination"}]}` — with a closed role vocabulary read from the
  manifest's own argument declarations, never a hand list.

## 5 · SEQUENCE BETWEEN INSTRUCTED ACTS — ⚠ PARTIALLY SUPERSEDED 08-19: an `after`-clause IS a trigger (the operator, on ba-0004-nt: "restart should happen AFTER the AI is done checking"); consistent with you-is-the-agent — the trigger fires on the agent's own completed act, a future ledger event. Bare `then` remains unmarked sequence, and the act->act `after` field stays the v2 idea for THAT

*"stop alpha. THEN launch beta."* · *"restart it AFTER YOU HAVE CHECKED the others"* — an
ordering between two acts the operator commanded. Not a trigger (no world condition starts
anything; YOU finish one act and begin the next), and v1.2 deliberately does not mark it — a
reader that reorders the acts scores the same as one that keeps the order.
⇒ v2: an `after` field on an action naming another ACTION index — order as a relation between
  acts, exactly how the writer's plans already carry it. Cheap; take with items 2+3.

## 6 · MANNER ON AN ACTION (operator, during review, 2026-08-18 — qual-0004)

*"stop the vms ONE AT A TIME"* — not a trigger (nothing gates when the act starts) and not
item-5 sequence between acts: it is ordering WITHIN one collective act — HOW the execution
unfolds. The remaining action-side qualifier after triggers were taken: WHETHER/WHEN is item
4 (built), what ORDER is item 5, HOW is this. v1 leaves it unmarked, so a reader that
serialises and one that blasts all vms at once score the same — and the constraint binds
THIS request only, never a rule ([[issue_map]] manner constraint, OPEN).
⇒ v2: a `manner` field on an action — the phrase's offsets, nothing more. Take with 2+5.

## 7 · THE EVIDENCE→OBJECT LINK (operator, during review, 2026-08-18 — diag-0001)

A diagnosis case marks the patient and the testimony and never says WHICH testimony is about
WHICH patient. Trivial at one object + one evidence; a two-patient report — "vm2
blue-screens and the dmz drops pings" — has two links, and crossed links score the same as
correct ones. Declared an omission in the schema docstring since v1.0; a ledger item now
because the operator felt the gold "produce nothing" — the missing production is this
relation, plus D1's eventual needs (the diagnosis flow starts from evidence BOUND to a thing).
⇒ v2: evidence spans join attachments with role "evidence" under a no-action entry, or a
  `about` field on an evidence span naming the object index. Decide when D1 is built —
  the diagnosis machinery's own shape should pick the encoding, not the eval's guess.

## 8 · TYPED IDENTIFIERS — ip / path / mac (operator, post-freeze, 2026-08-18) — COVERAGE, not schema

*"reading comprehension for ip address/path — non-standard text which requires encyclopedia
to understand."* The v1 schema can already SAY these (an identifier is an object span, often
role `value`); the frozen 59 just contain none. Two distinct future homes:
  · CLEAN cases — "add 192.168.1.5 to the allowlist": the identifier is a TYPED VALUE, not
    noise. Scored slot for the attribute-classes reader (ip/mac/serial — designed, unbuilt)
    + the Encyclopedia as its teacher. ~4 seeds, reviewed alone, re-frozen as v1.1 — the
    explicit-commit path. Deferred by the operator: "add them later since its a step up."
  · NOISE twins — pasted log lines / paths mid-command (`embedded-junk`), with the expansion
    phase as planned. The spec filed identifiers under noise; the operator's question exposed
    that only the PASTED form is noise — the typed-value form is clean capability.

## 9 · FUSED WORDS — a missing SPACE is a typo class of its own (operator, 2026-08-19)
*"does the typo also cover two words or more as one string? like hellothere? ... i do
wonder if we should cover it."* Not covered today: recognition is per-token, so `nowait`
never meets the two-word marker `no wait`. The cover is the same family — an unknown
token that SPLITS into two known closed-set words, accepted only where the construct
votes, same notice, same [[gorgon-typo-risk-ladder]] — but NO CERTIFIED CASE prices it.
⇒ v2.1: add **fused** as a fifth noise class (~10 twins, operator-certified), then build
against the measured cell. Never before.

## 10 · v3 — LEARNED PATTERNS: the stores teach the reader (operator, 2026-08-20)
*"add a case for v3, encyclopedia/archive/package, IE learned patterns — maybe we add a
moc for ip addresses and mac addresses and see if it can pick them up."* The v3 axis is
KNOWLEDGE-SOURCED reading: seeds where requests name typed identifiers ("stop the vm at
10.0.0.5" · "which vm has mac aa:bb:cc:dd:ee:ff"), against a MOCK attribute-class
declaration (ip/mac as [[gorgon-attribute-classes]]: TYPE, UNIT, OWNER, SOURCE — a class
with no reader turns an unknown-noun ASK into a capability BOUNCE). Measures whether a
taught pattern is PICKED UP by the reader without corpus. Joins identifiers v1.1
(ledger #8) and the typo-risk ladder's store-sourced candidates — same axis: what the
lab has LEARNED informs the read, never grants authority.
⇒ SCOPED BY THE OPERATOR 08-20: v3 comes AFTER the current table is finished, and it is
planned as THE LAST release — grow toward **~300 sentences with a few dozen patterns**,
a comfortable future corpus. v3 closes the READ saga.

## 11 · v3 SCOPE, SETTLED 08-20 NIGHT — what closes READ
**55 seed drafts** in `seeds_v3.py`, **22 strata** — the operator's second sweep
("what other families might we encounter?") added ten: ordinals · fallback (act-anaphora,
'if that fails') · pairwise (different value per conjunct — the one-patient rule itself
forced the two-acts draft) · negated-query · schedules (recurrence triggers, the clock's
sibling slot) · superlatives (attr-class TYPE licenses the ordering) · naming-lists ·
quoted-values ('do not touch' — quotes are structural) · audit (events.log questions,
NO lab spans) · capability (can-you generic vs polite order — the measured 0/14 family).
DEFERRED with reasons: preference (route's), comparative-reference (value-copy), undo
(cross-turn). All 55 build+validate. The operator certifies, then noise twins, then
freeze — ~55 clean + twins + the 148 ≈ the ~300 target.
⇒ TWO SCHEMA RULINGS BEFORE THE FREEZE:
  1. MANNER — read but unsayable in gold. Proposal: `manner: {action: text}`, scored
     like triggers.
  2. STORE — learned-words cases carry mock store state. Proposal: `store: [entries]`
     per case; the runner seeds a THROWAWAY archive before read_case; certifying the
     case IS ratifying the mock.
⇒ THREE SCOPE DECISIONS (operator): embedded-junk + code-switch noise — build as v3
twins or declare out of scope in the freeze note · noise twins over the new seeds
(mechanical) · the READ closing document at the freeze.
⇒ EXPLICITLY NOT v3 (standing rulings): cross-turn (LAST) · A2 model swap · N1 wiring.
