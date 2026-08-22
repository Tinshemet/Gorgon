# `orchestrator/languages/` — the plain-text layer, one folder per language

Gorgon's chain is **plain text → computational model → code**. Only the first link is
language-dependent, and this folder is where it lives. Everything here reads a sentence and
produces a **language-neutral state**; everything downstream (the planner, the gates' verdict,
the executor) reads that state and never the sentence.

    orchestrator/languages/
      README.md              ← this file: the contract, the wiring, how to add a language
      english/
        codex.py             ← THE LANGUAGE CODEX: every closed class English is read with
        seam/                ← the English scaffold: READ (pass 1 · pass 2), front door,
                               speech acts, testimony, temporal, gates 1–4, pipeline

**Gorgon reads English, by declaration** (V2-LEDGER #12, 2026-08-22). A second language is
not a translation of this one — the words cross, the grammar does not. It is a second
scaffold that produces the same neutral state, certified against its own gold by someone who
reads it. Until one exists, a token from another script in a *licensing* slot (verb, role
marker, trigger marker) is an automatic REJECT — "the verb is inexpressible" — never an
UNKNOWN bounce, never a translation. Flavour (greetings) and names pass through the slot;
they carry no authority.

## 1 · The contract — what a language must produce

The neutral state is `pipeline.Run` (english/seam/pipeline.py). A language's `run(request,
board, world, model)` returns one, and nothing outside this folder may depend on anything
else the scaffold knows. Its fields, by what downstream reads them for:

| field | what it is | read by |
|---|---|---|
| `declarations` | the OBJECT rows — `Declared(kind, span, name, where…)` at **original** offsets | pass 2, gates, the planner |
| `table` | handles over the rows (`Symbol(handle, row)`) — the enum pass 2 answers in | gate 3, the program |
| `operations` | `Operation(operator, on, value)` — manifest operators over handles, never verbs | the planner, gate 4 |
| `conditions` · `goals` | what will be true once run · the states an ACHIEVE asks to hold | the engine |
| `asks` · `questions` · `bounces` | to the OPERATOR · the same, addressable · to the MODEL | the door |
| `illegal` · `discarded` · `suggested` | what a gate refused · what nothing warranted · legal-but-unasked | the door, the verdict |
| `linguistics` · `notices` · `repairs` | the gate-4 findings · housekeeping surfaced · what the harness changed | the door |
| `produces` · `outcome` | `program` / `answer` / `neither` · the verdict word | the door (routes on `produces`) |
| `teaches` · `governs` · `answered` | proposed archive entries · proposed rules · lookups needing no program | the door, the archive |

Three invariants every language must keep, because the eval and the gates assume them:

1. **Offsets are original bytes.** The front door may build a working VIEW (typos fixed,
   fillers dropped) but every span reported maps back to the sentence as typed
   (`front_door.View.to_original`). Gold is char offsets; a language that rewrites text
   cannot be scored.
2. **Operators, not verbs.** Pass 2 answers with a manifest operator (`stop_vm`), chosen from
   the enum the board offers. The sentence's verb *licenses* the choice (a clause whose
   verb-position word is a segment of an offered operation may pick only that operation's
   family); it is never emitted. An unrecognised verb licenses nothing — it rejects.
3. **Slots, not shapes.** The roles that come back — patient · destination · source · value ·
   excluded · evidence · reference · beneficiary — plus the channels on an act (trigger ·
   manner) and the act's kind (instruct · query · rule · report) ARE the key downstream.
   ROUTE and RESOLVE are functions of that signature, not of the language.

## 2 · The wiring — who calls the language

Pinned in `tests/test_language_layer.py`; a new caller is a decision somebody records.

| caller | what it takes from the language | note |
|---|---|---|
| `orchestrator/door.py` | `pipeline.run` · `linguistics.mood_of` · `pass1.agent_name` · `governing.rules_from` · `scan._index` · `scan.ENUMERATORS` · `temporal.CLOCK` | the last three are **English vocabulary leaking into the door** — a second language would need the door to read the codex, not `scan`. Finding, not fixed. |
| `orchestrator/ai/chat/shortcuts/plan.py` · `words.py` | `speech_act`, the two passes, the archive | the `plan`/`words` REPL shortcuts print what each stage read |
| `tests/bench/read_eval/runner.py` | `front_door.read` · `pass1.run_scanned` · `pass2.symbol_table/operations_by_clause/prepare/clauses_of` · `scan.clause_around/quoted_clauses` · `testimony.read` · `iso.is_condition` | the eval reads what production reads — every collector is a thing the seam reads |
| `tests/bench/*` · `tests/test_*.py` | module internals | 40 files, 152 import lines; all mechanical |

## 3 · The codex — where the language's words live

`english/codex.py` holds every closed class the scaffold reads with: determiners, pronouns,
prepositions, conjunctions, auxiliaries, copulas, wh-words, negators, contractions, hedges,
courtesy, openers, comparators, enumerators, magnitude phrases, naming cues, excluders,
temporal units/deictics/recurrence, testimony modals, retractions/corrections, destructive
words, reciprocals. One place, sectioned by the reader that consumes each class. A seam module
imports its classes from the codex and holds **no English of its own** — enforced by the test.

What is *not* in the codex, on purpose: check names (`OWNS`/`TAKES` — the gate vocabulary),
speech-act kind names, manifest segments derived from the board, and the in-module test
fixtures (`EXPECTED`, `CASES`, `WANT`). Those are the model's words, not the language's.

Ordering matters in several classes (longest-match-first for multiword phrases; the
contraction map is keyed by spelling). The codex is a Python module rather than JSON for
that reason — tuples keep order, frozensets say "membership only", and a regex fragment
stays a regex fragment. Behaviour-preserving by construction: the consolidation was proven
byte-identical on the v3 eval (`tests/bench/read_eval/results/`, 2026-08-22, seed 1).

## 4 · How to add a language

Not a translation. A scaffold. In this order, and the first two steps are paper:

1. **Measure the pointer's floor.** No tool does this today. What it needs: a pass-1 call
   over sentences in your language with certified span gold, scored on detection and
   boundary (the `read_eval` runner's scoring, pointed at pass 1 alone). The nearest existing
   pattern is `tests/bench/twopass/token_probe.py` — it builds production's exact call and
   sends it raw over `/api/chat` with the token counts kept — but it measures pass-2 cost
   and proposals on four English rungs, not pointing, so it is a starting pattern, not the
   probe. Small models tokenise non-Latin scripts badly (more tokens per word, less
   training data); if pointing is at chance, stop — there is no reader to build on (the
   five failed architectures are the proof that the model cannot read alone).
2. **Write the gold first.** A `cases/<lang>-v1.jsonl` in the read_eval schema, certified by
   a native reader through `review.py`. The schema is language-neutral: char spans, roles,
   channels. The corpus-is-spent lesson applies from day one — qualify before you score.
3. **Write the codex.** `languages/<lang>/codex.py` with the same section names as English.
   Expect classes that do not exist (no articles, no order/request distinction by form) and
   classes English lacks (object markers like Hebrew `את`, case, clitic prefixes). An absent
   class is declared absent, not faked.
4. **Write the scaffold** under `languages/<lang>/seam/`, producing `Run`. Reuse what is
   language-neutral by import — the gates, `effects`, `housekeeping`, `archive`, `issues`,
   the `schema` types — and rewrite what is not: `scan`, `speech_act`, `linguistics`,
   `testimony`, `temporal`, `front_door`, `iso`, and both passes.
5. **Write the 14 rungs natively** — `languages/<lang>/rungs.py`, `RUNGS: Dict[int, str]`.
   The ladder's *meaning* per rung is fixed (`tests/bench/rungs.py`); the wording is yours, as
   a speaker would actually ask. Then run the benchmark:

       PYTHONPATH=. python3 -m tests.bench.language_benchmark --language <lang> --runs 3

   It runs every rung through your scaffold and grades the **computational model** that
   comes out — operations with handles resolved to selectors `{kind, …where}`, plus the
   ACHIEVE goals — against the language-neutral answer key (`pass2.WANT` resolved + GOALS).
   Only unambiguous rungs are graded; the rest are shown. **CANDIDATE = every graded rung
   passes on every run.** The operator's criterion (08-22): *"if it can produce a correct
   computational model on the 14 rungs it is a candidate for the ability to port it over."*
   English, the reference, scores **7/8 graded** today (see §6).
6. **Wire it** at the door by language declaration, never detection-and-translation. A
   sentence in an undeclared script rejects.
7. **Seal it**: the `-cs` twin pattern (a foreign token in a licensing slot) becomes that
   language's control in the other direction.

## 5 · Inventory of the English scaffold (2026-08-22)

Classified by evidence: what the module imports, and how many closed-class English words it
held before the codex. *scaffold* = reads the language · *neutral* = reads the state ·
*mixed* = both, with the English named.

| module | lines | class | evidence |
|---|---|---|---|
| `scan` | 1263 | scaffold | 17 constants / ~270 words — GRAMMAR, OBJECT_OPENERS, COMPARATORS, ENUMERATORS, MAGNITUDE, LINKING… |
| `speech_act` | 1122 | scaffold | 22 constants / ~340 words — CONTRACTIONS(141), PREPOSITIONS, PRONOUNS, AUXILIARIES, WH_WORDS… |
| `pass1` | 1940 | mixed | DISTINCT, EXCLUDERS, PLURAL_PRONOUNS + 13 inline collections; the rest is the pointer protocol |
| `pass2` | 1423 | mixed | CLAUSE_WORDS, _CUT_DETS, _CUT_NEG + 5 inline; the verb licence is `[a-z]+` (English by construction) |
| `front_door` | 328 | scaffold | the view/offset map is neutral; 5 inline closed sets are English |
| `iso` | 398 | scaffold | HEDGES, EMPHATIC, BACKCHANNEL, TROUBLE, APOLOGY, FILLED_PAUSE |
| `linguistics` | 610 | scaffold | LIGHT_VERBS, ACHIEVE_MARKERS + 4 inline |
| `testimony` | 194 | scaffold | NEG_MODALS, NEG_DO, COPULAS, ITERATIVES, INDEFINITES |
| `temporal` | 268 | scaffold | UNITS, WEEKDAYS, MONTHS, DEICTIC, RECURRING, STANDING… |
| `self_repair` | 215 | scaffold | RETRACTIONS, CORRECTIONS, DANGLING(58) |
| `reading_answers` | 130 | scaffold | NEGATION, AFFIRMATION, SIMILE |
| `residue` | 406 | scaffold | RELATIONAL_WORDS |
| `schema` | 709 | mixed | the `Declared`/row types are neutral; PRONOUNS, RESTRICTORS, DETERMINERS, BOUNDARIES are English |
| `governing` | 126 | scaffold | CONTRACT_VERBS |
| `archive` | 663 | mixed | OPERATION_VERBS (forget/unlearn/discard) + 1 inline; the store itself is neutral |
| `gate3` · `gates12` | 484 · 425 | neutral | legality against the manifest; OWNS are check names |
| `gate4` | 816 | mixed | DESTRUCTIVE_WORDS, RECIPROCAL are English; the checks are neutral |
| `effects` · `housekeeping` · `issues` · `asking` · `surface` · `repair` | — | neutral | read the state; CASES/TAKES are fixtures and check names |
| `pipeline` | 934 | neutral | orchestration of the above; 1 inline collection |

The folder moves whole (operator, 08-22: `orchestrator/languages/english/seam`). The neutral
modules ride along because they are the scaffold's *runtime*, imported by the scaffold and
by nothing else; a second language imports them from here. Splitting them out is a later
step, taken when a second scaffold makes the line real.

## 6 · What the benchmark found on English (2026-08-22, seed 1, with the lab)

Graded 8 rungs, **PASS 7/8** — 1 · 2 · 3 · 5 · 11 · 12 · 14. Reported 6 (no unambiguous key:
4 · 6 · 8 · 9 · 10 · 13). Chain outcomes SERVE 7 · BOUNCE 3 · ASK 4.

**Rung 7 FAILS, and the cause is a precision defect, not a benchmark artifact.** *"make sure
exactly 3 vms carry the 'prod' label"* comes out as `count(vm) = 3` — the `label=prod` filter
is gone. Traced: every pass-1 stage keeps it; the loss is at the **front door**, stage 4 (N3,
"restore the missing clause break"), where `pass2.merge_cut_points` votes a comma before
`carry` — `"…exactly 3 vms, carry the 'prod' label"` — severing the relative predicate from
its noun phrase. An unfiltered count is the shape that **removes members** (the deletion rung's
own note in `tests/test_ghost_writer.py`), so this misreading bills precision, not
housekeeping. Not live — `pipeline.run` has no executing consumer — and not fixed here: N3 is
an operator ruling, and the fix belongs to whoever rules on it (a cut must not split a noun
phrase from a predicate that restricts it). Filed in the 08-22 handover.
