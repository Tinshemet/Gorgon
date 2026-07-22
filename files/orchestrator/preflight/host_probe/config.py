"""config.py — host-probe config (loaded from preflight/config.json, one dir up)."""
import json
import os

_CFG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")))
_THRESHOLDS            = _CFG["thresholds"]
_NET_TIMEOUT           = _CFG["net_timeout"]
_ARM_CPU_PREFIXES      = tuple(_CFG["arm_cpu_prefixes"])
_X86_CPU_NAMES         = set(_CFG["x86_cpu_names"])
_STEALTH_PRODUCT_HINTS = [tuple(h) for h in _CFG["stealth_product_hints"]]
_MS_WINDOWS_ISO_PAGE   = _CFG["ms_windows_iso_page"]
