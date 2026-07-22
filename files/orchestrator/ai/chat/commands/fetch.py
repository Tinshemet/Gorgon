"""fetch — download a VM disk from the client machine, with resume + verify."""

import os
import sys
from typing import List

from rich.panel import Panel

from .base import Command
from . import context as ctx


class FetchCommand(Command):
    names = ("fetch",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        # fetch <vm_name> [--out /dest/dir] — download VM disk from client machine
        if not rest:
            ctx.console.print("[bold red]Usage: fetch <vm_name> [--out /dest/dir][/bold red]")
            sys.exit(1)
        if ctx.API_URL == "local":
            ctx.console.print("[bold red]fetch requires remote mode (API_URL must be set)[/bold red]")
            sys.exit(1)
        import requests as _req, hashlib as _hl, pathlib as _pl
        vm_name = rest[0]
        out_dir = rest[rest.index("--out") + 1] if "--out" in rest else os.getcwd()
        out_dir = _pl.Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        headers = {"Authorization": f"Bearer {ctx._TOKEN}"} if ctx._TOKEN else {}

        # Fetch checksum first so we can verify after download
        ctx.console.print(f"[dim]Fetching SHA256 for [bold]{vm_name}[/bold]...[/dim]")
        try:
            cs_resp = _req.get(f"{ctx.API_URL}/images/{vm_name}/sha256",
                               headers=headers, timeout=30, verify=ctx._VERIFY)
        except Exception as e:
            ctx.console.print(f"[bold red]Cannot reach client machine: {e}[/bold red]")
            sys.exit(1)
        if not cs_resp.ok:
            ctx.console.print(f"[bold red]{cs_resp.status_code}: {cs_resp.text}[/bold red]")
            sys.exit(1)
        cs_data      = cs_resp.json()
        expected_sha = cs_data["sha256"]
        disk_name    = cs_data["disk"]
        total_bytes  = cs_data["size_bytes"]
        out_path     = out_dir / disk_name

        # Resume if partial file exists
        resume_from = out_path.stat().st_size if out_path.exists() else 0
        if resume_from >= total_bytes:
            ctx.console.print(f"[green]Already complete:[/green] {out_path}")
        else:
            dl_headers = dict(headers)
            if resume_from:
                dl_headers["Range"] = f"bytes={resume_from}-"
                ctx.console.print(f"[dim]Resuming from {resume_from // 1024 // 1024} MB...[/dim]")

            with _req.get(f"{ctx.API_URL}/images/{vm_name}", headers=dl_headers,
                          stream=True, timeout=ctx._TIMEOUT, verify=ctx._VERIFY) as r:
                if not r.ok:
                    ctx.console.print(f"[bold red]Download failed {r.status_code}: {r.text}[/bold red]")
                    sys.exit(1)
                mode = "ab" if resume_from else "wb"
                downloaded = resume_from
                with open(out_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=ctx._IO_CHUNK):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pct = downloaded * 100 // total_bytes
                            ctx.console.print(
                                f"  [dim]{pct}%  {downloaded // 1024 // 1024} / "
                                f"{total_bytes // 1024 // 1024} MB[/dim]",
                                end="\r",
                            )
            ctx.console.print()

        # Verify checksum
        ctx.console.print("[dim]Verifying checksum...[/dim]")
        h = _hl.sha256()
        with open(out_path, "rb") as f:
            for chunk in iter(lambda: f.read(ctx._IO_CHUNK), b""):
                h.update(chunk)
        actual_sha = h.hexdigest()
        if actual_sha != expected_sha:
            ctx.console.print(f"[bold red]Checksum MISMATCH — file may be corrupt![/bold red]\n"
                              f"  expected: {expected_sha}\n  actual:   {actual_sha}")
            sys.exit(1)
        ctx.console.print(Panel(
            f"[bold green]{vm_name}[/bold green] downloaded and verified.\n"
            f"Disk: [bold]{out_path}[/bold]\n"
            f"SHA256: [dim]{actual_sha}[/dim]",
            border_style="green", title="fetch_vm complete",
        ))
