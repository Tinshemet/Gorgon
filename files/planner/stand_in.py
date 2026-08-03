"""
stand_in.py — a declared `$parameter` survives translation, by not being a `$` while it travels.

THE DEFECT, MEASURED 2026-08-03 ON THE OPERATOR'S OWN REQUEST. Asked for

    procedure mashu(STRING name, STRING os_name): a vm named $name running $os_name

Gorgon wrote, kept, and reported DONE on:

    PROCEDURE mashu(STRING name, STRING os_name) {
      CALL launch_vm(name: work-laptop);
      ENSURE COUNT(SELECT vm) = 1;
      ...

`work-laptop` is the operator's real machine. It appears in no part of the request, and both
declared parameters bind nothing. A reusable procedure that starts somebody's actual laptop.

WHY, AND EVERY LAYER WAS BEHAVING AS WRITTEN. `refs`-shaped residue is stripped at the goal
layer by `extract._unwrap`, on an argument that is exactly right for an ACTING request: a
goal has no bindings, nothing has been bound and nothing can be, so `${lab}` is notation the
model reached for rather than a reference to anything. Rung 13 is the measurement that put it
there. But under `procedure p(STRING name):` the operator DECLARED `name` one clause earlier,
so `$name` is the one thing at that layer which is not residue — it is a reference to
something already known. Stripping it deletes the identity filter, `count(vm WHERE
name=…) = 1` collapses to `count(vm) = 1`, and a lab holding one machine already satisfies
that. Nothing needs creating, so the writer reuses. Measured, both phrasings:

    "a vm called $name running $os_name"  -> count(vm) = 1                      (unfiltered)
    "a vm called box1 running linux"      -> count(vm WHERE name=box1) = 1      (a creation)

THE FIX IS TO MAKE THE FIRST LOOK LIKE THE SECOND while it crosses the seam, and to put it
back afterwards. A declared parameter is replaced by a STAND-IN IDENTITY — an ordinary name
the extractor treats like any other, chosen so that nothing in any world can match it — and
once the writer has planned the creation it now has no choice but to plan, every occurrence
of that identity becomes `$param` again.

IT IS [[gorgon-declare-dont-infer]] AND NOTHING ELSE. Only a `$p` whose `p` is in the
signature is stood in for. An undeclared `$foo` is left exactly as it was, so it still
reaches `_unwrap` and is still stripped — and the caller is TOLD, because a reference to a
parameter nobody declared is a typo the operator wants to hear about rather than a request
to guess.

TWO PROPERTIES THE TOKEN MUST HAVE, and both were measured rather than assumed:

    DIGIT-FREE      "a vm named box1 running box2" came back as `eq: 2`. A digit inside a
                    name leaks out of the name and into the COUNT, so a procedure taking
                    `os2` would author two machines. Digits are removed, not rejected.
    UNMATCHABLE     the whole point is that the writer must not find one already there. The
                    prefix is what buys this, and it is why the prefix is config rather than
                    a literal: an operator whose lab really does hold a `param_name` needs
                    somewhere to change it.

WHAT IT DOES NOT FIX, STATED PLAINLY BECAUSE IT WILL BE THE NEXT QUESTION. The extractor
routes a value by RECOGNISING it, not by its slot: "running linux" reaches `os_type` because
`linux` is an OS, and "running <stand-in>" falls back to `status: running` and drops the
value. So an identity parameter binds reliably and a VALUE parameter binds only where the
phrasing names its slot — `with os $os_name` works, `running $os_name` does not. That is a
weakness of the word "running", not of this module, and it is measured in
`tests/test_stand_in.py` so the day it changes is visible.
"""
from typing import Any, Dict, List, Tuple

from planner.ir import config as _config
from planner.ir import refs as _refs

# Digits are stripped rather than rejected — see the module docstring. `os2` stands in as
# `param_os`, which is still unique among the declared parameters because `_mint` says so.
_DIGITS = str.maketrans("", "", "0123456789")


def _mint(param: str, taken: set) -> str:
    """The stand-in identity for one declared parameter. Digit-free, and unique among peers."""
    out = _config.STAND_IN_PREFIX + str(param).translate(_DIGITS)
    if not out.strip("_"):
        # A parameter named entirely of digits leaves the prefix alone; it still needs to be
        # a name, and it still needs to differ from its neighbours.
        out = _config.STAND_IN_PREFIX + "p"
    while out in taken:
        out += "_"
    taken.add(out)
    return out


