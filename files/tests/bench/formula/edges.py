"""THE EDGES BETWEEN MOVES — derived from the slots, never asked for.

Two clauses are not independent. *"Create a network called lab"* and *"put web on lab"* are
joined, and the join is the thing rung 3 loses. The operator's fold needs those joins, and
the whole point is that NOBODY SUPPLIES THEM: they fall out of comparing what one move
PRODUCES against what another CONSUMES.

    ASKS→FILTERS   i observes an attribute, j filters on it       ← BINDING TIME
    MAKES→NAMES    i brings into being the identity j references
    MAKES→SCOPES   i fixes the population j quantifies over
    SETS→FILTERS   i sets an attribute value, j filters on it
    SETTLES→CHECKS i assigns over a set, j asserts a RELATION over an overlapping one
    COVERS         i EXCEPTS an identity, j handles it            ← the exception's other half
    APART          i and j drive one attribute to different values over disjoint sets

ASKS→FILTERS is the one that matters most, because it is
[[gorgon-the-writer-fails-rung-11]] made visible at the FRONT of the pipeline. A filter on
an attribute that some other move had to go and ASK cannot be resolved at plan time. Today
nothing carries that fact from the reading to the writer, and the writer resolves it early
and plans nothing. The edge is the carrier.

COVERS is the exception's other half, and it is gate 3's relation question ANSWERED rather
than asked: rung 8 excepts `db` and then handles `db`, so the pair is total. An `except`
with no COVERS edge is a hole in the request — a set carved out and then abandoned.
"""
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from planner.gates import claims as _claims

from .slots import Move

ASKS_FILTERS = "ASKS→FILTERS"
MAKES_NAMES = "MAKES→NAMES"
MAKES_SCOPES = "MAKES→SCOPES"
SETS_FILTERS = "SETS→FILTERS"
COVERS = "COVERS"
APART = "APART"
SETTLES = "SETTLES→CHECKS"

# the fixed order is the arithmetic — never re-order, only append
KINDS_OF_EDGE: Tuple[str, ...] = (
    ASKS_FILTERS, MAKES_NAMES, MAKES_SCOPES, SETS_FILTERS, COVERS, APART, SETTLES,
)
CODE: Dict[str, int] = {name: i for i, name in enumerate(KINDS_OF_EDGE)}

# an edge that forces one move to precede another. APART is symmetric and orders nothing.
ORDERING: Set[str] = {ASKS_FILTERS, MAKES_NAMES, MAKES_SCOPES, SETS_FILTERS, SETTLES}


class Edge(NamedTuple):
    src: int
    dst: int
    kind: str
    on: str          # the attribute or identity the join runs through

    def __repr__(self):
        return f"{self.src}—{self.kind}({self.on})→{self.dst}"


# ── what a move puts into the world, and what it needs from it ────────────────────────
def _identity(move: Move, kinds=None) -> Optional[Tuple[str, str, object]]:
    """The identity this move is ABOUT, if it names one: (kind, key-attr, value)."""
    subject = move.filled.get("subject")
    key = _claims.key_of(subject, kinds) if subject else None
    if not key:
        return None
    value = (move.filled.get("filter") or {}).get(key)
    return ("id", subject, value) if value is not None else None


def produces(move: Move, kinds=None) -> Set[tuple]:
    """What this move makes true — identities brought into being, attributes set, facts asked."""
    out: Set[tuple] = set()
    count = move.filled.get("count")
    asserts_existence = count is not None and count[1] != 0
    ident = _identity(move, kinds)
    if ident and asserts_existence:
        out.add(ident)
    for attr, value in (move.filled.get("target") or {}).items():
        out.add(("attr", attr, _hashable(value)))
    if move.filled.get("fact"):
        out.add(("fact", move.filled["fact"], None))
    if move.filled.get("makes"):
        out.add(("kind", move.filled["makes"][0], None))
    return out


def consumes(move: Move, kinds=None) -> Set[tuple]:
    """What this move relies on already being true."""
    out: Set[tuple] = set()
    subject = move.filled.get("subject")
    key = _claims.key_of(subject, kinds) if subject else None
    for attr, value in (move.filled.get("filter") or {}).items():
        if attr == key:
            continue                    # naming YOURSELF is not a reference to elsewhere
        out.add(("attr", attr, _hashable(value)))
        points_at = _claims.refers_to(attr, kinds)
        if points_at:
            out.add(("id", points_at, _hashable(value)))
    if move.filled.get("source"):
        out.add(("id", subject, move.filled["source"]))
    for attr, value in (move.filled.get("target") or {}).items():
        points_at = _claims.refers_to(attr, kinds)
        if points_at:
            out.add(("id", points_at, _hashable(value)))
    return out


def excepts(move: Move, kinds=None) -> Set[tuple]:
    out: Set[tuple] = set()
    subject = move.filled.get("subject")
    key = _claims.key_of(subject, kinds) if subject else None
    for attr, value in (move.filled.get("except") or {}).items():
        out.add(("attr", attr, _hashable(value)))
        if attr == key and subject:
            out.add(("id", subject, _hashable(value)))
    return out


def _hashable(v):
    if isinstance(v, dict):
        return tuple(sorted((k, _hashable(x)) for k, x in v.items()))
    if isinstance(v, list):
        return tuple(_hashable(x) for x in v)
    return v


def _filter_attrs(move: Move) -> Set[str]:
    return set((move.filled.get("filter") or {}).keys())


