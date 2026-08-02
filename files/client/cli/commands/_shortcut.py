"""_shortcut.py — a shell verb that IS a REPL shortcut. One implementation, two doors.

WHY THIS EXISTS. `plan`, `routines`, `books` and `procedures` were reachable only by opening
the chat REPL and typing them there. `gorgon <args>` goes to this package instead, so the
whole engine architecture — the thing every measurement on this project is about — could not
be typed at a shell prompt.

THE OBVIOUS FIX IS THE WRONG ONE. Reimplementing each of them here would give two versions of
`plan`'s intent resolution, two consent prompts, two ledger renderings, and they would
disagree the first day one was edited. So a command here DELEGATES: it constructs the phrase
the REPL would have received and hands it to the shortcut that already handles it.

THE SHORTCUT'S OWN `matches` IS THE GRAMMAR, and it is asked rather than re-stated. If the
shortcut would not have matched what was typed, this prints usage instead of running
something the REPL would have refused — so the two doors cannot drift into accepting
different things.

`messages` AND `runtime_drift_count` ARE THE CHAT'S, and none of the four delegated
shortcuts reads either — they take them only to satisfy the base signature. Passing `[]` and
`0` is therefore not a stub standing in for something; it is the honest value. A shortcut
that starts reading the live session cannot be delegated to from a shell and should say so
here rather than quietly receive an empty one.
"""
import importlib

from client.cli.commands.base import Command
from client.cli.commands.context import console


class ShortcutCommand(Command):
    """Base for a shell verb backed by a chat shortcut. Set `shortcut` and `usage`."""

    # (module under orchestrator.ai.chat.shortcuts, class name in it)
    shortcut: tuple = ()
    usage: tuple = ()

    def phrase(self, cmd: str, rest: list) -> str:
        """The input the REPL would have seen. Overridden where the verb differs."""
        return " ".join([cmd, *rest]).strip()

    def run(self, cmd: str, rest: list, verbose: bool) -> None:
        mod_name, cls_name = self.shortcut
        try:
            mod = importlib.import_module(f"orchestrator.ai.chat.shortcuts.{mod_name}")
            shortcut = getattr(mod, cls_name)()
        except ImportError:
            # THE SAME DEGRADATION `mission` ALREADY USES. A client-only checkout has no
            # orchestrator package, and saying so beats an ImportError traceback.
            console.print(f"[bold red]`{cmd}` needs the orchestrator package, which is not "
                          f"installed here.[/bold red]")
            return

        said = self.phrase(cmd, rest)
        if not shortcut.matches(said):
            console.print(f"[dim]{self.__doc__ or ''}[/dim]" if not self.usage else "")
            for line in self.usage:
                console.print(f"  [cyan]{line}[/cyan]")
            return
        shortcut.run(said, [], 0, verbose)
