# SEAL — THE FRONT DOOR

**Status: SIGNED — scoped attestation, 2026-09-19.** Everything below is factual and
reproducible. Section 6 carries the operator's attestation and what it does NOT cover.

A seal is the [[gorgon-the-seal-pattern]] artifact for one surface: frozen corpora, hash-bound,
operator-certified. It records what was measured, what was *not*, and **who authored the gold** —
because a seal that hides the last of those is worse than no seal at all.

---

## 0 · THE DOOR'S CHARTER — operator ruling, 2026-09-19

> *"The front door should only fix typos on obviously wrong / non-existent words, fix noise,
> add commas and spaces where obvious. If anything changes meaning it's not the door's job —
> if it can alter a meaning, we just move it to route to ask. I would rather not serve
> something than serve something the user didn't ask for."*

⇒⇒ **THIS RULING MOVED 20 CASES AND CHANGED THE HEADLINE NUMBER.** Recall read **56/56** before
it; **20 cases moved from REPAIRED to ASKED**, and five more were added afterwards pinning the
fusion and suppression rulings, so §3 now reads **41/41 repaired** with those 20 in the
`ambiguous` column instead. That is not capability lost; it is capability moved to a channel
that cannot silently act. **Read §3's recall row with this paragraph or it reads as a
regression.**

⇒ Every stage-2 repair violated the charter, which is what a closed phrase IS: 8 retractions
(cancel what stands) · 8 corrections (redirect the target) · 2 wrappers (an order becomes a
question) · 2 courtesy literals (⚠ flip FETCH → ACHIEVE, i.e. **grant write authority** —
see the 2026-08-14 finding, 7/7 phrasings). A false retraction is the worst direction: it
cancels an order the operator gave, and they see a request that was accepted and did nothing.

⇒ The door still FINDS the repair and carries **all** candidates with what each would DO.
It does not apply one. ROUTE asks.

### A FUSION is the door's job — the exception is a code pattern

Operator, same ruling: *"those are fused, fused is also a front door issue, unless it's a coding
pattern again."* So `cancelthat` → `cancel that` stays, **even though the result is a
retraction**, and that is not a contradiction of the clause above:

| | | |
|---|---|---|
| `forgte it` | the letters are **wrong** — which word was meant? | **guessing** → decline |
| `cancelthat` | the letters are **right**, only the space is missing | **spacing** → open it |

Verified 2026-09-19: **0 of 15 code patterns opened** (identifiers `web-01` · `lab-core-2`,
camelCase `myVM`, flags `--no-color` · `-xzf`, paths `/etc/web/temp.cfg` · `~/.gorgon/workspace`),
and the ruling is pinned by `mr-0057…59` so it cannot regress silently.

### ⇒⇒ THE DOOR'S SCOPE IS CLOSED — this is the whole remit

Operator: *"I think after this we are mostly done with what the front door should cover.
**Endless typo seeking is off the table** … since all of those are closed class (in the sense
that they can be easily computed)."*

    1  typos on obviously wrong / NON-EXISTENT words
    2  noise
    3  commas and spaces where obvious
    4  fusions          — except a code pattern
    ────────────────────────────────────────────────
    NOT  anything that changes meaning   -> carry the candidates, ROUTE asks
    NOT  open-ended typo seeking

⇒ **THE COMPUTABILITY GUARANTEE IS THE POINT.** Every one of those operates over a CLOSED CLASS
  — a declared set the door can enumerate — which is what makes it decidable rather than a
  judgement. The moment a repair needs the open language it is not the door's work. That is the
  same line §4 draws around `fleet`, and the reason the veto sets are vetoes and never licences.
  **A new capability request for this surface should be answered against this list.**


## 1 · What is sealed

The **front door** — `orchestrator/languages/english/seam/front_door.py`.

⇒⇒ **THE CLAUSE-CUT RULE IS NOT SEALED HERE — OPERATOR RULING 2026-09-19.** *"The clause cuts …
this is for READ to decide, since READ does taxonomy, not front door."* `pass2._first_cut` and
`merge_cut_points` live in READ and decide a question of TAXONOMY — where one clause ends and
the next begins. The door merely APPLIES that decision, restoring the comma so pass 1's span
walk can see the boundary (N3, operator-approved `db32859`, 2026-08-19, after 5 certified span
losses). Applying is not deciding.

