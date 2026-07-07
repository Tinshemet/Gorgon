# Compatibility shim — real implementation lives in executor/api/qemu_config.py.
# This module exists so that mock.patch("shared.api.qemu_config.list_profiles")
# continues to work in the test suite without modification.
from executor.api.qemu_config import *      # noqa: F401, F403
from executor.api.qemu_config import (      # noqa: F401
    list_profiles,
    OVMF,
)
