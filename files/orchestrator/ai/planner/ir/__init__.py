"""
ir — MEDUSA, the Gorgon procedure language: the typed program form the model emits
instead of English.

Named for one of the gorgons. The platform is Gorgon; this is one of its own, and a
program written in it is a `.med` file.

WHY THIS EXISTS. The planner used to understand goals by matching English — 33
hand-maintained vocabularies, `vms` in seven separate constants. A missing verb silently
dropped a whole capability. Measured: the ladder scored 7/10 on its own wording and 2/10
on paraphrases of the same capability, and a goal translator that aimed at "canonical
English" traded rungs rather than winning them, because English has no way to mark the
difference between "make sure X" and "do X". A typed program does.

WHAT IS WHERE — one concern per file, and the language itself is DATA:

    config/     the manifest — ops, resource KINDS, predicate shapes, every prompt string
    schema.py   the tool the model fills in, assembled from the manifest
    validate.py well-formed? grounded? (never "meaningful" — that is a human's job)
    render.py   the operator's SQL-shaped view, one direction
    execute.py  the visitor — one case per op; every effect still leaves through the gate
    derive.py   close an unmet predicate by COMPUTING the fix, where the model cannot

The test this structure exists to pass: adding a resource type is ONE ROW in
config/ir.defaults.json and zero language code. Same for a predicate. If something has
to be edited in Python to extend the language, it is in the wrong place.

There is no parser here. The model CALLS `emit_program` and the statements arrive as
validated JSON arguments; translation is schema validation, which the codebase already
performs on every tool call.
"""

from .config import (KINDS, LANGUAGE, LOOP_VAR, OPS, PREDICATES, SIGIL,
                     packages_for)
from .derive import derive
from .execute import Unsatisfied, run
from .render import render
from .schema import (emit_program_tool, statement_from, statement_tools,
                     system_prompt)
from .validate import coerce_body, kinds_used, validate

# The tool schema is built from the manifest at import time; call emit_program_tool()
# directly if a caller ever needs to rebuild it after overriding config at runtime.
EMIT_PROGRAM_TOOL = emit_program_tool()

__all__ = [
    "EMIT_PROGRAM_TOOL", "emit_program_tool", "system_prompt",
    "statement_tools", "statement_from",
    "validate", "coerce_body", "kinds_used",
    "render", "run", "Unsatisfied", "derive",
    "KINDS", "OPS", "PREDICATES", "SIGIL", "LOOP_VAR", "LANGUAGE", "packages_for",
]
