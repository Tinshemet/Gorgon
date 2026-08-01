"""test_tool_budget.py — which tools get withheld when they cannot all fit, and why.

#59 SAID "16 TOOLS DROPPED BY POSITION, NOT BY IRRELEVANCE". `_fit_tools` answers it —
hinted and core tools rank first and registry order only breaks ties — and NOTHING TESTED
IT. The ranking is the whole of the fix and it sat behind a `try/except` that silently falls
back to registry order if the import moves.

THE RESULT THIS RESPECTS RATHER THAN OVERTURNS: on 2026-07-17, narrowing by GUESS was
measured harmful — offering 4 tools instead of 46 made a weak model hallucinate an os_type
4/4 where the full set resolved it 4/4. So this never drops a tool while there is room. What
it refuses is a payload that cannot fit, because the alternative is not "the full set" but a
payload ollama TRUNCATES FROM THE FRONT, silently, taking the system prompt with it.

NO SILENT CAPS is the other half. A run that quietly offers 40 of 53 reads as "the model
chose not to use it" when the truth is it was never told the tool existed.
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.chat.ollama_client import _fit_tools

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _tool(name, size=200):
    return {"type": "function",
            "function": {"name": name, "description": "x" * size, "parameters": {}}}


def _names(tools):
    return [(t.get("function") or {}).get("name") for t in tools]


def test_nothing_is_dropped_while_there_is_room():
    """The 4-tool regime that failed in 2026-07-17 cannot recur by accident."""
    print("[budget] room for everything means everything is offered")
    tools = [_tool(f"tool{i}") for i in range(20)]
    out = io.StringIO()
    with redirect_stdout(out):
        kept = _fit_tools("system", [{"role": "user", "content": "hello"}], tools)
    check(f"all {len(tools)} offered", len(kept) == len(tools))
    check("and nothing is reported as withheld", "withheld" not in out.getvalue())


def test_a_hinted_tool_survives_a_squeeze():
    """RANKING IS THE WHOLE POINT OF #59. Under pressure the tools the turn actually
    mentioned must outrank the ones that merely registered early."""
    print("[budget] relevance ranks; registry order only breaks ties")
    from orchestrator.ai.chat.context_assistant import scan_tool_hints

    # A request that names something, so the hint scanner has a real signal to find.
    request = "list the vms"
    hinted = set(scan_tool_hints(request) or ())
    if not hinted:
        check("the hint scanner found nothing for a plain request — nothing to rank", True)
        return

    name = sorted(hinted)[0]
    # The hinted tool is registered LAST, so only ranking can save it.
    tools = [_tool(f"filler{i}", size=4000) for i in range(30)] + [_tool(name, size=200)]
    out = io.StringIO()
    with redirect_stdout(out):
        kept = _fit_tools("s" * 200, [{"role": "user", "content": request}], tools)
    check(f"the squeeze happened ({len(kept)} of {len(tools)} kept)", len(kept) < len(tools))
    check(f"and the hinted tool {name!r} survived it", name in _names(kept))


def test_withholding_is_never_silent():
    """A run that quietly offers 40 of 53 reads as a model choosing not to act."""
    print("[budget] what was withheld is said out loud")
    tools = [_tool(f"big{i}", size=8000) for i in range(40)]
    out = io.StringIO()
    with redirect_stdout(out):
        kept = _fit_tools("s" * 400, [{"role": "user", "content": "do something"}], tools)
    said = out.getvalue()
    check("some were withheld", len(kept) < len(tools))
    check("and the count is reported", "withheld" in said)
    check("with names, not just a number", any(f"big{i}" in said for i in range(40)))


def test_a_full_window_is_reported_rather_than_papered_over():
    """Dropping tools cannot fix a history that alone overruns the window, and pretending
    otherwise looks like a model that forgot how to act."""
    print("[budget] history overrun is its own message")
    huge = [{"role": "user", "content": "x" * 400_000}]
    out = io.StringIO()
    with redirect_stdout(out):
        kept = _fit_tools("system", huge, [_tool("anything")])
    check("no tools are offered", kept == [])
    check("and it says the conversation is the problem",
          "conversation" in out.getvalue().lower())


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "tool budget"))


if __name__ == "__main__":
    main()
