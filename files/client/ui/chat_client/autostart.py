"""chat_client/autostart.py — launch the orchestrator locally when it's not already up."""

import os
import time
from urllib.parse import urlparse

from client import config as _cfg
from client.ui.chat_client.conn import SERVER_URL
from client.ui.chat_client.net import server_reachable as _server_reachable
from client.ui.chat_client.render import draw as _draw
from shared import server_control as _sc


def autostart_server(stdscr: "curses.window") -> bool:
    """Launch the orchestrator if its files are present alongside the client. Returns True when ready.

    Uses the shared launch() for the actual spawn, but keeps its own readiness poll:
    unlike the admin/agent-load path (which polls `pgrep` for a PID), the chat client
    waits on HTTP reachability and redraws the curses UI each tick so it stays live.
    """
    _files_dir = _cfg.FILES_DIR
    _orch_mod  = os.path.join(_files_dir, "orchestrator", "http", "api_server.py")

    if not os.path.exists(_orch_mod):
        return False

    port = urlparse(SERVER_URL).port or _cfg.DEFAULT_PORT

    _sc.launch(
        files_dir=_files_dir,
        host=_cfg.SPAWN_HOST,
        port=port,
        app=_cfg.UVICORN_APP,
        log_level=_cfg.SPAWN_LOG_LEVEL,
        log_path=_cfg.LOG_PATH,
        token_file=_cfg.TOKEN_FILE,
    )

    for _ in range(_cfg.AUTOSTART_POLL_COUNT):
        time.sleep(_cfg.AUTOSTART_POLL_INTERVAL_S)
        _draw(stdscr, "")
        if _server_reachable():
            return True

    return False
