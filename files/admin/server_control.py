"""
admin/server_control.py — Local orchestrator process control (admin-TUI knobs).

Only useful when the admin TUI runs ON the orchestrator machine. The actual
process handling (find / launch / poll) is the shared definition in
``shared.server_control``; this module just binds it to the admin config's
timing/host/port knobs so the TUI keeps its own tunables.
"""

from admin import config
from shared import server_control as _sc


def local_pid() -> "int | None":
    """Return the PID of a locally running server process, or None."""
    return _sc.local_pid(config.PGREP_PATTERN)


def spawn_server() -> "int | None":
    """Spawn the orchestrator server detached and poll until it's up (the start-server
    body, shared with the restart verb). Returns the new PID, or None."""
    return _sc.spawn_orchestrator(
        files_dir=config.FILES_DIR,
        host=config.SPAWN_HOST,
        port=config.DEFAULT_PORT,
        app=config.UVICORN_APP,
        log_level=config.SPAWN_LOG_LEVEL,
        log_path=config.LOG_PATH,
        pgrep_pattern=config.PGREP_PATTERN,
        wait=config.STARTUP_WAIT_TICKS * config.STARTUP_WAIT_INTERVAL_S,
        poll_interval=config.STARTUP_WAIT_INTERVAL_S,
    )
