"""chat_client/vnc.py — pick a host + launch a VNC viewer for a launched VM."""

from typing import Optional

from client import config as _cfg
from client.ui.chat_client.conn import SERVER_URL


def vnc_host() -> str:
    """Return the host to point a VNC viewer at (derived from the server URL)."""
    from urllib.parse import urlparse
    parsed = urlparse(SERVER_URL)
    host   = parsed.hostname or "localhost"
    return "localhost" if host in ("localhost", "127.0.0.1", "::1") else host


def try_open_vnc(port: int) -> Optional[str]:
    """Try each configured VNC viewer; return the one that launched, or None."""
    import subprocess as _sp
    host = vnc_host()
    for viewer in _cfg.VNC_VIEWERS:
        try:
            _sp.Popen([viewer, f"{host}:{port}"],
                      stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            return viewer
        except FileNotFoundError:
            continue
    return None
