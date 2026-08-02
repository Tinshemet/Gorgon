"""commands/routines.py — gorgon routines [run]."""

from client.cli.commands._shortcut import ShortcutCommand


class RoutinesCommand(ShortcutCommand):
    """What runs without being asked — and what is due right now."""

    names = ("routines",)
    shortcut = ("routines", "Routines")
    usage = ("gorgon routines       what is declared, and what is due",
             "gorgon routines run   run everything due, through the ordinary path")
