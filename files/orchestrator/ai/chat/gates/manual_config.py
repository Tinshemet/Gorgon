"""
manual_config.py — the manual-config prompt + clarify drain.

_manual_config_gate handles create_vm(manual=True) interactive config;
_clarify_drain prompts for each missing field of a clarify response. Both concern
arg-fixup/prompting and share OS_TYPE_ALIASES.
"""

from typing import List, Optional, Tuple

from shared.display import console
from orchestrator.sanitizer.sanitizer import OS_TYPE_ALIASES

from ..chat_types import TurnState, GateOutcome
from .config import _OS_KEYWORDS


def _manual_config_gate(tool_name: str, raw_args: dict, pre_gate_result: Optional[dict],
                        state: "TurnState") -> Tuple[dict, Optional[dict], "GateOutcome"]:
    """Interactive per-VM config when create_vm was called with manual=True.

    Prompts for os/cpu/mem/disk, applies them, marks os_type clarified, and
    clears the pre-gate result (manual config owns the missing fields). Returns
    (raw_args, pre_gate_result, outcome): EXIT (Ctrl-C) or PROCEED.

    Example::

        _manual_config_gate("create_vm", {"name": "v", "manual": True}, None, st)
        # prompts for config → (raw_args_without_manual, None, GateOutcome.PROCEED)
    """
    if tool_name == "create_vm" and raw_args.get("manual"):
        raw_args = dict(raw_args)
        raw_args.pop("manual", None)
        def_os   = raw_args.get("os_type", "linux")
        def_cpu  = raw_args.get("cpu_cores", 2)
        def_mem  = raw_args.get("memory_mb", 4096)
        def_disk = raw_args.get("disk_size_gb", 20)
        console.print(
            f"\n  [cyan]Configuring [bold]{raw_args.get('name')}[/bold]"
            f"  [{def_os} | {def_cpu} CPU | {def_mem} MB | {def_disk} GB][/cyan]"
        )
        console.print("  [dim]Press Enter for defaults, or specify: e.g. 'windows, 8GB, 4 CPU, 50GB'[/dim]")
        try:
            man_input = console.input("[bold cyan]  Config:[/bold cyan] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return raw_args, pre_gate_result, GateOutcome.EXIT
        if man_input:
            import re as _re
            for kw in _OS_KEYWORDS:
                if kw in man_input.split():
                    raw_args["os_type"] = OS_TYPE_ALIASES.get(kw, kw)
                    break
            m = _re.search(r'(\d+)\s*gb(?!\s*disk)', man_input)
            if m:
                raw_args["memory_mb"] = int(m.group(1)) * 1024
            m = _re.search(r'(\d+)\s*mb', man_input)
            if m:
                raw_args["memory_mb"] = int(m.group(1))
            m = _re.search(r'(\d+)\s*(?:cpu|core)', man_input)
            if m:
                raw_args["cpu_cores"] = int(m.group(1))
            m = _re.search(r'(\d+)\s*gb\s*disk', man_input)
            if m:
                raw_args["disk_size_gb"] = int(m.group(1))
        # Manual config owns os_type — give it a value and mark it clarified so
        # the pre-gate doesn't re-ask; then drop the pre-gate result entirely.
        if not raw_args.get("os_type"):
            raw_args["os_type"] = def_os
        state.clarified_fields.add("os_type")
        state.clarified_values.add(("os_type", raw_args["os_type"]))
        pre_gate_result = None
        state.confirmed_tool_types.discard("create_vm")   # each VM needs its own config
    elif tool_name == "create_vm" and "manual" in raw_args:
        raw_args = dict(raw_args)
        raw_args.pop("manual", None)
    return raw_args, pre_gate_result, GateOutcome.PROCEED


def _clarify_drain(result: dict, tool_name: str, state: "TurnState",
                   messages: List[dict]) -> GateOutcome:
    """Drain a clarify response: prompt for each missing field (or a verbatim
    clarify answer / the overwrite shortcut), update state, inject the re-plan
    message. Returns EXIT (Ctrl-C) or SKIP_TOOL (drained — caller breaks the tool
    loop; the post-loop re-plans with the answers).

    Example::

        _clarify_drain({"clarify": True, "needs_clarification": "name",
                        "question": "Name?"}, "create_vm", state, msgs)
        # → GateOutcome.SKIP_TOOL after recording the answer
    """
    # Drain ALL missing fields in one pass — no Ollama round-trip per field.
    filled: dict = {}
    missing_fields = result.get("missing") or [{
        "field":    result.get("needs_clarification", ""),
        "question": result.get("question", "Please provide more detail."),
        "options":  result.get("options", []),
    }]
    for mf in missing_fields:
        q    = mf["question"]
        opts = mf["options"]
        f    = mf["field"]

        # No field to fill. Two distinct cases:
        #
        # 1. tool_name == "clarify": the AI asked the user a question
        #    (e.g. "Did you mean 'loq'?"). Pass the answer back verbatim
        #    so the AI decides the next step — don't override intent.
        #
        # 2. tool_name != "clarify": executor returned a "Save anyway /
        #    Cancel" prompt. Tell the AI to retry with force=true.
        if not f:
            if opts:
                console.print(
                    f"[yellow]?[/yellow] {q}  "
                    + "  ".join(f"[{o}]" for o in opts)
                )
            else:
                console.print(f"[yellow]?[/yellow] {q}")
            try:
                _conf = console.input("[bold cyan]You:[/bold cyan] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye.[/dim]")
                return GateOutcome.EXIT
            _cancelled = (
                not _conf
                or (opts and _conf.lower() == opts[-1].lower())
                or _conf.lower() in ("no", "cancel", "n")
            )
            if tool_name == "clarify":
                # AI-initiated question — return the answer verbatim
                if _conf:
                    filled[f] = _conf
                    messages.append({"role": "user", "content": _conf})
            elif _cancelled:
                messages.append({"role": "user", "content": "_INTERNAL_ The user cancelled. Do not retry this operation."})
                state.op_cancelled = True
            else:
                hint = result.get("hint", "")
                messages.append({"role": "user", "content": _conf})
                messages.append({"role": "user", "content": f"_INTERNAL_ The user confirmed. {hint} Keep ALL original arguments exactly as they were."})
            state.clarify_happened = True
            state.clarify_answer   = _conf
            state.clarify_field    = ""
            break

        if opts:
            console.print(
                f"[yellow]?[/yellow] {q}  "
                + "  ".join(f"[{o}]" for o in opts)
            )
        else:
            console.print(f"[yellow]?[/yellow] {q}")
        try:
            clarified = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            return GateOutcome.EXIT
        if clarified:
            # Overwrite shortcut: user said "overwrite" for a name conflict.
            if f == "name" and "overwrite" in clarified.lower():
                orig = result.get("original_name", "")
                if orig:
                    filled["name"]      = orig
                    filled["overwrite"] = "true"
                    messages.append({"role": "user", "content": clarified})
                    messages.append({
                        "role":    "user",
                        "content": f"_INTERNAL_ The user chose to overwrite. Call create_vm again with name='{orig}' and overwrite=true, keeping ALL other original arguments exactly as they were.",
                    })
                    state.clarified_fields.update(filled.keys())
                    state.clarified_values.update(filled.items())
                    state.clarify_happened = True
                    state.clarify_answer   = clarified
                    state.clarify_field    = "overwrite"
                    break
            filled[f] = clarified
            messages.append({"role": "user", "content": clarified})
            # If the user named a specific distro, inject os_name so the
            # executor can auto-find the matching ISO.
            if f == "os_type" and clarified.lower().strip() in OS_TYPE_ALIASES:
                filled["os_name"] = clarified.lower().strip()
    state.clarified_fields.update(filled.keys())
    state.clarified_values.update(filled.items())
    if filled:
        _field_summary = ", ".join(f"{k}='{v}'" for k, v in filled.items())
        _iso_hint = (
            " The user named a specific distro — you MUST call scan_isos first,"
            f" then pass the matching ISO path as iso_path in create_vm."
            if "os_name" in filled else ""
        )
        messages.append({
            "role":    "user",
            "content": f"_INTERNAL_ The user provided the missing values: {_field_summary}. Call the correct tool using these EXACT values — do not invent different ones.{_iso_hint}",
        })
    state.clarify_happened = True
    state.clarify_answer   = str(filled)
    state.clarify_field    = ", ".join(filled.keys())
    return GateOutcome.SKIP_TOOL
