"""serve — run this node as the orchestrator/executor HTTP API."""

import sys
from typing import List

from rich.panel import Panel

from .base import Command
from . import context as ctx


class ServeCommand(Command):
    names = ("serve",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        import uvicorn
        # Parse: serve [host] [port] [--cert cert.pem --key key.pem]
        positional = [a for a in rest if not a.startswith("--")]
        flags      = rest  # full list for --flag parsing
        host = positional[0] if positional else "0.0.0.0"
        port = int(positional[1]) if len(positional) > 1 else 8080
        cert = flags[flags.index("--cert") + 1] if "--cert" in flags else None
        key  = flags[flags.index("--key")  + 1] if "--key"  in flags else None
        tls_line = (
            f"[green]TLS ON[/green] — cert: {cert}"
            if cert else
            "[yellow]TLS OFF[/yellow] — use --cert / --key for HTTPS (required over untrusted networks)"
        )
        ctx.console.print(Panel(
            f"[bold cyan]gorgon orchestrator service[/bold cyan]\n"
            f"Listening on [bold]{host}:{port}[/bold]\n"
            f"{tls_line}\n"
            f"[dim]Set API_TOKEN on this machine and on every client before connecting.[/dim]",
            border_style="cyan", title="Orchestrator Machine",
        ))
        uvicorn_kwargs: dict = {"host": host, "port": port, "log_level": "warning"}
        if cert and key:
            uvicorn_kwargs["ssl_certfile"] = cert
            uvicorn_kwargs["ssl_keyfile"]  = key
        elif cert or key:
            ctx.console.print("[bold red]--cert and --key must both be provided for TLS.[/bold red]")
            sys.exit(1)
        uvicorn.run("orchestrator.http.api_server:app", **uvicorn_kwargs)
