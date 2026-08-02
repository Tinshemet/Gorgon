"""commands/procedures.py — gorgon procedures [show|verify|run|delete|syntax] <name>."""

from client.cli.commands._shortcut import ShortcutCommand


class ProceduresCommand(ShortcutCommand):
    """The stored Medusa programs: what Gorgon has written, and what each one says."""

    names = ("procedures", "procs")
    shortcut = ("procedures", "Procedures")
    usage = ("gorgon procedures                 what is stored, and whether each is well",
             "gorgon procedures show <name>     read the program",
             "gorgon procedures verify [<name>] read it back and check it",
             "gorgon procedures run <name>      run it, through the ordinary path",
             "gorgon procedures delete <name>   forget it",
             "gorgon procedures syntax          (re)write the language reference")

    def phrase(self, cmd, rest):
        # `procs` IS AN ALIAS AND THE SHORTCUT KNOWS ONLY ONE WORD. Normalising here keeps
        # the alias a CLI convenience rather than a second name the REPL grammar has to
        # carry — the shortcut stays the one authority on what a valid invocation is.
        return " ".join(["procedures", *rest]).strip()