def _disjoint(a: Move, b: Move) -> bool:
    """Do these two moves provably act on non-overlapping sets?"""
    fa, fb = a.filled.get("filter") or {}, b.filled.get("filter") or {}
    for attr in set(fa) & set(fb):
        if fa[attr] != fb[attr]:
            return True                 # same attribute, different value -> cannot overlap
    for x, y in ((a, b), (b, a)):
        for attr, value in (x.filled.get("except") or {}).items():
            if (y.filled.get("filter") or {}).get(attr) == value:
                return True             # one excepts exactly what the other selects
    return False


# ── the derivation ────────────────────────────────────────────────────────────────────
def derive(moves: List[Move], kinds=None) -> List[Edge]:
    """Every join between these moves, computed. No model call, no operator question."""
    made = [produces(m, kinds) for m in moves]
    used = [consumes(m, kinds) for m in moves]
    skipped = [excepts(m, kinds) for m in moves]
    found: List[Edge] = []

    for i, a in enumerate(moves):
        for j, b in enumerate(moves):
            if i == j:
                continue
            # ASKS→FILTERS — the binding-time edge
            for tag, attr, _ in made[i]:
                if tag == "fact" and attr in _filter_attrs(b):
                    found.append(Edge(i, j, ASKS_FILTERS, attr))
            # MAKES→NAMES / SETS→FILTERS — a produced thing that another move needs
            for item in made[i] & used[j]:
                tag, attr, value = item
                if tag == "id":
                    found.append(Edge(i, j, MAKES_NAMES, f"{attr}={value}"))
                elif tag == "attr":
                    found.append(Edge(i, j, SETS_FILTERS, f"{attr}={value}"))
            # COVERS — i carves a set out, j is the one that handles it. This fires on any
            # ATTRIBUTE, not only on an identity: rung 8 excepts `name=db` and rung 6
            # excepts `label=red`, and both are a set carved out and handed to another move.
            for tag, attr, value in skipped[i]:
                handled = (tag, attr, value) in used[j] or (tag, attr, value) in made[j]
                if not handled and (b.filled.get("filter") or {}).get(attr) == value:
                    handled = True
                if handled:
                    found.append(Edge(i, j, COVERS, f"{attr}={value}"))
            # MAKES→NAMES on ONE identity — i is the bare existence claim, j says more about
            # the same thing. "create beta" must precede "beta is running", and the only
            # thing distinguishing them is that one filter is a SUBSET of the other.
            ida, idb = _identity(a, kinds), _identity(b, kinds)
            if ida and ida == idb:
                fa = set((a.filled.get("filter") or {}).items())
                fb = set((b.filled.get("filter") or {}).items())
                if fa < fb:
                    found.append(Edge(i, j, MAKES_NAMES, f"{ida[1]}={ida[2]}"))
            # MAKES→SCOPES — i fixes how many there are, j quantifies over them. j's scope
            # must CONTAIN i's: a narrower filter on j would be acting on a different set,
            # which is rung 6's two groups and exactly what must NOT join.
            count = a.filled.get("count")
            scopes = (
                count and count[1] != 0
                # a RELATION asserts that something holds, not that anything exists. Rung 4's
                # "make sure they all ping each other" creates no machines, and letting it
                # scope the moves that DO create them makes the request cyclic.
                and not a.filled.get("predicate")
                and a.filled.get("subject") == b.filled.get("subject")
                and (b.filled.get("target") or b.filled.get("makes"))
            )
            if scopes:
                fa = set((a.filled.get("filter") or {}).items())
                fb = set((b.filled.get("filter") or {}).items())
                # and j cannot be scoped by something it has explicitly EXCEPTED — rung 8's
                # "every vm except db" is not waiting on db.
                carved = any((a.filled.get("filter") or {}).get(attr) == value
                             for attr, value in (b.filled.get("except") or {}).items())
                if fb <= fa and not carved:
                    found.append(Edge(i, j, MAKES_SCOPES, str(a.filled.get("subject"))))
            # SETTLES→CHECKS — an assurance runs AFTER whatever makes it true. Rung 6's
            # "the red group shares a network" must settle before "the red group can all
            # ping each other" is worth asking; a check that precedes its own subject is
            # not a check. Domain-general — it says nothing about which rung it came from.
            if (a.filled.get("target") and not a.filled.get("predicate")
                    and b.filled.get("predicate") and not b.filled.get("target")
                    and a.filled.get("subject") == b.filled.get("subject")):
                fa = set((a.filled.get("filter") or {}).items())
                fb = set((b.filled.get("filter") or {}).items())
                if fa <= fb or fb <= fa:
                    found.append(Edge(i, j, SETTLES, str(b.filled.get("predicate"))))

    # APART — symmetric, recorded once, in canonical order
    for i, a in enumerate(moves):
        for j in range(i + 1, len(moves)):
            b = moves[j]
            ta, tb = a.filled.get("target") or {}, b.filled.get("target") or {}
            shared = {k for k in set(ta) & set(tb) if ta[k] != tb[k]}
            if shared and _disjoint(a, b):
                for attr in sorted(shared):
                    found.append(Edge(i, j, APART, attr))

    return sorted(set(found))


def orders(edges: List[Edge]) -> List[Edge]:
    """Only the edges that constrain sequence. APART constrains nothing."""
    return [e for e in edges if e.kind in ORDERING]
