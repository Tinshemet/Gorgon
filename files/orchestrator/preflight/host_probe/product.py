"""product.py — product-identity lookup (internet) + stealth SMBIOS inference."""
import hashlib
from typing import Any, Dict

from .net import _net_get
from .config import _STEALTH_PRODUCT_HINTS


def _lookup_product(manufacturer: str, product: str) -> Dict[str, Any]:
    """Query DuckDuckGo to verify a product exists; return found flag + summary."""
    query  = f"{manufacturer} {product} laptop desktop specifications"
    params = urllib.parse.urlencode({"q": query, "format": "json", "no_html": "1"})
    data   = _net_get(f"https://api.duckduckgo.com/?{params}")
    if not data:
        return {}
    return {
        "found":   bool(data.get("AbstractText") or data.get("Answer")),
        "summary": (data.get("AbstractText") or data.get("Answer") or "")[:300],
        "source":  data.get("AbstractSource", ""),
    }


# Cross-checks machine type, CPU, arch, product existence, memory, and ISO arch against local QEMU and DuckDuckGo.
# In: dict args, bool verbose → Out: List[dict] issues

def _stealth_infer_from_product(product_name: str) -> Dict[str, str]:
    """Infer ``{manufacturer, bios_vendor, smbios_type}`` from a product name.

    Args:
        product_name: Product string (e.g. ``"ThinkPad X1"``).

    Returns:
        Dict with inferred SMBIOS fields, or empty dict if no hint matched.

    Example::

        _stealth_infer_from_product("ThinkPad X1 Carbon")
        # → {"manufacturer": "Lenovo", "bios_vendor": "Lenovo",
        #    "smbios_type": "Notebook"}
        _stealth_infer_from_product("unknown box")
        # → {}
    """
    pn = product_name.lower()
    for keyword, mfr, bios_vendor, smbios_type in _STEALTH_PRODUCT_HINTS:
        if keyword in pn:
            result: Dict[str, str] = {"manufacturer": mfr, "bios_vendor": bios_vendor}
            if smbios_type:
                result["smbios_type"] = smbios_type
            return result
    return {}

