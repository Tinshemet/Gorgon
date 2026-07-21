"""
tool_dispatch/tools/base.py — the Tool contract.

One tool = one Tool subclass in its own module under tool_dispatch/tools/. Set
`names` (the tool name(s) it answers to) and implement run(args, ctx). Subclasses
auto-register (see __init__.py) just by existing — adding a tool is dropping a
file.

`ctx` (ToolCtx) carries the per-call context the dispatcher builds: `verbose`
plus the injected callables that differ between the executor path (stubs) and
the orchestrator pipeline path (real): raw_os_type, placeholder_vm_names,
resolve_iso, preflight_check, show_preflight_warning, and `redispatch` (used by
the `revert` tool to re-run a recorded action). Most tools use only ctx.verbose.
"""

# Every concrete Tool subclass appends itself here as it is defined.
ALL_TOOLS = []


class ToolCtx:
    """Per-call context passed to every Tool.run(args, ctx)."""

    def __init__(self, verbose, raw_os_type, placeholder_vm_names,
                 resolve_iso, preflight_check, show_preflight_warning, redispatch):
        self.verbose = verbose
        self.raw_os_type = raw_os_type
        self.placeholder_vm_names = placeholder_vm_names
        self.resolve_iso = resolve_iso
        self.preflight_check = preflight_check
        self.show_preflight_warning = show_preflight_warning
        self.redispatch = redispatch          # (tool_name, args) -> result


class Tool:
    names: tuple = ()      # tool name(s); empty = abstract, not registered

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.names:
            ALL_TOOLS.append(cls)

    def run(self, args: dict, ctx: ToolCtx):
        """Execute the tool. Return its result (a dict, or a list for list_vms etc.)."""
        raise NotImplementedError
