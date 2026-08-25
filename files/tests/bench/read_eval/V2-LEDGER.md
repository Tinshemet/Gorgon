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
     ✅ RULED 08-21 (operator): *"a way to control how the procedure acts … not a meta
     control but more about how the pipeline is handled — so it should be expressed."*
     TAKEN — manner joins the gold as the act's second CONTROL channel beside triggers
     (trigger = when-control, manner = how-execution-is-handled: pacing, ordering,
     concurrency). NOT meta-control: confirmation/verification/authority stay the
     gates' territory. Per-act `manner: {action: text}`, verbatim span, scored like
     triggers. On a plural patient the constraint lands on the DERIVED LOOP at
     lowering — gold records it on the act; the loop inherits it as execution policy.
     It never decorates the noun, never grants.
  2. STORE — learned-words cases carry mock store state. Proposal: `store: [entries]`
     per case; the runner seeds a THROWAWAY archive before read_case; certifying the
     case IS ratifying the mock.
     ✅ RULED 08-21 (operator): *"yes for the test, we give not just ip/mac/etc — we
     create a few entries for a bunch of stuff, as well as redherrings, and see how
     the ai choose."* TAKEN, and STRENGTHENED: each mock is a POPULATED store —
     several entries across kinds PLUS red herrings. The eval measures SELECTION
     under distraction, not pickup of the only entry present. Certification ratifies
     the whole mock, decoys included.
     ⇒ EXTENDED SAME DAY (operator): FOUR decoy classes — (1) near-miss same kind ·
     (2) unrelated but SOUNDS similar · (3) name overlap, different meaning ·
     (4) completely unrelated filler (*"like a tomato"*). And THREE measured
     capacities: **correctness** (precision — exactly the right entry) ·
     **relevancy** (the pick bears on the ask) · **inference** (their composition —
     *"sometimes you need to infere what is actually being asked of you"*: the
     educated guess when the ask under-determines). The axes are independent — a
     correct call can be irrelevant, a relevant call incorrect. Build-time proposal:
     score misses BY THE CLASS of decoy that captured the model, so each failure
     names its axis; an inference sub-stratum carries deliberately under-specified
     asks. BOUNDARY (standing): inference resolves the READ and may feed a question;
     an inferred read deciding a write still climbs the confirmation ladder —
     inference never grants.
  3. PAIRWISE SHAPE (added to the docket by the validator itself) — ✅ RULED 08-21
     (operator): *"sounds good — again make it cover not just one case but a few."*
     The two-acts draft is BLESSED: one verb, one act per conjunct pair, all acts
     sharing the verb's offsets — the elided verb is real, just unspoken; the
     one-patient rule stands untouched. COVERAGE WIDENED: the stratum grows beyond
     pw-0001/0002 to a few — three-conjunct chains, mixed flavours (value ·
     destination · unit), same shape covered, not sampled once.
⇒ THREE SCOPE DECISIONS (operator): embedded-junk + code-switch noise — build as v3
twins or declare out of scope in the freeze note · noise twins over the new seeds
(mechanical) · the READ closing document at the freeze.
  · decision 1 ✅ RULED 08-21 (operator): *"yes add it"* — BOTH classes BUILD as v3
    noise twins. Drafted interpretations (certification ratifies): EMBEDDED JUNK —
    the slot decides (junk in a closed slot is excluded by the reader; the same
    bytes in a naming slot are a legal mint, twin gold carries them); CODE-SWITCH —
    the closed classes do NOT grow: a politeness token in another language reads
    clean; a foreign VERB never fires a producer, so the twin's gold says UNKNOWN
    bounce — the bounce IS the correct answer, and UNKNOWN is never filtered.
  · decisions 2+3 ✅ CONFIRMED 08-21: six-class noise twins generate mechanically
    over all v3 seeds · READ.md numbers land at the freeze.
