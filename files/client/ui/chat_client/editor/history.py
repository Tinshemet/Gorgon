"""
history.py — what the operator typed before, and walking back through it.

WHY IT IS NOT JUST A LIST. Recall has one rule that a list does not express: what you were
part-way through typing must survive being walked away from. Press Up, read an old request,
press Down, and the half-written line is back — otherwise recall is a trap, and the operator
learns not to use it.

THE DRAFT IS STASHED ON THE FIRST STEP BACK and restored when the walk returns to the
present. That is the whole of it, and it is the piece a naive index-into-a-list gets wrong.
"""
from typing import List, Optional

from client import config as _cfg


class History:
    """Sent messages, newest last, with a cursor that walks back through them."""

    def __init__(self, limit: int = None) -> None:
        self.limit = int(limit if limit is not None else _cfg.INPUT_HISTORY)
        self.items: List[str] = []
        self.at: Optional[int] = None    # None = at the present, not walking
        self.draft: str = ""

    def remember(self, text: str) -> None:
        """Keep a sent message and return to the present.

        A REPEAT DOES NOT EARN A SECOND ENTRY. Sending the same request twice while testing a
        phrasing is ordinary, and it should not cost two presses of Up to get past it.
        """
        text = (text or "").strip()
        if text and (not self.items or self.items[-1] != text):
            self.items.append(text)
            del self.items[:-self.limit]
        self.reset()

    def reset(self) -> None:
        self.at = None
        self.draft = ""

    def back(self, current: str) -> Optional[str]:
        """One step older, or None when there is nothing older. Stashes *current* first."""
        if not self.items:
            return None
        if self.at is None:
            self.draft = current
            self.at = len(self.items) - 1
        elif self.at > 0:
            self.at -= 1
        else:
            return None
        return self.items[self.at]

    def forward(self) -> Optional[str]:
        """One step newer. Past the newest, the stashed draft comes back."""
        if self.at is None:
            return None
        if self.at < len(self.items) - 1:
            self.at += 1
            return self.items[self.at]
        # PAST THE NEWEST IS THE PRESENT, not the newest again.
        self.at = None
        was, self.draft = self.draft, ""
        return was
