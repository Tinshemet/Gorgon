# Rules for building the two-pass pipeline

Written 2026-08-08 at the operator's instruction, before any of it is built.

> *"Over the last month you have been writing code without thinking first, meaning half the
> time we chase bugs you made."*

That is accurate and this document exists because of it. **The cost is not the bug.** The cost
is that a self-inflicted bug is indistinguishable from a real finding until it has been chased
— so it spends the operator's attention while wearing the costume of a measurement.

Every rule below is derived from something that actually went wrong, and names it. A rule
without a corpse is not in this document.

---

## 0 · When to come back to this page

Return here, and re-read from the top, whenever any of these is true:

- a test fails for a reason that surprises you
- you are about to write the same thing a second way
- you are about to change something you did not write in this session
- you notice you have been editing for more than one item
- you feel uncertain and are about to guess in order to keep moving
- the operator says something is wrong

**When uncertain, the move is never "write more code to find out".** It is: run the smallest
thing that would tell you, or ask. Guessing forward is how every entry in §2 happened.

---

## 1 · Scope of a session

**S1 · One item per session.** The plan names the item. Finish it or report it unfinished. Do
not start the next one because the current one went quickly.

**S2 · Approval of a design is not approval of an implementation.** A schematic being approved
means the design is right, not that code may begin. Building starts when an item is agreed as
the session's item.

**S3 · Park findings, do not chase them.** A defect found mid-item gets written down and
reported, not fixed on the spot — unless it blocks the item. Every drift has cost a withdrawal
and a re-measurement.

**S4 · Say what is superseded.** When new work obsoletes old work, say so plainly and in the
same breath. Dead code that still looks alive is the most expensive thing in this repo.

---

## 2 · Writing

Each of these is a rule because it already went wrong. The failure is named.

**W1 · Never leave a symbol nothing calls.** After adding any constant, function, method or
branch, grep for its callers before moving on. If the count is zero, either wire it in the same
turn or delete it.
> *`SETTLES` was declared, added to two tables, and the block that emits it never inserted. It
> sat in the tree looking implemented. This is the dominant defect class in the whole project
> and it happened inside code written to demonstrate a fix for it.*

**W2 · Structural edits use `Edit`, never a heredoc or `sed`.** A string replacement that does
not match is silent; `Edit` fails loudly.
> *W1's bug was caused exactly this way — a heredoc whose indentation did not match, replacing
> nothing and reporting success.*

**W3 · A rename is finished when the old name greps to zero.** Not when the definition changed.
> *`holes` -> `set_aside` left a live caller in another file.*

**W4 · Anything with two directions is round-tripped before it is trusted.** If there is an
encode and a decode, run `decode(encode(x)) == x` over every case available, in the same turn
the second direction is written.
> *`build()` silently dropped `observe`'s filter — turning "check the gateway" into "ping the
> whole lab" — and dropped `source` entirely. Both were found only by a held-out row.*

**W5 · Read declarations from the manifest; never re-list them by hand.** If the manifest knows
which attributes exist, which are observed, which are settable, which values are legal — ask
it. A hand-written list is a copy that will drift.
> *`filterable()` was built from `attrs` alone and omitted `observed`, so rung 11 blocked on
> `alive` — the exact attribute the rung exists to test. `choose_subject` matched the synonym
> list without the kind's own name, so "vm" matched nothing.*

**W6 · Never half-apply a change.** If the wiring cannot be finished in this turn, revert the
half that exists. A suppressed question with nothing consuming the replacement is worse than
either end.
> *Gate 3's `supply()` derived a join and suppressed the question, and the consumer was never
> built.*

**W7 · Prefer deleting an option to adding a repair.** Measured five times: only subtractive
moves have ever worked here. If the fix is "and then we correct it afterwards", stop.

**W8 · When a value can be computed, do not ask for it.** Anything derivable from the manifest
or from another field is computed. Asking creates a second source of truth and a way to be
wrong.
> *This is why `settled` is computed from `observed` and never requested.*

---

## 3 · Verifying

**V1 · Every edit is exercised in the same turn, by running the specific behaviour it changed.**
Not the suite — the behaviour. The suite passing means nothing about code the suite does not
reach.

**V2 · `run_all.py` is the arbiter, never `pytest`.** `pytest` reports `check()`-harness files
as passing when they fail.

**V3 · Never diagnose from n=1.** Temperature 0 is not deterministic on this stack. A single
run is an anecdote; a claim needs at least three.

**V4 · Never run a model probe and a suite at the same time.** They contend for the GPU and the
results of both become noise.

**V5 · A measurement gets its expected answer written down BEFORE it runs.** A held-out set is
sealed and committed before the machinery that has to pass it.

**V6 · Report the number that came back, not the number that was hoped for.** If the result is
0 of 14, the sentence is "0 of 14".

---

## 4 · Specific to this design

**D1 · The symbol table is the contract.** Pass 2 may reference only names pass 1 declared and
gates 1–2 confirmed. An unresolvable reference is a hard error, never a warning and never a
silent repair.

**D2 · Pass 1 asks for nouns only. Pass 2 asks for verbs only.** If a field in pass 1 starts
describing what happens, it belongs in pass 2 and the schema is wrong.

**D3 · `settled` is computed from the manifest's `observed`, never asked.** See W8.

**D4 · One question per model call.** Measured: the same model, the same sentences — eight
fields returned the identical answer every time; one question per call was 10 of 10. The single
exception is a pair of questions that disambiguate each other, and that exception must be
justified by a measurement, not by convenience.

**D5 · Every schema field is required, with refusal as an explicit positive answer.** An
optional field returns `{}`. Put the refusal option first so a relapse shows up as refusals
rather than as plausible-looking answers.

**D6 · No free text in a condition.** The moment a condition field takes prose, the parsing
problem returns wearing a different hat. Conditions are closed grammar over declared names.

**D7 · Gates 1–2 must never read a program shape.** They see declarations. If a gate needs to
know what Medusa looks like, it is the wrong gate.

---

## 5 · The honest-report rule

**H1 · State what was not done.** Unfinished, skipped, untested, assumed — say which.

**H2 · A correction is one sentence and then the work continues.** No re-litigating.

**H3 · Distinguish "measured" from "believed".** If it has not been run, it is not a result.
