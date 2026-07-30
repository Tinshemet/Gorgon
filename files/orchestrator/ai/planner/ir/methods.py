"""methods.py — MEDUSA CLASSES: what a kind can be ASKED, and who owns the answer.

A predicate today floats free of any object. `REACH(SELECT vm)` has to say which machines
it means, and every caller has to agree about what "reach" is over a set. That agreement
failed, silently, in the way this file exists to make impossible:

    production   reach = every member PROBED and alive. No topology at all.
    the bench    reach = the members share a network (+ probed, after A5).

Both implementations were CORRECT and they disagreed, because one name was doing two jobs.
The operator's reformulation, 2026-07-30:

    $web.reach()    can THIS MACHINE be pinged        — what production was implementing
    $lab.reach()    are all its members CONNECTED     — what the bench was implementing

So it was never one predicate with a missing check. It was two METHODS on two classes,
sharing a spelling. Split by receiver, the question "REACH of what?" cannot be asked
wrongly, because the scope IS the receiver — which is the argument for classes generally:
most of what an author gets wrong in this language is scope, and a method has none to get
wrong.

WHAT LIVES HERE AND WHAT DOES NOT. This module answers "does kind K have method M, and
what does M mean for K" from the MANIFEST. It does not touch a world — evaluating a method
still goes through the injected seams, exactly as every other predicate does, because the
registry lives in the Active Library and reachability in the findings ledger, and neither
belongs to the language.

ONE AUTHORITY, deliberately, because this is the fact most likely to be written twice: the
bench seam and the production seam must dispatch the same way or the split re-creates the
disagreement it was invented to remove, one level down.
"""
from typing import Any, Dict, List, Optional

from . import config


def methods(kind: str) -> Dict[str, Any]:
    """Every method the manifest declares on `kind`. Empty for a kind that has none."""
    return dict(((config.KINDS.get(kind) or {}).get("methods") or {}))


def has(kind: str, name: str) -> bool:
    """Does this class answer this method?"""
    return name in methods(kind)


def receivers(shape: str) -> List[str]:
    """The kinds a predicate may be asked OF, from the manifest.

    A predicate with no `receivers` is not a method and may only be asked the old way,
    over a `select`. That keeps the two forms distinguishable rather than making every
    predicate secretly object-oriented.
    """
    return list((config.PREDICATES.get(shape) or {}).get("receivers") or [])


def is_method_call(pred: Any) -> bool:
    """Is this predicate asked OF an instance rather than over a query?

    The distinction is the presence of `on`, not the shape — `reach` is both a method and
    a free predicate, and which one a statement means is decided by how it was written.
    """
    return isinstance(pred, dict) and pred.get("on") is not None


def kind_of(receiver: Any, bindings: Optional[Dict[str, str]] = None,
            world_kind=None) -> Optional[str]:
    """Which class the receiver belongs to, or None when it cannot be known.

    Two ways of knowing, and both are needed. STATICALLY, a name bound by `new` or `fetch`
    carries its kind — the validator has that map and can dispatch before anything runs.
    At RUN TIME the binding may be a plain name, so a caller may supply `world_kind` to ask
    the registry what it is.

    None rather than a guess. Dispatching a method on the wrong class is exactly the defect
    this split removes, and inventing an answer here would put it straight back.
    """
    name = receiver
    if isinstance(name, str) and name.startswith(config.SIGIL):
        name = name[len(config.SIGIL):]
    if bindings and name in bindings:
        return bindings[name]
    if callable(world_kind):
        return world_kind(name)
    return None


def doc(kind: str, name: str) -> str:
    """What this method means for this class — the manifest's own words."""
    return ((methods(kind).get(name) or {}).get("doc") or "")


def offered() -> Dict[str, List[str]]:
    """{kind: [method, ...]} for every class that declares any.

    Used by the prompt and the schema so the author is told what an object can be asked,
    from the same table the validator polices — a listing built separately is how the four
    agreements drift apart.
    """
    return {kind: sorted(methods(kind)) for kind in config.KINDS if methods(kind)}
