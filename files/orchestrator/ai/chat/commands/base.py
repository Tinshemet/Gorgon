"""
base.py — Command base class + auto-registration for the direct-CLI package.

One Command subclass per file; declaring a subclass with a non-empty ``names``
registers it (via ``__init_subclass__``) into ``ALL_COMMANDS``, which the package
``__init__`` folds into the verb → instance registry. Adding a command is a matter
of dropping a file — nothing else is touched. Mirrors client/cli/commands/base.py.
"""

from typing import List

# Every concrete Command subclass appends itself here at class-definition time.
ALL_COMMANDS: list = []


class Command:
    """A single ``gorgon <verb>`` sub-command.

    Subclasses set ``names`` (the verb(s) they answer to) and ``min_args`` (the
    minimum number of args after the verb; fewer falls through to help — this
    preserves the legacy ``cmd == "x" and rest`` arity guards) and implement
    ``run``.
    """

    names: tuple = ()      # empty = abstract, not registered
    min_args: int = 0      # minimum len(rest) required to dispatch

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.names:
            ALL_COMMANDS.append(cls)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        """Execute the command. ``cmd`` is the matched verb (multi-name commands
        branch on it), ``rest`` the args after it, ``verbose`` echoes raw JSON."""
        raise NotImplementedError