⇒ So the 29 cut cases are **READ's gold to adjudicate, in READ's seal**, not this one. The cut
  spec's numbers stay in §3 as a **declared dependency** — the door's behaviour changes if the
  rule changes, and a reader is owed that — but they are not certified by this attestation and
  the operator does not sign for them here.

Seven passes, all measured:

| | pass | measured by |
|---|---|---|
| 0 | unicode space fold | property: no undeclared silent edit |
| 0a | separator fusion | door corpus |
| 0b | word split | door corpus + dictionary sweep |
| 1 | filled pause | door corpus |
| 2 | closed-phrase typo | door corpus |
| 3 | sim check | door corpus |
| 4 | clause-break restore | property: every restored comma is announced, and every announcement lands |

⇒⇒ **PASS 4'S MEASUREMENT CHANGED WHEN THE CUT RULE LEFT THIS SEAL (2026-09-19).** It used to
read *"cut spec (29 cases, 8 rules)"* — which measured whether the CUT was right, a question
that is READ's. Rescoping left pass 4 with regression examples and **no measurement**, a blind
pass inside a sealed surface. The property above asks the door's own question instead: given
whatever cuts it was handed, does it apply them faithfully and announce each one. **It holds
even if every cut rule is wrong**, which is what makes it a measurement of THIS surface.

⚠ AND THE FIRST DRAFT OF IT WAS VACUOUS. The property suite's 520 generated inputs trigger
**0 clause cuts** — measured — so both sides of its equality were zero and a door that never
cut at all would have passed. The mutation harness caught it: `comma restored in silence` went
undetected. `_cut_corpus` now supplies 88 inputs built from the eight rules' own shapes, and
the property asserts it saw at least 20 restored commas before it asserts anything else.

## 2 · Bound to these bytes

```
git HEAD                   40511f7
door corpus  cases.jsonl   8fb810c81f737643   (161 cases)
cut corpus   cases.jsonl   6f2a73f93a68d89c   (29 cases)
vocabulary fingerprint     e26ba3535b5a9d2e
veto sets                  FALSE_FUSIONS 292 · FALSE_TYPOS 144 · FALSE_PRINTS 558
DUAL_CLASS_VERBS           snapshot, template
CUT_NEGATION               24 forms
```

`tests/test_seal_front_door.py` asserts these still match. **A seal whose hashes have moved is
void**, and it says so by going red.

## 3 · The numbers — and what KIND each one is

⚠ **Counts and rates are not the same kind of number and must never be read as one.** A corpus is
a COUNT over hand-chosen hazards — its denominator is the author's imagination. A sweep is a RATE
over a defined (synthetic) population.

⚠ **THE TWO CUT-SPEC ROWS ARE A DECLARED DEPENDENCY, NOT PART OF THIS ATTESTATION** (§1). The
door's behaviour changes if the cut rule changes, so a reader is owed the figures — but the
rule is READ's taxonomy and the operator does not sign for it here.

| | value | kind |
|---|---|---|
| door corpus — recall (`must_repair`) | **41/41 · 100%** | count |
| door corpus — false repair (`must_not_touch`) | **0/69 · 0.0%** | count |
| door corpus — calibration (`ambiguous`) | **51/51 · 100%** | count |
| cut spec — cuts made where English has a boundary | **11/11 · 100%** | count · ⚠ **NOT CERTIFIED HERE** |
| cut spec — false cut | **0/18 · 0.0%** | count · ⚠ **NOT CERTIFIED HERE** |
| 6,000 sampled dictionary words, one frame | **1/6000 · 0.02%** | rate |
| 3,000 sampled sentences, six frames | **0/3000 · 0.00%** | rate |

⚠⚠ **THE SWEEP ROWS HAD NO SCRIPT UNTIL 2026-09-19, AND ONE OF THEM WAS WRONG.** They were
recorded from an ad-hoc measurement; nothing in the repo reproduced either, so nothing could
contradict them. The dictionary row read **0/6000** and is **1/6000** — and the miss predates
every commit of the last two days (checked at `9af44f5`). **The number was wrong when it was
written and stayed wrong because it was unfalsifiable.** Both rows now come from
`tests/bench/door_eval/sweep.py`; re-run it whenever a closed class or a veto set moves.

