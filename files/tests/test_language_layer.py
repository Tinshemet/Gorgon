#!/usr/bin/env python3
"""
test_language_layer.py — the plain-text layer has ONE home for its words and a PINNED set of
callers.

WHY THIS EXISTS. Gorgon reads English by declaration (V2-LEDGER #12, 2026-08-22) and the English
lives in `orchestrator/languages/english/`. The chain is plain text -> computational model ->
code, and only the first link is language-dependent — which is only true if the language stays
IN its folder. Two ways it leaks, both measured on the day of the move:

  1. A closed class declared in a reader module instead of the codex (`scan.py` held 17 of
     them; `speech_act.py` 22). A second language would have to find them all. The codex is
     the one place; a module-level English word-collection anywhere else in the scaffold FAILS.
  2. A caller outside the folder reaching for the language's WORDS instead of its STATE
     (`door.py` imports `scan.ENUMERATORS` and `temporal.CLOCK`). Those exist today and are
     pinned below as decisions; a new one is a decision somebody records here, not a drift.

THREE PROPERTIES:
  A. THE CODEX IS THE ONLY HOME — read off the AST of every scaffold module: no module-level
     assignment whose value is a collection of >= 3 alphabetic string literals, except in
     `codex.py` and except the pinned non-language constants (check names, kinds, fixtures).
  B. THE CODEX IS A LEAF — it imports nothing from the scaffold or the planner. A language's
     words depend on nothing; everything depends on them.
  C. THE CALLERS ARE PINNED — every module outside `orchestrator/languages/` that imports from
     it is in the list below, with what it takes.

Run:  PYTHONPATH=. python3 -m pytest tests/test_language_layer.py -q
"""
import ast
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG = os.path.join(ROOT, "orchestrator", "languages", "english")
SEAM = os.path.join(LANG, "seam")
PKG = "orchestrator.languages.english"

# ── A: module-level constants that LOOK like closed classes but are the MODEL's words ──────
# (check names the gates own, speech-act kinds, in-module fixtures). Pinned, not inferred.
NOT_LANGUAGE = {
    # WORD_TYPES: what KIND of learned word an archive entry is (class · attribute · unit ·
    # value) — a fact about the STORE, the same in every language; not a word of English
    "archive.py":    {"WORD_TYPES"},
    "asking.py":     {"TAKES"},
    "effects.py":    {"CASES"},
    "gate3.py":      {"OWNS"},
    "gate4.py":      {"OWNS"},
    "gates12.py":    {"GATE1_OWNS", "GATE2_OWNS", "UNSETTLED_KIND"},
    "iso.py":        {"QUALIFIERS", "PLACED"},
    "linguistics.py": {"OWNS"},
    "pass1.py":      {"EXPECTED", "BUILDS"},
    "pass2.py":      {"WANT"},
    # _DETS is DEFINITE | INDEFINITE from the codex, composed at import — not a list of its own
    "values.py":     {"_DETS"},
}

# ── C: who calls the language from outside its folder, and for what ───────────────────────
# Production callers take the STATE (pipeline.run, mood_of) — and, today, three WORD leaks in
# door.py (ENUMERATORS, CLOCK, _index) recorded as a finding in languages/README.md §2.
PINNED_CALLERS = {
    "orchestrator/door.py",
    "orchestrator/ai/chat/shortcuts/plan.py",
    "orchestrator/ai/chat/shortcuts/words.py",
}
# The bench and the unit tests reach module internals by design; they are not production.
BENCH_PREFIXES = ("tests/",)


def _is_word(s: str) -> bool:
    return bool(s) and all(c.isalpha() or c in " '-–." for c in s)


def _word_collections(tree):
    """Module-level NAME = <collection of >=3 alphabetic strings> — the shape of a closed class."""
    found = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
        if not isinstance(tgt, ast.Name) or node.value is None:
            continue
        strs = [n.value for n in ast.walk(node.value)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        words = [s for s in strs if _is_word(s)]
        if len(words) >= 3 and tgt.id.isupper():
            found.append(tgt.id)
    return found


def test_codex_is_the_only_home():
    offenders = []
    for path in sorted(glob.glob(os.path.join(SEAM, "*.py"))):
        base = os.path.basename(path)
        if base == "codex.py":
            continue
        tree = ast.parse(open(path, encoding="utf-8").read())
        for name in _word_collections(tree):
            if name not in NOT_LANGUAGE.get(base, set()):
                offenders.append(f"{base}:{name}")
    assert not offenders, (
        "English closed classes outside the codex — move them to "
        "orchestrator/languages/english/codex.py or pin them in NOT_LANGUAGE with a reason:\n  "
        + "\n  ".join(offenders))


def test_codex_is_a_leaf():
    tree = ast.parse(open(os.path.join(LANG, "codex.py"), encoding="utf-8").read())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level or mod.startswith(("orchestrator", "planner", "engines", "executor")):
                bad.append(mod or "." * node.level)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith(("orchestrator", "planner", "engines", "executor")):
                    bad.append(a.name)
    assert not bad, f"the codex must import nothing from the project: {bad}"


def test_callers_are_pinned():
    callers = set()
    for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        rel = os.path.relpath(path, ROOT)
        if rel.startswith("orchestrator/languages/") or "__pycache__" in rel:
            continue
        src = open(path, encoding="utf-8", errors="replace").read()
        if PKG in src or "from .languages" in src or "from ..languages" in src:
            callers.add(rel)
    production = {c for c in callers if not c.startswith(BENCH_PREFIXES)}
    new = production - PINNED_CALLERS
    gone = PINNED_CALLERS - production
    assert not new, f"new caller(s) of the language layer — record the decision here: {sorted(new)}"
    assert not gone, f"pinned caller(s) no longer import the language layer — update the pin: {sorted(gone)}"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
