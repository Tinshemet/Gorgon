"""scope.py — is this CALL inside the context a scope permits? (K5, the matching half)

`rules.RuleSet.scopes(tool)` answers what the LAW says; this answers whether one call is
inside it. They are apart on purpose: the resolver has never known what a VM is, and the
question here is about a call's targets.

⇒⇒ **PROVE INCLUSION, NEVER DETECT EXCLUSION** — the whole reason a scope is not a ban.
  The operator, 2026-08-13: *"it's not to keep something out, it's to only allow something
  specific in."* So nothing here looks for a bad target. It asks whether the call has SHOWN
  itself to be inside, and refuses when it has not — which is how an unbound target fails.
  `delete_vm` over the unfiltered set of every machine passed every check this system had,
  because there was nothing to catch; it fails here because nothing proved it was inside.

⇒⇒ **AND THE DEFERRAL RULE, WHICH IS THE OTHER HALF OF BEING SOUND.** A caller answers only
  with what it can read. The front seam holds selectors and never a literal; an executor
  holds literals and no selector. A caller that cannot evaluate a governing scope DEFERS —
  it does not refuse on information it does not have, because under the union ruling (c)
  another scope it cannot read might be the one that admits. Refusing there would be a
  FALSE REFUSAL manufactured out of missing information, and the layering that catches the
  deferred case already exists: `executor._red_line`'s own docstring calls the check at the
  call *"the backstop that cannot be dodged"*.

  ⇒ THE COST OF THAT, STATED: a tool scoped only by `args` is not refused at the front seam,
    because the seam cannot see an argument that does not exist yet. The seam's protection
    is the OBJECT binding — which is exactly the blast-radius case it was wanted for.

⇒ **WHY A GROUP ON THE CALL SIDE CAN BE IGNORED.** A select's `any` / `all` / `not` groups
  are AND-ed with its flat bindings (`planner/program.py::_one` answers each group and
  returns False before it ever reads them), so the selected set is ALWAYS a subset of the
  members matching the flat bindings. A subset of something inside the scope is inside the
  scope. So proving inclusion on the flat bindings alone is sound, and a carve-out can only
  make the call narrower than the thing already admitted.
"""
from typing import Any, Dict, List, Optional

# The select keys that are structure rather than an attribute binding. Same four
# `planner/program.py::_one` skips — named here because a scope reads a select and must
# agree with the thing that RUNS one.
_STRUCTURE = ("kind", "any", "all", "not")


def _args_admit(context: Dict[str, Any], args: Optional[Dict[str, Any]]) -> bool:
    """Every literal the scope names must be PRESENT and EQUAL in the call.

    ABSENT IS OUTSIDE, NOT INSIDE. A missing argument proves nothing, and the default for
    an unproven scope is out. Arguments the scope does not name are unconstrained — a scope
    limits what it mentions and says nothing about the rest of the call.
    """
    if not isinstance(args, dict):
        return False
    return all(k in args and args[k] == want for k, want in context.items())


def _object_admits(context: Dict[str, Any], selector: Optional[Dict[str, Any]]) -> bool:
    """The call's SELECTOR must assert everything the scope requires — `select_of`'s shape.

    THE SHAPE IS THE IR SELECT AND NOT A SECOND ONE. `schema.select_of` is the one builder
    of "which members", and a scope that spoke its own dialect would need a translator at
    every seam — which is how two answers to one question start.

    A NON-SCALAR BINDING IS UNPROVEN, DELIBERATELY. `{"in": [...]}` widens an attribute
    against a scope that names one value, and `{"in": ["scratch"]}` against a scope wanting
    `scratch` is inside in truth and refused here. That is a conservative refusal and the
    right direction for a permission: two scopes union, so a set of permitted values is
    written as two rules.
    """
    if not isinstance(selector, dict) or not selector:
        return False
    if context.get("kind") and selector.get("kind") != context.get("kind"):
        return False
    for attr, want in context.items():
        if attr in _STRUCTURE:
            continue
        if selector.get(attr) != want:
            return False
    return True


def _readable(scope: Dict[str, Any], args: Any, selector: Any) -> bool:
    """Can THIS caller evaluate this scope at all? (Not: does it admit.)"""
    bind = scope.get("bind")
    return ((bind == "args" and isinstance(args, dict))
            or (bind == "object" and isinstance(selector, dict) and bool(selector)))


def admits(scope: Dict[str, Any], args=None, selector=None) -> bool:
    """Is this one call inside this one scope? An unknown binding admits nothing."""
    context = scope.get("context") or {}
    if scope.get("bind") == "args":
        return _args_admit(context, args)
    if scope.get("bind") == "object":
        return _object_admits(context, selector)
    return False


def outside(tool: str, scopes: List[Dict[str, Any]], args=None,
            selector=None) -> Optional[str]:
    """Why this call falls outside every scope governing `tool` — or None when it may run.

    None is returned in three distinct situations, and they are not the same fact:

        UNGOVERNED   no scope names this tool — the ban law alone governs it, exactly as
                     before scopes existed. This is the containment rule: one authored
                     scope must not ban the world
        ADMITTED     a governing scope proved the call inside (union — any one is enough)
        DEFERRED     a governing scope exists that THIS caller cannot read, so the question
                     belongs to a layer that can. Never refuse on missing information

    A string is returned only for the fourth case: every governing scope is readable here
    and not one of them admits the call.
    """
    if not scopes:
        return None
    if not all(_readable(s, args, selector) for s in scopes):
        return None
    if any(admits(s, args=args, selector=selector) for s in scopes):
        return None
    named = "; ".join(s["text"] for s in scopes if s.get("text"))
    return (f"{tool} may run only inside a declared scope, and nothing shows this call is "
            f"inside one" + (f" — {named}" if named else ""))
