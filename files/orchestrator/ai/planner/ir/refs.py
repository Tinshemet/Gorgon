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


def is_reference(value: Any) -> bool:
    """True if the string is exactly one reference and nothing else."""
    if not isinstance(value, str):
        return False
    m = _TOKEN.fullmatch(value.strip())
    return m is not None


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
