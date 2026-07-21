"""audit.py — append-only trail for high-impact contract/agent actions.

Records who did what to which agent file, and when, to ~/.gorgon.audit.log (0600).
High-impact = the operator-gated actions: forge / sign / edit a contract, and
switch / load / reset the active agent. The trail must never break the action, so
every write is best-effort.
"""
import os
from datetime import datetime
from typing import List, Optional

from shared.config import AUDIT_LOG_FILE

_PATH = AUDIT_LOG_FILE


def path() -> str:
    return _PATH


def record(action: str, target: str = "", operator: Optional[str] = None, detail: str = "") -> None:
    """Append one audit line: <iso-time>  <operator>  <action>  <target>  <detail>."""
    try:
        line = "\t".join([
            datetime.now().isoformat(timespec="seconds"),
            operator or "?",
            action,
            target or "-",
            detail or "",
        ]) + "\n"
        fd = os.open(_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(line)
    except Exception:
        pass  # auditing must never block or break the underlying action


def tail(n: int = 20) -> List[str]:
    """The most recent *n* audit lines (newest last), or [] if none."""
    try:
        with open(_PATH) as f:
            return [ln.rstrip("\n") for ln in f.readlines()[-n:]]
    except (FileNotFoundError, OSError):
        return []
