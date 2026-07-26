# Ladder rungs 4–7 as IR, written by hand

The design note (artifact `580d54ac`) prescribes this as the first thing to produce, and
says explicitly that it is **not code**: write the benchmark rungs as IR by hand, and
check that they say what the goals mean. An afternoon, no implementation. Only then
answer the question that carries real risk — can the local model emit valid IR for them?

This is that exercise. Findings are at the bottom; four of them, and two are load-bearing
enough to settle before any code is written.

The node set under test (design note §03):

| op | fields | meaning |
|---|---|---|
| `new` | `var`, `kind` | create a resource, bind it to a name |
| `call` | `tool`, `args` | one catalog tool, through the normal gate |
| `foreach` | `select`, `call` | apply ONE call to every member of a set |
| `ensure` | `predicate` | a postcondition over the registry |

Plus the derived `imports` header (§07). It is shown once, on rung 4, and elided
afterwards — nothing in this exercise varies it, which is itself the point of deriving
it rather than authoring it.

---

## Rung 4 — collective loop

> create 5 vms, put them all in a network, give them all the 'fleet' label, and make
> sure they all ping each other

Checker: `reach("fleet", minimum=5)` — at least five VMs carry `fleet` **and** all of
them share one common network.

```json
{
  "imports": [{"package": "core"}],
  "body": [
    {"op":"new","var":"net","kind":"network"},
    {"op":"new","var":"v1","kind":"vm"},
    {"op":"new","var":"v2","kind":"vm"},
    {"op":"new","var":"v3","kind":"vm"},
    {"op":"new","var":"v4","kind":"vm"},
    {"op":"new","var":"v5","kind":"vm"},

    {"op":"call","tool":"add_label","args":{"name":"$v1","label":"fleet"}},
    {"op":"call","tool":"add_label","args":{"name":"$v2","label":"fleet"}},
    {"op":"call","tool":"add_label","args":{"name":"$v3","label":"fleet"}},
    {"op":"call","tool":"add_label","args":{"name":"$v4","label":"fleet"}},
    {"op":"call","tool":"add_label","args":{"name":"$v5","label":"fleet"}},

    {"op":"foreach",
     "select":{"kind":"vm","tag":"fleet"},
     "call":{"tool":"add_vm_to_network","args":{"net_name":"$net","vm_name":"$item"}}},

    {"op":"ensure","predicate":{"reach":{"kind":"vm","tag":"fleet"},"min":5}}
  ]
}
```

**Does it say what the goal means?** Yes — and note the ordering is load-bearing in a way
the English never made explicit: the `foreach` can only select `tag=fleet` *after* the
labels exist. Write the attach before the labelling and it selects an empty set. The IR
makes that dependency visible; the English sentence hides it behind "them all".

**Statement count: 13**, against a 17-tool-call minimum. The `foreach` collapses five
attaches into one statement, which is the shape working as intended.

---

## Rung 5 — filtered collective

> launch every vm that is currently stopped

Seeded: `web` (stopped), `db` (running), `cache` (stopped).

```json
[
  {"op":"foreach",
   "select":{"kind":"vm","status":"stopped"},
   "call":{"tool":"launch_vm","args":{"name":"$item"}}}
]
```

**One statement.** This is the cleanest result in the exercise and worth dwelling on:
the filter is `select`'s `WHERE`, structurally inseparable from the action.

This is the rung the goal translator mangled worst — it split `"that is currently
stopped"` off as a second clause, turning the goal into `launch every vm`, which would
have started `db` too. In IR the filter cannot be separated from the call it filters,
because it is a field of the same node. That failure is not merely avoided; it is
unrepresentable.

---

## Rung 6 — partition

> create 3 vms labelled 'red' and 2 vms labelled 'blue', put the red ones together on
> their own network, and put the blue ones on a different network

Checker: both groups internally reachable, **and** sharing no common network.

```json
[
  {"op":"new","var":"rednet","kind":"network"},
  {"op":"new","var":"bluenet","kind":"network"},

  {"op":"new","var":"r1","kind":"vm"},
  {"op":"new","var":"r2","kind":"vm"},
  {"op":"new","var":"r3","kind":"vm"},
  {"op":"new","var":"b1","kind":"vm"},
  {"op":"new","var":"b2","kind":"vm"},

  {"op":"call","tool":"add_label","args":{"name":"$r1","label":"red"}},
  {"op":"call","tool":"add_label","args":{"name":"$r2","label":"red"}},
  {"op":"call","tool":"add_label","args":{"name":"$r3","label":"red"}},
  {"op":"call","tool":"add_label","args":{"name":"$b1","label":"blue"}},
  {"op":"call","tool":"add_label","args":{"name":"$b2","label":"blue"}},

  {"op":"foreach","select":{"kind":"vm","tag":"red"},
   "call":{"tool":"add_vm_to_network","args":{"net_name":"$rednet","vm_name":"$item"}}},
  {"op":"foreach","select":{"kind":"vm","tag":"blue"},
   "call":{"tool":"add_vm_to_network","args":{"net_name":"$bluenet","vm_name":"$item"}}},

  {"op":"ensure","predicate":{"disjoint":["$rednet","$bluenet"]}}
]
```

