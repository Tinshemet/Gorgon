"""
ir/config — the procedure language, loaded from JSON.

  ir.defaults.json  — the full manifest: ops, resource kinds, predicate shapes, prompt
  ir.json           — this deployment's overrides (win on merge)

Same shape as shared/, client/, admin/, orchestrator/ and executor/config. This file
holds NO literal language values of its own: every op, kind, predicate and string the
model is shown comes from the manifest, so extending the language is a data change.

That is not tidiness — it is the design note's extensibility test. A new resource type
must be one row in `kinds`, touching zero language code; a new predicate one row in
`predicates`. If a value lives here as a Python literal, the test fails for it.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_json(path: str) -> dict:
    """Load a JSON file, returning an empty dict on any error."""
    try:
        return json.load(open(path))
    except Exception:
        return {}


def _merge(base: dict, over: dict) -> dict:
    """Overrides win, one level deep — so a deployment can retune `prompt.intro`
    without restating the whole prompt block."""
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = {**out[k], **v} if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


_CFG = _merge(load_json(os.path.join(_HERE, "ir.defaults.json")),
              load_json(os.path.join(_HERE, "ir.json")))


def _c(key: str):
    """A merged setting; KeyError if the defaults manifest is missing it."""
    return _CFG[key]


SIGIL      = _c("sigil")           # marks a reference to a bound name
LOOP_VAR   = _c("loop_var")        # the member inside a foreach
PARAM_TYPES = _c("param_types")    # declarable parameter types -> {sql}
FIELDS     = _c("fields")          # every statement field, described once

OPS        = _c("ops")             # statement type -> {required, doc}
KINDS      = _c("kinds")           # THE RESOURCE MANIFEST: kind -> {package, create, list, key, attrs}
PREDICATES = _c("predicates")      # shape -> {source, operand, comparators, doc}
PROMPT     = _c("prompt")          # every string the model is shown
SCHEMA     = _c("schema")          # tool-schema knobs


def packages_for(kinds_used) -> list:
    """The packages a program depends on, DERIVED from the kinds it touches.

    The model never writes an import; the harness computes one. See the design note §07
    — every kind names its package, so the dependency set falls out of the body.
    """
    seen, out = set(), []
    for k in kinds_used:
        pkg = (KINDS.get(k) or {}).get("package")
        if pkg and pkg not in seen:
            seen.add(pkg)
            out.append({"package": pkg})
    return out


def as_dict() -> dict:
    """The merged manifest, defaults ∪ overrides."""
    return dict(_CFG)
