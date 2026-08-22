# READ — the closing document (DRAFT, finalized at the v3 freeze)

*Drafted 2026-08-20 night. The v3 numbers and the stability bars land at the freeze;
everything else below is settled and operator-ruled.*

## What READ is

The seam turns one operator sentence into facts the rest of the system can use: object
spans, action clauses with typed attachments, triggers, evidence, rules, queries,
reports. It is measured by a frozen, operator-certified, hash-bound eval (the seal
pattern): every gold label was accepted by one keypress of the operator's, every fix
was measured against that gold with the clean row required to hold, and a release
changes only by explicit commit.

## The architecture — a thin model waist

    deterministic READING            one model QUESTION            deterministic LAW
    tokens → closed-class rules  →   per clause: which op,     →   licence · gates ·
    spans, clauses, constructs       on which handle, value        typed repair · IR

The model points (anchors) and answers one closed-menu question per clause. Everything
else — boundaries, constructs, triggers, junk repair, role typing — is positional
grammar over closed classes, with domain vocabulary read from the manifest and the
stores (SSOT: every closed set has exactly one home; nothing domain is hand-listed).

## The conventions (operator rulings, chronological)

grammar decides, never meaning · a span is verbatim bytes at real offsets · the
exception is its own object (scored inverted) · a query PRODUCES (wh-NP is the span;
the asked property stays unmarked) · `tell me` before an interrogative is a wrapper ·
courtesy marks nothing · every malfunction predicate is testimony · evidence is opaque
· an after-clause IS a trigger; bare `then` is sequence · manner is HOW · the sim-check
principle: a repair fires only where the grammar votes — no vote, no change · the
typo-risk ladder: recognition may widen through the stores, authority narrows with
blast radius · a typo'd name is the name.

## The noise thesis (v2/v2.1, closed)

Six noise classes — terse, typos, no-punct, voice, fused (+ two reserved: embedded-junk,
code-switch — RULING AT FREEZE: built or declared out of scope). All measured to zero
act loss and at-or-near clean span rates via the front door: junk out ASAP, one layer
down, offset maps composing back to original bytes, every repair a notice.

## The numbers

    baseline (certified, 2026-08-18):  detect 84% · exact 27% · attach ~60% ·
                                       triggers 4/8 · hallucinations 78
    v2.1 close (2026-08-20):           detect 97% · exact 95% · attach 97% ·
                                       triggers 100% · hallucinations 4
    stability (n=3, same code, 08-20): BYTE-IDENTICAL across all three runs, every
                                       cell, every stratum — the wobble band is ZERO.
                                       The historical ±2-4 attach flicker died when
                                       the attach mechanisms went deterministic.
                                       (clean settles at 76/79 attach across n=3.)
    v3 baseline:                       «fill at freeze»
    v3 close:                          «fill»

## Declared floors and non-goals

- **Model-variance floor**: ±2–4 attach across cold runs at temp 0 — the model's own.
- **Out of READ, by design (the operator's own closure, 08-20)**: OPEN VOCABULARY is
  answered by the archive + encyclopedia — a new word is taught, never patterned;
  FREE SEMANTICS is mostly moot because the confirmation system (+ the typo-risk
  ladder) stands between any misread intent and a harmful act; CROSS-TURN comes AFTER
  v3 — it needs a good reader beneath it and is handled at ROUTE, not READ. Also
  route's: alternation choice, preference weighting. Deferred: value-copy
  comparatives, undo (cross-turn).
- **Domain-unlocked, not reading-unlocked**: attribute-value attachments arrive with
  attribute classes; file-domain readings arrive with file kinds (the media gap).

## Declared gaps in the frozen sets

- **FLAVOUR IS UNMARKED IN v1/v2/v2.1 (declared 2026-08-22, not repaired).** The mood
  channel (schema v2.4) arrived after those releases were sealed, so three certified clean
  cases carry a flavour token with no `mood` on it: `sc-0002` ("stop alpha — sorry, i meant
  beta", deference), `sc-0004` ("label the vms test, er, staging", filler) and `cc-0001`
  ("when you get a chance, stop the test vms", deference). Measured against the codex's own
  closed classes, not by eye. **They were NOT retro-fitted, because a seal means a seal** —
  amending them would re-open certified gold and is a release decision, not a fix. A reader
  scored against v1/v2/v2.1 is therefore never billed for a mood it did miss, and never
  credited for one it read. v3 is the first set where mood is scored.

## What v3 added

«fill at freeze: 22 strata, the store-fixture mechanism, the schema rulings (manner,
store, pairwise grouping), the twins, the final table»
