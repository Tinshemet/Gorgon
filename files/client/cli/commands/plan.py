"""commands/plan.py — gorgon plan [--dry] <request>."""

from client.cli.commands._shortcut import ShortcutCommand


class PlanCommand(ShortcutCommand):
    """Route one request through the engine architecture, and print what each stage did."""

    names = ("plan",)
    # NO `min_args`, DELIBERATELY. Falling through to "unknown command: plan" for a bare
    # `gorgon plan` would tell the operator the verb does not exist, when what is missing
    # is the request. The shortcut's own `matches` decides, and usage is printed.
    shortcut = ("plan", "Plan")
    usage = ("gorgon plan <request>         plan it and run it",
             "gorgon plan --dry <request>   plan it and show it, WITHOUT acting")
