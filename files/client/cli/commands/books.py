"""commands/books.py — gorgon books."""

from client.cli.commands._shortcut import ShortcutCommand


class BooksCommand(ShortcutCommand):
    """The creation ledger: what the system believes it made, and what the lab says."""

    names = ("books",)
    shortcut = ("books", "Books")
    usage = ("gorgon books   the creation ledger",)
