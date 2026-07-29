# What each failing cell writes — the FIRST DRAFT

One authoring call per cell, **no repair, no revision, no sanitiser**. This is the model's own program. The ladder scores what comes out the far end of the repair loop, which for `para:8` is a different and worse program.

A single draft is a SAMPLE, not a pass rate — temp 0 is not deterministic here. Read it for shape; take rates from the ladder.

## lit:8 — rung 8, exception

**Tests:** a general rule with one carve-out that must survive it

**Goal:** put every vm on a network called core, except db — db goes on a network called dmz instead

**The draft does not parse.** No Medusa exists — this is the channel failure, and the raw reply is the evidence:

```
{"body": [{"op": "new", "var": "core_net", "kind": "network", "args": {"net_name": "core"}}, {"op": "foreach", "select": {"kind": "vm"}, "do": [{"op": "call", "tool": "add_vm_to_network", "args": {"net_name": "$core_net", "vm_name": "$item"}}, {"op": "ensure", "predicate": {"shape": "not", "of": {"shape": "is", "of": "$item.name", "eq": "db"}}}], {"op": "call", "tool": "add_vm_to_network", "args": {"net_name": "dmz", "vm_name": "db"}}}]}
```

_441 bytes returned._

---

## para:8 — rung 8, exception

**Tests:** a general rule with one carve-out that must survive it

**Goal:** connect all the machines to a network named core, apart from db, which belongs on dmz

**Medusa** (4 statements, validator: INVALID):

```
STORE core = NEW network(net_name: core);
FOREACH $item IN SELECT vm {
  add_vm_to_network(net_name: $core, vm_name: $item);
}
STORE dmz = NEW network(net_name: dmz);
FOREACH $item IN SELECT ? WHERE name = 'db' {
  add_vm_to_network(net_name: $dmz, vm_name: $item);
}
```

**Objections on this draft:**

- `statement 4: select must name a kind`

<details><summary>as stored (IR)</summary>

```json
[
 {
  "op": "new",
  "var": "core",
  "kind": "network",
  "args": {
   "net_name": "core"
  }
 },
 {
  "op": "foreach",
  "select": {
   "kind": "vm"
  },
  "do": [
   {
    "op": "call",
    "tool": "add_vm_to_network",
    "args": {
     "net_name": "$core",
     "vm_name": "$item"
    }
   }
  ]
 },
 {
  "op": "new",
  "var": "dmz",
  "kind": "network",
  "args": {
   "net_name": "dmz"
  }
 },
 {
  "op": "foreach",
  "select": {
   "name": "db"
  },
  "do": [
   {
    "op": "call",
    "tool": "add_vm_to_network",
    "args": {
     "net_name": "$dmz",
     "vm_name": "$item"
    }
   }
  ]
 }
]
```

</details>

---

## para:9 — rung 9, diagnosis

**Tests:** the goal names an end-state; find WHICH member breaks it

**Goal:** n1, n2 and n3 should all be able to reach one another — sort out whatever is stopping that

**Medusa** (2 statements, validator: INVALID):

```
FOREACH $item IN SELECT vm {
  add_vm_to_network(net_name: $item.networks[0], vm_name: $item);
}
ACHIEVE REACH(SELECT vm) >= 3;
```

**Objections on this draft:**

- `statement 1 (foreach body) → statement 1: net_name=$item.networks[0] reads a field off $item, which is a NAME, not a call's result — only something bound by `graft` has fields. Select what you need instead, or graft the call whose answer you mean.`

<details><summary>as stored (IR)</summary>

```json
[
 {
  "op": "foreach",
  "select": {
   "kind": "vm"
  },
  "do": [
   {
    "op": "call",
    "tool": "add_vm_to_network",
    "args": {
     "net_name": "$item.networks[0]",
     "vm_name": "$item"
    }
   }
  ]
 },
 {
  "op": "achieve",
  "predicate": {
   "shape": "reach",
   "select": {
    "kind": "vm"
   },
   "min": 3
  }
 }
]
```

</details>

---

## para:7 — rung 7, convergence

**Tests:** diff what IS against what is wanted, and change only the difference

**Goal:** there should end up being precisely three machines tagged prod, no more and no fewer

**Medusa** (2 statements, validator: VALID):

```
FOREACH $item IN SELECT vm WHERE labels = 'prod' {
  add_label(name: $item, label: prod);
  stop_vm(name: $item);
}
FOREACH $item IN SELECT vm {
  add_label(name: $item, label: prod);
  ACHIEVE COUNT(SELECT vm WHERE labels = 'prod') = 3;
}
```

<details><summary>as stored (IR)</summary>

```json
[
 {
  "op": "foreach",
  "select": {
   "kind": "vm",
   "labels": "prod"
  },
  "do": [
   {
    "op": "call",
    "tool": "add_label",
    "args": {
     "name": "$item",
     "label": "prod"
    }
   },
   {
    "op": "call",
    "tool": "stop_vm",
    "args": {
     "name": "$item"
    }
   }
  ]
 },
 {
  "op": "foreach",
  "select": {
   "kind": "vm"
  },
  "do": [
   {
    "op": "call",
    "tool": "add_label",
    "args": {
     "name": "$item",
     "label": "prod"
    }
   },
   {
    "op": "achieve",
    "predicate": {
     "shape": "count",
     "select": {
      "kind": "vm",
      "labels": "prod"
     },
     "eq": 3
    }
   }
  ]
 }
]
```

