"""commands/referendum.py — review the AI's rule PROPOSALS: list | show | sign | reject.

A referendum is the agent asking for a durable change to the law (a typed, weighted rule
it proposes but cannot enact). The operator reviews it here; ``sign`` re-auths with the
current safeword, lets the operator set the FINAL weight (the AI only proposed one), and
enacts it as a rule via a versioned, audited contract re-sign. Amendments (human-authored)
go through ``gorgon contract amend``; this surface is for what the AI asks for.
"""
import os

from client.cli.commands.base import Command
from client.cli.commands.context import _auth_sessions, _require_operator_password, console


def _active_agent_key() -> str:
    from shared import agent_select as _sel
    a = os.environ.get("GORGON_AGENT") or _sel.get_selection() or "doorman.grgn"
    return os.path.splitext(os.path.basename(a))[0]


class ReferendumCommand(Command):
    names = ("referendum",)

    def run(self, cmd, rest, verbose):
        from orchestrator.ai.agent import proposals as _P
        sub = rest[0] if rest else ""
        _op = _auth_sessions.current_username() if _auth_sessions else None

        if sub == "list":
            agent = rest[1] if len(rest) >= 2 else _active_agent_key()
            pend = _P.pending(agent)
            if not pend:
                console.print(f"[dim]No pending referendums for '{agent}'.[/dim]")
                return
            console.print(f"[bold]Pending referendums — {agent}[/bold]")
            for p in pend:
                console.print(f"  [bold cyan]{p['id']}[/bold cyan]  [{p['kind']}]  {p['origin']}  "
                              f"“{p['text'][:56]}”  proposed w:{p['proposed_weight']}")
            console.print(f"[dim]  gorgon referendum show <id> · sign <id> · reject <id>[/dim]")

        elif sub == "show" and len(rest) >= 2:
            agent = rest[2] if len(rest) >= 3 else _active_agent_key()
            p = _P.get(agent, rest[1])
            if not p:
                console.print(f"[bold red]No referendum {rest[1]} for '{agent}'.[/bold red]")
                return
            console.print(f"[bold]REFERENDUM {p['id']}[/bold] — {p['kind']} — proposed by {p['origin']}")
            if p.get("prompted_by"):
                console.print(f"  [dim]prompted by:[/dim] {p['prompted_by']}")
            console.print(f"  [dim]text:[/dim]   {p['text']}")
            console.print(f"  [dim]effect:[/dim] {p.get('effect')}")
            console.print(f"  [dim]proposed weight:[/dim] {p['proposed_weight']}   "
                          f"[dim]status:[/dim] {p['status']}")

        elif sub == "sign" and len(rest) >= 2:
            if not _require_operator_password("enact a referendum"):
                return
            agent = rest[2] if len(rest) >= 3 else _active_agent_key()
            p = _P.get(agent, rest[1])
            if not p or p.get("status") != "pending":
                console.print(f"[bold red]No pending referendum {rest[1]} for '{agent}'.[/bold red]")
                return
            import getpass
            import shared.bundle as _bundle
            from shared.grgn_sign import read as _read_grgn
            from orchestrator.ai.agent import forge as _forge, AGENT_DIR as _agent_dir
            from orchestrator.ai.agent.contract.rules import RuleSet, effective_rules
            from shared import audit as _audit
            path = _bundle.resolve_grgn(agent + ".grgn", _agent_dir)
            g, st = _read_grgn(path)
            if g is None:
                console.print(f"[bold red]Cannot read {agent}'s contract ({st}).[/bold red]")
                return
            if not g.get("contract", {}).get("signed"):
                console.print("[bold red]Contract is unsigned — sign it before enacting rules.[/bold red]")
                return
            # Show the current law + the proposal, so the operator weighs it in context.
            labels = {0: "critical", 1: "important", 2: "standard", 3: "minor", 4: "advisory"}
            by = RuleSet(effective_rules(g["contract"])).by_weight()
            console.print("[bold]── CURRENT LAW (by weight) ──[/bold]")
            for w in sorted(by):
                for r in by[w]:
                    console.print(f"  {w} · {labels.get(w, 'weak')}  [{r['kind']}] {r['text'][:60]}")
            console.print("[bold]── THIS REFERENDUM ──[/bold]")
            console.print(f"  ? · [{p['kind']}] {p['text']}   [dim](proposed w:{p['proposed_weight']})[/dim]")
            prior = getpass.getpass("Current safeword to enact: ")
            raw = console.input(f"Assign weight [0–4, blank = proposed {p['proposed_weight']}]: ").strip()
            try:
                weight = int(raw) if raw else int(p["proposed_weight"])
            except ValueError:
                console.print("[bold red]Weight must be an integer 0–4.[/bold red]")
                return
            rule = _P.to_rule(p, weight)
            new_rules = list(g["contract"].get("rules") or []) + [rule]
            try:
                _forge.amend(g, {"rules": new_rules}, prior, prior_safeword=prior)   # same safeword, re-sign
                _forge.write_grgn(g, path)
                _P.mark_enacted(agent, p["id"], weight)
                v = g["contract"]["version"]
                console.print(f"[green]✓ enacted as a w:{weight} {rule['kind']} rule. "
                              f"{agent} → v{v}. Logged.[/green]")
                _audit.record("referendum.enact", f"{agent} {p['id']} w:{weight}", _op)
            except ValueError as e:
                console.print(f"[bold red]{e}[/bold red]")

        elif sub == "reject" and len(rest) >= 2:
            if not _require_operator_password("reject a referendum"):
                return
            agent = rest[2] if len(rest) >= 3 else _active_agent_key()
            if _P.reject(agent, rest[1]):
                from shared import audit as _audit
                _audit.record("referendum.reject", f"{agent} {rest[1]}", _op)
                console.print(f"[green]Rejected referendum {rest[1]}.[/green]")
            else:
                console.print(f"[yellow]No pending referendum {rest[1]} for '{agent}'.[/yellow]")

        else:
            console.print("[yellow]Usage: gorgon referendum "
                          "list [agent] | show <id> [agent] | sign <id> [agent] | reject <id> [agent][/yellow]")
