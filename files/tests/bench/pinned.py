"""The request conditions every bench call runs under — ONE copy of them.

WHY THIS EXISTS AT ALL. Nine call sites across the bench each wrote
`{"temperature": 0.0, "num_ctx": _OLLAMA_CTX}` by hand. That is the stale-twin shape this
codebase keeps paying for — `of`, `select`, `NOT`-as-array were all one builder growing a
fix the other never got — and conditions are worse than schema in one respect: a drifted
condition does not fail, it just makes two numbers quietly incomparable.

WHAT IS PINNED, AND THE RULE FOR ADDING TO IT. A knob belongs here if leaving it to the
runtime lets the SAME prompt produce a different answer. The measured position (screen of
2026-07-30, 4 models x 3 forced reloads x 2 sweeps of the quantifier corpus) is that the
model reload itself changes NOTHING — 16/16 identical answers across epochs for every
model tested, including one at a 29%/71% CPU/GPU spill. So none of this is a fix for an
observed defect. It closes variables we have NOT measured, cheaply, so that a future
disagreement is attributable rather than mysterious:

  num_parallel  THE ONE THAT CAN ACTUALLY BITE. Concurrent requests are batched together,
                and batch composition changes the order of floating-point reductions, so
                an identical prompt can decode differently depending on what else was in
                flight. The benches are sequential today; nothing enforces that they stay
                that way, and the default is auto rather than 1.
  keep_alive    a run longer than the idle timeout would otherwise straddle two model
                loads, silently, in the middle of a column.
  seed, top_k   redundant at temperature 0 and kept anyway: "temperature 0 is
                deterministic" is exactly the assumption [[ladder-is-not-a-feedback-loop]]
                records as false.
  num_ctx       already pinned by config; restated here so one place answers the question.

NOT PINNED: `num_gpu`. Forcing a layer count would make the load FAIL rather than spill
when VRAM is short, turning a measured non-issue into a hard outage on a 6 GB card — and
the offload split was measured not to matter. It is recorded by `env_stamp` instead, which
is the honest treatment for a variable that moves and does not signify.

THIS IS THE BENCH'S POLICY, NOT PRODUCTION'S. `ollama_client` deliberately keeps its own:
production wants the operator's configured behaviour, not reproducibility.
"""
from __future__ import annotations

from typing import Any, Dict

from orchestrator.ai.chat.ollama_client import _OLLAMA

# Never unload between calls. Ollama reads -1 as "keep resident until told otherwise".
KEEP_ALIVE = -1

# A fixed seed makes the sampler's own state one less thing to wonder about. The value is
# arbitrary; what matters is that it does not change.
SEED = 0


def options(temperature: float = 0.0, **extra: Any) -> Dict[str, Any]:
    """The `options` block for a bench request. `extra` is for a caller with a genuine
    reason to add one, and it wins — this pins defaults, it does not forbid intent."""
    return {"temperature": temperature, "num_ctx": _OLLAMA["num_ctx"],
            "seed": SEED, "top_k": 1, **extra}


def payload(model: str, messages: list, temperature: float = 0.0,
            **rest: Any) -> Dict[str, Any]:
    """A whole request body under the pinned conditions. `rest` carries `tools`, `format`
    and anything else the caller needs; `options` may be overridden wholesale by passing
    it, which is what a probe deliberately varying a condition should do."""
    body = {"model": model, "stream": False, "messages": messages,
            "keep_alive": KEEP_ALIVE, "options": options(temperature)}
    body.update(rest)
    return body