</details>

---

## para:11 — rung 11, result-dependent

**Tests:** the condition is a call's ANSWER, not an attribute anything can query

**Goal:** check which machines respond and shut down whichever ones don't

**The draft does not parse.** No Medusa exists — this is the channel failure, and the raw reply is the evidence:

```
{"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [{"op": "call", "tool": "guest_ping", "args": {"name": "$item"}, "graft": "answer"}, {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": true}, "then": []}, {"op": "else": [{"op": "call", "tool": "stop_vm", "args": {"name": "$item"}}]}]}]}
```

_313 bytes returned._

---

## lit:13 — rung 13, idempotent-reentry

**Tests:** the goal ALREADY holds — doing it again must change nothing

**Goal:** take 5 vms, put them all in a network, give them all the 'fleet' label, and make sure they all ping each other

**Medusa** (4 statements, validator: INVALID):

```
STORE vms = NEW AMOUNT(5) vm;
FOREACH $item IN $vms {
  add_label(name: $item, label: fleet);
  create_network(net_name: new-net);
  add_vm_to_network(net_name: new-net, vm_name: $item);
}
FOREACH $item IN SELECT vm {
  guest_ping(name: $item);
  guest_ping(name: $item, from: $item);
}
ACHIEVE REACH(SELECT vm) >= 5;
```

**Objections on this draft:**

- `statement 1: NEW vm also requires 'os_type' — put them in this statement's own arguments, e.g. NEW vm(os_type: ...). NEW already calls create_vm; do NOT add a separate create_vm call.`

<details><summary>as stored (IR)</summary>

```json
[
 {
  "op": "new",
  "var": "vms",
  "kind": "vm",
  "amount": 5
 },
 {
  "op": "foreach",
  "in": "$vms",
  "do": [
   {
    "op": "call",
    "tool": "add_label",
    "args": {
     "name": "$item",
     "label": "fleet"
    }
   },
   {
    "op": "call",
    "tool": "create_network",
    "args": {
     "net_name": "new-net"
    }
   },
   {
    "op": "call",
    "tool": "add_vm_to_network",
    "args": {
     "net_name": "new-net",
     "vm_name": "$item"
    }
   }
  ]
 },
 {
  "op": "foreach",
  "select": {
   "kind": "vm"
  },
  "do": [
   {
    "op": "call",
    "tool": "guest_ping",
    "args": {
     "name": "$item"
    }
   },
   {
    "op": "call",
    "tool": "guest_ping",
    "args": {
     "name": "$item",
     "from": "$item"
    }
   }
  ]
 },
 {
  "op": "achieve",
  "predicate": {
   "shape": "reach",
   "select": {
    "kind": "vm"
   },
   "min": 5
  }
 }
]
```

</details>

---

## para:13 — rung 13, idempotent-reentry

**Tests:** the goal ALREADY holds — doing it again must change nothing

**Goal:** use five machines, wire them together on one private network, tag every one of them 'fleet', and confirm each can reach the others

**Medusa** (6 statements, validator: INVALID):

```
STORE machines = NEW AMOUNT(5) vm;
FOREACH $item IN $machines {
  add_label(name: $item, label: fleet);
}
STORE net = NEW network;
FOREACH $item IN $machines {
  add_vm_to_network(net_name: $net, vm_name: $item);
  guest_ping(name: $item);
}
ACHIEVE REACH(<not a set: '$machines'>) >= 5;
ENSURE COUNT(SELECT network) = 1;
```

**Objections on this draft:**

- `statement 1: NEW vm also requires 'os_type' — put them in this statement's own arguments, e.g. NEW vm(os_type: ...). NEW already calls create_vm; do NOT add a separate create_vm call.`
- `statement 5: reach needs `select` — the set to measure, e.g. {'kind':'vm','tag':'prod'}`

<details><summary>as stored (IR)</summary>

```json
[
 {
  "op": "new",
  "var": "machines",
  "kind": "vm",
  "amount": 5
 },
 {
  "op": "foreach",
  "in": "$machines",
  "call": {
   "tool": "add_label",
   "args": {
    "name": "$item",
    "label": "fleet"
   }
  }
 },
 {
  "op": "new",
  "var": "net",
  "kind": "network"
 },
 {
  "op": "foreach",
  "in": "$machines",
  "do": [
   {
    "op": "call",
    "tool": "add_vm_to_network",
    "args": {
     "net_name": "$net",
     "vm_name": "$item"
    }
   },
   {
    "op": "call",
    "tool": "guest_ping",
    "args": {
     "name": "$item"
    }
   }
  ]
 },
 {
  "op": "achieve",
  "predicate": {
   "shape": "reach",
   "select": "$machines",
   "min": 5
  }
 },
 {
  "op": "ensure",
  "predicate": {
   "shape": "count",
   "select": {
    "kind": "network"
   },
   "eq": 1
  }
 }
]
```

</details>

---

