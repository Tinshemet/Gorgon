"""What a `$reference` means, in one place.

Both the validator and the visitor have to answer the same question — which names does
this string refer to, and what does it evaluate to — and they answered it separately, each
by testing `value.startswith(SIGIL)`. That treats the whole string as one name, which is
right for `$vms` and wrong for everything else. Rung 12 is where it showed: the model
wrote

    snapshot_create(name: $item, snap_name: $item-snap)

which is exactly the intent — a snapshot's name derived from the VM it belongs to — and
was rejected as a reference to an undeclared variable `item-snap`. The model was not
wrong; the language had no way to build a name out of a value.

So a string is a TEMPLATE. It holds zero or more `$name` (or `$name.field`) tokens:

  - exactly one token and nothing else  -> the value itself, type preserved. `$vms` stays
    a list, so `FOREACH … IN $vms` still iterates rather than walking a string.
  - anything else                       -> textual substitution, e.g. `$item-snap`.

The type-preserving case has to come first. Collapsing it into substitution would quietly
stringify every set in the language.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import config

# A name, optionally reaching into a grafted result: $answer.reachable. Deliberately does
# NOT include `-`, which is what makes `$item-snap` split the way the author meant.
_TOKEN = re.compile(re.escape(config.SIGIL) + r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")


def names(value: Any) -> List[str]:
    """Every name `value` refers to — the root only, not the fields under it.

    `$answer.reachable` refers to `answer`; whether it HAS a `reachable` field is a
    question about the result at run time, not about what the program declares.
    """
    if not isinstance(value, str):
        return []
    return [m.split(".", 1)[0] for m in _TOKEN.findall(value)]


def substitute(text: Any, resolve) -> str:
    """Rewrite every `$reference` in *text* through `resolve(root, whole) -> str | None`.

    HERE BECAUSE THE TOKEN GRAMMAR IS HERE. The authoring stand-in needs to find the
    references in an operator's REQUEST — free English, not an IR value — and the one thing
    it must not do is write a second regex for what a `$name` is. `$item-snap` splits into
    `$item` plus `-snap` for a reason rung 12 paid for, and a private copy of that rule in
    another module is the copy that would not have been updated.

    `resolve` RETURNING None LEAVES THE TEXT ALONE, which is what makes the caller able to
    tell the difference between a reference it recognised and one it did not — an
    undeclared `$foo` must survive intact so somebody can be told about it, not be silently
    swallowed by the rewrite that was supposed to help.
    """
    if not isinstance(text, str):
        return text

    def _one(m: "re.Match") -> str:
        got = resolve(m.group(1).split(".", 1)[0], m.group(0))
        return m.group(0) if got is None else str(got)

    return _TOKEN.sub(_one, text)


def is_reference(value: Any) -> bool:
    """True if the string is exactly one reference and nothing else."""
    if not isinstance(value, str):
        return False
    m = _TOKEN.fullmatch(value.strip())
    return m is not None


# A NAME YOU CAN BIND IS A NAME YOU CAN READ. Same character set as a reference token,
# minus the dotted path — you bind `answer`, not `answer.alive`.
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def is_referenceable(name: Any) -> bool:
    """Can a program refer back to something bound under this name?

    THE INVARIANT: the set of legal BINDING names must equal the set of READABLE names.
    It did not, and the gap is silent. `-` is deliberately excluded from a reference token
    so `$item-snap` composes a name out of `$item` plus `-snap` — which rung 12 needs — but
    that also means a variable called `red-net` can be bound and then never read: `$red-net`
    parses as `$red` followed by the literal text `-net`.

    Rung 6's paraphrase walked straight into it, three samples out of three:

        STORE red-net = NEW network;
        add_vm_to_network(net_name: $red-net, vm_name: $item);
            -> "net_name=$red-net refers to $red, which is never created"

    The author is told it never created something it plainly did create, one line above.
    Binding a name the language cannot pronounce is not a program error to diagnose, it is
    a name the language should never have accepted.
    """
    return isinstance(name, str) and _NAME.match(name.strip()) is not None


def _lookup(path: str, scope: Dict[str, Any]) -> Any:
    """Walk `name.field.field` through scope, returning None at the first missing step."""
    head, *rest = path.split(".")
    cur = scope.get(head)
    for field in rest:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(field)
    return cur


def resolve(value: Any, scope: Dict[str, Any]) -> Any:
    """Evaluate a template against `scope`, recursing through dicts and lists.

    An unknown name is left standing as written rather than becoming an empty string —
    an argument that reads `$missing` in a ledger row is debuggable; one that silently
    reads `` is not.
    """
    if isinstance(value, dict):
        return {k: resolve(v, scope) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, scope) for v in value]
    if not isinstance(value, str):
        return value

    whole = _TOKEN.fullmatch(value.strip())
    if whole:                                     # type-preserving: sets stay sets
        found = _lookup(whole.group(1), scope)
        return value if found is None else found

    def sub(m: re.Match) -> str:
        found = _lookup(m.group(1), scope)
        return m.group(0) if found is None else str(found)

    return _TOKEN.sub(sub, value)
