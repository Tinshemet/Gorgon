"""chat_client/autostart.py — launch the orchestrator locally when it's not already up."""

import os
import sys
import time

from client import config as _cfg
from client.ui.chat_client.conn import SERVER_URL
from client.ui.chat_client.net import server_reachable as _server_reachable
from client.ui.chat_client.render import draw as _draw


def autostart_server(stdscr: "curses.window") -> bool:
    """Launch the orchestrator if its files are present alongside the client. Returns True when ready."""
    _files_dir = _cfg.FILES_DIR
    _orch_mod  = os.path.join(_files_dir, "orchestrator", "http", "api_server.py")

    if not os.path.exists(_orch_mod):
        return False

    from urllib.parse import urlparse
    port = urlparse(SERVER_URL).port or _cfg.DEFAULT_PORT

    env = os.environ.copy()
    env["PYTHONPATH"] = _files_dir
    try:
        token = open(os.path.expanduser(_cfg.TOKEN_FILE)).read().strip()
        env["API_TOKEN"] = token
    except Exception:
        pass  # no token file — run without an API token (orchestrator may allow it)

    _log_path = _cfg.LOG_PATH
    import subprocess as _sp
    _sp.Popen(
        [sys.executable, "-m", "uvicorn",
         _cfg.UVICORN_APP,
         "--host", _cfg.SPAWN_HOST, f"--port", str(port),
         "--log-level", _cfg.SPAWN_LOG_LEVEL],
        cwd=_files_dir, env=env,
        start_new_session=True,
        stdout=open(_log_path, "w"),
        stderr=_sp.STDOUT,
    )

    for _ in range(_cfg.AUTOSTART_POLL_COUNT):
        time.sleep(_cfg.AUTOSTART_POLL_INTERVAL_S)
        _draw(stdscr, "")
        if _server_reachable():
            return True

    return False
