# Medusa — the node set, settled before the surface

Written 2026-07-26, before any human-writable syntax exists. The order is deliberate: a
surface designed for four node types and then retrofitted to nine is the expensive
mistake this project keeps saying it wants to avoid. Everything below is a shape to react
to, not a decision already taken.

Today's four — `new`, `call`, `foreach`, `ensure` — carry ladder rungs 4–7 (4/4, rung 6 at
less than half the English path's cost) and stop at 8. Every stopping point has a name,
and this document is the list of names.

---

## What the ladder actually proved is missing

| rung | fails because | needs |
|---|---|---|
| 8 carve-out | `SELECT` cannot exclude — "every vm except db" is unwritable | `NOT` |
| 10 derived set | one creator per kind; "create by cloning" unsayable | creator choice |
| 11 result-dependent | the ping answers are **discarded** — nowhere to put them | result binding **+** `if` |
| 13 re-entry | `NEW vm x5` against a world already holding five | (idempotency, below) |

Note rung 11 carefully: **`if` alone does not fix it.** The condition is a call's answer,
so a conditional with nowhere to put that answer still cannot express the goal. Result
binding is what makes the conditional useful on the case that motivated it.

---

## 1. Predicate combinators — `NOT`, `AND`, `OR`

The smallest change and the one with the most reach, because predicates already appear in
three places: `ensure`, contract `goal_predicate` clauses, and (later) trigger conditions.

```json
{"shape": "not", "of": {"shape": "count", "select": {...}, "eq": 0}}
{"shape": "all", "of": [ {...}, {...} ]}
{"shape": "any", "of": [ {...}, {...} ]}
```

`NOT` is needed in **two positions**, and they are not the same operator in the same
place. Doing one without the other leaves rung 8 unwritable:

```json
// inside a predicate
{"shape": "not", "of": <predicate>}

// inside a SELECT — this is what rung 8 needs
{"kind": "vm", "not": {"name": "db"}}
```

## 2. Result binding — `graft`

```json
{"op": "call", "tool": "guest_ping", "args": {"name": "$item"}, "graft": "answer"}
```

The bound value is the tool's own result object, so `$answer.reachable` is readable by a
predicate. This is the construct the Barenboim exercise flagged on day one and rung 11
measured: observation feeding a later step is most of what an investigation *is*.

**Open question worth settling now:** inside a `foreach`, does `graft` bind per-iteration
(overwritten each pass) or accumulate into a list? Per-iteration is simpler and is what a
conditional inside the loop needs. Accumulation is what "collect all the answers, then
act" needs. They are different features and pretending otherwise will hurt.

## 3. Conditional — `if` / `else`

```json
{"op": "if", "cond": <predicate>,
 "then": [ <statement>, ... ], "else": [ <statement>, ... ]}
```
```sql
IF NOT $answer.reachable {
  stop_vm(name: $item);
} ELSE {
  add_label(name: $item, label: ok);
}
```

**Constraint to hold:** `cond` is a PREDICATE, never a free expression. The moment
conditions become arbitrary expressions we are writing a general language, and the "no
parser — validation is schema-checking" property that makes this cheap is gone. Anything
a condition needs to say, the predicate language should learn to say.

## 4. Loop — `while` (DROPPED 2026-07-26)

Recorded with a reservation, stated plainly.

```json
{"op": "while", "cond": <predicate>, "do": [ ... ], "max": 10}
```

`max` is **mandatory, not optional**. A loop over external state is unbounded by nature,
and the harness already carries a thrashing bound because unbounded retry was a *measured*
failure, not a hypothetical one.

The reservation: "keep doing X until Y holds" is what `ENSURE` + derivation already does —
declaratively, with a bound, and self-correcting. Rung 7 is exactly that case and it works
*without* a loop. Before `while` earns its place, it is worth naming a goal that needs it
and that `ENSURE` cannot express; if none turns up, the language is smaller for it.

## 5. Failure handling — `ifails` (try/catch DROPPED 2026-07-26)

```json
{"op": "try", "do": [ ... ], "catch": [ ... ]}
```

Two things to get right, both about not undermining machinery that already exists.

**It overlaps `ALTERNATIVES_TOOL`.** The engine already has OR-trees — try this, else that
— and the CE gate *prices* those alternatives. `try/catch` is plausibly the program-level
spelling of that, and shipping both without connecting them means two mechanisms for one
idea, which is the SSOT collapse the unified rule set was built to end.

