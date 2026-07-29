# Ladder failures, with the programs

Source log: `/tmp/claude-1000/-home-tinshemet/fb267b41-753c-4cb0-9e73-72410465ac01/scratchpad/card2.log`

Every cell below is one the ladder scored 0/3. The program shown is the LAST one the run produced for that cell — after any repair rounds — which is not always what the model first wrote. Where they differ it is called out in the diagnosis.

## lit:8 — rung 8, exception

**Tests:** a general rule with one carve-out that must survive it

**Goal:** put every vm on a network called core, except db — db goes on a network called dmz instead

**Outcome:** NO PROGRAM — `JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 350 (char 349) — not counted as a failure`

> The decoder never delivered a parseable program, so there is nothing to read. This is the finding, not a gap in the report.

**Diagnosis:** CHANNEL. The decoder dies at the same character position every time and no program is ever produced, so we have NEVER OBSERVED what the model would write for the literal wording — which matters, because the literal column says `except db`, the same word few-shot 7 demonstrates a carve-out with. Whether the model can do rung 8 at all is unknown, not answered.

---

## lit:13 — rung 13, idempotent-reentry

**Tests:** the goal ALREADY holds — doing it again must change nothing

**Goal:** take 5 vms, put them all in a network, give them all the 'fleet' label, and make sure they all ping each other

**Outcome:** INVALID

**Objections:**

- `statement 1: NEW vm also requires 'os_type' — put them in this statement's own arguments, e.g. NEW vm(os_type: ...). NEW already calls create_vm; do NOT add a separate create_vm call.`
- `statement 1: the lab already holds 5 vm(s) — AMOUNT makes 5 MORE, not 5 in total. FETCH first and create the difference, or state the end state with ACHIEVE COUNT.`
- `statement 4: reach needs `select` — the set to measure, e.g. {'kind':'vm','tag':'prod'}`

**Program:**

```
STORE vms = NEW AMOUNT(5) vm;
FOREACH $item IN $vms {
  add_label(name: $item, label: fleet);
  create_network(net_name: new-net);
  add_vm_to_network(net_name: new-net, vm_name: $item);
}
FOREACH $item IN $vms {
  guest_ping(name: $item);
  guest_ping(name: $item, from: $item);
}
ACHIEVE REACH(<not a set: '$vms'>);
```

**Diagnosis:** WORLD BLINDNESS, VISIBLE — and I had this wrong until this report printed the program. I wrote that rung 13's reasoning failure was 'unobservable because repair returns nothing'. It is not: the first draft is right here, and the validator names the defect outright — `the lab already holds 5 vm(s) — AMOUNT makes 5 MORE, not 5 in total`. The model writes `NEW AMOUNT(5) vm` into a lab holding five, which is the exact mistake `f2ae63c` states the rule against and the same defect as para:9. The CHANNEL is what stops it RECOVERING — repair delivers nothing — but the reasoning failure is observed, not hidden. Two distinct faults in one cell, and reporting only the terminal outcome hid the more important one.

---

## para:7 — rung 7, convergence

**Tests:** diff what IS against what is wanted, and change only the difference

**Goal:** there should end up being precisely three machines tagged prod, no more and no fewer

**Outcome:** VALID · checker FAIL   world: 4 vms ['four', 'one', 'three', 'two'] | nets [] | 4 calls

**Program:**

```
FOREACH $item IN SELECT vm {
  add_label(name: $item, label: prod);
}
ENSURE COUNT(SELECT vm INCLUDE labels = [prod]) = 3;
```

**Diagnosis:** NOT A STABLE FAILURE — this cell is roughly 60%. It came back 2/3 on two separate targeted re-runs, splitting WITHIN a single run, and its history is 0/3 then 3/3 three times then 0/3 twice on a byte-identical authoring path (prompt and schema hashes verified equal). Read it as a coin flip, not as red or green. n=3 cannot tell a 60% cell from a broken one, which is the real defect here.

---

## para:8 — rung 8, exception

**Tests:** a general rule with one carve-out that must survive it

**Goal:** connect all the machines to a network named core, apart from db, which belongs on dmz

**Outcome:** INVALID

