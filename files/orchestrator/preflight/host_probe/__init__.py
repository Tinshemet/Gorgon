"""
host_probe — host/internet capability probing for the pre-flight gate.

Split into focused sub-modules; this facade re-exports the surface the validator and
the tests import (so callers keep importing from ``orchestrator.preflight.host_probe``):

  - net.py       cached network probes + the custom-mode / net-enabled state
  - qemu.py      QEMU capability introspection (machine types, CPU models) + cpu classify
  - product.py   product-identity lookup + stealth SMBIOS inference
  - validate.py  the VM/profile internet+host validators the pre-flight calls

Custom mode is process state (set_custom_mode); read it via custom_mode() so a change
is seen live across modules.
"""

from .net import set_custom_mode, custom_mode, net_enabled, _net_get, _net_head
from .qemu import _get_qemu_machine_types, _get_qemu_cpu_models, _is_arm_cpu, _is_x86_cpu
from .product import _lookup_product, _stealth_infer_from_product
from .validate import _validate_with_internet, _validate_profile_for_host
