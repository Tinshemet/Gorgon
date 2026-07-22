"""net.py — cached network probes + the custom/net-enabled mode state.

_CUSTOM_MODE / _NET_ENABLED are process state set via set_custom_mode(); read them
through custom_mode()/net_enabled() so a change is seen live across modules.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from .config import _NET_TIMEOUT

_NET_CACHE:  Dict[str, Any] = {}
_NET_ENABLED = True
_CUSTOM_MODE = False   # set True via set_custom_mode() to skip product verification


def custom_mode() -> bool:
    """True when custom mode is on (product verification skipped)."""
    return _CUSTOM_MODE


def net_enabled() -> bool:
    """True when network probes are enabled."""
    return _NET_ENABLED


def set_custom_mode(enabled: bool) -> None:
    """Toggle custom mode, which disables DuckDuckGo product verification."""
    global _CUSTOM_MODE
    _CUSTOM_MODE = enabled


# Fetches JSON from a URL with an MD5 session cache and timeout; returns None on failure.
# In: str url, dict? headers → Out: dict | None
def _net_get(url: str, headers: Dict = None) -> Optional[Dict]:
    """Fetch JSON from a URL with session caching and timeout.

    Args:
        url:     URL to fetch; must return JSON.
        headers: Optional extra headers (User-Agent added automatically).

    Returns:
        Parsed JSON dict, or ``None`` if the request failed or networking
        is disabled.

    Example::

        _net_get("https://api.example.com/data")
        # → {"key": "value"} on success, None on failure
    """
    if not _NET_ENABLED:
        return None
    cache_key = hashlib.md5(url.encode()).hexdigest()
    if cache_key in _NET_CACHE:
        return _NET_CACHE[cache_key]
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": _CFG["user_agent"]})
        with urllib.request.urlopen(req, timeout=_NET_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            _NET_CACHE[cache_key] = data
            return data
    except Exception:
        _NET_CACHE[cache_key] = None
        return None


# Checks if a URL exists via HEAD request; returns False on failure.
# In: str url → Out: bool
def _net_head(url: str) -> bool:
    """Check if a URL exists via HEAD request.

    Args:
        url: URL to probe with HTTP HEAD.

    Returns:
        ``True`` if the server returned a 2xx response; ``False`` on any
        error or when networking is disabled.

    Example::

        _net_head("https://example.com/file.iso")
        # → True if the file exists, False if 404 or unreachable
    """
    if not _NET_ENABLED:
        return False
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": _CFG["user_agent"]})
        with urllib.request.urlopen(req, timeout=_NET_TIMEOUT):
            return True
    except Exception:
        return False


# Queries the local QEMU binary for all supported machine types (result is cached).
# In: str binary → Out: set
