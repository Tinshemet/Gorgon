"""gates/ — the four legality gates over a reading.

    1  COMPLETENESS  is the pattern WHOLE?      a hole, a drop or a mutation is illegal
    2  TRUTH         does it REFER?             naming what cannot exist is illegal
    3  REASONING     is it COHERENT?            unsatisfiable / vacuous / contradictory
    4  VIABILITY     does the WHOLE hold?       legal parts, illegal composition

THE OPERATOR'S FRAME, 2026-08-07, and it is what makes these buildable at all: *"the AI's job
is to STANDARDISE the human's response to a measurable pattern, and the gates catch IF THE
PATTERN THE AI TRANSLATED IS LEGAL. that's all."*

**A GATE IS A TYPE CHECKER, NOT AN ORACLE.** It never asks "is this what the operator meant?"
— that needs a world oracle and is where every previous design collapsed into a heuristic. It
asks "is this pattern legal?", which is decidable from the request, the manifest and the world.

**AND THE RUNGS ARE SAMPLES OF HOW PEOPLE TALK, NEVER THE RULE.** *"we don't flag the rung for
what they are, we use them as examples for user patterns in nature."* A check written to
recognise rung 8 is a hard-coded answer wearing a gate's name. If a rule stops working when
the wording changes, it was never a gate — which is why the PARAPHRASE arm is the honest
measure and the literal arm flatters us.
"""
