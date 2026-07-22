"""render.py — the pre-flight warning panel (yellow box + options presented to the user)."""

from typing import Dict


# Renders a yellow warning panel and presents the pre-flight options to the user.
# In: dict preflight, Console → Out: nothing (console output)
def _show_preflight_warning(preflight: Dict, console: object) -> None:
    """Display a pre-flight warning panel and present options to the user."""
    from rich.panel import Panel
    reason     = preflight.get("reason", "")
    question   = preflight.get("question", "Confirm?")
    options    = preflight.get("options", [])
    correction = preflight.get("correction", "")

    lines = [f"[yellow]⚠[/yellow] {reason}"]
    if correction:
        lines.append(f"[dim]{correction}[/dim]")

    console.print(Panel(
        "\n".join(lines),
        title="[bold yellow]Pre-flight Check[/bold yellow]",
        border_style="yellow",
    ))

    opts_str = "  ".join(f"[dim][{o}][/dim]" for o in options) if options else ""
    console.print(f"\n[ai]Assistant:[/ai] {question}  {opts_str}\n")
