#!/usr/bin/env python3
"""
test_editor.py — the chat input is an editor, and the layout math is testable without a TTY.

WHAT IT REPLACED, and why this is not a nicety. The input was a bare `str` with two
operations: append a printable character, drop the last one. No cursor, no arrow keys, no
recall, and the renderer clipped the line at the window edge — so a request longer than the
terminal was typed BLIND. The operator hit exactly that while prompt-testing on 2026-08-03:
the echo read `…and os $os_na` and there was no way to see what had been cut.

THE WRAPPING IS THE PART MOST LIKELY TO BE WRONG, which is why `Buffer` holds no curses and
computes its own rows. A cursor sitting at the very end of a line that filled its last row
exactly belongs at the START of the next row — where the next character will actually appear
— and getting that wrong puts the caret one row above the text it is about to type.

Run:  PYTHONPATH=. python3 -m tests.test_editor
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.ui.chat_client.editor import Buffer, History

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_editing():
    print("[buffer] the edits a one-key input could not do")
    b = Buffer("hello world")
    check("text round-trips", b.text == "hello world")
    b.home()
    b.right(); b.right()
    b.insert("XY")
    check("insert lands at the cursor, not the end", b.text == "heXYllo world")
    b.backspace()
    check("backspace removes at the cursor", b.text == "heXllo world")
    b.end(); b.kill_word()
    check("^W drops the word behind the cursor", b.text == "heXllo ")
    b.kill_line()
    check("^U drops what is before the cursor", b.text == "")


def test_lines():
    print("\n[buffer] a request may be more than one line")
    b = Buffer("one")
    b.newline(); b.insert("two")
    check("newline splits at the cursor", b.text == "one\ntwo")
    b.home()
    check("backspace at column 0 JOINS the line above", b.backspace() and b.text == "onetwo")

    b = Buffer("ab\ncd")
    b.to_start(); b.end()
    check("delete at end of line pulls the next one up",
          b.delete() and b.text == "abcd")


def test_motions_report_the_edge():
    """THE SEAM THE COMPOSER READS. `up()` returning False is what means 'recall'."""
    print("\n[buffer] a motion reports whether it could move")
    b = Buffer("only one line")
    b.to_start()
    check("up at the top reports False", b.up() is False)
    check("left at the start reports False", b.left() is False)
    b.to_end()
    check("down at the bottom reports False", b.down() is False)
    check("right at the end reports False", b.right() is False)
    b2 = Buffer("a\nb")
    b2.to_start()
    check("but down WITH somewhere to go reports True", b2.down() is True)


def test_wrapping():
    print("\n[buffer] wrapping, and where the caret lands")
    rows, r, c = Buffer("hello world").wrapped(5)
    check("a long line becomes several rows", rows == ["hello", " worl", "d"])
    check("the caret follows the text", (r, c) == (2, 1))

    # THE EDGE THIS FUNCTION EXISTS FOR.
    b = Buffer("abcde")            # exactly one row wide at width 5, caret at the end
    rows, r, c = b.wrapped(5)
    check("a line that fills its row exactly opens the next one", rows == ["abcde", ""])
    check("and the caret is at the START of it", (r, c) == (1, 0))

    check("an empty buffer still occupies one row", Buffer("").wrapped(8)[0] == [""])
    check("height agrees with the rows it produced", Buffer("hello world").height(5) == 3)
    # Width 0 is clamped to 1, so "ab" is two rows — and the caret, sitting at the end of a
    # full row, opens a third. Same rule as above, at the narrowest width there is.
    check("a width of zero does not divide by zero",
          Buffer("ab").wrapped(0)[0] == ["a", "b", ""])

    rows, r, c = Buffer("ab\ncd").wrapped(10)
    check("an explicit newline is its own row", rows == ["ab", "cd"] and (r, c) == (1, 2))


def test_history():
    print("\n[history] recall must not eat what you were writing")
    h = History(limit=3)
    for m in ("first", "second"):
        h.remember(m)
    check("back gives the newest first", h.back("draft") == "second")
    check("then the one before", h.back("draft") == "first")
    check("and stops at the oldest", h.back("draft") is None)
    check("forward walks toward the present", h.forward() == "second")
    check("THE DRAFT COMES BACK past the newest", h.forward() == "draft")
    check("and then there is nothing newer", h.forward() is None)

    h2 = History(limit=3)
    h2.remember("same"); h2.remember("same")
    check("a repeat does not earn a second entry", h2.items == ["same"])
    for m in ("a", "b", "c", "d"):
        h2.remember(m)
    check("the limit is honoured", len(h2.items) == 3 and h2.items == ["b", "c", "d"])
    check("an empty history recalls nothing", History().back("x") is None)


def test_bindings():
    print("\n[keys] bindings come from config, not from literals")
    from client.ui.chat_client.editor import keys
    import curses
    check("every action in the config resolved to at least one key",
          all(v for v in keys.BINDINGS.values()))
    check("a curses name became its terminal's code",
          curses.KEY_LEFT in keys.BINDINGS["left"])
    check("a control character stayed itself", "\x17" in keys.BINDINGS["kill_word"])
    check("an unbound key is None", keys.action_for("z") is None)
    check("a printable is not a command", keys.printable("z") and not keys.printable("\x01"))
    check("a tab is not printable — it would misalign every computed column",
          not keys.printable("\t"))

    b = Buffer("abc")
    check("apply performs the motion and names it",
          keys.apply(b, curses.KEY_LEFT) == "left" and b.col == 2)
    check("apply on an unbound key does nothing", keys.apply(b, "q") is None and b.col == 2)


class _Screen:
    """The smallest thing `draw` can paint on. Records what landed where."""

    def __init__(self, h=20, w=40):
        self.h, self.w, self.painted, self.cursor = h, w, [], None

    def getmaxyx(self):
        return self.h, self.w

    def erase(self):
        self.painted = []

    def addstr(self, y, x, text, attr=0):
        if y >= self.h or x >= self.w:
            import curses
            raise curses.error("off screen")
        self.painted.append((y, x, text))

    def move(self, y, x):
        self.cursor = (y, x)

    def refresh(self):
        pass


def test_layout():
    """THE STRIP GROWS, AND THE SCROLLBACK PAYS FOR IT — asserted, not eyeballed."""
    print("\n[render] the input strip is laid out from the buffer's height")
    from client.ui.chat_client import render, state

    check("one line needs one row", render.input_rows(Buffer("hi"), 40) == 1)
    check("a wrapped line needs more", render.input_rows(Buffer("x" * 100), 40) == 3)
    check("and it is capped", render.input_rows(Buffer("x" * 10000), 40) <= 8)
    check("an empty buffer still needs one", render.input_rows(Buffer(""), 40) == 1)

    # `_cp` ASKS CURSES FOR A COLOUR PAIR, which raises outside `initscr()` — and it is
    # evaluated as an ARGUMENT to addstr, so the raise happens inside the same try/except
    # that guards drawing past the screen edge and nothing is painted at all. Stubbed here
    # rather than worked around, because the thing under test is the LAYOUT.
    was_cp, was_waiting, was_pw = render._cp, state.waiting, state.is_password
    render._cp = lambda *_a, **_k: 0
    try:
        state.waiting = state.is_password = False
        s = _Screen(h=20, w=40)
        render.draw(s, Buffer("hello"))
        rows = {y for y, _x, _t in s.painted}
        check("nothing is painted below the hint line", max(rows) <= 18)
        check("the caret is placed after the gutter", s.cursor == (17, 3 + 5))

        # A TALL BUFFER MUST NOT PUSH ANYTHING OFF THE BOTTOM.
        s2 = _Screen(h=20, w=40)
        render.draw(s2, Buffer("y" * 300))
        check("a tall input still leaves the hint line alone",
              max(y for y, _x, _t in s2.painted) <= 18)
        check("and the caret stays inside the strip",
              s2.cursor is not None and s2.cursor[0] <= 18)

        # A STRING STILL DRAWS — the waiting branch and `_process_response` pass one.
        s3 = _Screen()
        render.draw(s3, "")
        check("a plain string is still accepted", s3.painted)

        state.is_password = True
        s4 = _Screen()
        render.draw(s4, Buffer("secret"))
        check("a password is masked in the strip",
              not any("secret" in t for _y, _x, t in s4.painted))
    finally:
        render._cp, state.waiting, state.is_password = was_cp, was_waiting, was_pw


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "editor"))


if __name__ == "__main__":
    main()