def substitute(request: str, declared: Dict[str, str]) -> Tuple[str, Dict[str, str], List[str]]:
    """`(rewritten request, {stand-in: parameter}, [undeclared names referred to])`.

    Example::

        substitute("a vm named $name with os $os_name", {"name": "string", "os_name": "string"})
        # -> ("a vm named param_name with os param_os_name",
        #     {"param_name": "name", "param_os_name": "os_name"}, [])
    """
    if not request or not declared:
        return request, {}, []
    tokens: Dict[str, str] = {}          # stand-in -> parameter
    by_param: Dict[str, str] = {}        # parameter -> stand-in, so `$name` twice is one name
    taken: set = set()
    unknown: List[str] = []

    def _resolve(root: str, whole: str):
        if root not in declared:
            # LEFT ALONE ON PURPOSE. It goes on to be stripped as residue exactly as before,
            # and the caller reports it rather than this module deciding what a typo meant.
            if root not in unknown:
                unknown.append(root)
            return None
        if root not in by_param:
            by_param[root] = _mint(root, taken)
            tokens[by_param[root]] = root
        # A DOTTED REFERENCE STANDS IN AS ITS ROOT. `$answer.reachable` is a field of
        # something bound at RUN time and cannot be a parameter of the procedure, so the
        # root is what was declared and the rest was never ours to keep.
        return by_param[root]

    return _refs.substitute(request, _resolve), tokens, unknown


def restore(program: Dict[str, Any], tokens: Dict[str, str]) -> set:
    """Turn every stand-in in *program* back into `$parameter`, in place. Returns what bound.

    BY VALUE, EVERYWHERE, AND THAT IS SAFER THAN THE RULE BESIDE IT. `_declare` may only
    substitute inside a CREATION, because it matches on an argument's NAME and a name can
    collide with a target the PLANNER chose by reading the world — the measured disaster
    being eight `delete_vm` calls whose victims all became `$name`. This matches on a value
    THIS MODULE MINTED from the operator's own `$p` moments earlier. Provenance, not
    resemblance: there is no way for a stand-in to appear anywhere the operator did not put
    it, so there is nowhere it must not be replaced.
    """
    if not tokens:
        return set()
    sigil = _config.SIGIL
    bound: set = set()

    def _value(v: Any) -> Any:
        if isinstance(v, str) and v in tokens:
            bound.add(tokens[v])
            return f"{sigil}{tokens[v]}"
        return v

    def _selectors(node: Any):
        """Every `select` in a goal or predicate, however it is nested."""
        if isinstance(node, list):
            for kid in node:
                yield from _selectors(kid)
        elif isinstance(node, dict):
            for field, val in node.items():
                if field == "select" and isinstance(val, dict):
                    yield val
                elif isinstance(val, (dict, list)):
                    yield from _selectors(val)

    def _sel(node: Any) -> None:
        for sel in _selectors(node):
            for attr in list(sel):
                sel[attr] = _value(sel[attr])
        # `every`/`observe` name their set the same way a `select` does, and a goal built
        # from one carries the stand-in in exactly the same slot.
        if isinstance(node, dict):
            for field in ("every", "observe", "must"):
                if isinstance(node.get(field), dict):
                    for attr in list(node[field]):
                        node[field][attr] = _value(node[field][attr])
        if isinstance(node, list):
            for kid in node:
                _sel(kid)
        elif isinstance(node, dict):
            for val in node.values():
                if isinstance(val, (dict, list)):
                    _sel(val)

    def _walk(statements) -> None:
        for st in statements or ():
            args = st.get("args")
            if isinstance(args, dict):
                for arg in list(args):
                    args[arg] = _value(args[arg])
            if isinstance(st.get("from"), str):
                st["from"] = _value(st["from"])
            # A FACT EMBEDS A NAME RATHER THAN EQUALLING IT — the kind's own template builds
            # `answer(...)` around it — so this is a substring replacement, as it is in
            # `_parameterise` for the same reason.
            fact = st.get("fact")
            if isinstance(fact, str):
                for token, param in tokens.items():
                    if token in fact:
                        bound.add(param)
                        fact = fact.replace(token, f"{sigil}{param}")
                st["fact"] = fact
            _sel(st.get("predicate"))
            for block in ("do", "then", "else", "ifails"):
                _walk(st.get(block))

    _walk(program.get("body"))
    # THE CONTRACT TOO, and for the reason `_declare` gives: `achieves` is what a future goal
    # is matched against, so a body taking `$name` under a contract still naming the stand-in
    # would advertise a promise it does not keep — and would be reached for by nothing, since
    # no real goal can ever mention a name minted to match nothing.
    _sel(program.get("achieves"))
    return bound
