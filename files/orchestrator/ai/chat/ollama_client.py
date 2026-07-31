"""
ollama_client.py — Ollama AI Client Layer

HTTP communication with Ollama: system prompt construction and the
blocking chat API call. OLLAMA_URL and OLLAMA_MODEL are the two
tuneable globals for this layer.
"""

import json
import os
import sys
from typing import Dict, List

import requests

from orchestrator.executor_client import get_ovmf as _get_ovmf, get_profiles as list_profiles
from ..active_library import LIBRARY
from ..agent.contract      import system_prompt_template, default_toolkit, is_forbidden
from ..tools        import TOOLS
from shared.display import console
import orchestrator.preflight.host_probe as _host_probe

_CFG = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))
_OLLAMA = _CFG["ollama"]

OLLAMA_URL   = os.environ.get("OLLAMA_URL",   _OLLAMA["url"])
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", _OLLAMA["model"])


# Assembles the LLM system prompt from live OVMF/profile state and custom-mode flag.
# In: nothing → Out: str
# General-capability guidance appended to EVERY agent's prompt (unless the agent forbids
# run_command). Un-fences the model from the VM-only tool regime for ordinary work, and
# enforces the probe-verify honesty rule so an effect isn't "done" until it's confirmed.
_EVERYDAY_OPS = """

═══ EVERYDAY OPERATIONS (run_command) ═══
You are NOT limited to the VM tools for ordinary computer work. To create/read/transform
files, format data (CSV/JSON/text), and similar everyday tasks, WRITE THE COMMAND with
run_command (lang="shell" or "python") — do not ask for or invent a specialized tool.
  • Sandboxed: run_command can only WRITE under the workspace (its working directory); writes
    elsewhere fail. Reading outside the workspace or using the network needs the OPERATOR to
    grant it for this session — ask; you cannot grant it yourself.
  • run_command success means the command RAN, not that the goal is met. To treat a step as
    done, VERIFY the effect with local_probe (e.g. after writing vms.csv, local_probe
    file_exists on it) — the same rule as guest_probe for VM commands. Unverified ≠ done.
  • run_command runs on the HOST; run_guest_command runs INSIDE a VM. Pick by target."""


def _run_command_available() -> bool:
    """True if the active agent may use run_command — not blacklisted, and (if the agent
    declares an explicit toolkit whitelist) included in it. Governs whether the everyday-ops
    guidance is added, so a blacklisting agent's prompt never mentions a tool it can't use."""
    tk = default_toolkit()
    if tk and "run_command" not in tk:
        return False
    return not is_forbidden("run_command")


def _build_system_prompt() -> str:
    """Assemble the system prompt (tool list + rules) sent to the model."""
    profiles    = [p["name"] for p in list_profiles()]
    ovmf_status = "AVAILABLE" if _get_ovmf().get("available") else "NOT FOUND (SeaBIOS fallback active)"
    custom_note = (
        "\nCUSTOM MODE ACTIVE (-cu): product_name and manufacturer can be any fictional values. "
        "Skip all warnings about unverifiable hardware."
    ) if _host_probe.custom_mode() else ""

    # Active Library: current system state + relations, so the model resolves
    # references ("same OS as test1", "all redteam VMs") from ground truth
    # instead of re-deriving them from chat history. Refreshed every turn.
    _digest = LIBRARY.ai_digest()
    state_section = (
        f"\n\n═══ CURRENT STATE (live registry — resolve any reference against this) ═══\n{_digest}\n"
        if _digest else ""
    )

    # The prompt TEMPLATE (persona + innate rules) lives in the active .grgn agent
    # file; the substrate fills the live tokens here. Swap the .grgn → swap the
    # whole prompt. Literal .replace (not str.format) so any braces a hand-edited
    # prompt introduces are left untouched.
    prompt = system_prompt_template()
    for token, value in (
        ("{custom_note}",   custom_note),
        ("{ovmf_status}",   ovmf_status),
        ("{profiles}",      str(profiles)),
        ("{state_section}", state_section),
    ):
        prompt = prompt.replace(token, value)
    if _run_command_available():
        prompt += _EVERYDAY_OPS
    return prompt


