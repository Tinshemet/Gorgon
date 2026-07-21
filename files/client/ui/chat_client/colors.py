"""
chat_client/colors.py — curses colour pairs for the chat TUI.

The palette, custom-colour slot, and hex fallback come from client/config. The
C_* ids are symbolic colour-pair slots (structural, not tunables).
"""

import curses

from client import config as _cfg

C_HEADER = 1
C_CYAN   = 2
C_GREEN  = 3
C_RED    = 4
C_DIM    = 5
C_YELLOW = 6
C_BOLD   = 7

_CUSTOM_COLOR_SLOT = _cfg.CUSTOM_COLOR_SLOT   # first free slot above the standard 8+8


def _hex_to_curses(hex_color: str) -> tuple:
    """Parse a ``#RRGGBB`` hex string to (r, g, b) scaled 0-1000 for curses.

    Returns ``COLOR_FALLBACK_RGB`` on bad input.

    Example::

        _hex_to_curses("#7355a3")  # → (451, 333, 639)
        _hex_to_curses("bad")      # → config fallback
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return _cfg.COLOR_FALLBACK_RGB   # fallback ~gray
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)


def init_colours(color_hex: str = None) -> None:
    """Initialise curses colour pairs from the configured palette + accent hex."""
    def _cc(name):
        return getattr(curses, f"COLOR_{name}")
    color_hex = color_hex or _cfg.TEXT_COLOR
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_HEADER, _cc(_cfg.COLOR_HEADER_FG), _cc(_cfg.COLOR_HEADER_BG))
    curses.init_pair(C_CYAN,   _cc(_cfg.COLOR_CYAN),   -1)
    curses.init_pair(C_GREEN,  _cc(_cfg.COLOR_GREEN),  -1)
    curses.init_pair(C_RED,    _cc(_cfg.COLOR_RED),    -1)
    curses.init_pair(C_YELLOW, _cc(_cfg.COLOR_YELLOW), -1)
    curses.init_pair(C_BOLD,   _cc(_cfg.COLOR_BOLD),   -1)

    if curses.can_change_color():
        r, g, b = _hex_to_curses(color_hex)
        curses.init_color(_CUSTOM_COLOR_SLOT, r, g, b)
        curses.init_pair(C_DIM, _CUSTOM_COLOR_SLOT, -1)
    else:
        # Terminal can't redefine colors — fall back to nearest standard
        curses.init_pair(C_DIM, _cfg.DIM_FALLBACK_SLOT, -1)  # bright-black (gray)


def cp(n: int) -> int:
    """Return the curses attribute for colour-pair number ``n``."""
    return curses.color_pair(n)
