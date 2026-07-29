"""
ir/config — MEDUSA, the Gorgon procedure language, loaded from JSON.

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


LANGUAGE   = _c("language")        # name, version, file extension
SIGIL      = _c("sigil")           # marks a reference to a bound name
LOOP_VAR   = _c("loop_var")        # the member inside a foreach
PARAM_TYPES = _c("param_types")    # declarable parameter types -> {sql, py, doc}
SURFACE    = _c("surface")         # the written spelling of things the IR stores plainly
FIELDS     = _c("fields")          # every statement field, described once

OPS        = _c("ops")             # statement type -> {required, doc}
QUANTIFIERS = _c("quantifiers")    # all/any/single/not -> {ops, doc}: how many things a
                                   # clause is about, and what that licenses
OP_CATEGORIES = _c("op_categories")  # "structural" (a decomposition CHOOSES these) vs
                                     # "intent" (fetch/ensure/achieve — supplied by the
                                     # operator's intent, never the author's to guess)
NOT_OPS    = _c("not_ops")         # a word written as a statement that is not one -> where it belongs
SANITIZE   = _c("sanitize")        # artifact kinds the sanitiser removes -> {severity, why, evidence}
KINDS      = _c("kinds")           # THE RESOURCE MANIFEST: kind -> {package, create, list, key, attrs}
PREDICATES = _c("predicates")      # shape -> {source, operand, comparators, doc}
PROMPT     = _c("prompt")          # every string the model is shown
SCHEMA     = _c("schema")          # tool-schema knobs
AUTHORING  = _c("authoring")       # "program" (one tool) or "statements" (one per op)
INTENT     = _c("intent")          # how the OPERATOR says check-vs-bring-about (ir/intent.py)
GATE       = _c("gate")            # the schema gate's weighted factors and bands (ir/gate.py)

OBSERVED_VALUES  = _c("observed_values")    # true / false / unknown
OBSERVED_UNKNOWN = _c("observed_unknown")   # the value meaning "nobody asked"


def observed(kind: str) -> dict:
    """This kind's findings-sourced attributes -> {fact, by, doc}.

    Empty for a kind that has none, which is most of them: an observed attribute exists
    only where a tool goes and LOOKS. See `_observed_doc` in the manifest for why the
    answer to decision 6 was "nothing escapes a loop" rather than an accumulator.
    """
    return (KINDS.get(kind) or {}).get("observed") or {}


def queryable(kind: str) -> set:
    """Every attribute legal in a SELECT ... WHERE for this kind — registry, observed,
    and the harness's own synonyms.

    ONE authority for the question. The attribute set was read straight off `attrs` in
    four separate places (the validator's legality check, its rejection message, the
    schema offered to the author, and the prompt's "queryable on" line), so adding a
    findings-sourced attribute in the manifest alone would have been accepted by the
    validator and never OFFERED to the model — the schema-withholding failure that
    accounted for more measured "model errors" than anything else. A new row is now
    visible in all four places or none.
    """
    spec = KINDS.get(kind) or {}
    return set(spec.get("attrs") or ()) | set(spec.get("aliases") or ()) | set(observed(kind))


def canonical(kind: str, attr: str) -> str:
    """An attribute under its ONE name — `tag` and `labels` are both `label`.

    The harness has its own synonyms and a program written either way means the same
    thing, so every check that reasons about an attribute has to resolve them first or it
    silently skips the spellings it does not recognise.
    """
    return ((KINDS.get(kind) or {}).get("aliases") or {}).get(attr, attr)


def values_for(kind: str, attr: str):
    """The closed set of values `attr` may take, or None when it is open text.

    ONE answer for both sorts of attribute — a registry one with a fixed vocabulary
    (`status` is running or stopped) and an observed one (`alive` is true, false or
    unknown). Callers ask this instead of knowing which sort they hold, so offering a new
    constrained attribute to the author stays a manifest row.

    None is a real answer and means "anything": a name or a label is open by nature and
    pretending otherwise would reject legitimate programs.
    """
    spec = KINDS.get(kind) or {}
    attr = canonical(kind, attr)
    if attr in (spec.get("observed") or {}):
        return list(OBSERVED_VALUES)
    vals = (spec.get("attr_values") or {}).get(attr)
    return list(vals) if vals else None


def fact_key(kind: str, attr: str, member: str):
    """The ledger key holding `attr` for `member` — `reachable(web)`, or None if this
    attribute is not observed.

    The template binds the kind's KEY to the member, so the manifest writes it the same
    way the tool's own yield schema does. Read from the query side here and from the call
    side in findings.yield_fact; both format the same template, which is what stops the
    two directions from drifting into different vocabularies.
    """
    spec = observed(kind).get(attr)
    key = (KINDS.get(kind) or {}).get("key")
    if not spec or not key:
        return None
    try:
        return spec["fact"].format(**{key: member})
    except (KeyError, IndexError):
        return None


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
