"""WHO SPENDS MORE — the bigger model or the smaller one? And what does a stronger one propose?

    PYTHONPATH=. python3 -m tests.bench.twopass.token_probe --dump      # show the payload
    PYTHONPATH=. python3 -m tests.bench.twopass.token_probe --models llama3.1:8b,qwen2.5:14b

`engines.channel` parses the message and throws the counts away, so this makes the SAME call —
same payload, same schema, same options — and keeps `prompt_eval_count` and `eval_count`.

⇒ **THE PROMPT SIDE IS THE SAME FOR BOTH BY CONSTRUCTION**, since the payload is built once and
  sent to each. So a difference in `prompt_eval_count` is the TOKENISER, and a difference in
  `eval_count` is how much each model chose to say.
"""
import argparse
import json
import urllib.request
from typing import Dict, List

from ..formula.legal import Board

RUNGS = (4, 13, 11, 5)


def payload_for(rung: int, board: Board, order: str = "pinned", filtered: bool = False):
    """The exact question pass 2 asks, for one rung."""
    import engines.channel as channel
    from . import pass1, pass2
    was, channel.constrained = channel.constrained, lambda *a, **k: {}
    try:
        rows = pass1.run_scanned(pass1.EXPECTED[rung].request, board=board)
    finally:
        channel.constrained = was
    table = pass2.symbol_table(rows, board)
    operators = pass2.operators_offered(
        board, order, pass1.EXPECTED[rung].request if filtered else "")
    names = [s.handle for s in table]
    return (pass2.ASK,
            pass2._payload(pass1.EXPECTED[rung].request, table, operators, None),
            pass2._schema(names, operators, False, True))


def call(model: str, prompt: str, payload: str, schema: dict, timeout: int = 900) -> Dict:
    """The same call `channel.constrained` makes, with the counts kept."""
    from engines.channel import KEEP_ALIVE, _options
    from orchestrator.ai.chat.ollama_client import OLLAMA_URL as url
    body = {"model": model, "stream": False, "format": schema,
            "keep_alive": KEEP_ALIVE, "options": _options(0.0),
            "messages": [{"role": "system", "content": prompt},
                         {"role": "user", "content": payload}]}
    req = urllib.request.Request(f"{url}/api/chat", method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as got:
        raw = json.loads(got.read().decode())
    answer = raw.get("message", {}).get("content", "")
    return {"answer": answer,
            "prompt_tokens": raw.get("prompt_eval_count"),
            "answer_tokens": raw.get("eval_count"),
            "ms": round(raw.get("total_duration", 0) / 1e6)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="llama3.1:8b,qwen2.5:14b")
    ap.add_argument("--dump", action="store_true",
                    help="print the payload verbatim, so a human or another model can answer it")
    args = ap.parse_args()
    board = Board()

    if args.dump:
        for rung in RUNGS:
            prompt, payload, schema = payload_for(rung, board)
            print("=" * 96)
            print(f"RUNG {rung}")
            print("=" * 96)
            print(f"SYSTEM:\n{prompt}\n")
            print(f"USER:\n{payload}\n")
            print(f"SCHEMA operators: {schema['properties']['operations']['items']['properties']['operator']['enum']}")
            print(f"SCHEMA on:        {schema['properties']['operations']['items']['properties']['on']['enum']}")
        return

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    totals: Dict[str, List[int]] = {m: [0, 0] for m in models}
    print("=" * 100)
    print(f"{'rung':<6} {'model':<16} {'prompt':>8} {'answer':>8} {'ms':>8}   steps")
    print("=" * 100)
    for rung in RUNGS:
        prompt, payload, schema = payload_for(rung, board)
        for model in models:
            try:
                got = call(model, prompt, payload, schema)
            except Exception as exc:
                print(f"{rung:<6} {model:<16} <failed {type(exc).__name__}>")
                continue
            try:
                steps = json.loads(got["answer"]).get("operations", [])
            except Exception:
                steps = []
            totals[model][0] += got["prompt_tokens"] or 0
            totals[model][1] += got["answer_tokens"] or 0
            shown = ", ".join(f"{s.get('operator')}({s.get('on')})" for s in steps)
            print(f"{rung:<6} {model:<16} {got['prompt_tokens'] or 0:>8} "
                  f"{got['answer_tokens'] or 0:>8} {got['ms']:>8}   {shown[:44]}")
    print("=" * 100)
    for model, (p, a) in totals.items():
        print(f"  {model:<16} prompt {p:>6}   answer {a:>6}   total {p + a:>6}")


if __name__ == "__main__":
    main()
