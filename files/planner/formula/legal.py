"""THE LEGAL-MOVE GENERATOR — the board, read off the manifest.

The operator's chess framing, 2026-08-07: *"a full board of chess has a lot of possible
legal moves at each turn, and it changes based on which pieces are left and where they are
— but we don't need that. We need the AI to fill the formula EACH TURN, and that spews our
best legal move."*

That is the saving. You never enumerate the whole game; you generate the legal moves from
the CURRENT position, which is small. Here the position is the manifest plus the kind under
discussion, and everything below is DECLARED — `attrs`, `attr_values`, `observed`,
`setters`, `creators`, `relations`. Nothing is inferred and nothing is hardcoded, so a kind
added tomorrow is covered without an edit here.

Why this is the lever rather than a nicety: the one thing measured to move a rung is
REMOVING A WRONG OPTION ([[gorgon-detectors-not-producers]]), and only SUBTRACTIVE schema
moves have ever worked ([[gorgon-offering-is-not-using]]). A legal-move generator is
subtraction computed per turn.
"""
from typing import Dict, List, Optional, Sequence, Set

from .slots import CMP, PRED, SLOTS, provenance_of


class Board:
    """What the manifest permits. Every answer is declared, none is inferred."""

    def __init__(self, kinds=None):
        if kinds is None:
            from planner.ir import config as _config
            kinds = _config.KINDS or {}
        self.kinds = kinds

    # ── the pieces ────────────────────────────────────────────────────────────────────
    def subjects(self) -> List[str]:
        return sorted(self.kinds)

    def _spec(self, kind: str) -> dict:
        return self.kinds.get(kind) or {}

    def filterable(self, kind: str) -> List[str]:
        """Attributes a `filter` or `except` may narrow on.

        OBSERVED ATTRIBUTES BELONG HERE and not in `settable` — that asymmetry is the whole
        of rung 11. You may select the machines that did not answer; you may not order a
        machine to answer. PDDL cannot express the difference and will happily satisfy
        `(imply (not (alive ?v)) (stopped ?v))` by STARTING the dead machines.
        """
        return sorted(set(self._spec(kind).get("attrs") or []) | set(self.observable(kind)))

    def settable(self, kind: str) -> List[str]:
        """Attributes a `target` may drive. AN OBSERVED ATTRIBUTE IS NOT SETTABLE — you
        cannot demand a machine be reachable, only that it be stopped."""
        out = {s.get("attr") for s in (self._spec(kind).get("setters") or {}).values()
               if isinstance(s, dict) and s.get("attr")}
        return sorted(out - set(self.observable(kind)))

    def observable(self, kind: str) -> List[str]:
        """Attributes that must be ASKED. These are the binding-time hazards."""
        return sorted(self._spec(kind).get("observed") or {})

    def values(self, kind: str, attr: str) -> Optional[List[str]]:
        """The CLOSED set a value may take, or None when the value is open text."""
        table = self._spec(kind).get("attr_values") or {}
        got = table.get(attr)
        return sorted(got) if got else None

    def relations(self, kind: str) -> List[str]:
        """Predicates the world can check over a set. `reach` is declared by the engine's
        own probe rather than by a kind, so it is offered wherever a set can be formed."""
        return [p for p in PRED if p]

    def makeable(self, kind: str) -> List[str]:
        """Kinds that can be created ONE PER MEMBER of this kind — rung 12's snapshot."""
        out = []
        for other, spec in self.kinds.items():
            if other == kind:
                continue
            for creator in (spec.get("creators") or {}).values():
                if isinstance(creator, dict) and kind in str(creator.get("of") or
                                                             creator.get("member_arg") or
                                                             spec.get("create_args") or ""):
                    out.append(other)
                    break
            else:
                if kind in str(spec.get("create_args") or ""):
                    out.append(other)
        return sorted(set(out))

    def provenance(self, kind: str) -> Optional[str]:
        return provenance_of(kind, self.kinds)

    # ── the legal moves ───────────────────────────────────────────────────────────────
    def offers(self, kind: str) -> Dict[str, object]:
        """Every slot this kind can legally fill, with its permitted values where closed.

        THIS IS THE PROMPT. The model is shown only this, so a slot the manifest cannot
        honour is never even mentioned — it cannot be chosen wrongly because it does not
        appear.
        """
        return {
            "subject": kind,
            "filter": self.filterable(kind),
            "except": self.filterable(kind),
            "count": sorted(c for c in CMP if c),
            "predicate": self.relations(kind),
            "target": self.settable(kind),
            "fact": self.observable(kind),
            "makes": self.makeable(kind),
            "source": [self.provenance(kind)] if self.provenance(kind) else [],
            "_closed_values": {a: self.values(kind, a) for a in self.filterable(kind)
                               if self.values(kind, a)},
        }

    def legal_keys(self, kind: str) -> Set[int]:
        """Which of the whole key space this kind could ever reach.

        The exclusions are structural, not stylistic: a move that goes and ASKS the world
        is not also a move that changes it, and a move that MAKES one thing per member is
        not also a cardinality claim about the members.
        """
        from itertools import product

        from .slots import BIT

        available = {
            "subject": True,
            "filter": bool(self.filterable(kind)),
            "except": bool(self.filterable(kind)),
            "count": True,
            "predicate": bool(self.relations(kind)),
            "target": bool(self.settable(kind)),
            "fact": bool(self.observable(kind)),
            "makes": bool(self.makeable(kind)),
            "source": bool(self.provenance(kind)),
        }
        keys: Set[int] = set()
        for present in product([False, True], repeat=len(SLOTS)):
            chosen = {name for name, on in zip(SLOTS, present) if on}
            if not self._well_formed(chosen, available):
                continue
            bits = 0
            for name in chosen:
                bits |= BIT[name]
            comparators = [c for c in CMP if c] if "count" in chosen else [None]
            relations = [p for p in PRED if p] if "predicate" in chosen else [None]
            for c, p in product(comparators, relations):
                keys.add(bits | (CMP[c] << len(SLOTS)) | (PRED[p] << (len(SLOTS) + 3)))
        return keys

    @staticmethod
    def _well_formed(chosen: Set[str], available: Dict[str, bool]) -> bool:
        if "subject" not in chosen:
            return False                      # a move with no subject is about nothing
        if any(name in chosen and not available[name] for name in chosen):
            return False
        if "fact" in chosen and (chosen & {"target", "count", "makes", "predicate"}):
            return False                      # asking is not acting
        if "makes" in chosen and (chosen & {"target", "count", "predicate"}):
            return False                      # a generator is not also a claim
        if "target" in chosen and "count" in chosen:
            return False                      # assign OR count, never both in one move
        if "predicate" in chosen and "count" not in chosen:
            return False                      # a relation needs a size to hold over
        if "predicate" in chosen and "target" in chosen:
            return False
        return True


def census(board: Optional[Board] = None) -> Dict[str, Set[int]]:
    board = board or Board()
    return {kind: board.legal_keys(kind) for kind in board.subjects()}
