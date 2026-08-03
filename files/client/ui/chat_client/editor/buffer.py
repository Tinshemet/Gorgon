"""
buffer.py — an editable block of text with a cursor. No curses, no I/O, no policy.

WHY THIS IS ITS OWN CLASS. The chat input was a bare Python string with two operations on
it — append a printable character, drop the last one (`app.py`, before this). That is not a
small editor; it is no editor, and it shows the moment a request is longer than a phrase:
a typo in the third word costs the whole line. The same absence is why a `.medusa` file
could be read from the chat and never changed.

BOTH CONSUMERS WANT THE SAME OBJECT, and only the same object will do. The composer is this
buffer one row tall in the input strip; the program editor is this buffer filling the screen
over a file. Writing the cursor arithmetic twice would give two sets of off-by-ones to find,
and the second one would be found by an operator mid-edit.

IT HOLDS NO POLICY, DELIBERATELY. What Enter means is the consumer's business — the composer
sends, the editor breaks the line — and a buffer that decided would have to be told which
caller it was serving. So the motions REPORT rather than act: `up()` returns False when there
is nowhere above, and the composer reads that False as "recall the previous message" while
the editor reads it as "already at the top". One seam, two readings, no flag.

AND IT WRAPS ITS OWN TEXT. `wrapped()` returns the screen rows and where the cursor landed
among them, because the alternative is curses code doing arithmetic that cannot be tested
without a terminal. Wrapping is the part most likely to be wrong (a cursor at the exact end
of a full row belongs at the start of the next one) and it is now a pure function of a
string and a width.
"""
from typing import List, Tuple

_NL = "\n"
# What counts as inside a word, for ^W. Anything else ends one.
_WORD = str.isalnum


class Buffer:
    """Text plus a cursor. Every motion returns whether it could move."""

    def __init__(self, text: str = "") -> None:
        self.set(text)

    # ── the text itself ──────────────────────────────────────────────────────
    def set(self, text: str) -> None:
        """Replace the contents and put the cursor at the end."""
        self.lines: List[str] = (text or "").split(_NL) or [""]
        self.row = len(self.lines) - 1
        self.col = len(self.lines[self.row])

    @property
    def text(self) -> str:
        return _NL.join(self.lines)

    @property
    def empty(self) -> bool:
        return self.text.strip() == ""

    def clear(self) -> None:
        self.set("")

    # ── editing ──────────────────────────────────────────────────────────────
    def insert(self, s: str) -> None:
        """Insert a printable string at the cursor. Newlines inside it split lines."""
        for i, part in enumerate(s.split(_NL)):
            if i:
                self.newline()
            line = self.lines[self.row]
            self.lines[self.row] = line[:self.col] + part + line[self.col:]
            self.col += len(part)

    def newline(self) -> None:
        """Break the line at the cursor."""
        line = self.lines[self.row]
        self.lines[self.row:self.row + 1] = [line[:self.col], line[self.col:]]
        self.row += 1
        self.col = 0

    def backspace(self) -> bool:
        """Delete behind the cursor, joining onto the line above at column 0."""
        if self.col:
            line = self.lines[self.row]
            self.lines[self.row] = line[:self.col - 1] + line[self.col:]
            self.col -= 1
            return True
        if not self.row:
            return False
        above = self.lines[self.row - 1]
        self.col = len(above)
        self.lines[self.row - 1] = above + self.lines.pop(self.row)
        self.row -= 1
        return True

    def delete(self) -> bool:
        """Delete under the cursor, pulling the next line up at end of line."""
        line = self.lines[self.row]
        if self.col < len(line):
            self.lines[self.row] = line[:self.col] + line[self.col + 1:]
            return True
        if self.row >= len(self.lines) - 1:
            return False
        self.lines[self.row] = line + self.lines.pop(self.row + 1)
        return True

    def kill_to_end(self) -> bool:
        """^K — drop the rest of the line, or join the next one if already at the end."""
        line = self.lines[self.row]
        if self.col < len(line):
            self.lines[self.row] = line[:self.col]
            return True
        return self.delete()

    def kill_line(self) -> bool:
        """^U — drop what is before the cursor on this line."""
        if not self.col:
            return False
        self.lines[self.row] = self.lines[self.row][self.col:]
        self.col = 0
        return True

    def kill_word(self) -> bool:
        """^W — drop the word behind the cursor, trailing whitespace and all."""
        if not self.col:
            return self.backspace()
        line = self.lines[self.row]
        at = self.col
        while at and not _WORD(line[at - 1]):
            at -= 1
        while at and _WORD(line[at - 1]):
            at -= 1
        self.lines[self.row] = line[:at] + line[self.col:]
        self.col = at
        return True

    # ── motion — each returns False when there was nowhere to go ─────────────
    def left(self) -> bool:
        if self.col:
            self.col -= 1
            return True
        if not self.row:
            return False
        self.row -= 1
        self.col = len(self.lines[self.row])
        return True

    def right(self) -> bool:
        if self.col < len(self.lines[self.row]):
            self.col += 1
            return True
        if self.row >= len(self.lines) - 1:
            return False
        self.row += 1
        self.col = 0
        return True

    def up(self) -> bool:
        if not self.row:
            return False
        self.row -= 1
        self.col = min(self.col, len(self.lines[self.row]))
        return True

    def down(self) -> bool:
        if self.row >= len(self.lines) - 1:
            return False
        self.row += 1
        self.col = min(self.col, len(self.lines[self.row]))
        return True

    def home(self) -> bool:
        moved = self.col != 0
        self.col = 0
        return moved

    def end(self) -> bool:
        was = self.col
        self.col = len(self.lines[self.row])
        return self.col != was

    def to_start(self) -> None:
        self.row = self.col = 0

    def to_end(self) -> None:
        self.row = len(self.lines) - 1
        self.col = len(self.lines[self.row])

    # ── laying it out ────────────────────────────────────────────────────────
    def wrapped(self, width: int) -> Tuple[List[str], int, int]:
        """Soft-wrap to *width*. Returns (rows, cursor_row, cursor_col).

        A LOGICAL LINE THAT IS AN EXACT MULTIPLE OF THE WIDTH STILL OWNS A ROW, and the
        cursor sitting at its very end belongs at the START of the row after it — where the
        next character will actually appear. Getting that wrong puts the caret one row above
        the text it is about to type, which is the bug this function exists to have tested.
        """
        width = max(1, width)
        rows: List[str] = []
        cur_row = cur_col = 0
        for r, line in enumerate(self.lines):
            first = len(rows)
            chunks = [line[i:i + width] for i in range(0, len(line), width)] or [""]
            rows.extend(chunks)
            if r == self.row:
                cur_row = first + self.col // width
                cur_col = self.col % width
                if cur_row >= len(rows):
                    # The cursor is past the last chunk — the line filled its final row
                    # exactly, so the caret opens a new one.
                    rows.append("")
        return rows, cur_row, cur_col

    def height(self, width: int) -> int:
        """How many screen rows this buffer needs at *width*."""
        return len(self.wrapped(width)[0])
