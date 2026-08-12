"""THE SLOT VOCABULARY — the only things an AI is ever asked for.

The operator's design, 2026-08-07: *"we give it a FORMULA, a math, an equation — all it has
to do is slot things into place, not invent stuff. That formula produces a unique key made
from our answers. The AI doesn't know what the final answer is, it only gives the order,
information and type, and the formula does the rest."*

So the model never names a shape. It answers nine ordinary questions, and WHICH ONES COME
BACK is the key. `every`, `select`, `per` and `observe` leave its vocabulary entirely —
which is the point, because choosing `count` when it should have chosen `every` is rung 11's
failure and that move stops existing.

    subject    what kind of thing?                 vm · network · snapshot
    filter     which of them?                      {status: stopped}
    except     which of them NOT?                  {name: db}
    count      how many?                           (eq, 5) · (min, 3)
    predicate  what relation must hold?            reach            [closed set]
    target     what must become true of them?      {network: core}
    fact       what should we go and ASK?          alive
    makes      what new thing per member?          (snapshot, vm)
    source     what is it copied from?             golden

The comparator rides INSIDE `count` rather than being its own slot. That is deliberate: on
the 14-request corpus `reach` always pairs with `min` and plain cardinality always with `eq`,
so a bare slot-presence key looks sufficient — but that correlation is very likely an
artifact of a small corpus, and typing the slot costs nothing.
"""
from typing import Dict, List, Optional, Tuple

# ── the nine slots, in a FIXED order. The order is the arithmetic; never re-order it.
SLOTS: Tuple[str, ...] = (
    "subject", "filter", "except", "count", "predicate", "target", "fact", "makes", "source",
)
BIT: Dict[str, int] = {name: 1 << i for i, name in enumerate(SLOTS)}

# comparators and relations are CLOSED SETS — an AI picking from a closed set is choosing a
# legal move, not inventing a shape.
CMP: Dict[Optional[str], int] = {
    None: 0, "eq": 1, "min": 2, "max": 3, "gte": 4, "lte": 5, "amount": 6,
}
PRED: Dict[Optional[str], int] = {None: 0, "reach": 1}

_CMP_KEYS = ("amount", "eq", "gte", "lte", "min", "max")
_SELECTORS = ("select", "every", "per", "observe")

# how many bits each field occupies in the packed sub-key
_SLOT_BITS = len(SLOTS)          # 9
_CMP_SHIFT = _SLOT_BITS          # 9
_PRED_SHIFT = _CMP_SHIFT + 3     # 12
SUBKEY_BITS = _PRED_SHIFT + 1    # 13 -> every sub-key is < 8192


class Move:
    """ONE LEGAL MOVE — one clause, reduced to the values an AI would have supplied.

    A move knows nothing about Medusa. It is nine optional values and nothing else.
    """

    __slots__ = ("filled", "text")

    def __init__(self, text: str = "", **filled):
        bad = set(filled) - set(SLOTS)
        if bad:
            raise ValueError(f"not a slot: {sorted(bad)}")
        self.filled = {k: v for k, v in filled.items() if v not in (None, {}, (), [])}
        self.text = text

    # ── the formula itself ────────────────────────────────────────────────────────────
    @property
    def key(self) -> int:
        """The sub-key: a number the AI never sees and cannot aim at.

            bits 0-8   which slots came back
            bits 9-11  the comparator inside `count`
            bit  12    the relation inside `predicate`
        """
        n = 0
        for name in SLOTS:
            if name in self.filled:
                n |= BIT[name]
        n |= CMP[self.comparator] << _CMP_SHIFT
        n |= PRED[self.filled.get("predicate")] << _PRED_SHIFT
        return n

    @property
    def comparator(self) -> Optional[str]:
        c = self.filled.get("count")
        return c[0] if c else None

    @property
    def mnemonic(self) -> str:
        """A human-readable spelling of the same number."""
        short = {"subject": "S", "filter": "F", "except": "X", "count": "C",
                 "predicate": "P", "target": "T", "fact": "?", "makes": "M", "source": "<"}
        out = []
        for name in SLOTS:
            if name not in self.filled:
                continue
            tag = short[name]
            if name == "count":
                tag += f"[{self.comparator}]"
            elif name == "predicate":
                tag += f"[{self.filled['predicate']}]"
            out.append(tag)
        return "·".join(out)

    def __repr__(self):
        return f"<move {self.mnemonic} k={self.key}>"


