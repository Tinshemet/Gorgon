# Compatibility shim — real implementation lives in orchestrator/preflight/validator.py.
# This module exists so that mock.patch("shared.preflight.validator._preflight_check")
# continues to work in the test suite without modification.
from orchestrator.preflight.validator import *         # noqa: F401, F403
from orchestrator.preflight.validator import (         # noqa: F401
    _preflight_check,
    _show_preflight_warning,
)