**Objections:**

- `statement 4: select must name a kind`

**Program:**

```
STORE core = NEW network(net_name: core);
FOREACH $item IN SELECT vm {
  add_vm_to_network(net_name: $core, vm_name: $item);
}
STORE dmz = NEW network(net_name: dmz);
FOREACH $item IN SELECT ? WHERE name = '['app1', 'app2', 'app3']' {
  add_vm_to_network(net_name: $dmz, vm_name: $item);
}
add_vm_to_network(net_name: $core, vm_name: db);
```

**Diagnosis:** MODEL, two separate defects. (1) CARDINALITY: `db` is one object identified by the kind's key, so its statement is a plain `call` naming it — the model writes a `foreach` over a select of one, and that loop is what let the missing `kind` exist at all. (2) THE CARVE-OUT IS ABSENT from the first loop, so every vm including db lands on core, which the checker forbids. Fixing (1) alone leaves the rung red. NOTE the scored program is the POST-REPAIR one: the first draft gets `db` right and the repair loop, handed `select must name a kind` twice, rewrote `name = 'db'` into the complement `['app1','app2','app3']` — inverting the goal while still not supplying the kind.

---

## para:9 — rung 9, diagnosis

**Tests:** the goal names an end-state; find WHICH member breaks it

**Goal:** n1, n2 and n3 should all be able to reach one another — sort out whatever is stopping that

**Outcome:** INVALID

**Objections:**

- `statement 1 (foreach body) → statement 1: net_name=$item.networks[0] reads a field off $item, which is a NAME, not a call's result — only something bound by `graft` has fields. Select what you need instead, or graft the call whose answer you mean.`

**Program:**

```
FOREACH $item IN SELECT vm {
  add_vm_to_network(net_name: $item.networks[0], vm_name: $item);
}
ACHIEVE REACH(SELECT vm) >= 3;
```

**Diagnosis:** WORLD BLINDNESS — the same defect rung 13 was reworded to expose on 2026-07-28. CURRENT STATE shows `n1: networks=mesh0`, `n2: networks=mesh0`, `n3:` with none. One line identifies the fault. The model writes `NEW vm` three times into a lab already holding all three. Its earlier 3/3 was NOT a pass worth having: it re-created three existing machines and an existing network, then re-attached everything, which satisfies an end-state-only checker without ever diagnosing anything. Rung 9 has no `best`/`minimum`, so a 10-call bulldoze scores the same as the single `add_vm_to_network` the task needs.

---

## para:11 — rung 11, result-dependent

**Tests:** the condition is a call's ANSWER, not an attribute anything can query

**Goal:** check which machines respond and shut down whichever ones don't

**Outcome:** NO PROGRAM — `JSONDecodeError: Expecting ',' delimiter: line 1 column 245 (char 244) — not counted as a failure`

> The decoder never delivered a parseable program, so there is nothing to read. This is the finding, not a gap in the report.

**Diagnosis:** CHANNEL. Malformed JSON at the same character position, unchanged all day.

---

## para:13 — rung 13, idempotent-reentry

**Tests:** the goal ALREADY holds — doing it again must change nothing

**Goal:** use five machines, wire them together on one private network, tag every one of them 'fleet', and confirm each can reach the others

**Outcome:** INVALID

**Objections:**

- `statement 1: the lab already holds 5 vm(s) — AMOUNT makes 5 MORE, not 5 in total. FETCH first and create the difference, or state the end state with ACHIEVE COUNT.`

**Program:**

```
STORE machines = NEW AMOUNT(5) vm(os_type: linux);
FOREACH $item IN $machines {
  add_label(name: $item, label: fleet);
}
STORE net = NEW network;
FOREACH $item IN $machines {
  add_vm_to_network(net_name: $net, vm_name: $item);
  guest_ping(name: $item);
}
ACHIEVE REACH(SELECT vm WHERE label = 'fleet') >= 5;
ENSURE COUNT(SELECT network) = 1;
```

**Diagnosis:** As lit:13 — world blindness in the draft, channel failure in the repair. The terminal `REPAIR_UNDELIVERED:empty` names the second and buries the first.

---