⇒ THE ONE MISS, and it is a DEPENDENCY defect, not the door's:

      stop the anyway vm   ->   stop the, anyway vm

  Cut rule 3 treats `anyway` as a release word inside a determiner phrase — `the ___ vm` is a
  noun phrase and no boundary belongs in it. That is the same position error `DUAL_CLASS` fixed
  for rule 6, in a rule that never got it. **It is READ's taxonomy to fix (§1)**; the door
  applied faithfully what it was handed, which is what property 7 measures.

### The environment the numbers were measured in

⚠ **THE SUITE WAS NOT HERMETIC WHEN THE FIRST DRAFT OF THIS SEAL WAS WRITTEN.** Found
2026-09-18: `planner/procedures.py` binds `LIBRARY = Store()` at module scope and `_home()`
reads `GORGON_HOME` at IMPORT, which happens during pytest COLLECTION — before the session
fixture that sandboxes it. Every suite run had been reading the operator's real
`~/.gorgon/procedures`. **21 red items were that, not defects.**

⇒ **THE NUMBERS ABOVE ARE UNAFFECTED, AND THAT WAS CHECKED RATHER THAN ASSUMED.** Both scorers
  were re-run with `GORGON_HOME` set and unset; the output is byte-identical. The door eval
  declares its own world (`world: 9 declared`), so `known` never reaches `archive.ARCHIVE`.

⇒ `test_harness_integrity` now asserts the environment: the four `GORGON_HOME`-rooted stores
  must bind inside the sandbox (checked against a witness conftest records at import, because a
  test that imports them itself cannot see the bug), and a sweep of every product module reports
  any module-level object bound under the operator's real home that is not declared. 57 are
  declared. **The credential store and the session store were CLOSED on 2026-09-18** (`b1aa5af`)
  — they hardcoded `Path.home()` and read no environment variable at all. **55 remain**: the
  signing key, the executor token, the audit log and the executor's VM directories, all
  config-rooted and therefore NOT closed by the `GORGON_HOME` fix.

Direction: damage numbers LOW, work-done numbers HIGH, and **only meaningful as a pair** — a door
that does nothing scores perfectly on damage and 0/41 on recall. Recall held 100% at every step
while false repair fell from 54.3% to 0.0%.

## 4 · What is NOT measured — declared, not omitted

- **Real operator language.** Every number above is over hand-written cases or synthetic
  template-filled sentences. `stop the antiseptic vm` is not a thing anyone types. The instrument
  built to measure real input is the persona marathon, and it is EMPTY (2000/2000 rows fell back
  to clean text). Until that is repaired, nothing here describes a real request.
- **Bare-name lists without commas**, and **value respeaks without commas** — named out of scope
  by `_first_cut`'s own note.
- **`fleet` as a verb — RULED IN, AND THE BLOCKER IS NOW LOCATED (2026-09-18).** It is a real
  operation: `orchestrator/ai/chat/commands/fleet.py` broadcasts `exec|stop|launch|ping|status`
  across a labelled fleet, and `gates/safety.py` y/n-gates `exec` and `stop` as *"the high-stakes
  fleet actions"*. **The door cannot see a blast-radius command.** Admitting it turns
  `launch the fleet even though the lab network is slow` into a patient of `even though`.
  Measured, not assumed:
    · it is NOT a clause cut — `_first_cut` and `merge_cut_points` both return nothing here
    · `DUAL_CLASS_VERBS` does NOT reach it, and adding it there turns
      `test_clause_cuts::test_the_declared_duals_are_grounded_in_the_manifest` red — `fleet` is
      a LABEL, not a kind with creators, so the 2026-09-18 derive-from-the-manifest ruling
      excludes it and its guard says so
    · the fix is the determiner-position test — *a word behind `the` is a noun, not a verb* —
      which `pass2`'s rule 6 already runs (`nxt in CUT_DETS`) and which **`pass1` runs nowhere**,
      across its five `_operation_words` call sites (406 · 702 · 989 · 1032 · 1408)
  ⇒ **THIS IS READ PASS-1 WORK, NOT FRONT-DOOR WORK**, and it belongs to phase B2.
