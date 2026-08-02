"""reference.py — the Medusa reference, WRITTEN OUT OF THE LANGUAGE ITSELF.

WHY IT IS GENERATED AND NOT TYPED. A hand-written syntax guide is a second description of
the grammar, and the day somebody adds an op or renames a keyword there are two answers to
"what can a program say" — with nothing to say which is current. This project has paid that
bill before: the 33 regex vocabularies [[gorgon-procedure-language]] was written to end, and
`clause_ledger._verbs()` reading the chat config rather than listing verbs again.

So every word here comes from `ir.defaults.json`: the ops and their fields, the predicates
and their comparators, the parameter types, and the printed keywords. Rename `ENSURE` in the
surface table and this file says `ENSURE`'s new name the next time it is written.

WHAT IS NOT DERIVED IS THE EXAMPLES, and that is deliberate rather than an omission. An
example is a JUDGEMENT about what a person needs to see first — which shape to reach for,
which mistake to not make — and no table holds that. They are written below, marked as
written, and every one of them is PARSED BY THE TEST SUITE so a stale example fails rather
than misleads.

WHERE IT GOES. Beside the procedures, in the folder the operator opens to read them —
`~/.gorgon/procedures/SYNTAX.md`. Not `.medusa`, because `Store.names()` lists every
`*.medusa` in that directory and a reference file would arrive in the library as a program.
"""
from typing import Any, Dict, List

from . import config


def _w(key: str) -> str:
    """A printed keyword, from the surface table — the same source the renderer prints."""
    return config.SURFACE.get(key, key.upper())


# ── the examples, WRITTEN, and every one parsed by tests/test_reference.py ────────────────
#
# ORDERED BY WHAT A PERSON REACHES FOR FIRST, not by which op is most interesting. The first
# is the two-line shape the operator settled on 2026-08-02: a creation and what it produced.
_EXAMPLES: List[Dict[str, str]] = [
    {"title": "make something, and say what you made",
     "why": "`NEW` says a new thing comes into being; `CALL create_vm(…)` says WHICH "
            "constructor makes it; `STORE x =` binds it so later lines can refer to it. "
            "A creation re-reads the world and files a failure if what was asked for is "
            "not there, so it needs no ENSURE after it.",
     "code": "PROCEDURE build_box() {\n"
             "  STORE box1 = NEW CALL create_vm(os_type: linux, name: box1);\n"
             "  PUBLISH(box1);\n"
             "}"},
    {"title": "take an argument, so it is a library entry and not a macro",
     "why": "A procedure whose values are all literals can only ever cover the one goal it "
            "was written from. A parameter is what lets the writer REACH FOR it: `$box` "
            "matches whatever the goal has in that slot.",
     "code": "PROCEDURE build_named(STRING box) {\n"
             "  STORE vm1 = NEW CALL create_vm(os_type: linux, name: $box);\n"
             "  ENSURE COUNT(SELECT vm WHERE name = '$box') = 1;\n"
             "  PUBLISH(vm1);\n"
             "}"},
    {"title": "check something, and make something so",
     "why": "ENSURE asks *is this so, here?* and stops the program if not. ACHIEVE says "
            "*make it so* — it computes the difference and closes it, so the run cannot "
            "pass that line until it holds. Check versus make.",
     "code": "PROCEDURE labelled() {\n"
             "  ACHIEVE COUNT(SELECT network WHERE name = 'lab') = 1;\n"
             "  CALL add_vm_to_network(net_name: lab, vm_name: box1);\n"
             "  ENSURE COUNT(SELECT vm WHERE network = 'lab') >= 1;\n"
             "}"},
    {"title": "read the world before acting on it",
     "why": "FETCH binds what is already there, so one program is correct whatever the lab "
            "holds. `COUNT` binds a number; a plain SELECT binds the matching names as a set.",
     "code": "PROCEDURE top_up() {\n"
             "  STORE running = FETCH COUNT(SELECT vm WHERE status = 'running');\n"
             "  IF COUNT(SELECT vm WHERE status = 'running') = 0 {\n"
             "    CALL launch_vm(name: box1, display: 'none');\n"
             "  }\n"
             "}"},
    {"title": "do the same thing to every member of a set",
     "why": "FOREACH names the set with SELECT (a query over the world now) or with IN (a "
            "set you bound, or a literal list). Inside the body, $item is the current member.",
     "code": "PROCEDURE stop_all() {\n"
             "  FOREACH $item IN SELECT vm WHERE status = 'running' {\n"
             "    CALL stop_vm(name: $item);\n"
             "  }\n"
             "  ENSURE COUNT(SELECT vm WHERE status = 'running') = 0;\n"
             "}"},
    {"title": "a routine — a procedure the clock calls",
     "why": "A routine is not a second kind of thing. It is a procedure carrying EVERY in "
            "its header, which is the one fact no statement in the body could state. WHEN "
            "makes it a trigger instead: the WORLD calls it rather than the clock.",
     "code": "PROCEDURE nightly() EVERY 24h {\n"
             "  FOREACH $item IN SELECT vm WHERE label = 'prod' {\n"
             "    CALL snapshot_create(name: $item, snap_name: nightly);\n"
             "  }\n"
             "}"},
]