def context_floor() -> Dict[str, int]:
    """What every turn costs BEFORE the operator has typed anything.

    The system prompt and the tool schemas are re-sent on every single call, so they are a
    floor, not a budget. Returned as numbers rather than printed so the CLI, the HTTP
    server and a test can all ask the same question and get the same answer.
    """
    sp = len(_build_system_prompt())
    ts = len(json.dumps(TOOLS))
    return {"system_chars": sp, "tools_chars": ts, "tools": len(TOOLS),
            # chars/4 UNDER-estimates JSON, which tokenises worse than prose because of
            # the punctuation — so a floor computed this way is optimistic, and the real
            # count from `prompt_eval_count` is the one to trust.
            "est_tokens": (sp + ts) // 4, "num_ctx": _OLLAMA["num_ctx"]}


def _warn_if_truncated(reply: Dict, payload: Dict) -> Dict:
    """Say so when the prompt did not fit. Ollama will not.

    FOUND 2026-07-31, reported as "the AI only answered in one word and ignored commands".
    53 tool schemas are ~7.8k tokens and the system prompt ~1.4k against a `num_ctx` of
    8192, so the payload OVERFLOWED BEFORE THE FIRST MESSAGE. Measured on the real API:
    `prompt_eval_count` came back 8191 of 8192 and the reply was the single word "Hello".

    Ollama does not error on this. It silently drops from the front of the context — the
    system prompt and part of the tool definitions — which is exactly why the two symptoms
    arrive together: the model loses its instructions AND the tools it was told to call,
    and has no room left to generate. It reads as a stupid model rather than a full buffer.

    THE CHECK IS ON `prompt_eval_count`, THE SERVER'S OWN COUNT, not our estimate. Today's
    other bug hid for weeks behind an estimate of what we thought we sent; a number the
    server reports back cannot drift from what it actually did.
    """
    used, limit = reply.get("prompt_eval_count") or 0, _OLLAMA["num_ctx"]
    if used and used >= limit * 0.98:
        floor = context_floor()
        console.print(
            f"[error]CONTEXT OVERFLOW — the prompt did not fit and was silently "
            f"truncated.[/error]\n"
            f"  used {used} of num_ctx {limit} tokens before generating anything\n"
            f"  floor: {floor['tools']} tool schemas (~{floor['tools_chars']//4} est. tokens) "
            f"+ system prompt (~{floor['system_chars']//4} est.)\n"
            f"  → replies will be short and tool calls will be dropped. Narrow the tool set "
            f"for this turn, or raise num_ctx in orchestrator/ai/chat/config.json.")
    return reply


# POSTs the full chat payload (with tools) to the Ollama API and returns the parsed JSON response.
# In: List[dict] messages → Out: dict response
def _call_ollama(messages: List[Dict], tools: List[Dict] = None) -> Dict:
    """Send the conversation to Ollama's chat API; return the parsed response.

    `tools` overrides the offered tool set (used for round-0 tool-narrowing);
    None = the full TOOLS list.
    """
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [{"role": "system", "content": _build_system_prompt()}] + messages,
        "tools":    TOOLS if tools is None else tools,
        "stream":   False,
        "options":  {"temperature": _OLLAMA["temperature"], "num_ctx": _OLLAMA["num_ctx"]},
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=_OLLAMA["timeout"])
        resp.raise_for_status()
        return _warn_if_truncated(resp.json(), payload)
    except requests.ConnectionError:
        console.print(
            f"[error]Cannot connect to Ollama at {OLLAMA_URL}[/error]\n"
            f"  → Start: [bold]ollama serve[/bold]\n"
            f"  → Pull:  [bold]ollama pull {OLLAMA_MODEL}[/bold]"
        )
        sys.exit(1)
