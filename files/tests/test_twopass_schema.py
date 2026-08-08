"""test_twopass_schema.py — pass one's declaration schema.

Item 2 of the two-pass plan. The schema makes no model call, so everything here is
deterministic and the suite can own it.

WHAT THIS PINS, in order of what matters:

    1. THE TYPE ORDER, LITERALLY. Item 1 measured that moving ONE entry of an enum from the
       front to the back doubled exact matches and removed every spurious step, with no change
       to prompt, schema or model. Order is a HIDDEN PARAMETER, so it is pinned here BY VALUE:
       adding a kind to the manifest must fail this test rather than silently move behaviour.
    2. `settled` is COMPUTED and cannot be supplied. It is the field the writer has never been
       given, and a caller that could pass it in would eventually pass it wrong.
    3. an OBSERVED attribute is filterable and never settable — the asymmetry rung 11 lives on.
    4. every schema is CLOSED, with refusal available and ordered safely.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.bench.formula.legal import Board
from tests.bench.twopass import schema as S

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


# ── 1 · the order, pinned by value ────────────────────────────────────────────────────
def test_the_type_list_is_pinned_and_is_not_alphabetical():
    print("\n[order] the enum order is a hidden parameter, so it is pinned by value")
    got = S.types_offered()
    check("every kind appears with its set form",
          all(f"{k}{S.SET_SUFFIX}" in got for k in Board().kinds))
    check("and each kind is immediately followed by its own set",
          all(got[i + 1] == got[i] + S.SET_SUFFIX for i in range(0, len(got), 2)))

    # THE PIN. If the manifest gains a kind this fails, which is the entire point — the
    # alternative is behaviour moving with no visible cause.
    expected = ["vm", "vm_set", "network", "network_set", "file", "file_set",
                "profile", "profile_set", "snapshot", "snapshot_set",
                "template", "template_set"]
    check(f"the order is exactly the manifest's own, not sorted (got {got})", got == expected)
    check("and it is NOT alphabetical — sorted() would reshuffle on any new kind",
          got != sorted(got))


# ── 2 · settled is computed, never supplied ───────────────────────────────────────────
def test_settled_is_computed_from_the_manifest_and_cannot_be_passed_in():
    print("\n[settled] a set defined by something the world must be ASKED is residual")
    board = Board()
    observed = board.observable("vm")
    check(f"the manifest declares an observed attribute for vm ({observed})", bool(observed))

    plain = S.settled_of("vm", {"status": "running"}, board)
    asked = S.settled_of("vm", {observed[0]: False}, board)
    check("a filter on a STORED attribute settles at plan time", plain == S.PLAN_TIME)
    check("a filter on an OBSERVED attribute settles at RUN time", asked == S.RUN_TIME)
    check("and an unfiltered set settles at plan time",
          S.settled_of("vm", {}, board) == S.PLAN_TIME)

    # `declare_from` takes no `settled` argument at all — the strongest form of "cannot".
    row = S.declare_from("unresponsive", "vm_set", {observed[0]: False}, S.EXISTING, board)
    check("declare_from derives it", row.settled == S.RUN_TIME)
    check("and exposes it as `residual`, which is what the writer needs", row.residual)
    check("a plain set is not residual",
          not S.declare_from("fleet", "vm_set", {}, S.EXISTING, board).residual)
    check("`settled` is not a parameter of declare_from",
          "settled" not in S.declare_from.__code__.co_varnames[
              :S.declare_from.__code__.co_argcount])


# ── 3 · observed is filterable, never settable ────────────────────────────────────────
def test_an_observed_attribute_can_be_selected_on_but_never_demanded():
    print("\n[asymmetry] you may select the machines that did not answer; you may not order "
          "a machine to answer")
    board = Board()
    observed = set(board.observable("vm"))
    check("observed attributes ARE offered as conditions",
          observed <= set(S.attributes_for("vm_set", board)))
    check("and are NOT offered as things that can be set",
          not (observed & set(board.settable("vm"))))
    check("the set form and the plain form offer the same conditions",
          S.attributes_for("vm", board) == S.attributes_for("vm_set", board))
    check("an undeclared kind offers nothing rather than raising",
          S.attributes_for("wombat", board) == [])


# ── 4 · the schemas are closed, and refusal leads ─────────────────────────────────────
def test_every_schema_is_closed_and_the_safe_answer_comes_first():
    print("\n[schemas] closed enums, required fields, and the safe option leading")
    types = S.type_schema()["properties"]["answer"]
    check("the type question is a closed enum", "enum" in types)
    check("and it offers the pinned list", types["enum"] == S.types_offered())

    ex = S.existence_schema()["properties"]["answer"]
    check("existence is a two-option enum", len(ex["enum"]) == 2)
    check("and EXISTING comes first — every measured error was toward NEW, so a relapse "
          "into first-member picking shows up as over-refusal, not over-creation",
          ex["enum"][0] == S.EXISTING)

    where = S.where_schema("vm_set")["properties"]["answer"]
    attrs = where["items"]["properties"]["attribute"]
    check("the condition attribute is a closed enum", "enum" in attrs)
    check("and it cannot carry free text", attrs.get("type") == "string")

    for name, built in (("names", S.names_schema()), ("type", S.type_schema()),
                        ("where", S.where_schema("vm_set")),
                        ("existence", S.existence_schema())):
        check(f"the {name} schema requires an answer rather than permitting {{}}",
              built.get("required") == ["answer"])
        check(f"and the {name} schema forbids extra properties",
              built.get("additionalProperties") is False)


# ── 5 · the row, and the table pass two is shown ──────────────────────────────────────
def test_a_declared_row_knows_what_it_is():
    print("\n[row] kind, set-ness and residual all fall out of the two stated fields")
    board = Board()
    one = S.declare_from("web", "vm", {"name": "web"}, S.NEW, board)
    many = S.declare_from("fleet", "vm_set", {}, S.EXISTING, board)
    check("a plain kind is not a set", not one.is_set and one.kind == "vm")
    check("a set knows its kind", many.is_set and many.kind == "vm")
    check("an unrecognised existence falls back to the SAFE answer",
          S.declare_from("x", "vm", {}, "nonsense", board).existence == S.EXISTING)


def test_rung_11s_symbol_table_is_expressible_and_marks_its_residual():
    print("\n[rung 11] the table item 1 proved the model can then act on")
    board = Board()
    rows = [S.declare_from("fleet", "vm_set", {}, S.EXISTING, board),
            S.declare_from("unresponsive", "vm_set", {"alive": False}, S.EXISTING, board)]
    check("both rows are sets over vm", all(r.is_set and r.kind == "vm" for r in rows))
    check("exactly one is residual", [r.residual for r in rows] == [False, True])

    table = S.render(rows)
    check("the rendered table names both", "fleet" in table and "unresponsive" in table)
    check("and it SHOWS the binding time, which is the fact the writer has never been given",
          S.RUN_TIME in table)
    check("an empty table renders rather than crashing", S.render([]) != "")


def test_the_questions_format_and_carry_the_gloss():
    print("\n[questions] they are declared here and used in item 3 — so they are exercised "
          "here, or a bad placeholder waits until then to surface")
    try:
        typed = S.TYPE_Q.format(name="fleet", suffix=S.SET_SUFFIX)
        wheres = S.WHERE_Q.format(name="fleet")
        exists = S.EXISTENCE_Q.format(name="fleet", new=S.NEW, existing=S.EXISTING)
        formatted = True
    except (KeyError, IndexError) as exc:
        typed = wheres = exists = ""
        formatted = False
        print(f"       {type(exc).__name__}: {exc}")
    check("every question formats with its placeholders", formatted)
    check("the type question names the thing and the set suffix",
          "fleet" in typed and S.SET_SUFFIX in typed)
    check("the where question offers the empty-list escape", "empty list" in wheres)

    # THE GLOSS IS THE MEASURED PART: it lifted a weak wording from 54% to 77% and collapsed
    # the spread between synonym pairs from 31 points to 8. Losing it would cost silently.
    check("the existence question GLOSSES both options rather than naming them bare",
          all(w in exists for w in ("created", "built", "provisioned",
                                    "previously created", "reused")))
    check("and it anchors the judgement to THIS thing, not the sentence",
          "THIS thing" in exists)
    check("the names question asks for a GROUP to be named too — the whole point of pass one",
          "group" in S.NAMES_Q.lower())


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "two-pass schema")


if __name__ == "__main__":
    sys.exit(main())
