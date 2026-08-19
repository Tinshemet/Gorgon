"""cold.py — sample the COLD path, which is the only path production takes.

    from tests.bench.cold import cold_sample
    readings = cold_sample(lambda: run_scanned(request, board=b), n=3)

# ⇒⇒ WHY (2026-08-17, measured): ollama's KV/prompt cache makes a REPEATED identical prompt
#   return one answer and a RECOMPUTED one another — each condition perfectly stable, so a
#   probe that re-sends one request looks rock solid while measuring a path the product
#   never takes (production never repeats a request):

        rung 10 repeated, nothing between        20/20   ['vms']
        rung 10 with ANY request in between      10/10   ['them', 'vms']   <- the REAL one

# ⇒ `cold_sample` fires one THROWAWAY request between samples, evicting the prefix so every
#   measured call is a recompute. The throwaway varies by index (a constant throwaway would
#   itself go warm). Benches that walk DISTINCT cases (the read eval) never need this — the
#   cases themselves are the eviction.
"""
from typing import Callable, List


def _evict(i: int) -> None:
    try:
        from engines.channel import constrained
        constrained("answer the question.", f"is throwaway request number {i} a request?",
                    {"type": "object", "properties": {"answer": {"type": "string",
                                                                 "maxLength": 8}},
                     "required": ["answer"]}, timeout=60)
    except Exception:
        pass                                    # eviction is best-effort; the sample matters


def cold_sample(fn: Callable[[], object], n: int = 3) -> List[object]:
    """n samples of fn(), each preceded by a cache-evicting throwaway. Order preserved."""
    out = []
    for i in range(n):
        _evict(i)
        out.append(fn())
    return out