**Does it say what the goal means?** Yes, and better than the English does. "their own
network" and "a different network" are two separate assertions in the sentence that the
harness has to infer are *mutually exclusive*; here `disjoint` states it once, and it is
the checker's own condition rather than a proxy for it.

This is the artifact's worked example, and it survives contact with the real checker.

---

## Rung 7 — convergence

> make sure exactly 3 vms carry the 'prod' label

Seeded: `one` (prod), `two` (prod), `three`, `four`. So the world starts at two, and
exactly one label must be added — and none removed.

```json
[
  {"op":"ensure","predicate":{"count":{"kind":"vm","tag":"prod"},"eq":3}}
]
```

**One statement — and this is the one that does not work as written.** It states the
goal perfectly and contains no plan. An `ensure` that fails raises, which routes to the
revision loop; nothing in the program adds a label.

The design note is aware of this and calls it convergence in one line (§06), but the
mechanism it relies on is the STRIPS/Terraform mode explicitly *deferred* in §08 —
"when a procedure is nothing but ENSURE clauses, the harness MAY derive the plan". Until
that exists, rung 7 either has no body, or has a body that hardcodes the answer
(`add_label three prod`) and is therefore not convergent at all: run it against a world
already at three and it goes to four, which is exactly the bug the translator caused.

---

# Findings

## 1. `new` cannot create a set — rungs 4 and 6 unroll

`new` binds ONE resource. "create 5 vms" is therefore five statements with five distinct
variables, and every subsequent per-member operation is five more. Rung 4 is 13
statements; rung 6 is 15.

The programs are *correct*. The concern is who writes them. The harness already unrolls
this deterministically (`_cardinal_create_steps` mints `vm1..vmN`), but under the IR the
**model** does it — and the measured weakness that motivated the collective expander in
the first place is precisely that this model class cannot expand a collective loop (0/3
at N=3). Asking it to emit five parallel `new` statements plus ten parallel calls, with
consistent variable names, is asking for the thing it is known to be bad at.

**Proposed:** `new{var, kind, count}`, where `count > 1` binds `$var` to a SET, and
`foreach{select: {"var": "$var"}}` iterates it. Rung 4 becomes six statements. This is
not new capability — it is the existing cardinal-creation behaviour, expressed in the
language instead of recovered from English by a regex.

## 2. `ENSURE` must reach beyond the registry, or rung 4's assurance is inexpressible

The design note defines `ensure` as "a postcondition over the registry". Rung 4's clause
is *"make sure they all ping each other"* — and reachability is **not registry state**.
It is a finding, produced by a probe, and the epistemic-acceptance layer already treats
it that way: `mesh(fleet)` is recorded in the findings ledger, deliberately not inferred
from a tool's success flag.

So either `ensure` can query findings, or the ladder's assurance clauses cannot be
written. The note lists this as an open question — *"whether SELECT reaches beyond the
registry into findings / ledger"* — and rung 4 answers it: **it must.**

Worth stating the consequence, because it is a feature: if `SELECT` reads findings, then
*"trigger when p_world for delete_vm drops below 0.5"* becomes expressible, which is the
note's own example of what that would unlock.

## 3. The predicate language needs more than count/eq

Three shapes appear in four rungs: `count … eq` (7), `disjoint` (6), `reach … min` (4).
Two of them are set relations, not scalar comparisons.

This is small but it should be settled deliberately rather than grown. The predicate
vocabulary is the part `ENSURE`, contract `goal_predicate` clauses and trigger conditions
all share, so a shape added carelessly here is added in three places at once.

## 4. A pure-`ENSURE` program states the goal, not the plan

Rung 7 is the whole convergence case and it reduces to one `ensure` with no body. That is
either the most elegant result in the exercise or a hole, depending on a decision that
has not been made: does the harness derive a plan from an unsatisfied predicate?

- **If yes**, rung 7 is one line and self-correcting, and the note's deferred
  option-3 mode is no longer optional — it is what makes convergence work.
- **If no**, convergence programs need an explicit body, and that body must itself be
  conditional ("add a label only if the count is short"), which the four node types
  cannot express — there is no conditional.

**This is the decision that most constrains v1**, and it should be made before the
node set is fixed rather than discovered during implementation.

---

# What this exercise settled

The claim under test was the note's: *"These four express every benchmark rung from 4
through 7."*

**Rungs 4, 5 and 6: confirmed.** They express cleanly, and rungs 5 and 6 express *better
than the English does* — rung 5's filter cannot be detached from its action, and rung 6's
separation is stated once rather than inferred from two sentences. Both of those are
failures the goal translator actually produced today, and both are unrepresentable here.

**Rung 7: not confirmed.** It expresses the goal in one statement and cannot act on it
without a decision that is currently deferred.

Two of the four findings (#1 set-valued `new`, #2 `ensure` over findings) are additions
the rungs *demand* rather than conveniences. Neither is large. Both should land before the
model-emission experiment, because that experiment tests whether llama3.1 can emit *this*
IR — and it should be asked about the IR we intend to keep.

**Next**: settle finding #4, fold #1–#3 into the node set, then run the experiment the
note names as the only step carrying real risk — can the local model emit valid IR for
these four goals? Two afternoons to know, against two weeks to find out the hard way.