**A `catch` must not swallow.** The design's posture is that failure routes to REVISION
carrying an objection; a handler that quietly recovers defeats the honesty layer. So a
`catch` should RECORD what it caught into the ledger and remain visible in the close —
compensation, not concealment.

## 6. Concurrency — a flag before a stream

The motivation is real: launching fifty VMs serially is slow. The cheap form first:

```json
{"op": "foreach", "select": {...}, "call": {...}, "parallel": true}
```

That buys the concurrency win with no new node types and no new execution model — the
gate, ledger and audit keep working unchanged. Dart-style streams with `yield` are a much
larger addition and should be justified by something `parallel` cannot do.

Concurrency also sharpens an open question from the design note that is currently
academic: **query freshness** — live per statement, or a snapshot at procedure entry? A
parallel `foreach` can mutate the set it is iterating. That must be answered before
`parallel` ships, not after.

## 7. Idempotency — probably NOT a node

Rung 13 fails because `NEW vm x5` runs against a world already holding five. The tempting
fix is a construct; the better fix is that `new` and `call` SKIP when their effect already
holds — which is what the design note already claims `ENSURE` gives "by construction", and
what the harness's already-satisfied pre-emption does today for English steps.

Recorded here so it is not solved twice.

---

## What this costs, honestly

**Blocks arrive.** `if`, `while` and `try` all carry statement lists, where `foreach`
deliberately carries a single call — a choice made because measured evidence said
llama3.1 emits flat lists reliably and struggles with nesting.

**Constrained decoding changes that calculus.** Nesting is now enforced by the decoder
rather than hoped for, which is why the strict `oneOf` schema works today and failed
through the tool-call channel this morning. The original objection is much weaker — but
this is still the biggest thing the expansion does to the language's shape, and it should
be spent knowingly rather than discovered.

**The visitor grows.** Four cases become eight or nine. That remains small, and the split
holds: vocabulary is data (the manifest says a shape exists), semantics are code (what it
does). A new op needs a visitor case, and that is better as an explicit cost than a
silently unexecutable statement.

## Suggested order, by evidence

1. **`NOT` / `AND` / `OR`** — smallest, unblocks rung 8, and predicates are shared by three
   consumers so the reach is wide.
2. **`graft` + `if`/`else`** — together, because neither fixes rung 11 alone.
3. **Measure.** Those two steps alone could take the ladder from 4/13 to 7/13.
4. Then decide `while`, `try/catch` and `parallel` with that data rather than ahead of it.

Steps 1–2 are the ones the ladder demands. Everything after is judgement, and better made
once the first two have been measured.


---

## Surface decisions, settled 2026-07-26

**Upper-case keywords, C-family braces.** `DO … END` became `{ … }`, and the redundant
`AS` after a procedure signature is gone — the brace already opens the block, and two
openers is one more thing to get wrong when writing by hand.

The braces are not cosmetic. Every construct still to come — `if`/`else`, `ifails` —
carries a statement LIST, and `DO … END` does not nest legibly. Fixing the shape before
those land is much cheaper than migrating procedures already written in the old one.

**`NEW 5 vm(...)`** rather than a trailing multiplier: it reads the way the request does.
A `$parameter` count reads the same way, and used to vanish from the rendering entirely.

**The loop variable prints as `$item`,** which is what the body actually references. It
printed `x` before — two names for one thing, in the single place a reader most needs to
follow the binding.

```sql
PROCEDURE test_fleet(X INT) {
  IMPORT core;

  LET net = NEW network;
  LET vms = NEW $X vm(os_type: linux);
  FOREACH $item IN $vms {
    add_label(name: $item, label: test);
  }
  FOREACH $item IN SELECT vm WHERE label = 'test' {
    add_vm_to_network(net_name: $net, vm_name: $item);
  }
  ENSURE REACH(SELECT vm WHERE label = 'test') >= $X;
}
```

**`graft` names a result** — `into` was the placeholder, `assert` was rejected (it means
"check this is true" everywhere else, and that operation is already `ensure`), and `embed`
collides with embeddings in an AI-adjacent codebase. Written form is `LET` either way,
since naming a result and naming a resource are the same act.