- ⚠ **THE DOOR IS NOT ON EVERY PATH OPERATOR TEXT ENTERS BY** (found 2026-09-19). The 2026-08-19
  direction was *"ONE normalization layer at the reader's front door, before ANY construct
  reads."* It is one layer inside ONE construct — `pipeline.run` (`pipeline.py:287`). Two other
  production paths read raw text, and both were measured, not assumed:
    · `orchestrator/door.py::facts` — the ROUTING door, whose own docstring says it *"runs on
      every request that arrives"*. `stpo every vm` and `stopevery vm` yield `acting=()` raw and
      `acting=('stop',)` through the door — **2 of 6 probes differ**, i.e. the regime ladder can
      read a typo'd order as carrying no verb at all.
    · `reading_answers.settle` — the operator's REPLY to a clarifying question. `its a netwrok`
      settles to nothing raw and to `network` through the door — **2 of 6 probes differ**, and
      that module's own docstring says a clarification that fails *"will be re-asked forever
      with no clue why."*
  ⇒ Neither is a defect IN the door, and neither is measured by anything in this seal. **The
    seal certifies the door, not its reach.**

  ⇒⇒ **AMENDMENT, 2026-09-19, AFTER THE ATTESTATION.** Both paths were WIRED the same day this
    was signed: `door.py::facts` and `reading_answers.kinds_named` now normalise through the
    door before they read, and `tests/test_language_layer.py::test_the_front_door_is_on_every
    _path_operator_text_enters_by` guards it — proven able to fail against the unwired code.
    `Facts.request` keeps the operator's own bytes; only the READING is normalised.
    ⇒ **THE ATTESTATION'S EXCLUSION STANDS AS WRITTEN AND IS NOT REPAIRED BY THIS.** §6 says the
      operator does not attest the door's REACH, and that remains true: a guard in the language
      layer is not an instrument in this seal, and nothing here MEASURES reach. The gap is
      closed; the seal still does not certify it. **A signed document is amended, not edited.**

- **A corpus at 100% no longer DISCRIMINATES.** It can catch a regression; it cannot find a
  defect. On 2026-09-18 adding fourteen words minted 70 latent traps and the corpus — at 100% —
  was blind to every one. A random sweep sampled two. **The corpus guards; the sweeps discover;
  the fingerprint catches staleness neither can see.** Three instruments, three blindnesses.

## 5 · ⚠ WHO AUTHORED THE GOLD — the line that decides what this seal is worth

**Claude wrote all 161 door cases and all 29 cut cases. The operator has adjudicated the 10
that no external authority settles, and overturned one of them.**

The plan for this work said, in bold: *"You annotate this, not me — the fixer never approves
their own fix."* **For two days that was not followed** — Claude wrote every case and adjudicated
every one. It was followed on 2026-09-19, and the first thing the operator's review produced was
an OVERTURN (`am-0027`) of a case whose stated reason contradicted their own earlier ruling. The
review found something. That is the argument for the rule.

What mitigates it, exactly and no further:

- **Gold was written BLIND** — from the module's stated contract, with the door not run, and
  frozen before it was scored.
- **Disagreements were surfaced, never retro-fitted.** One turned out to be Claude's own gold
  error (`anyway`, two cuts not one) and is recorded as such in the corpus.
- **The split cases are adjudicated by an outside authority** — `/usr/share/dict/american-english`
  decides whether a word is English, and Claude does not.
- **The `ambiguous` gold is re-derived from the catalogue** by `test_door_corpus`, which never
  calls `FD.read` — so those answers cannot have been read off the door.

What is NOT mitigated:

- **Which cases exist is Claude's choice, and that choice IS the measurement.** A different 161
  would give a different number. The operator ruled on the ten that had no other authority; they
  did not choose which ten existed.
