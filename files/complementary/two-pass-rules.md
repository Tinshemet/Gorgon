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

**W6 · Never half-apply a change. Test before applying, wire it when you can, test again after
wiring.** Three beats, and none of them is optional:

1. **Test before applying.** Prove the change does what it claims, on the smallest case that
   shows it, *before* it goes into the tree. A change that has never been run is a guess with
   good formatting.
2. **Wire it when you can.** Anything that can be connected to its real caller in this turn is
   connected in this turn. If it genuinely cannot be, revert the half that exists — a
   suppressed question with nothing consuming the replacement is worse than either end.
3. **Test again after wiring.** Exercise it *through the real caller*. Passing in isolation
   says nothing about being reached, and being reached is the thing that keeps failing here.

> *Gate 3's `supply()` derived a join and suppressed the question, and the consumer was never
> built — beat 2 skipped. `SETTLES` was declared, tabled, and never emitted — beat 3 would have
> caught it in seconds. `_offered()` survived a rewrite that stopped calling it — beat 3 again.*

**W7 · Prefer deleting an option to adding a repair.** Measured five times: only subtractive
moves have ever worked here. If the fix is "and then we correct it afterwards", stop.

**W7b · NEVER ASK THE MODEL TO DESCRIBE. ASK IT TO MOVE.** A question whose answer is an
account of its own understanding degrades; a question whose answer is a choice from a closed
set performs. Measured repeatedly on one day, same model, same sentences:

| asked to DESCRIBE | asked to MOVE |
|---|---|
| "list the conditions" -> `[]` | "does this mean alive=false?" -> correct |
| "what does 'it' refer to?" -> *"the request itself"* | "what has to be done?" -> resolved `it` to beta, 3/3 |
| "is this create or use?" -> 62-85% | "what does the request DO to it?" -> killed the create-bias |
| "list the things" -> chunks the sentence into parts | "point at an anchor" -> 14/14 |

> *The operator, 2026-08-08: "it CAN do references, but seems to fail when actually
> presented."* It resolved a pronoun perfectly while never being asked about the pronoun.

⇒ THIS IS WHY ANCHOR-AND-SCAN WORKS. We stopped asking the model to describe a sentence and
  started asking it to point at part of one. Everything else is read by code.

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

**D8 · THE VERB DECIDES WHAT THE NOUN IS — attribute, action, object, or mood.** A noun has no
role until a verb gives it one, and the same noun takes different roles under different verbs:

| | | |
|---|---|---|
| give X the `'fleet'` **label** | light verb + attribute-noun | an **attribute** |
| **take** a snapshot | light verb + kind-noun | an **action** |
| **restore** a snapshot | contentful verb | the **object** itself |
| **make sure** there are two left | light verb + adjective | a **mood** — achieve, not do |

> *The operator, 2026-08-09: "snapshot IS an object but in this context its also the
> verb/action" · "find me a snapshot, and take a snapshot are 2 different actions with only the
> verb being different, this is again the create/use".*

This is D-something rather than a writing rule because it decides **which pass owns a word**,
and getting it wrong puts a bogus object in the symbol table — which pass 2 then dutifully
operates on. Rungs 4, 7, 12 and 13 all fail this way and **not one of them is a pass 2 error.**

⇒ **THE NAMES ARE ESTABLISHED, SO USE THEM.** `snapshot` is a **dot object** (`event•object`)
  in Pustejovsky's Generative Lexicon, and the verb performs **type coercion** to pick a facet.
  `take a snapshot` / `give a label` / `make sure` are **light verb constructions** (a.k.a.
  support verbs) — the verb empties itself and the noun carries the predicate. Whether the noun
  pre-exists is the **effected vs affected object** distinction (Fillmore), which is this
  project's create/use fork under its proper name.

⇒ **AND THE MANIFEST ALREADY HOLDS THE QUALIA STRUCTURE, so this is a lookup and not a
  judgement.** GL's AGENTIVE role (how a thing comes into being) is our `creators`; its TELIC
  role (what it is for) is our `acts`; the attribute slots are our `setters`. **If the
  governing verb is a creator of that kind the noun is the product; if it is an act or setter
  taking that kind the noun is an argument.** The light-verb list is a closed class of English
  — `take · give · make · do · run · get · have · carry` — with the same status as
  `COMPARATORS` and `ENUMERATORS`.

⇒ **THE MOOD ROW IS NOT A PARSING RULE AND MUST NOT BE TREATED AS ONE.** Every rung filed as a
  *reasoning error* — 7, 9, 14 — is a `make sure`. The request is in the ACHIEVE mood and pass
  2 only knows how to DO, which is why no rephrasing fixed rung 14 and why `delete_vm(vms)`
  keeps appearing: asked to ENSURE two machines remain, the only thing sayable is to delete
  them. Medusa has `ACHIEVE`; this pipeline does not reach it.

**Two things this rule already indicts, and they are named so they cannot be forgotten:** the
shipped fix for rungs 4 and 13 keys on a QUOTED word beside an attribute, which is a proxy for
the attribute reading — it works, it is safe, and it is the symptom rather than the cause. And
`snapshot.creators.create` declares only a tool, with **no source argument**, so nothing says
`create_snapshot` consumes a vm — which is why gate 3 excludes creators from its
wrong-kind-operator rule and why the clean version of the fix cannot be written yet.

---

## 5 · The honest-report rule

**H1 · State what was not done.** Unfinished, skipped, untested, assumed — say which.

**H2 · A correction is one sentence and then the work continues.** No re-litigating.

**H3 · Distinguish "measured" from "believed".** If it has not been run, it is not a result.

**H4 · Always show the current state of the code, simply and informatively.** When reporting on
code, paste what it *is* — not a description of what it does. A summary is a claim about the
code; the code is the evidence, and the operator should never have to take the claim on trust.

Simply and informatively means: the part that matters, as it stands right now, short enough to
read. Not a whole file, not a diff fragment with no context, and never a paraphrase.

> *Every entry in §2 was invisible in my own reporting and visible the instant the code was
> looked at. `SETTLES` "was added". `_offered()` "hands the model its legal moves". Both
> sentences were true of the source and false of what ran.*