def provenance_of(kind: Optional[str], kinds=None) -> Optional[str]:
    """The attribute a creator RECORDS when it copies something — `cloned_from` for a vm.

    Read off the manifest's own `creators`, so a kind added later is covered without an
    edit here. A creator that takes a `from` but records nothing (`from_template`) leaves
    no trace to filter on, and is correctly not offered.
    """
    from planner.ir import config as _config
    table = kinds if kinds is not None else (_config.KINDS or {})
    spec = table.get(kind) or {}
    for creator in (spec.get("creators") or {}).values():
        if isinstance(creator, dict) and creator.get("from") and creator.get("records"):
            return creator["records"]
    return None


# ── reading a known-good IR goal BACK into slots ──────────────────────────────────────
def reduce(goal: dict) -> Move:
    """Reduce one IR goal to the slots an AI would have had to supply.

    This direction exists only to MEASURE — to ask whether the slot vocabulary can express
    every reading we already believe is correct. The pipeline runs the other way.
    """
    sel = {}
    for name in _SELECTORS:
        if name in goal:
            sel = dict(goal[name])
            break
    filled = {"subject": sel.pop("kind", None)}
    provenance = provenance_of(filled["subject"])
    if provenance and provenance in sel:
        filled["source"] = sel.pop(provenance)
    neg = sel.pop("not", None)
    if neg:
        filled["except"] = dict(neg)
    if sel:
        filled["filter"] = sel
    for c in _CMP_KEYS:
        if c in goal:
            filled["count"] = (c, goal[c])
            break
    shape = goal.get("shape")
    if shape and shape != "count":
        filled["predicate"] = shape
    if goal.get("must"):
        filled["target"] = dict(goal["must"])
    if goal.get("fact"):
        filled["fact"] = goal["fact"]
    if goal.get("make"):
        filled["makes"] = (goal["make"], goal.get("link"))
    if goal.get("cloned_from") or goal.get("source"):
        filled["source"] = goal.get("cloned_from") or goal.get("source")
    return Move(**filled)


# ── THE FORMULA'S OTHER HALF: the key SELECTS the form, the values FILL it ────────────
def build(move: Move) -> dict:
    """Turn a filled move back into an IR goal — WITHOUT the AI having chosen a shape.

    This is the whole claim, and it is checkable: the selector keyword is DERIVED from
    which slots came back, never supplied.

        fact present                  -> observe
        makes present                 -> per
        target present, count absent  -> every … must
        otherwise                     -> select … <count>

    If this reconstructs every hand-written correct reading, the AI's shape choice was
    never load-bearing information — it was a liability.
    """
    f = move.filled
    sel: Dict[str, object] = {"kind": f.get("subject")}
    sel.update(f.get("filter") or {})
    if f.get("except"):
        sel["not"] = dict(f["except"])

    if f.get("source"):
        # DECLARED, NOT HARDCODED: the manifest names the attribute a creator RECORDS when
        # it copies something, so "clone web into two" becomes a filter on provenance rather
        # than the world-dependent arithmetic rung 10's reading resorts to.
        attr = provenance_of(f.get("subject"))
        if attr:
            sel[attr] = f["source"]

    if "fact" in f:
        # the filter must survive. Dropping it turns "check whether the gateway answers"
        # into "ping the whole lab" — held-out row 6 caught exactly that.
        return {"observe": sel, "fact": f["fact"]}
    if "makes" in f:
        make, link = f["makes"]
        out = {"per": sel, "make": make}
        if link:
            out["link"] = link
        return out
    if "target" in f and "count" not in f:
        return {"every": sel, "must": dict(f["target"])}
    out = {"shape": f.get("predicate") or "count", "select": sel}
    if "count" in f:
        comparator, n = f["count"]
        out[comparator] = n
    return out
