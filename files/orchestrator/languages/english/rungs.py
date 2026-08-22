"""rungs.py — THE 14 RUNGS, AS THIS LANGUAGE SAYS THEM.

Every language package carries `RUNGS: Dict[int, str]` — the complexity ladder's fourteen
requests written the way a native speaker would actually ask for them. **Not a translation of
the English**: the ladder's *meaning* per rung is fixed (tests/bench/rungs.py names the
reasoning load each one adds), the wording is the language's own.

`tests/bench/language_benchmark.py` reads these, runs them through this language's scaffold,
and grades the COMPUTATIONAL MODEL that comes out against the language-neutral answer key.
A language whose scaffold produces the correct model on the graded rungs is a candidate for
porting; one that cannot is not, whatever it does on single sentences.

For English the rungs ARE the scaffold's own rung corpus (`pass1.EXPECTED`), so there is one
source and this module only exposes it under the contract's name.
"""
from typing import Dict

from .seam.pass1 import EXPECTED

RUNGS: Dict[int, str] = {n: e.request for n, e in EXPECTED.items()}
