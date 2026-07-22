"""
claim_types.py — the typed-claim registry, as classes.

A claim type declares how a model-PROPOSED finding is validated: its value_type
(coercion, so the ledger stays typed) and an optional guest_probe ``assertion``
(probe-grounding, so a false claim is dropped). The 18-odd type DEFINITIONS stay
data (claim_types.json); this module wraps each in a :class:`ClaimType` with the
behaviour — coerce the value, build the fact key, build the probe spec — and models
the value coercions as :class:`ValueType` strategies (one class per shape), which
kills the procedural coerce if/elif.
"""

import json
import os
from typing import Any, Dict, Optional


class ValueType:
    """How a claimed value of a given shape is coerced (keeps the ledger typed: a
    balance is an int, not the string '5000'). One subclass per shape."""

    name: str = ""
    aliases: tuple = ()

    def coerce(self, raw: Any) -> Any:
        raise NotImplementedError


class StringValue(ValueType):
    name = "string"; aliases = ("str",)
    def coerce(self, raw): return str(raw)


class IntValue(ValueType):
    name = "int"; aliases = ("integer",)
    def coerce(self, raw): return int(raw)


class FloatValue(ValueType):
    name = "float"
    def coerce(self, raw): return float(raw)


class BoolValue(ValueType):
    name = "bool"; aliases = ("boolean",)
    def coerce(self, raw): return str(raw).strip().lower() in ("1", "true", "yes")


# name/alias → strategy instance; adding a shape = add a ValueType subclass here.
_VALUE_TYPES: Dict[str, ValueType] = {}
for _cls in (StringValue, IntValue, FloatValue, BoolValue):
    _inst = _cls()
    for _n in (_cls.name,) + _cls.aliases:
        _VALUE_TYPES[_n] = _inst


def value_type(name: str) -> ValueType:
    """The ValueType strategy for a declared value_type name (unknown → string)."""
    return _VALUE_TYPES.get(name, _VALUE_TYPES["string"])


class ClaimType:
    """One typed claim: its value coercion + optional probe assertion. Instantiated
    from a claim_types.json entry; wraps the data with the fact-key + probe-spec
    behaviour the findings ledger needs."""

    def __init__(self, name: str, value_type_name: str = "string",
                 assertion: Optional[str] = None, operand: bool = False):
        self.name            = name
        self.value_type_name = value_type_name
        self.value           = value_type(value_type_name)
        self.assertion       = assertion
        self.operand         = bool(operand)

    @property
    def grounded(self) -> bool:
        """True if a guest_probe can confirm this claim (has an assertion)."""
        return bool(self.assertion)

    def coerce(self, raw: Any) -> Any:
        """Coerce a claimed value to this type (ValueError/TypeError on a bad value)."""
        return self.value.coerce(raw)

    def fact_key(self, value: Any) -> str:
        """The ledger fact key for a claimed value, e.g. ``port_open(443)``."""
        return f"{self.name}({value})"

    def probe_spec(self, vm: Any, value: Any, operand_val: Any = None) -> Optional[str]:
        """The independent guest_probe spec ``vm:assertion:value[:operand]`` this
        claim must pass before it's recorded, or None (an unverified claim)."""
        if not self.assertion:
            return None
        spec = f"{vm}:{self.assertion}:{value}"
        if self.operand:                       # two-operand assertion (e.g. host_reachable)
            spec += f":{operand_val or ''}"
        return spec


def load_claim_types() -> Dict[str, ClaimType]:
    """The claim-type registry {name: ClaimType} built from claim_types.json."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "claim_types.json")) as f:
            raw = json.load(f).get("types", {}) or {}
    except Exception:
        return {}
    out: Dict[str, ClaimType] = {}
    for name, spec in raw.items():
        if isinstance(spec, dict):
            out[name] = ClaimType(name, spec.get("value_type", "string"),
                                  spec.get("assertion"), spec.get("operand", False))
    return out


def claim_type(name: str) -> Optional[ClaimType]:
    """The ClaimType for a name, or None if it isn't a declared type."""
    return load_claim_types().get(name)
