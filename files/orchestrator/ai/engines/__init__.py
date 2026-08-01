"""engines — mounted capabilities the orchestrator routes to.

An engine is a manifest plus an adapter. That is the whole contract, and it is small on
purpose: a kitchen was made mountable in ~25 lines and no code (2026-08-01), which is what
makes "every engine must be Medusa-compatible" a morning's work rather than a tax.

NOT `planner/engine.py` — that is the score engine's POLICY BUNDLE, a bag of dependencies
rather than a mounted capability. Two things wearing one word; the older keeps the name.
"""
from .base import Engine, describe          # noqa: F401
from .channel import Answer, Channel, stub  # noqa: F401
from .medusa import MedusaEngine            # noqa: F401
from .orchestrator import Orchestrator      # noqa: F401
from .qemu import LabWorld, QemuEngine      # noqa: F401
from .registry import Registry              # noqa: F401
from .translation_cache import TranslationCache  # noqa: F401
from .session import INTENT_REGIME, REGIMES, Session, rank  # noqa: F401

from .executor import ExecutorEngine  # noqa: E402,F401
