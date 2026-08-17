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

## 4 · ACTION TRIGGERS — after/before/when/if AS DECOMPOSITION (operator, during review, 2026-08-18)

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

## 3 · ARGUMENT ROLES (operator, during review, 2026-08-18)

*"put on the lab network every vm carrying the prod label"* — the vm is the THEME, the
network the DESTINATION, and the attachment says only that both belong to `put`.
⇒ ⚠ **A ROLE SWAP IS INVISIBLE TO v1.** A reading that puts the network onto the vms scores
  identically to the correct one. That failure class is real (rung 3's
  `add_vm_to_network(web, lab)` vs `(lab, web)`) and unbilled until v2.
⇒ v2: roles on attachment members — `{"action": 0, "objects": [{"span": 1, "role": "theme"},
  {"span": 0, "role": "destination"}]}` — with a closed role vocabulary read from the
  manifest's own argument declarations, never a hand list.

## 5 · SEQUENCE BETWEEN INSTRUCTED ACTS (audit, 2026-08-18)

*"stop alpha. THEN launch beta."* · *"restart it AFTER YOU HAVE CHECKED the others"* — an
ordering between two acts the operator commanded. Not a trigger (no world condition starts
anything; YOU finish one act and begin the next), and v1.2 deliberately does not mark it — a
reader that reorders the acts scores the same as one that keeps the order.
⇒ v2: an `after` field on an action naming another ACTION index — order as a relation between
  acts, exactly how the writer's plans already carry it. Cheap; take with items 2+3.