- ~~**The 8 precision traps are POLICY**~~ — **THIS WAS WRONG, corrected 2026-09-19.** They are
  mechanical: the door never repairs a real English word, verified three ways (every trap token
  is in the dictionary and survives; of 254 dictionary words one edit from a control word that
  the veto set does not name, **0 of the 12 substantive ones are damaged**). The dictionary
  decides them, exactly like the split cases, so they need no adjudication. **The policy was on
  the other side and was not being reviewed at all**: the 20 `must_repair` cases where the door
  CREATED a control phrase from noise. The charter in §0 settles those.
- **The 29 cut cases are the weakest ground.** No dictionary settles a clause boundary, and one
  of the 29 was already wrong once.

**The review that closes this is 10 cases**, and it is DONE.

The other 175 have an external authority, are mechanically derived from a declared closed set,
or belong to another surface:

| | left the review because |
|---|---|
| 8 precision traps | mechanical — the dictionary decides, see above |
| 29 clause cuts | **READ's taxonomy, not the door's** — operator ruling 2026-09-19, §1 |
| the rest | derived from a declared closed set, or decided by `/usr/share/dict/american-english` |

**THE OPERATOR RULED ALL TEN ON 2026-09-19** (`am-0001…0006`, `am-0024…0027`):

- **Nine upheld** — the six lexical ties and three of the four narrowing controls.
- **One OVERTURNED: `am-0027`.** *"We use the grammar here to understand that snapshot here is
  an ACTION rather than a noun."* The gold had declined `have you snapshto it` as `unlicensed`
  on the stated reason that *"snapshot is a kind noun"* — which contradicted the operator's own
  2026-09-18 `DUAL_CLASS_VERBS` ruling. **That was the defect describing itself as a rule**, and
  it was surfaced to them as a CONFLICT rather than resolved by its author.
  ⇒ Fixed at the cause: a dual now gets BOTH slots in the sim check. The chain tested
    `cand in nouns` first, so the verb branch was unreachable for exactly the words whose whole
    point is that POSITION decides. `artifact` and `checkpoint` still decline — they are not
    declared duals — so the three upheld narrowing controls are untouched.
  ⇒ Re-deriving the veto sets against the widened `ops` minted **11 new `FALSE_FUSIONS`**
    (`forget`, `into`, `setup`, `within` …). The fingerprint caught them; nothing else would
    have.

## 6 · Attestation

> Certification is the operator's. Three shapes were offered on 2026-09-18 — **full** (gold
> reviewed and attested) · **scoped** (the instrument certified, gold authored by Claude and
> reviewed at a stated level) · **deferred** (the factual record signed now, the gold attested
> later). The review completed on 2026-09-19 and the operator took **SCOPED**, which is the
> honest shape: the 10 cases with no external authority were adjudicated, and the other 175
> were not, because something else already decides them.

```
CERTIFIED BY:          Tinshemet  (operator)
DATE:                  2026-09-19
SCOPE OF ATTESTATION:  SCOPED — the instrument, and the gold at a stated level.

  I attest that the factual record in sections 1-5 is what was measured, over the bytes named
  in section 2, by the code at the commit named there.

  I adjudicated the 10 cases that no external authority settles. Nine I upheld; one — am-0027 —
  I OVERTURNED, and it was fixed at its cause rather than in the case. Claude authored every
  case in both corpora, and WHICH cases exist remains Claude's choice, which section 5 states
  plainly and this attestation does not repair.

  I do NOT attest:
    · the clause-cut rule — it is READ's taxonomy and belongs to READ's seal (section 1)
    · that the door describes REAL OPERATOR LANGUAGE — it does not, and section 4 says so:
      every figure here is over hand-written cases or synthetic templates, and the instrument
      built to measure real input is EMPTY
    · anything about the door's REACH — it is not on every path operator text enters by
      (section 4), and this seal certifies the door, not its wiring
```

⇒ **ENTERED BY CLAUDE ON 2026-09-19 AT THE OPERATOR'S INSTRUCTION** (*"sounds good, sign it"*),
  in the session that produced the work above. Recorded because a seal that hides who typed the
  signature fails the same way as one that hides who wrote the gold — and because the fixer
  typing the attestation is exactly the shape section 5 exists to expose. **The decision is the
  operator's; the transcription is not theirs, and a reader is owed the difference.**