def _ops_section() -> List[str]:
    out = ["## The statements", "",
           "Every op the language has, with the fields it takes. `required` is what a "
           "statement of that kind cannot be written without.", ""]
    for op in sorted(config.OPS):
        spec = config.OPS[op] or {}
        word = _w(op)
        req = ", ".join(spec.get("required") or ()) or "—"
        fields = ", ".join(spec.get("fields") or ()) or "—"
        acts = "  ·  **acts on the world**" if spec.get("acts") else ""
        out += [f"### `{word}`{acts}", "",
                f"- required: `{req}`",
                f"- fields: `{fields}`"]
        for pair in spec.get("one_of") or ():
            out.append(f"- exactly one of: `{'` or `'.join(pair)}`")
        doc = (spec.get("doc") or "").strip()
        if doc:
            out += ["", doc]
        out.append("")
    return out


def _predicates_section() -> List[str]:
    out = ["## The checks", "",
           "What an `ENSURE`, an `ACHIEVE`, an `IF` or a trigger's `WHEN` can ask. "
           "`source` says where the answer comes from — the registry knows what EXISTS, the "
           "findings know what was OBSERVED, and the two are different questions.", ""]
    for name in sorted(config.PREDICATES):
        spec = config.PREDICATES[name] or {}
        comps = spec.get("comparators") or {}
        shown = ", ".join(f"`{v}`" for v in comps.values()) or "—"
        out += [f"### `{name.upper()}`", "",
                f"- reads: {spec.get('source', '—')}",
                f"- compares with: {shown}"]
        doc = (spec.get("doc") or "").strip()
        if doc:
            out += ["", doc]
        if spec.get("derivable") is False:
            out += ["", f"**An `{_w('achieve')}` cannot close this one.** "
                        f"{(spec.get('_derivable_doc') or '').strip()}"]
        out.append("")
    return out


def _types_section() -> List[str]:
    out = ["## Parameter types", "",
           "What a `PROCEDURE`'s signature may declare.", "",
           "| written | means |", "| --- | --- |"]
    for name in sorted(config.PARAM_TYPES):
        spec = config.PARAM_TYPES[name] or {}
        out.append(f"| `{spec.get('sql', name.upper())}` | {spec.get('doc', '')} |")
    out.append("")
    return out


def _keywords_section() -> List[str]:
    plain = {k: v for k, v in config.SURFACE.items()
             if isinstance(v, str) and not k.startswith("_")}
    words = sorted(set(plain.values()))
    combinators = sorted((config.SURFACE.get("combinators") or {}).values())
    return ["## Every keyword", "",
            "  ".join(f"`{w}`" for w in words + combinators), ""]


def _examples_section() -> List[str]:
    out = ["## Worked examples", ""]
    for ex in _EXAMPLES:
        out += [f"### {ex['title']}", "", "```", ex["code"], "```", "", ex["why"], ""]
    return out


def render_reference() -> str:
    """The whole reference, as Markdown."""
    lang = config.LANGUAGE or {}
    head = [
        f"# {str(lang.get('name', 'Medusa')).title()}"
        f" — the language, and how to write one",
        "",
        "**This file is GENERATED from the language definition itself.** Editing it changes "
        "nothing; the next save overwrites it. Every op, check, type and keyword below is "
        "read out of `ir.defaults.json`, so it cannot describe a grammar the parser does "
        "not have.",
        "",
        f"A program is a `{lang.get('extension', '.medusa')}` file in this folder. **The "
        f"text IS the program** — there is nothing stored beside it and no compiled form "
        f"underneath, so an edit here is an edit to what runs. Save one and it is read "
        f"back and checked immediately; ask for the result with `gorgon procedures verify`.",
        "",
        "```",
        f"{_w('procedure')} name(TYPE arg) [{_w('every')} 1h | {_w('when')} <check>] {{",
        "  … statements …",
        "}}".replace("}}", "}"),
        "```",
        "",
        f"A value beginning `{config.SIGIL}` is a reference — to a parameter, or to something "
        f"an earlier line bound with `{_w('bind')}`.",
        "",
    ]
    return "\n".join(head + _examples_section() + _ops_section()
                     + _predicates_section() + _types_section()
                     + _keywords_section()).rstrip() + "\n"


def examples() -> List[Dict[str, str]]:
    """The worked examples, so a test can parse every one of them."""
    return list(_EXAMPLES)