⇒ PER-SEED RULINGS, 08-21 MORNING (operator; seeds updated at the build sweep):
  · id-0002 ✅ *"mark it as a query — since we have the value but not the key"* — a
    REVERSE LOOKUP: the sentence GIVES the value (the mac bytes) and ASKS for the
    key, the owning vm. The given value is the query act's real input argument and
    is expressed as a gold span with a value role; the wh-NP is the asked side.
    cs-0007 REFINED, not broken — the line is property vs value: an asked PREDICATE
    ("running") stays unmarked; a given VALUE (bytes selecting through a learned
    attribute class) is marked. Query-side store selection becomes scorable — and
    value→owner through an attr_class is exactly what the classes exist for.
  · un-0002 ✅ *"each value should be scored indpendently"* — creation SPEC values
    are CARVED OUT: patient shrinks to the minted kind ("a vm"), and every spec
    value ("4 cores" · "8gb of ram") is its own value-role span, scored on its own.
    Creation-side units measurable value-by-value, symmetric with set-acts.
    Build note: validator must accept multiple value roles on one act — if it
    refuses, that is a sanctioned schema tweak in the sweep.
  · al-0001 ✅ *"score both — the 'or' is scored like a trigger since boolean
    operators are triggers; the decision is at RESOLVE, not ROUTE — not a legal
    issue that needs routing, a resolvement issue."* NO alternation flag — the
    question dissolves: both members stay scored spans, and the boolean operator
    itself is expressed in the TRIGGER channel like any condition (al-0002's
    "whichever is stopped" already IS one — the family unifies). Architecturally:
    routing sees a fully legal act; WHICH member is acted on resolves where
    selectors meet the world — the world satisfies one member.
  · ap-0001/0002 ✅ *"the renames are scanned as well but are treated as refernces"*
    — the apposition IS expressed: its own gold span, attached to the SAME referent
    with a REFERENCE role. One patient stands; the reference co-names it, never
    counts as a second thing. The reader is scored on binding the equivalence —
    the read the apposition-as-teaching harvest depends on. Build note: `reference`
    joins the attachment roles in the sweep.
  · co-0001 ✅ *"sure — it helps us later to test resolvment and routing"* —
    concession stays TESTIMONY ON A BYSTANDER (malfunction predicate = testimony);
    NEVER an excluded-role: "even though" pre-empts an objection, it removes no one.
    "Except" is a different construction — and the sweep found v2 ALREADY covers it
    (the `excluded` role, ruled 08-18; two cases carry it): no new drafts needed. Noted for later: concession cases
    are resolve/route test material — known bystander state exercises the seam
    between legality and what the world satisfies. A concession never grants;
    whether it pre-answers a confirmation tier is a gates question for another day.
  · or-0001 ✅ *"we keep it — again resolve issue"* — the ordinal STAYS INSIDE the
    span: "the first vm" is one selector NP, verbatim. The ordinal's work is
    RESOLVE's: the attr-class TYPE licenses the ordering axis, the world orders and
    picks. The read hands the selector over whole — same shape as al-0001.
  · nl-0001 ✅ *"yes keep this, because i use it myself: 'create 5 vms named 1-5' or
    'create 3 vms named after musicians and a network called the stadium and add
    those vms to it'"* — ONE SPAN carrying the mints, because naming specs are often
    GENERATORS (ranges, themes), not lists: the names may not exist as bytes in the
    sentence at all. The line vs un-0002: literal VALUES present in the sentence
    carve and score; a NAMING SPEC is one generative unit — mints happen where the
    generator runs. COVERAGE: the operator's own two sentences join the build sweep
    as drafts — range-naming, theme-naming, and the compound create+create+add with
    within-sentence anaphora ("those vms … to it").
  · cap-0002 ✅ *"i think we add it and treat a polite order as a refusable order
    IE, we read it, and let ROUTE handle it"* — the BENEFICIARY role is TAKEN:
    "the test vms" attaches to the create act as beneficiary, so a silently
    dropped purpose qualifier (the linguistic sweep's measured gap) becomes a
    visible miss. And the polite order's status is settled at its proper stage:
    the READ produces the order faithfully — "can you create a network…" IS a
    create — and ROUTE decides its fate like any order (a REFUSABLE order, not a
    softened one). Completes the morning's stage assignments: alternation →
    RESOLVE · ordinal → RESOLVE · polite form → ROUTE. A beneficiary expresses
    for-whom; it never infers extra acts.
⇒ EXPLICITLY NOT v3 (standing rulings): cross-turn (LAST) · A2 model swap · N1 wiring.

## 12 · v3 CERTIFICATION, 2026-08-22 — the operator's rulings from the review chair
65 cases keyed in two rounds (58/7, then 62/3 after the fixes). Each reject is a ruling in
the operator's own words; the fix happens at seed source and the case re-pends by hash.

  · ca-0001 / ca-0002 / ca-0002-ej ✅ *"you do need to carry the evidence to stop because
    its a future reference"* · *"you need to carry the evidence because its an important
    reference, regardless if its used as part of the operator"* — EVIDENCE IS CARRIED: the
    because-clause attaches to the act with role `evidence` (ap-0001's shape). Taken as
    **schema v2.1 rule**: an evidence span nothing attaches to is a FAULT (planted fault
    #27 in selfcheck; every frozen set already obeyed it — it bit exactly five v3 golds).
  · co-0001 / co-0002 ✅ *"should include 'alpha' as part of the evidence"*, then the shape:
    *"drop the other object since its irrelevant to the main cause technically, but you do
    file it into evidence … 'stop vmA because networkA is slow' becomes 'stop' -> 'vmA' +
    evidence 'networkA is slow', file -> 'networkA is slow'"* · *"it becomes a cross turn
    evidence, just not acted upon"*. So: THE BYSTANDER IS NOT AN OBJECT — it lives inside
    the testimony; the evidence span is the WHOLE clause (subject included — the subject is
    carved out only when it is the patient, v2's diagnosis convention); the act carries it;
    and the downstream consequence is FILING, not acting — cross-turn evidence, which is
    LAST's surface and explicitly not v3's. The read expresses; a later stage files.
    ⇒ SUPERSEDES v1 `adj-0003` (identical sentence, certified 08-18 with `alpha` as an
    unattached object and no evidence). OPEN for the freeze: whether adj-0003 rides in
    "the 148" as-is (sealed means sealed) or is dropped as superseded. Same family, not
    ruled today: the 13 v2 cases with a bystander object inside a TRIGGER clause
    (cond-0003 'only if the lab network is up') — trigger, not evidence; nothing forces it.
  · mn-0001 / mn-0002 — rejected *"you should carry the span of 'one at a time' because
    its action control"*, and the gold ALREADY carried it as `manner`: the REVIEWER never
    painted the trigger/manner channels. Display fix (magenta ⟨…⟩t / ⟨…⟩m + a channel
    column on the action line); all 8 channel cases re-pended — six of them had been
    ACCEPTED with the trigger invisible — and all 8 re-accepted with the channel shown.
    Lesson for the seal pattern: an accept ratifies only what the reviewer SHOWED.
  · nl-0004 ✅ *"that 'add' does not have a patient and a destination, its supposed to be
    a 'put on network' request"* — the add is DIRECTED like pw-0002: 'those vms' patient,
    the network span destination. 'it' stays spanless (the bare-pronoun rule: point at
    the thing, never the pointer — fb-0001's 'kill it' → alpha).
  · id-0001-cs — *"needs to be an open discussion about multi language support"*, held
    the same afternoon. The operator's two avenues: (1) *"the AI is not really good at
    reading and extracting data ALONE — see our previous 5 attempts"*, so a language with
    no hand-written scaffold has NO reader, not a weaker one; (2) *"not every language can
    support this task CLEANLY — some don't translate nicely, the type of actions can not
    be expressed the same as in english"*, so extraction can be impossible by the grammar
    itself (pro-drop objects, no order/request distinction by form). *"READ is 'read
    sentence → extract data', that's all READ is — change the language, the rules change,
    and our AI that is already prone to mistakes is also unreliable."* ⇒ RULED: **Gorgon
    READS ENGLISH, by declaration.** Translation is not a mechanism (the words cross, the
    grammar doesn't). Foreign FLAVOUR and NAMES pass through the slot (no authority);
    a foreign token in a LICENSING slot (verb · role marker · trigger marker) is
    **an automatic REJECT — "the verb is inexpressible"** — not an UNKNOWN bounce that
    asks, and never a translation. id-0001-cs is the CONTROL for the declaration;
    sa-0002-cs its partner (flavour costs nothing). Two cases is the stratum.
    ⇒ REPRESENTATION OPEN: the gold schema has no REJECT outcome (spans · actions ·
    attachments only) — a case-level outcome is a schema v2.2 brief, not built.
    ⇒ FINDING, same session (n=3 seeds, byte-identical): the seam TODAY reads the Hebrew
    verb and fires `stop_vm` — the licence at pass2 takes the first `[a-z]+` word as the
    verb (`the`), finds no operation, and hands the clause to the model as "free
    translation". An unrecognised verb is the LEAST constrained one. Defect against the
    declaration; subtractive fix, scheduled, not done.

## 13 · v3.1 — THE CORPUS HOLES, CLOSED AS DRAFTS (operator, 2026-08-22 evening)
*"i want to cover everything … READ should be able to parse +95% of english"* — READ only,
not ROUTE or RESOLVE; feasible, in-scope input a user would type as a request or in a plain
session. v3 is FINAL: anything after fixes, never replaces. So the last additions are the
constructs the structure_map and coverage_map named and NO stratum held — checked against
every clean sentence in v1+v2+v3, not against the reader registries (which are stale).

⇒ **SCHEMA v2.2 — THE OUTCOME.** Every gold in the corpus had a span or an act; the reading
  "produce NOTHING" was never certified, and it is the reading the courtesy hazard, the polite
  orders, the commitment and the foreign verb all rest on. `outcome: none | reject`, optional;
  **no actions ⇔ an outcome** (an empty reading is a statement, not an omission; a declared
  outcome with an act is a contradiction). Spans free in both — the object NP still detects.
  Three planted faults (selfcheck 30). id-0001-cs carries `reject` — the control.
⇒ **THE SEAL NOW BINDS store AND outcome.** Found while adding it: the verdict hash covered
  sentence+gold only, so a changed mock never staled an accept — "certification ratifies the
  store, decoys included" (#11) was a sentence, not a binding. Additive: unchanged cases keep
  their hash; lw-0001/2/3 go STALE once and are re-keyed with the store SHOWN (the reviewer
  now prints outcome and store — the 08-22 lesson: an accept ratifies only what was shown).
⇒ **SIX STRATA, 35 CASES, every judgement call marked RULING NEEDED in its seed note:**
  · null-turn (9) — acknowledgement · resolution · unrelated · noise · pure flavour ·
    COMMITMENT ("i'll stop alpha myself" — the operator's act, not Gorgon's) · a keyboard in
    the verb slot (drafted REJECT vs grubnash's UNKNOWN bounce — RULING) · neither/nor as a
    prohibition (no act, no span, like don't — RULING)
  · indirect-orders (7) — the measured 0/14 family: nominalised ("i need alpha stopped"),
    passive, would-you-mind, hortative, deontic should, deontic passive, subjunctive ACHIEVE
    ("it would be great if alpha were down" — the act span of a state-achieve, RULING)
  · tense-person (5) — "i stopped alpha" is a REPORT the ledger files, never an act; plus a
    report-and-order in one sentence. Time on a report ("yesterday") unmarked — RULING
  · deferred-time (4) — "stop every vm at 9pm" RUNS NOW today (the sweep's finding); one-shot
    clock, relative delay, deictic day on the TRIGGER channel; DURATION ("for an hour") on
    MANNER, the reverse act being RESOLVE's — RULING
  · conditional-branches (4) — unless · otherwise (the ELSE branch: two acts, complementary
    triggers, the IR cannot emit it, so READ certifies it first) · both-not-just-one ·
    condition + fallback-as-query
  · partitives (6) — "two of the lab vms" (whole span, a generator) · "all but two" (a COUNT
    cannot be excluded, one span — RULING) · any (= one of — RULING) · half · "vm 3" vs "3 vms"
⇒ **TWO SURFACE NOISE CLASSES** in the expander: list-form ("stop: alpha, beta, gamma" —
  fires only on coordinated, untagged members; 3 in v21, 0 in v3's role-tagged lists) and
  shouting (ALL CAPS + bangs, offsets untouched). The expander now carries manner (v2.0)
  through the offset map and store/outcome verbatim — it did not before.
⇒ **READ'S ACCEPTANCE CRITERION, in the operator's words: "95% of all feasible realistic
  sentences" — "not all of english per se but everything that can be thrown its way."**
  The unit is the INPUT STREAM, not the grammar: FEASIBLE = in scope and expressible (about
  the lab, readable by a scaffold); REALISTIC = what a user would actually type to this
  service as a request or in a plain session, in whatever shape it arrives (the noise
  classes are "how it arrives", the strata are "what it says") — not constructs, not this
  corpus, not "yeah" back-and-forth. Certifying
  constructs makes READ COVER them; the 95% can only be measured on a HELD-OUT of realistic
  input — A1's sealed 51 plus fresh cold sentences, qualified first (how much is feasible,
  blind re-graded into plain English) — scored after the readers are built against this
  gold. The corpus is the ruler, not the measurement; the held-out is the measurement.

## 14 · v3.1 CERTIFICATION — 93/100, and READ IS FED BY RESOLVE (operator, 2026-08-22 night)
Seven rejects, and three of them are one ruling: **a turn can carry a FACT without carrying a
program**, and some turns cannot be read at all without the previous one.

  · tp-0003 ✅ *"i actually go with C since its actually better as evidence because its not a
    temporal trigger but a reference, 'every day' is a temporal trigger for example, **past
    action are evidence and future are triggers, usually**"* — THE TENSE RULE, and it decides
    the channel: a PAST temporal reference is EVIDENCE (it asserts something happened), a
    FUTURE one is a TRIGGER (it starts an act). `yesterday` becomes an evidence span on the
    report; `every night`, `at 9pm`, `in 10 minutes` stay triggers. No new channel needed.
  · nt-0002 / nt-0006 / nt-0007 ✅ *"should be treated as testimony, a subset of evidence
    which are user input"* — TESTIMONY IS EVIDENCE WITH A USER SOURCE. *"thanks, that
    worked"* is the system's act resolved; *"i'll stop alpha myself"* is the user resolving
    it. Both are facts the issue ledger files (D3's `Issues.answers()`), neither is a program.
  · nt-0009 + a NEW CLASS ⇒ **TURN-DEPENDENT**, the operator's own name: *"they are only
    understandable by the fact of the previous turns"*. *"check"*, *"lets continue"* are
    **usually too vague**; *"stop that"*, *"whats next"*, even a straight *"yes"* are **fine
    IN CONTEXT**. This is the ISO defect from a week ago named properly: a bare *"yeah"* was
    **both tonal and context-requiring**, and no reader can settle it alone.
    ⇒⇒ **THE PROPOSAL, AND IT INVERTS THE PIPELINE'S SHAPE:** *"READ is fed by RESOLVE …
      RESOLVE dictates that the next answer is a 'yes or no' question meaning a READ 'yes' is
      legal AND EXTRACTABLE. READ -> ROUTE -> RESOLVE is a feedback loop that interact with
      eachother through **what messages are legal at what state**."* The corpus shape the
      operator wrote:
          context from RESOLVE: "expecting a y/n answer from user about a plan"
          user: "yes"   ->   "yes" (evidence)
      *"this is more of multi-turn context based that is answerable at ROUTE or RESOLVE but
      here READ is influenced by context, which is where unfortunately we need to account for
      — and hopefully the AI can help by being the one who gives the READ what it is looking
      for."*
    ⇒⇒ **WHERE THE HINT IS WRITTEN — CORRECTED BY THE OPERATOR THE SAME NIGHT:** *"i made a
      mistake, it needs to do it AFTER chunking BEFORE it makes a decision about what it is
      its looking at."* So the hint is written over the CHUNKED, NOT-YET-CLASSIFIED input:
      the clause split has run, nothing has been typed yet. **It records what a piece COULD
      be before the reading commits to what it IS** — which is what makes a wrong commitment
      auditable at ROUTE, and is strictly stronger than writing it pre-chunk (a hint about
      an unsplit string cannot name which piece it doubts).
    ⇒ ⚠ **HALF THIS LOOP IS ALREADY BUILT AND FED FROM THE WRONG SOURCE.** `pipeline.run`
      takes `answers=`, `asking.answered` matches them to the questions the GATES asked, and
      `reading_answers.py` gives an answer the same anchor-and-scan ladder a request gets
      (closed polarity markers first, decline when ambiguous). So the mechanism exists —
      what does not exist is RESOLVE (or any state) setting the expectation, READ seeing it,
      or a single certified case proving a bare answer reads correctly under one.

  · nt-0001 / td-0010 ✅ *"acknowledgment only carries resolution when the issue is
    diagnosis/query, meaning only when INFORMATION is the topic"* — so acknowledgement is
    CONTEXT-DEPENDENT and becomes a control pair rather than an edit: *"ok, got it"* with no
    state supplied stays `none` (nt-0001, unchanged and still certified); the same bytes
    under an answered query are TESTIMONY (td-0010, evidence `got it` — the receipt, not the
    courtesy). Second pair after `yeah`, and the same claim: the reading differs only by
    what RESOLVE supplied.
  · nt-0005 ✅ *"ambigius / mood indector for rage/desperation"* — NOT empty: it carries a
    STANCE, which is a fact about the speaker and therefore testimony. The word is flavour
    species A1 (deference), the FORCE is A3 (frustration) — and A3 says a prior attempt
    FAILED, i.e. a diagnosis context. READ carries the ambiguity in the hint instead of
    picking a side, which is the direct countermeasure to the measured 7/7 hazard where
    courtesy was read as intent.
    ⇒ ⚠ **`mood` JOINED THE HINT KINDS, AND THAT IS PROBABLY THE WRONG HOME.** The flavour
      taxonomy already names EIGHT species that each say something operational. If READ is
      to CARRY mood, that is a CHANNEL with a closed vocabulary, not a free-text gloss riding
      the hint. Drafted on the hint; RULING NEEDED on whether mood graduates.
⇒ **v3.1 AFTER THE RULINGS: 110 cases — 93 accepted · 7 STALE · 10 pending · 0 REJECTED.**
  Every reject of the certification round now has a ruling. 487 noise twins over 7 classes
  validate; selfcheck 35; suite 894.

## 15 · MOOD IS A CHANNEL (operator, 2026-08-22): *"mood should be its own channel i think
## because it is important to also provide it as evidence"*
Two claims, and the second is the enforceable one.

⇒ **A CHANNEL, NOT A HINT.** `mood` had been a hint kind for one hour and graduated the same
  night — one fact, one home; a free-text gloss and a closed channel for the same thing is the
  twin-owner defect. `gold.mood` is a LIST of {kind, text, start, end} — a span with a
  species, the way a trigger is a span on an act — because one turn may carry two (*"ugh,
  please…"* is frustration AND deference) and the reading must not have to choose. The
  vocabulary is the taxonomy's own eight, each already carrying an operational meaning:
  deference · closure · frustration · hostility · hedge · urgency · phatic · filler.
⇒ **ALSO EVIDENCE, ENFORCED:** every mood span must ALSO be an evidence span at the same
  offsets, so downstream can file it. Three planted faults (wrong species · lying offset ·
  a mood nothing files); selfcheck 39.
⇒ ⚠ **AND IT EXPOSED A RULE THAT WAS WRITTEN TOO NARROW.** v2.1 said evidence must be
  attached; v2.3 exempted `testimony`. But *"hey, check"* is CONTEXT-NEEDED, carries a phatic
  mood and therefore evidence, and has **no act to attach it to** — requiring attachment
  there is incoherent, not strict. Generalised: **an actless turn has nothing to attach
  evidence TO.** Every case the original rule caught (ca-0001, co-0001…) had an act, so this
  is the same rule stated correctly.
⇒ **BLAST RADIUS, MEASURED against the codex's own closed classes before touching anything:**
  · v3 DRAFT — 4 clean cases retro-fitted (they are a draft; staling is the mechanism):
    `lw-0003` deference · `sa-0002` phatic · `nt-0002` closure (beside its testimony) ·
    `td-0006` phatic (the case that generalised the exemption). Plus `nt-0005` frustration.
  · **`sa-0002-cs` DELIBERATELY GETS NO MOOD.** `בוקר טוב` cannot be READ as phatic — the
    closed classes do not grow (#11). It costs nothing and it is not identified, which is
    exactly what "flavour passes through the slot" means under the English declaration. The
    clean/code-switch pair now states that difference instead of implying sameness.
  · `io-0007` *"it would be great if alpha were down"* — a FALSE POSITIVE of the scan
    (`great` inside a subjunctive request, not a closure token). Untouched, recorded.
  · **FROZEN SETS: 3 clean cases carry a flavour token and are SEALED** — `sc-0002` ("sorry,
    i meant beta") · `sc-0004` ("er") · `cc-0001` ("when you get a chance") in v1/v2/v21.
    Retro-fitting them would break the freeze, so it was NOT done. **OPERATOR'S CALL:** amend
    at the next release, or let the frozen sets stand and note the gap in READ.md.

## 16 · A SENTENCE IN TWO LANGUAGES IS REFUSED — WHOLE (operator, 2026-08-22)
*"sa-0002-cs should also be rejected as it contains a different language and therefor NO
MATTER WHAT it should also be automatic reject. i am thinking we [have] a rule: ALL SENTENCES
CONTAINING A DIFFERENT LANGUAGE GET ASK AUTOMATICALLY, with the note basically telling them
that the project does not support multi-language sentences."*

⇒⇒ **THE REASON, AND IT IS THE LOAD-BEARING PART (operator, same night):** *"its because
  the other language isnt supported — WE CAN'T ORACLE IT, and we value SAFETY MORE THAN
  CONVENIENCE."* The refusal is not about the language. It is about **verifiability**: an
  unsupported language has no scaffold, no certified gold and no reviewer who can read it,
  so there is no ORACLE that could tell us whether the reading was right. A reading nobody
  can check, that then ACTS on the lab, is the exact shape this project refuses everywhere
  else — it is [[gorgon-the-seal-pattern]] stated for input instead of for evals, and it is
  why "prefer expensive and working" beats "never buy cheapness with verification". The cost
  is convenience, paid deliberately.
  ⇒ **AND IT GIVES THE RULE A PRINCIPLED TEST, better than "contains non-ASCII":** *can we
    oracle it?* Anything read AS LANGUAGE in an unsupported tongue cannot be oracled and is
    refused. (Externally corroborated: translating an unsafe request into a low-resource
    language beat GPT-4's safeguards 79% of the time — the unread language IS the attack
    surface, not merely an unsupported feature.)
⇒ **THIS SUPERSEDES THE SLOT READING IN #12.** That entry said a foreign token REJECTS in a
  licensing slot and that foreign FLAVOUR and NAMES pass through. The rule is now about the
  **SENTENCE**: any language mixing refuses, wherever it sits. `sa-0002-cs` is what proves
  it — *"בוקר טוב, stop the lab vms"* has a complete, legal English order in it and **still
  does not fire**. Both code-switch cases now make the same claim, which is the rule: it is
  not slot-dependent.
⇒ **REJECT AT READ, ASK AT THE DOOR.** The reading refuses; what the operator SEES is a
  question carrying the reason. So a refusal must say why: **schema v2.5 requires a `hint` on
  every `outcome: reject`** — a refusal with no reason is a silence, and a silence is the one
  answer this seam may not give. Two hint kinds added for it: `unsupported-language` and
  `inexpressible` (the keyboard-in-the-verb-slot case, nt-0008). Planted fault; selfcheck 40.
⇒ WHAT SURVIVES A REFUSAL, unchanged from #12: the object NP still DETECTS. Refusing to act
  is not refusing to read — and the detected span is what makes the ASK specific.
⇒ ⚠ **RULING NEEDED, and the oracle test sharpens it rather than settling it:** a NAME in
  another script — a vm actually called `אלפא`. A name is never INTERPRETED; it is matched
  against the store and the lab, so arguably there is nothing to oracle and #12's "names pass
  through the slot" survives. Against that stands the operator's own words — *"no matter
  what"* — and the fact that a name is exactly where an unreadable string gets closest to an
  act. Left OPEN: the strict reading makes a lab with non-Latin machine names unusable; the
  loose reading puts an uncheckable string one slot away from a target. The operator decides,
  and either way it is a declaration, not an inference.
⇒ **THE FLAVOUR GAP IS DECLARED, NOT REPAIRED.** Three certified clean cases in v1/v2/v2.1
  carry a flavour token with no mood channel (`sc-0002` · `sc-0004` · `cc-0001`) — the
  channel post-dates their seal. Recorded in READ.md under "Declared gaps in the frozen
  sets": a reader scored against those releases is neither billed nor credited for mood, and
  v3 is the first set where mood is scored. A seal means a seal.

## 17 · ATTRIBUTES ARE LEAVES, AND A NAME IS ONE — v3 RESET (operator, 2026-08-23)

**The ruling, in the operator's words:** *"attributes are 'leaves' of the class world since
they are meaningless technically to the AI … if the AI has no use for it, it's meaningless to
explain it. Their owner is the classes they are related to; one attribute can appear in a few
classes and their inherited children, but we use context to understand which is which. For
READ it's seamless — it only needs to understand that this is a 'learned' word that it's
looking for in which context: if a word appears in the correct context READ spans it, and if
there is a conflict it gives it to ROUTE for ASK with the hint 'X creates a conflict between
ClassX and ClassY'."* · *"the unit alone spans it if the class owns that unit; a learned word
could be a class, an attribute, a value — held in the archive: entry RAM, type unit, owners
computer (and its children)."* · *"attributes such as cores or ram should stay in their own
span because they need to be scrutinized differently … each attribute should be scrutinized
based on its class owner."* · on a tie: *"context and fit are both needed — if they are the
same then it's a tie; if something is MORE correct we use the more correct one."*

**And a NAME is a leaf** (ruled 08-23, on the question put as: its own span when assigned
at creation, scrutinised by the owner — yes). Read together with #11's naming-lists ruling
("a naming spec is one generative unit"): a LITERAL name at creation is a leaf per name
(`a` · `b` · `c`); a GENERATOR spec is itself the leaf — one value span (`1-5`, `after
musicians`) the owner runs. A name that REFERS (`stop alpha`) stays in its phrase.

**What changed in the gold:** `un-0002` — the value is NUMBER + UNIT (`8gb`), the attribute
word is context (matches `un-0001`'s `16gb`). `nl-0001..4` — patient is the minted kind
alone, every name a value span (nl-0004's single create keeps plain members: two mints, no
direction claimed). The sealed sets keep `a vm named alpha` whole — declared in READ.md.

**THE RESET (operator: "lets reset v3 entirely since a lot of changes have been made"):**
`v3-draft.review.json` → `.before-reset-0823`; the draft re-emitted from `seeds_v3`;
**110 pending** — every verdict to be made under the current rulings. The accepts of
08-21/22 are kept on disk as history, not as signatures.

**What the code does now (commits 172ad24 · 182e35a · 001ff55):** `archive.learned(word)`
serves {type · owners} for manifest and told words alike; `seam/values.py` lifts an assigned
number+unit out of its phrase as a VALUE_KIND row, ranks owners by context + fit, carries a
tie as `conflict` + hint; `Board.accept` is the owner's scrutiny read off `attr_classes`
(`16gb` → 16384); a NEW target takes the accepted value for its creator, an EXISTING target
without a setter REFUSES and gate 4 tells the operator. **Names as leaves are RULED, not yet
READ** — the reader lifts units today; names are the next step.

### 17b · A SELECTING VALUE IS A LEAF TOO — role `selector`, schema v2.6 (operator, 2026-08-23)

Asked on id-0001: *"stop [the vm at 10.0.0.5] — wouldn't this make sense that 10.0.0.5 is a
different span since it's an attribute?"* Ruled yes: one rule for every attribute value a class
owns — its own span whether it is GIVEN to the thing (`value`) or PICKS it (`selector`). The
owner scrutinises a selector exactly as an assignment (`8g:77q` is no ip, which is how the lab
knows it cannot look it up). A token no class owns stays in the phrase (id-0005, mg-0003's
`a month`); a THING inside a phrase stays too (`the vms on the lab network` — a network is a
thing, ba-0001's convention stands). Reshaped: id-0001 · id-0004 · id-0001-cs (`the vm` +
the identifier), mg-0001 · mg-0002 (`every vm` + `6gb`, `the vms` + `2 cores`; the comparator
and the attribute word are context the reading carries). The reader lifts selectors like every
other leaf; the phrase keeps the filter in `where` unless a comparator governs it.

## 18 · A LATER MENTION BINDS BY NUMBER AGREEMENT (operator, 2026-08-23)

On nl-0004's one miss — `add THOSE VMS to IT` — the operator: *"'those' is plural, and the only
plural here is the '3 vms', meaning it should be paired based on the plurality."* Three
mechanisms had bound a later mention and none looked at number: the scan re-sighting the same
NOUN, the bare-pronoun rule taking the MOST RECENT row, `resolve_proforms` matching a
modifier's CONTENT. Ruled: a mention carries a NUMBER (the codex's SINGULAR_PROFORMS /
PLURAL_PROFORMS, or the demonstrative heading a phrase); its candidates are the things declared
before it; AGREEMENT filters; a matching noun or modifier is the tie-breaker; exactly one best
binds, more than one binds NOTHING and travels to ROUTE as an ASK — *"'it' could be a vm or a
network"* — the same shape as the leaf rule. A full-phrase mention (`those vms`) is reported as
a span of its own thing; a bare pronoun is bound but never reported (the 08-22 rule: point at
the thing, never the pointer). Built as `seam/proforms.py` on the live path; nl-0004 reads
5/5. **The v3 draft was RESET AGAIN at the operator's word so every key is made under #17,
#17b and #18 together: 110 pending.**

## 19 · 'X's SNAPSHOT' — THE LEAF IS ITS OWN SPAN, X IS ITS OWNER (operator, 2026-08-23)

Before grading v3 the operator rejected po-0001 · po-0002 · po-0003 (and the twin po-0001-ej)
as authored: *"'X's snapshot' — snapshot here should be a value as a span."* The gold had kept
the whole genitive NP (`alpha's snapshots`) as one object span — it matched what the reader
produced, and both were wrong. The genitive is owner + leaf, the same shape as `the cpu of X`
(un-0003, ledger #17): the owner is the **patient**, the leaf is a **value** span of its own, and
the `'s` belongs to neither. Operator confirmed: *"patient for the owner."*

Gold first (2fca62c); the reader followed in the next commit — `values.py` rule 8 POSSESS,
`GENITIVE_CLITICS` in the codex: the leaf is lifted out as its own VALUE row, the owner keeps
the phrase minus the clitic and is re-typed by its own head; FIT is asked of the world in the
settle order (attribute/alias · taught word · a kind whose attrs/refs name the owner — so a vm
owns `snapshots` by `snapshot.vm`, read backwards) and an undeclared leaf (`disk`) is spanned
and REFUSED by the owner, to the operator via gate 4. The codex's contractions (`let's`,
`it's`) and a declared state word (`alpha's running`) are never split. **And the verb governs
the leaf, not its owner:** with the model live the split produced `delete_vm(alpha)` — pass 2
now drops a step on the owner that does not carry the leaf as its value, and gate 4 says the
lab's limit (`ungoverned_leaves`). Capture moved on exactly po-0001 · po-0001-ej · po-0002 ·
po-0003, and on 8 SEALED readings — qual-0006 · mc-0004 · mc-0004-nt in v1/v2/v21 — whose
gold is the whole NP and now needs re-certification under this ruling (operator's seal, one
at a time). `snapshot beta's disk` still glues the verb to the name (fix B, separate). The
operator had already keyed ACCEPT on po-0001 · po-0002 · po-0003 under the old gold and
withdrew it here; those three accepts are STALE against the corrected gold and are re-asked.
po-0001-ej was never keyed and stays pending.

## 20 · AN UNSHAPED IDENTIFIER IN THE SELECTOR SLOT IS AN ATTRIBUTE VALUE (operator, 2026-08-23/24)

Rejecting id-0005 mid-grading: *"8g:77q is a selector"*, then, asked to rule: *"8g:77q is an
attribute the same way an ip is, so it should be treated the same."* This overturns #17b's
one clause "a token no class owns stays in the phrase" — the SLOT is the licence, exactly as
the genitive slot is in #19: `the vm at ▸8g:77q` reads as `the vm` (patient) + `8g:77q`
(selector), and what differs from an ip is only the WORLD's answer at ASSIGN — the vm declares
no attribute of that shape, so the owner REFUSES and gate 4 asks the operator which attribute
it is. The old downstream (a capability BOUNCE to the model) asked the one party that cannot
know. 8g:77q itself is invented — planted 08-20 as the decoy no class owns — but the situation
it stands for is real: a serial from another system, a typo'd mac, a store the lab cannot read.

Built the same day (`values.py` rule 9 SELECT-UNSHAPED): the slot claims only an identifier
SHAPE — a digit or a separator in the token. The first cut fired on bare words and the controls
caught it before commit: `on lab` (rr-0001, ba-0001-te), `in here` (nt-0003), `than you`
(adj-0004, SEALED) — a bare word may be a NAME and stays in the phrase, ba-0001's convention
intact. Guards: declared shape (7's) · quantity (1's) · English (cc-0007) · clock (`at 21:30`,
qual-0005 sealed ×3, unmoved) · state · thing · attribute word · comparator. Capture: id-0005
the only mover in all four files; sealed 365/365 identical; suite 985.

## 21 · THE HAVE-FRAME IS THE GENITIVE ASKED — LEAF AS VALUE, NEVER SELECTOR (operator, 2026-08-24)

Asked before grading: *"should queries also include the new selector rule? … 'how many
snapshots does alpha have?' — snapshots becomes a selector?"* and, on the pair: *"same with
un-0004?"* Ruled: **"value not selector."** The line the gold already draws (id-0002 vs
id-0004): a SELECTOR picks the thing out of many; in the have-frame the thing is NAMED and
the leaf is what is ASKED — `does alpha have L` is `alpha's L` (#19) worn as a question, so
the leaf takes the same role the genitive gave it. po-0004 → `snapshots` (value) + `alpha`
(patient); un-0004 → `memory` (value) + `alpha` (patient); the COUNT/AMOUNT stays the
produced answer, unspanned. On flagging: already flagged twice — the action sits in
`queries` (gold) and the reading's predicate path marks "asked, not set" (id-0002's, in
values.py) — no third marker. Gold only; the reader that satisfies it is fix C, unbuilt:
today both sentences read as junk (`how many snapshots` a set, `does alpha` nothing). The
frame lives in these two cases only — no sealed have-frame exists, zero sealed movers.

## 22 · SCHEMA v3.0 — FULL VECTOR DECONSTRUCTION PER WORD, AND THE PURPOSE STRATUM (operator, 2026-08-24)

The operator, mid-grading: *"decomp every single sentence to its based components and compute
it as a vector (mood, plurality, etc) … so i can see if the verdict is right AND WHICH WORDS
FLIP IT THE WRONG WAY … this is the final form of this READ: full vector deconstruction per
word"* — and on scope: **v4 IS v3**, same sentences, gold deepened, ONE grading pass. Two
corrections told and taken: cells are DISCRETE closed-class facts, never embeddings; the fold
is COMPUTED from the words (*"the overall vector is calculated by the READ and i approve or
reject it"*).

Built (four steps + the rank path): `vectors.py` — 11 word dimensions + 7 fold dimensions,
every cell from a real reader, never a word list (the naive tagger read `let's` as a
genitive; the codex contraction wins, and that is now a test); `seeds_v3 --emit` attaches
vectors to all cases; `schema.py` v3.0 validates words-mirror-tokens and the closed dimension
lists; `capture.py` hashes PER DIMENSION so a diff names the axis that moved; `review.py`
binds the vector into the seal (every keyed verdict went STALE once, by design — the
operator accepted regrading) and gains `f` — FLIP a cell, the per-cell reject, machine-
readable so the fix lands where the cell was computed. RANKING NEVER SEES THE VECTOR:
`_rank_hash` binds to what the rater SAW, proven headless — ranks survive gold+vector churn,
only a reworded sentence stales. Grading and ranking stay two different issues.

**And the one corpus hole closed — PURPOSE, the operator's design:** *"purpose is
constructed from 2 things which are already implemented in a 'sibling', diagnosis, but on
the other way around … this a ledger entry, with a request attached … 'why is vm3 stopped?'
-> 'vm3 was stopped due to it being idle, reverse the decision?'"* Three seeds (pu-0001..3),
the to-/so-clause as EVIDENCE by cause's certified 08-22 convention, carried by the act.
The reader today DROPS the clause (det 1/2 on all three, code-only) — the 08-16
silent-qualifier defect, now priced in gold; the purpose reader mirrors the because-reader,
a future step. 113 cases; the corpus is otherwise declared CLOSED — anything further is a
repeat or remix (operator, 08-24).

## 23 · THE OF-GENITIVE'S LEAF IS BARE; THE ADJECTIVE LIVES ON ITS WORD (operator, 2026-08-24)

On sup-0002, the last open gold before grading: *"delete is the verb, oldest is an
attribute/adjective, snapshot is a value inside of alpha and alpha is the patient."* The
of-genitive is #19's other spelling and the leaf span is the BARE leaf — `snapshot` (value)
+ `alpha` (patient); `the oldest` sits outside every span, and `oldest` is a fact about its
own word: vector class `adj:sup` (superlative FORM — morphology with a 3+ stem so `the test
vms` never fires, plus most/least). It maps to NO declared attribute — like `disk`, the
world is missing the axis, and WHICH attribute orders "oldest" is RESOLVE's question to ask,
not READ's to guess. **08-21 stands untouched for THINGS** (or-0001: "the ordinal stays
inside the span"; sup-0001 "the biggest vm" is whole) — a filter on a thing lives in the
thing's span; a fact about a leaf-word lives on the word. Gold + vector only; the reader
already splits the two rows.

## 24 · THE QUEUE OF 08-25 — THE READER CATCHES UP TO THE GOLD (built while the operator returned to grade)

Six commits, one day, zero regressions on any control (code-only all-spans-exact 63 → 79 of
113; sealed readings moved on exactly FOUR terse/typo twins, every one now exact against its
sealed gold):
· **rule 8-of + the ordering ask** (58db5e1) — `the oldest snapshot of alpha` reads BARE
  leaf + owner (#23); `gate4.unordered_superlatives` asks by the declared TYPE licence
  (two axes → which? · none → teach).
· **E5b/E5c** (5d1e1c3) — a CARDINAL partitive is one quantifier (`two of` · `all but two
  of`), pt-* 6/6 exact; the cardinal is REQUIRED (`everything but the running vms` carves by
  predicate — the structure guard caught the first cut's fuse). Vector quant cells.
· **reasons.py** (7b6d348) — the operator's purpose-is-diagnosis-reversed design: because ·
  although · to/so-that read as EVIDENCE carried by the act; rows stripped subtractively;
  the runner collects; a symptom inside a reason is the reason's. The whole evidence family
  (cause · concession · purpose) went from unread to exact.
· **fix B** (3ca24dd) — D8's bare-name arm: anchor slide + left wall, licensed by verb
  EVIDENCE (`_verb_ops`) or — for a verb the manifest never met (`restart`) — the CLAUSE's
  own directive act; the first cut slid on `oh`/`please` and the 8-case regression was
  caught by the control before commit. Deferred-time adjuncts (`in 10 minutes` · `for an
  hour` · `tomorrow morning`) ride the act, never the thing.
· **rule 10** (this commit) — the HAVE-FRAME is the genitive asked (#21): `how many
  snapshots does alpha have?` reads `alpha` + bare `snapshots`; the frame's skin (`does
  alpha` · `have`) is never a thing.
· Closed classes homed: REASON_*, TRANSFER_VERBS, OBJECT_PRONOUNS in the codex — the
  language-layer guard enforced its own rule on the new module.

## 25 · A REDUCED RELATIVE DECOMPOSES — IT IS NOT ONE BLOB (operator, 2026-08-25, mid-grading)

Caught an accidental ACCEPT on rr-0001 and ruled the whole stratum: *"vms is the patient and
'running' should be labelled as status as well as 'on lab' as lab being a destination"* ·
*"all of rr are rejects"* · *"stuck at boot as one symptom span, last week as selector."* The
reduced-relative NP was gold as ONE object span (`the vms running on lab`); it splits into the
head (patient) + its restrictors, each its own span:
- **rr-0001** `stop the vms running on lab` — `the vms` patient · `running` SELECTOR (a status
  value; vector state=status:running) · `lab` (from `on lab`) DESTINATION.
- **rr-0002** `delete the snapshots taken last week` — `the snapshots` patient · `last week`
  temporal SELECTOR; `taken` is the elided relativizer, unspanned.
- **rr-0003** `restart the vms stuck at boot` — `the vms` patient · `stuck at boot` kept as
  ONE SYMPTOM span (SELECTOR) — a described condition the world cannot query cleanly, kept
  whole rather than split.

Gold only; supersedes the "keep the NP whole" reading these carried. All three verdicts went
STALE on re-emit (the accidental accept undone, the two rejects re-asked against new gold).
Both rr-0001 role calls then CONFIRMED by the operator: `running` = SELECTOR on the grounded
`status` attribute (a declared OBSERVED attribute — the `alive`/guest_ping fact answers it,
three-valued; RESOLVE reads the Active Library else probes the findings ledger — decision 6);
`lab` = DESTINATION ("technically a destination in this context"). Settled.

## 26 · THE CORPUS DECOMPOSITION PASS — 41 REJECTS, ONE ONTOLOGY (operator, 2026-08-25)

After grading v3.1 (72 accept · 41 reject), the operator ruled the 41 rejects were one theme:
"a lot are just repeats of no decomp at all." Worked through cluster by cluster; every ruling
is in [[gorgon-41-reject-rulings]] and [[gorgon-decomp-roles-pass]]. Gold + schema only, the
reader unchanged — the honest "gold ahead of reader" state.

NEW ROLES: conditional (over · more than · older than · stuck at boot) · anchor (last week ·
a month · today) · ownership (taken) · self (you = Gorgon, unique) · operator (i = the human,
mirror of self) · quantifier (two of · half of · any · all but · none) · ordinal (first/last
+ superlatives biggest/oldest — RANK and pick one; unified 08-25).
NEW ACTION KINDS: testimony (the operator's own reported act) · meta-control (governs the
INTERACTION not the lab — pacing, order, session flow).
NEW CHANNEL: pacing (an agent-availability condition on an act, `when you have a sec`).
NEW: outcome `acknowledge` · mood kind `affirmation` · hint kind `prohibition`.
PRODUCED SIGNALS (vector fold, for ROUTE/RESOLVE): tone (bland/affirmation/deference/urgency/
hedge/apology — emotional) · priority (deferrable/normal — pacing). Vector cells adj:sup
(superlative→ordinal) · adj:cmp (comparative→selector) · quant:card · quant:part.

KEY RULINGS: queries decompose the ASKED attribute (nq-0001 'not running' selector), not just
the subject; a reference (`it`/`that`) may point at an OBJECT or an ACTION (fb-0001), and one
object may have several (cb-0002); PREFERENCE = a meta-control ORDERING ('prefer X' = try X
first), not a new kind; -EST superlatives are ordinals (pick the extreme), -ER comparatives
are selectors (relational, 'smaller than what?'); courtesy splits on FLUFF vs INFO — 'good
morning' pure phatic, 'when you have a sec' a pacing meta-control carrying "agent is busy".
Validator relaxed: subject may be patient OR (none) one reference OR a prohibition's all-
excluded OR a self-only meta-control; a query may have zero; phatic/affirmation/pacing-carried
moods are not evidence. FIXED a latent bug: FOLD had two `mood` keys (DO/ACHIEVE and emotional)
— the second clobbered the first; emotional renamed `tone`, DO/ACHIEVE `mood` restored.

38+ cases reshaped across clusters A-J plus nl-0004 · io-0007 · nt-0009. Schema bump v3.1;
ALL 113 verdicts STALE (the corpus-wide vector change tone/priority stales even gold-unchanged
cases, since the seal covers the vector — #22). Suite 1011 passed.

## 27 · THE POST-REGRADE REFINEMENTS — FRAME, SELECTOR KINDS, REFERS (operator, 2026-08-25)

After re-grading v3.1 (98 accept · 15 reject), the 15 rejects resolved into a few ideas:
- **FRAME** — `i`/`you` are NOT verb arguments, they are speech-act PARTICIPANTS. One
  mechanism: a `frame` gold field, party `user` (i, leans testimony) or `agent` (you, leans
  meta). Moved out of the attachment objects (tp-0001/0005, nt-0007, pr-0002, io-0003,
  lw-0003, cap-0001, au-0001).
- **SELECTOR/ANCHOR/VALUE gain a KIND** (temporal · status · magnitude · identifier ·
  attribute). Resolves the anchor/selector confusion: ANCHOR only when it is the operand of
  a conditional (`a month` for `older than`); a standalone temporal filter is a SELECTOR
  kind temporal (rr-0002 `last week`, au-0002 `today`). STATUS is oracle-evaluated (the world
  reports it — decision 6): rr-0003 `stuck at boot` and io-0007 `were down` are status —
  `stuck at boot` a status SELECTOR (filters the set), `were down` a status VALUE (wished
  state of a named thing, achieve target). pr-0002 `smaller` selector kind magnitude
  (comparative, relational).
- **REFERS** — a reference span now names what it points to: a span index, or `a{N}` for an
  ACTION. cb-0002 both `it`->alpha(0); fb-0001 `that`->the stop ACTION(a0), `it`->alpha(0);
  nl-0004 `it`->the network(2).
- **QUERIES span the verb** — a capability query asks about the ACTION-unit: cap-0001
  `create` (query), au-0001 `run` (query), the `you` in frame.
- **nl-0004 naming values** — `after musicians` · `the stadium` = value (two patients now
  allowed for a compound create; one-patient rule relaxed to >=1).

Schema: `frame` gold key, MEMBER_KINDS, member optional `kind`/`refers`, party user/agent.
Review shows frame + kind/refers. Suite 1011. 15 cases STALE for re-grade.

## 28 · CONSISTENCY PASS — THE ONTOLOGY APPLIED RETROSPECTIVELY, v3 RESET (operator, 2026-08-25)

The operator asked whether ledger #27's fixes were applied corpus-wide or only to the rejected
cases. Honest audit: only the rejected ones — leaving 9 selectors without a KIND, 1 i/you not
in FRAME, 4 references without REFERS. Ruled: apply retrospectively, and reset v3 to grade
fresh tomorrow.

- **FRAME party renamed** user->TESTIMONY, agent->META — a user-frame IS a testimony, flagged
  as such (operator). `i`->testimony, `you`/`lets`->meta. td-0009 `lets` moved into frame.
- **REFERS now carries the WORDS** it references, not a span index (operator: "carry the
  name/words its referencing"). cb-0002 it->"alpha"; fb-0001 that->"stop" (the action),
  it->"alpha"; nl-0004 those vms->"3 vms", it->"a network"; ap-0001 the jumpbox->"alpha";
  ap-0002 alpha->"the jumpbox". or-0003 `one` and td-0007 `that` stay refers-less (cross-turn,
  the hint/context explains).
- **KINDS retrofitted on all 9 selectors**: identifier (10.0.0.5, 7f3k-2210, 8g:77q), status
  (running, not running, not responding), magnitude (6gb, 2 cores), entity (the lab — new KIND
  added). Now EVERY selector/anchor carries a kind.
- **nl-0004** those vms -> reference (not just patient); the add is two references, no patient
  (subject rule relaxed to patients==0 with refs>=1).
- **OWNERSHIP role RETIRED** — rr-0002 `taken` dropped (operator: "delete last week's
  snapshots — taken serves no purpose"); the role had no other user.
- Prior round: 98 accept / 15 reject -> reshaped (frame/kinds/refers) -> re-graded 107 accept /
  6 reject -> this consistency pass. Review shows frame + kind/refers.

Schema: MEMBER_KINDS += entity; refers = words (string); frame party testimony/meta; ownership
retired. Suite 1011. **v3 GRADING RESET — 113 pending, fresh grade tomorrow** (backup
.pre-reset-0825pm).

## 29 · TESTIMONY IS EVIDENCE, NOT AN ACTION + the day's rejects (operator, 2026-08-26)

Fresh grade: 108 accept / 5 reject. The rejects:
- **cb-0004 / fb-0002** — missed references: `it`->alpha, `that`->the prior act (restart /
  launch), spanned with `refers` (the words). Same as cb-0002/fb-0001.
- **rr-0001** — `on lab` reconsidered: destination -> SELECTOR kind entity (it filters which
  vms, it does not receive them).
- **sa-0001** — `you` (frame meta) + `check` (the queried verb) spanned — a capability query
  like cap-0001/au-0001.
- **tp-0005 -> THE MODEL CORRECTION** — *"'stopped alpha' is evidence, not an act directed at
  the AI, it's the frame."* A user REPORTING their own act is EVIDENCE carried under a
  frame(testimony), NOT a `testimony` action kind. **The testimony action kind is RETIRED**;
  applied to ALL THREE (tp-0001, tp-0005, nt-0007 — even the two accepted, operator: "make all
  testimony = evidence even the ones i approved"). A pure report (tp-0001, nt-0007) is evidence
  + frame + outcome testimony, no action; a report beside a command (tp-0005) is evidence +
  frame + the real act (launch beta). Schema: `testimony` removed from ACTION_KINDS; evidence
  under a testimony frame is carried by the frame (exempt from needing an act).

Suite 1011. The corpus stays uniform.

## 30 · TRIGGERS DECOMPOSE — THE LAST BLOB (operator, 2026-08-26)

The operator: *"do we decompose triggers? … i think its the last thing we dont really
decompose."* Yes. A trigger stops being one `{text}` clause and gains a KIND (conditional ·
temporal · fallback · coordination) and self-contained sub-SPANS (subject + condition),
mirroring the main clause. All 14 decomposed:
- **conditional** — `if alpha is up` -> alpha (patient) + up (selector status); `if that
  fails` -> that (reference->"stop") + fails (selector status); `unless it is the jumpbox` ->
  it (reference->"alpha") + the jumpbox (selector entity); `whichever is stopped`.
- **temporal** — `at 9pm`/`every night`/`in 10 minutes`/`tomorrow morning` -> the time
  (anchor kind temporal).
- **fallback** — `otherwise`; **coordination** — `or`.
The status inside a conditional is the same oracle-evaluated `selector kind status` as the
main clause; the time is the same `anchor kind temporal`. Self-contained (own offsets), so the
main span list is untouched. Schema: TRIGGER_KINDS, trigger.kind + trigger.spans; seeds.py
triggers[i] = (clause, kind, [subspans]); review shows the decomposition. Suite 1011.

THE DECOMPOSITION IS COMPLETE — no gold element is a blob any longer.

## 31 · QUERIES AND DIAGNOSIS DECOMPOSE TOO (operator, 2026-08-26)

Same treatment as triggers, extended to queries and diagnosis:
- **QUERY -> `ask` object** {kind: what it SEEKS, spans: [the wh-word, role `seek`]}.
  QUERY_KINDS = identity(what) · selection(which) · object-ref(who) · reason(why) ·
  count(how many) · amount(how much) · polar(is/can/does) · manner(how) · time(when) ·
  place(where). 10 queries decomposed (id-0002 selection, po-0004 count, un-0004 amount,
  nq-0002 polar, au-0001/au-0002 identity, cap-0001/sa-0001 polar, td-0008 identity). `tell
  me` (cb-0004) stays a bare query — no wh-word.
- **DIAGNOSIS (report) -> `finding` object** {kind: aspect, spans: [the status, value kind
  status]}. DIAGNOSIS_KINDS = state (`is down`) · event (`stopped`, `was stopped`) · progress
  (`is stopping`). ap-0001, tp-0002/3/4.
New role `seek` (the wh-word). ask/finding are pure {kind, spans} objects (no clause text of
their own, unlike triggers). Review shows them. Suite 1011.

Note: `ownership` role — ledger #28's "retired" edit silently no-op'd (it is followed by more
roles, not a paren); it stays DEFINED but UNUSED (rr-0002's `taken` was still dropped). Harmless.

**THE FULL ONTOLOGY IS DECOMPOSED**: spans, roles+kinds, references(refers), frame, channels
(trigger/manner/pacing), triggers, queries(ask), diagnosis(finding). Nothing is a blob.

## 32 · EVIDENCE DECOMPOSES TOO — AND A FULL CONSISTENCY AUDIT (operator, 2026-08-26)

Rejects (ca-0001, ca-0002, pu-0001): *"decomp the evidence like ap-0001."* The operator's real
ask: *"go through ALL prompts, make ALL RULES CONSISTENT, not just the ones i rejected."*

Built a corpus-wide AUDITOR (every rule x every case). It found the ONE remaining gap:
**evidence clauses were not decomposed** (15 cases) — every other rule (selector kinds,
refers, frame, trigger/query/diagnosis decomposition) was already uniform from the prior
consistency pass. Fixed all 15: an evidence span gains a KIND (state/event/progress/purpose/
outcome) and self-contained sub-spans, like a finding:
- **cause/concession** (they are stuck · it won't answer · alpha is busy · the lab network is
  slow) -> kind state, subject(reference/patient) + status(value kind status).
- **purpose** (to free memory · to save space) -> kind purpose + the goal object; `so we can
  roll back` kind purpose, no object.
- **testimony** (stopped alpha · stop alpha · i'll add the labels ... tomorrow) -> kind event,
  the reported act's patient (+ tomorrow anchor temporal).
- **outcome** (that worked · got it) -> kind outcome (+ status if any).
ap-0001's evidence span decomposed to match its report finding. Schema: EVIDENCE_KINDS,
evidence-span kind+spans validation; seeds.py evidence=(text, kind, [subspans]); review shows
it. AUDITOR RE-RUN: NO INCONSISTENCIES. Suite 1011.

THE ONTOLOGY IS FULLY DECOMPOSED AND UNIFORM — verified by an auditor, not by hand.

## 33 · MANNER DECOMPOSES TOO — and `one` is a cardinal, NOT an ordinal (operator, 2026-08-26)

Operator asked whether mn-0001 should decompose with `one` as an ordinal. Answer: NO — `one`
in `one at a time` is a CARDINAL inside a pacing idiom, not an ordinal (an ordinal ranks the
set and picks a member; this paces the whole set). But the MANNER channel should decompose
like the others, so all 4 done: `one at a time` -> sequential [one=quantifier]; `all at once`
-> simultaneous [all=quantifier]; `for an hour` -> duration [an hour=anchor temporal];
`not just one` -> scope [one=quantifier]. MANNER_KINDS = sequential/simultaneous/duration/
scope. Auditor extended (manner-no-kind) and RE-RUN: 0 inconsistencies. Suite 1011.

Every channel and clause in the gold now decomposes: trigger · manner · pacing · ask (query)
· finding (diagnosis) · evidence. The decomposition is total.

## 34 · POLITE REQUESTS + the day's small issues (operator, 2026-08-26)

Final grade: 106 accept, 5 issues (a light pass).
- **au-0001** `what did you just run?` — confirmed a QUERY (an audit query about the agent's
  own ledger; frame you=meta). No change.
- **cb-0003** `stop both alpha and beta` — `both` added as a QUANTIFIER (+ the manner
  `not just one` already scope-decomposed).
- **dt-0004** — the manner `for an hour` was already decomposed (duration, an hour=anchor
  temporal); the reject was on the pre-decomp version.
- **io-0001 `i need alpha stopped` + io-0007 `it would be great if alpha were down`** — both
  are POLITE/INDIRECT REQUESTS. New FRAME PARTY **`request`** (the user asks indirectly),
  distinct from `testimony` (reports) and `meta` (addresses the agent). io-0001 `i` -> frame
  request; io-0007 `it would be great` -> frame request over the achieve(alpha down).
Frame parties now: testimony · meta · request. Auditor clean, suite 1011.

## 35 · au-0001 PARALLELS cap-0001 (operator, 2026-08-26)

Final pass: 112 accept, 1 reject — au-0001 *"treat it like cap-0001, as a query."* The gap:
cap-0001 has a PATIENT (`networks`), au-0001 had none. Fixed: `what` in `what did you just
run?` IS the sought object, so it is a `patient` (in the attachment) AND the `seek` (in the
`ask`) — now structurally identical to cap-0001: `you` frame meta + a patient + a query with
`ask`. Auditor clean, suite 1011.

