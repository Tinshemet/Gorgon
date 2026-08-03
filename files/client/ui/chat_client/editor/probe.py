"""
probe.py — what does THIS terminal actually send? Run it and press keys.

WHY IT EXISTS. "the arrow keys did not work" is three different faults wearing one sentence:
the key never reached the client, it reached it as something unrecognised, or it was
recognised and the caret moved invisibly. Guessing between them costs a round trip each
time; this answers it in ten seconds, on the operator's own terminal, with no server and no
network.

    PYTHONPATH=. python3 -m client.ui.chat_client.editor.probe

Press keys. Each line shows what `get_wch()` returned, and which action — if any — the
bindings resolve it to. `q` quits.
"""
import curses

from client.ui.chat_client.editor import keys as _keys


def _run(stdscr) -> None:
    stdscr.keypad(True)
    curses.curs_set(1)
    rows = ["press keys — arrows, ^A, ^E, ^W, ^O.   'q' quits", ""]

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        for i, line in enumerate(rows[-(h - 1):]):
            try:
                stdscr.addstr(i, 0, line[:w - 1])
            except curses.error:
                pass  # past the edge — skip the row
        stdscr.refresh()

        try:
            ch = stdscr.get_wch()
        except curses.error:
            continue
        if ch == "q":
            return

        kind = "int" if isinstance(ch, int) else "str"
        shown = repr(ch)
        named = ""
        if isinstance(ch, int):
            named = next((n for n in dir(curses)
                          if n.startswith("KEY_") and getattr(curses, n) == ch), "")
        action = _keys.action_for(ch) or "—"
        rows.append(f"{kind:<4} {shown:<10} {named:<14} -> {action}")

        # THE FALLBACK PATH, SHOWN TOO: if ESC arrives alone the terminal is sending raw
        # sequences, and what follows is the half that says which arrow it was.
        if ch == "\x1b":
            stdscr.nodelay(True)
            tail = ""
            try:
                for _ in range(2):
                    nxt = stdscr.get_wch()
                    if not isinstance(nxt, str):
                        break
                    tail += nxt
            except curses.error:
                pass  # a bare Escape
            finally:
                stdscr.nodelay(False)
            rows.append(f"     ESC tail {tail!r:<10} -> {_keys.escaped(tail) or '—'}"
                        f"   (raw sequence — keypad is NOT assembling these)")


def main() -> None:
    curses.wrapper(_run)


if __name__ == "__main__":
    main()
