"""
editor — an editable text buffer for the curses chat, and the keys that drive it.

TWO CONSUMERS, ONE BUFFER, and that is the reason this is a package rather than a couple of
functions in `app.py`. The COMPOSER is this buffer one row tall in the input strip, where
Enter sends. The PROGRAM EDITOR is the same buffer filling the screen over a `.medusa` file,
where Enter breaks the line and ^S saves. Writing the cursor arithmetic twice would give two
sets of off-by-ones, and the second set would be found by an operator mid-edit.

`buffer` HOLDS NO CURSES AND NO POLICY, so it is testable without a terminal — including the
wrapping, which is the part most likely to be wrong. `keys` is the only module that imports
curses, and it decides nothing about what Enter means.
"""
from client.ui.chat_client.editor.buffer import Buffer
from client.ui.chat_client.editor.history import History

__all__ = ["Buffer", "History"]
