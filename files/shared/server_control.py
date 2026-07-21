"""server_control.py — the one definition of how the LOCAL orchestrator process
is managed: find it (``pgrep``), stop it (SIGTERM → SIGKILL), and launch it
(detached ``uvicorn``).

Every role that starts a local server used to reinvent the same Popen line —
`gorgon agent load` (client), the admin TUI, and the chat-client autostart. They
now all call in here:

  launch(...)             build the env + token + log and Popen uvicorn (no wait)
  spawn_orchestrator(...) launch + poll ``pgrep`` until it's up, return the PID
  stop_server(...) / restart_server(...)

Defaults (host / app / log-level / port / pgrep pattern / timeouts) come from
shared/config; any caller may override per call. The `GORGON_PORT` /
`GORGON_SERVER_LOG` env overrides still win — shared/config applies them.

Restarting is a HIGH-IMPACT action — only `gorgon agent load` uses it, and only
after operator re-authentication. The respawned server re-imports contract.py
fresh, so it picks up whatever agent_select points at: that's how load swaps the
active agent.
"""
import os
import signal
import subprocess
import sys
import time
from typing import Callable, Optional

from shared import config


def local_pid(pgrep_pattern: str = config.PGREP_PATTERN) -> Optional[int]:
    """PID of a locally running orchestrator server, or None."""
    try:
        out = subprocess.check_output(["pgrep", "-f", pgrep_pattern], text=True).strip()
        pids = [int(p) for p in out.splitlines() if p.strip()]
        return pids[0] if pids else None
    except Exception:
        return None


def launch(*,
           files_dir: Optional[str] = None,
           host: str = config.SERVER_HOST,
           port: int = config.SERVER_PORT,
           app: str = config.UVICORN_APP,
           log_level: str = config.SERVER_LOG_LEVEL,
           log_path: Optional[str] = config.SERVER_LOG_PATH,
           token_file: str = config.TOKEN_FILE) -> None:
    """Spawn a detached ``uvicorn`` for the orchestrator app — the single Popen the
    three roles share. Does NOT wait for readiness; callers poll however they like
    (``pgrep`` for a PID, or an HTTP reachability check). If a token file exists it
    is passed through as ``API_TOKEN``; otherwise the server starts without one
    (localhost only)."""
    files_dir = files_dir or config.FILES_DIR
    env = os.environ.copy()
    env["PYTHONPATH"] = files_dir
    try:
        with open(os.path.expanduser(token_file)) as f:
            env["API_TOKEN"] = f.read().strip()
    except Exception:
        pass  # no token file — start without an API token (localhost only)
    cmd = [sys.executable, "-m", "uvicorn", app,
           "--host", host, "--port", str(port), "--log-level", log_level]
    if log_path:
        with open(log_path, "w") as log_fh:
            subprocess.Popen(cmd, cwd=files_dir, env=env, start_new_session=True,
                             stdout=log_fh, stderr=subprocess.STDOUT)
    else:
        subprocess.Popen(cmd, cwd=files_dir, env=env, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def spawn_orchestrator(*,
                       wait: float = config.STARTUP_WAIT_S,
                       poll_interval: float = config.STARTUP_POLL_INTERVAL_S,
                       pgrep_pattern: str = config.PGREP_PATTERN,
                       on_tick: Optional[Callable[[], None]] = None,
                       **launch_kwargs) -> Optional[int]:
    """launch() the server (unless one is already up) and poll ``pgrep`` until it
    appears. Returns the PID (existing or new), or None if it didn't come up within
    *wait* seconds. *on_tick* runs once per poll — a curses caller can pass its
    redraw so its UI stays live while it waits. Extra kwargs pass through to
    launch() (host/port/app/log_level/log_path/token_file/files_dir)."""
    existing = local_pid(pgrep_pattern)
    if existing:
        return existing
    launch(**launch_kwargs)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        pid = local_pid(pgrep_pattern)
        if pid:
            return pid
        if on_tick:
            on_tick()
        time.sleep(poll_interval)
    return None


def stop_server(timeout: float = config.STOP_TIMEOUT_S,
                poll_interval: float = config.STOP_POLL_INTERVAL_S,
                pgrep_pattern: str = config.PGREP_PATTERN) -> bool:
    """SIGTERM the local server and wait for it to exit (SIGKILL as a last resort).
    Returns True if a server was found and stopped, False if none was running."""
    pid = local_pid(pgrep_pattern)
    if not pid:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if local_pid(pgrep_pattern) is None:
            return True
        time.sleep(poll_interval)
    leftover = local_pid(pgrep_pattern)
    if leftover:
        try:
            os.kill(leftover, signal.SIGKILL)
        except Exception:
            pass
    return True


def restart_server(**kwargs) -> Optional[int]:
    """Stop the running server (if any) and spawn a fresh one. Returns the new PID.
    Used by `gorgon agent load` to make the orchestrator re-read the active agent."""
    stop_server(pgrep_pattern=kwargs.get("pgrep_pattern", config.PGREP_PATTERN))
    return spawn_orchestrator(**kwargs)
