"""books — the creation ledger and the book keeper.

    THE RECORD PRECEDES THE OBJECT.

Today "it exists" is a CLAIM IN A RETURN VALUE. This makes it a FACT IN THE REGISTRY, and
that is the failure class this project has fought harder than any other: `create_vm` returns
`success: True` and the harness believes it; `guest_ping` returned `success: True` for dead
machines and three consumers believed it.

Placed ABOVE `active_library` and `planner/findings` because it reconciles both, which is
why it cannot live inside `planner/`.
"""
from .ledger import DELETED, EXIST, FAILED, MISSING, PENDING, Ledger, LEDGER
from .keeper import Keeper

__all__ = ["Ledger", "LEDGER", "Keeper",
           "PENDING", "EXIST", "FAILED", "DELETED", "MISSING"]
