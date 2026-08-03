"""
keys.py — which key does what, read from config, applied to a Buffer.

THE ONLY MODULE HERE THAT KNOWS ABOUT CURSES, and it knows one thing: `get_wch` hands back
an int for a special key and a str for everything else. That is the whole reason the map is
resolved at import rather than written as literals — `KEY_LEFT` is a number that depends on
the terminfo entry, so a hard-coded one is right on the author's terminal and wrong on
somebody else's.

WHAT IT DOES NOT DECIDE IS WHAT ENTER MEANS. The composer sends on Enter and the file editor
breaks the line, and both are correct — so Enter is not in the table and each consumer
answers for itself. A key map that decided would need to be told which caller it was serving,
which is a flag standing in for the fact that it is not one map.

A BINDING CURSES DOES NOT DEFINE IS DROPPED, NOT RAISED. `KEY_DC` is absent on some terminfo
entries, and a client that refuses to start because one key is missing has traded a small
loss of function for a total one.
"""
from typing import Any, Dict, Optional, Set

import curses

from client import config as _cfg
from client.ui.chat_client.editor.buffer import Buffer


def _resolve(names) -> Set[Any]:
    """`["KEY_LEFT", "\\x02"]` -> `{260, "\\x02"}`, skipping what this terminal lacks."""
    out: Set[Any] = set()
    for name in names or ():
        if isinstance(name, str) and name.startswith("KEY_"):
            code = getattr(curses, name, None)
            if code is not None:
                out.add(code)
        elif name:
            out.add(name)
    return out


# action -> the set of keys that perform it. Built once; the config is not re-read per keypress.
BINDINGS: Dict[str, Set[Any]] = {
    action: _resolve(names) for action, names in (_cfg.EDITOR_KEYS or {}).items()
}


# WHAT AN ARROW KEY LOOKS LIKE WHEN NCURSES DID NOT ASSEMBLE IT. With `keypad(True)` a
# cursor key arrives as ONE integer (`KEY_LEFT`); without it, or when the escape sequence
# arrives split across reads, the terminal's raw bytes come through instead — ESC, then `[`
# or `O`, then a letter. `curses.wrapper` does set keypad, so this is a fallback and not the
# main path; it costs three dict lookups and removes a failure mode where the arrows appear
# to do nothing while quietly typing `[D` into the operator's request.
_ESCAPED = {"A": "up", "B": "down", "C": "right", "D": "left",
            "H": "home", "F": "end"}


def escaped(tail: str) -> Optional[str]:
    """`"[D"` / `"OD"` -> `"left"`. The action a raw cursor-key sequence stands for."""
    tail = (tail or "").lstrip("[O")
    return _ESCAPED.get(tail[:1].upper()) if tail else None


def action_for(ch: Any) -> Optional[str]:
    """The action this key performs, or None if it is not bound."""
    for action, keys in BINDINGS.items():
        if ch in keys:
            return action
    return None


# The motions, by name. Each returns False when there was nowhere to go — which is what lets
# the composer read a failed `up` as "recall the previous message" without this module having
# an opinion about history.
_ON_BUFFER = {
    "left": Buffer.left, "right": Buffer.right, "up": Buffer.up, "down": Buffer.down,
    "home": Buffer.home, "end": Buffer.end, "delete": Buffer.delete,
    "backspace": Buffer.backspace, "kill_to_end": Buffer.kill_to_end,
    "kill_line": Buffer.kill_line, "kill_word": Buffer.kill_word,
}


def apply(buf: Buffer, ch: Any) -> Optional[str]:
    """Perform whatever *ch* is bound to. Returns the action name, or None if unbound.

    `"newline"` and an unbound key come back for the CALLER to decide — the first because
    what a line break means depends on whether this is a message or a file, the second
    because a printable character is the caller's to insert and a control key it does not
    recognise is the caller's to ignore.

    THE RETURN IS THE ACTION, NOT WHETHER IT MOVED, and the difference matters at the edges:
    `up` at the top of the buffer did nothing and still WAS an `up`. The composer needs to
    know both — that the key was `up`, and that the buffer could not honour it — so the
    motion's own False is read off the buffer by the caller when it cares.
    """
    action = action_for(ch)
    if action is None:
        return None
    fn = _ON_BUFFER.get(action)
    if fn is not None:
        fn(buf)
    return action


def moved(buf: Buffer, ch: Any) -> bool:
    """Perform a motion and report whether the buffer could actually move."""
    action = action_for(ch)
    fn = _ON_BUFFER.get(action) if action else None
    return bool(fn(buf)) if fn else False


def printable(ch: Any) -> bool:
    """Is this a character to insert rather than a command?

    TABS AND NEWLINES ARE NOT PRINTABLE by `str.isprintable`, which is correct here: a tab
    pasted into a one-line input would misalign every column the renderer computes, and a
    newline arrives as Enter and belongs to the caller.
    """
    return isinstance(ch, str) and len(ch) == 1 and ch.isprintable()
