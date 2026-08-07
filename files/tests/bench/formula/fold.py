"""THE FOLD — many legal moves collapsed into the one number that IS the request.

The operator, 2026-08-07: *"rung 11 — 'ping all vms' is one legal move and therefore has a
key, and 'stop all non-responding ones' is also one legal move. I want both, and the final
key that folds them, which is essentially the final rung 11 as key."*

# THE ALGEBRA, STATED PRECISELY

The operator called this a group-theory formula. The exact structure is worth pinning down,
because being precise about it is what makes it do work rather than decorate:

  * THE SLOT BITS ARE A GENUINE GROUP. Nine independent presence bits under XOR are
    (Z/2)^9 — the elementary abelian 2-group of order 512. With the comparator (7) and the
    relation (2) the whole key space is 512 x 7 x 2 = 7168 possible moves. THE FOURTEEN-RUNG
    CORPUS USES EIGHT. That ratio is the entire argument for the design: the model is
    currently choosing from an unbounded space of shapes to land on one of eight.

  * THE FOLD IS A COMMUTATIVE MONOID, NOT A GROUP. Associative, with the empty request as
    identity, and NO INVERSES — nothing you can fold onto "create five machines" to get
    back to nothing. That asymmetry is not a defect in the analogy, it is the domain being
    honest: acts on a lab do not undo by composition.

  * AND COMMUTATIVITY IS THE PAYOFF. The fold does not care what order the moves arrive in,
    because ORDER IS RECOVERED, not supplied — topologically, from the derived edges. The
    operator's sketch had the AI supply "the order, information and type". It turns out it
    only has to supply the information and the type. `observe alive` must precede
    `stop where alive=false` because ASKS→FILTERS says so, and no one had to say it.

    That removes a whole failure mode from the model's reach, and it means the clause
    splitter's grouping choices cannot change the answer.
"""
import json
from typing import Dict, List, NamedTuple, Optional, Tuple

from . import edges as _edges
from .slots import SUBKEY_BITS, Move

_EDGE_KINDS = len(_edges.KINDS_OF_EDGE)


class Signature(NamedTuple):
    """The whole request as one value."""
    number: int                     # THE key — exact, reversible, never hashed
    order: List[int]                # the topological order, as indices into the input
    subkeys: List[int]              # sub-keys in that order
    joins: List[_edges.Edge]        # every derived join
    cyclic: bool                    # the moves contradict each other on ordering
    moves: List[Move]

    @property
    def mnemonic(self) -> str:
        parts = [self.moves[i].mnemonic for i in self.order]
        return "  ▸  ".join(parts)

    @property
    def fingerprint(self) -> str:
        """A short stable spelling for tables. The NUMBER is the identity; this is a label."""
        return f"{self.number % (1 << 32):08x}"

    @property
    def residual(self) -> List[int]:
        """Moves that CANNOT be resolved at plan time, because they filter on an asked fact.

        This is the front half handing the back half exactly what it needs. The writer's
        rung-11 bug is that it resolves these early; it cannot know not to, because until
        now nothing computed the set.
        """
        return sorted({e.dst for e in self.joins if e.kind == _edges.ASKS_FILTERS})

    @property
    def holes(self) -> List[int]:
        """Moves that EXCEPT an identity nobody else handles — a set carved out and dropped."""
        covered = {e.src for e in self.joins if e.kind == _edges.COVERS}
        return sorted({i for i, m in enumerate(self.moves)
                       if m.filled.get("except") and i not in covered})


def _canonical(move: Move) -> str:
    return json.dumps({k: _plain(v) for k, v in sorted(move.filled.items())}, sort_keys=True)


def _plain(v):
    if isinstance(v, tuple):
        return list(v)
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in sorted(v.items())}
    return v


def _toposort(moves: List[Move], joins: List[_edges.Edge]) -> Tuple[List[int], bool]:
    """Recover the order from the joins. Deterministic: ties break on the move's own content.

    Returns (order, cyclic). A cycle is not an exception — it is a FINDING, and the caller
    is told rather than crashed.
    """
    n = len(moves)
    after: Dict[int, set] = {i: set() for i in range(n)}
    for e in _edges.orders(joins):
        if e.src != e.dst:
            after[e.dst].add(e.src)
    # THE TIE-BREAK MUST NOT MENTION THE INPUT POSITION. Two moves that no edge separates
    # are ordered by their own CONTENT, so shuffling the input cannot move them; and two
    # moves with identical content sort equal, which is harmless because their sub-keys and
    # their edges are identical too.
    tie = {i: (moves[i].key, _canonical(moves[i])) for i in range(n)}
    out: List[int] = []
    left = set(range(n))
    while left:
        ready = sorted((i for i in left if not (after[i] & left)), key=lambda i: tie[i])
        if not ready:
            return out + sorted(left, key=lambda i: tie[i]), True
        out.extend(ready)
        left -= set(ready)
    return out, False


def fold(moves: List[Move], kinds=None) -> Signature:
    """Many moves -> ONE number.

        FINAL = Σ subkey_i · 2^(13i)   +   edge_word · 2^(13n)

    Positional, exact and reversible — not a hash. Two requests share a number if and only
    if they are the same request-shape.
    """
    joins = _edges.derive(moves, kinds)
    order, cyclic = _toposort(moves, joins)
    place = {orig: slot for slot, orig in enumerate(order)}

    number = 0
    subkeys = []
    for slot, orig in enumerate(order):
        k = moves[orig].key
        subkeys.append(k)
        number |= k << (SUBKEY_BITS * slot)

    n = max(len(moves), 1)
    word = 0
    for e in joins:
        i, j = place[e.src], place[e.dst]
        if e.kind == _edges.APART:
            # APART is the one genuinely SYMMETRIC join — it has no direction to record, and
            # storing it in whatever order the moves arrived would leak the input's ordering
            # into the number. COVERS is directional (i carves out, j handles) even though it
            # constrains no sequence, so its direction is kept.
            i, j = min(i, j), max(i, j)
        word |= 1 << ((i * n + j) * _EDGE_KINDS + _edges.CODE[e.kind])
    number |= word << (SUBKEY_BITS * n)

    return Signature(number=number, order=order, subkeys=subkeys, joins=joins,
                     cyclic=cyclic, moves=list(moves))


# ── the monoid's identity ─────────────────────────────────────────────────────────────
EMPTY = Move()


def is_identity(sig: Signature) -> bool:
    return sig.number == 0
