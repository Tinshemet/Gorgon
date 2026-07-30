"""What the measurement was taken UNDER — recorded beside the number it produced.

THE DEFECT THIS CLOSES, found 2026-07-30. Rung 6 failed to build 3/3 in one run and built
5/5 in the next, on byte-identical code, and it took an hour to establish that the code was
not the variable. Nothing in either log said what the runs had in common or where they
differed, so the only way to ask was to re-run and hope.

This is [[gorgon-ladder-gate]]'s reason code applied one level out. That names the LAYER a
failure belongs to — language, model, harness, report. A stamp names the CONDITIONS the
whole column was measured under, so a comparison across different ones announces itself
instead of reading as a pass-rate change. Same argument as A2's goal-hash, and the same
rule: a baseline stores a premise, not only a verdict.

WHAT IS IN IT AND WHY EACH EARNED ITS PLACE:

  model + digest    two tags can point at one blob and one tag can be re-pulled. The
                    digest is the only thing that says the weights are the same weights.
  quantization      the same model at a different quant is a different model, and it is
                    the FIRST thing that changes when someone makes it fit in VRAM.
  num_ctx           the bench pins it; a change silently resizes the KV cache, which is
                    what decides whether the model fits on the card at all.
  offload           MEASURED TO VARY ON THIS MACHINE: llama3.1:8b loaded at 29%/71% and
                    27%/73% CPU/GPU within one morning, chosen per load from whatever
                    VRAM was free. A partial offload puts part of the arithmetic on a
                    different device, and at temperature 0 that is enough to change which
                    token wins. This is the field the incident was actually about.
  runtime           ollama's own version — the sampler and the scheduler live there.

NOT IN IT, deliberately: wall-clock time and host load. They vary constantly, they would
make every stamp differ, and a stamp that always reports a change reports nothing. The
fields here are ones that are stable in normal operation and meaningful when they move.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from orchestrator.ai.chat.ollama_client import OLLAMA_URL, _OLLAMA

# The fields a comparison is allowed to fail on. `offload` is deliberately ABSENT: it moves
# on its own between loads, so gating on it would void every baseline within a day. It is
# recorded and REPORTED, so a reader can see it, but it does not by itself void a number.
COMPARED = ("model", "digest", "quantization", "num_ctx", "runtime")


def _get(path: str, payload: Optional[dict] = None, timeout: int = 10) -> Dict[str, Any]:
    """One call to the runtime. Never raises: a stamp that fails to read a field must not
    take the measurement down with it — an unknown condition is worth recording as unknown,
    and `?` is honest where a crash is not."""
    try:
        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(f"{OLLAMA_URL}{path}", data=data,
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()) or {}
    except Exception:
        return {}


def _find(models: List[dict], model: str) -> dict:
    for m in models or ():
        if model in (m.get("model"), m.get("name")):
            return m
    return {}


def stamp(model: Optional[str] = None) -> Dict[str, Any]:
    """The conditions, as a plain dict. Safe to call when nothing is loaded.

    The identity fields come from `/api/tags`, which answers whether or not the model is
    resident — a stamp must not depend on having just run something. Only `offload` needs
    `/api/ps`, and it is the one field that legitimately reads `not loaded`.
    """
    model = model or _OLLAMA["model"]
    tagged = _find(_get("/api/tags").get("models"), model)
    details = tagged.get("details") or {}
    running = _find(_get("/api/ps").get("models"), model)
    total, vram = running.get("size") or 0, running.get("size_vram") or 0
    return {
        "model": model,
        "digest": (tagged.get("digest") or "?")[:12],
        "quantization": details.get("quantization_level") or "?",
        "parameters": details.get("parameter_size") or "?",
        "num_ctx": _OLLAMA.get("num_ctx"),
        # BY BYTES RESIDENT, not by layer count, which is what `ollama ps` displays — the
        # two disagree by a couple of points. Stated here so a reader comparing this line
        # against `ollama ps` knows why, rather than suspecting one of them.
        "offload": f"{round(100 * vram / total)}% GPU by bytes" if total else "not loaded",
        "runtime": f"ollama {_get('/api/version').get('version', '?')}",
    }


def describe(s: Dict[str, Any]) -> str:
    """One line, for a run summary."""
    return (f"{s.get('model')} ({s.get('parameters')}, {s.get('quantization')}, "
            f"digest {s.get('digest')}) · num_ctx {s.get('num_ctx')} · "
            f"offload {s.get('offload')} · {s.get('runtime')}")


def differs(recorded: Optional[Dict[str, Any]], now: Dict[str, Any]) -> List[str]:
    """Which COMPARED fields moved. Empty means the two numbers may be compared.

    A missing stamp returns a single explicit entry rather than silence: a baseline
    recorded before stamps existed is not known-comparable, it is UNKNOWN, and those read
    differently. The whole point is to stop an unstated premise passing for a met one.
    """
    if not recorded:
        return ["no stamp recorded — this baseline predates the stamp, comparability unknown"]
    return [f"{f}: {recorded.get(f)!r} -> {now.get(f)!r}"
            for f in COMPARED if recorded.get(f) != now.get(f)]
