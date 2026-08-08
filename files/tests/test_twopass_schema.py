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
        typed = S.TYPE_Q.format(name="fleet", suffix=S.SET_SUFFIX,
                                nouns=S.nouns_offered())
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
    # WITHOUT THE MANIFEST'S SYNONYMS THE QUESTION IS UNANSWERABLE: the enum says `vm` and the
    # request says "machines". Measured — every wording of rung 14 failed until these appeared.
    check("and it carries the manifest's own synonyms",
          "machine" in typed and "restore point" in typed)
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


def test_repeated_mentions_of_one_object_are_merged_by_computation():
    print("\n[coreference] two rows of one kind whose KEY holds the same value ARE the same "
          "thing — provable from the manifest, so it is computed and never asked")
    board = Board()

    # THE ACTUAL ROWS the model produced for rung 3, transcribed from the run. `web` is
    # mentioned in both clauses and came back as separate declarations, alongside a third
    # from the chunking. This is the operator's observation, pinned against real output.
    observed = [("a network", "network_set", {"members": "web"}),
                ("called lab", "network", {"net_name": "lab"}),
                ("a vm", "vm_set", {"name": "web", "network": "lab"}),
                ("named web", "vm", {"name": "web", "network": "lab"}),
                ("web", "vm", {"name": "web", "network": "lab"}),
                ("lab", "network", {"net_name": "lab"})]
    rows = [S.declare_from(n, t, w, S.EXISTING, board) for n, t, w in observed]
    merged = S.merge(rows, board)
    names = [r.name for r in merged]

    check(f"six rows collapse to four (got {len(merged)})", len(merged) == 4)
    check("the two `lab` mentions become one object", names.count("lab") == 0
          and any("lab" in r.references for r in merged))
    check("the two `web` mentions become one object", names.count("web") == 0
          and any("web" in r.references for r in merged))
    # THE FIRST MENTION DECLARES and later ones become its references — the operator's rule.
    # It carries the ordering, which a symmetric merge throws away.
    check("the FIRST mention is the declaration, not the shortest name",
          "called lab" in names and "named web" in names)
    check("and the later mentions survive AS references rather than being dropped",
          sorted(r for row in merged for r in row.references) == ["lab", "web"])

    # Conservative on purpose: a row with no key value cannot be PROVEN identical to anything.
    check("a row with no key value is left alone rather than guessed at",
          "a network" in names)
    check("and a set is never merged into an individual", "a vm" in names)

    # merging keeps every condition from both rows
    both = S.merge([S.declare_from("web", "vm", {"name": "web"}, S.EXISTING, board),
                    S.declare_from("web", "vm", {"name": "web", "network": "lab"},
                                   S.EXISTING, board)], board)
    check("the merged row carries conditions from both mentions",
          len(both) == 1 and both[0].where == {"name": "web", "network": "lab"})
    check("merging nothing returns nothing", S.merge([], board) == [])


def test_a_bare_pronoun_folds_onto_what_it_refers_to():
    print("\n[anaphora] 'create X then put it in Y' mentions X twice — the second time as "
          "'it'. Pronouns are a closed set, so the fold is computed, not asked")
    board = Board()

    # RUNG 2, EXACTLY as the model produced it: `it` came back as an object of its own.
    rows = [S.declare_from("vm", "vm_set", {}, S.NEW, board),
            S.declare_from("beta", "vm_set", {}, S.NEW, board),
            S.declare_from("it", "vm_set", {}, S.EXISTING, board)]
    merged = S.merge(rows, board)
    check(f"'it' stops being an object of its own (got {[r.name for r in merged]})",
          "it" not in [r.name for r in merged])
    check("and becomes a reference on the thing it refers to",
          any("it" in r.references for r in merged))
    check("which is the MOST RECENT compatible declaration, not the first",
          [r.name for r in merged if r.references] == ["beta"])

    # ⇒ THE GUARD THAT MATTERS MORE THAN THE FOLD. A pronoun with a RESTRICTION is a
    #   different object. Folding "the ones that do not answer" into "every vm" would merge a
    #   subset into its superset and destroy the one distinction rung 11 exists to test.
    pair = S.merge([S.declare_from("every vm", "vm_set", {}, S.EXISTING, board),
                    S.declare_from("the ones that do not answer", "vm_set",
                                   {"alive": False}, S.EXISTING, board)], board)
    check(f"a RESTRICTED description never folds into its superset (got {len(pair)})",
          len(pair) == 2)
    check("and the subset keeps its run-time marking",
          [r.residual for r in pair] == [False, True])
    # ⇒ THE REGRESSION THIS FILE EXISTS TO PREVENT. The naming question chunks "the ones that
    #   do not answer" down to the bare token `ones`, and `ones` used to be listed as a
    #   pronoun — so the fold merged it into `vm` and rung 11's subset vanished. Two correct
    #   mechanisms compounding into one wrong answer.
    r11 = "ping every vm and stop the ones that do not answer"
    chunked = [S.declare_from("ping", "vm_set", {}, S.NEW, board),
               S.declare_from("vm", "vm_set", {}, S.EXISTING, board),
               S.declare_from("ones", "vm_set", {}, S.EXISTING, board)]
    kept = S.merge(chunked, board, r11)
    check(f"a chunked restricted description is NOT folded away (got {len(kept)})",
          len(kept) == 3 and "ones" in [r.name for r in kept])
    check("because the REQUEST is consulted for a restrictor the chunker stripped",
          not S._is_bare_pronoun("ones", r11))
    check("and the same word with nothing after it would still fold",
          S._is_bare_pronoun("them", "stop them"))

    check("a pronoun with nothing before it is left alone rather than dropped",
          [r.name for r in S.merge([S.declare_from("it", "vm", {}, S.NEW, board)],
                                   board)] == ["it"])


def test_a_chunked_name_is_repaired_from_the_request():
    print("\n[expansion] the restriction is still in the request, so recover it rather than "
          "re-asking — measured: 'ones' types WRONG and 'the ones that do not answer' types RIGHT")
    r11 = "ping every vm and stop the ones that do not answer"
    check("a chunked restricted description is grown back",
          S.expand("ones", r11) == "the ones that do not answer")
    check("a determiner is picked up on the left",
          S.expand("vm", r11) == "every vm")
    check("and it STOPS at the clause boundary rather than swallowing the sentence",
          "ping" not in S.expand("vm", r11))
    check("a digit quantifier counts as a determiner",
          S.expand("vms", "create 5 vms, put them all in a network") == "5 vms")
    check("a word quantifier does too",
          S.expand("machines", "make sure there are exactly two machines left") == "two machines")
    check("nothing is added where no restrictor follows",
          S.expand("web", "create a vm named web") == "web")
    check("a name that is not in the request is returned untouched",
          S.expand("invented", r11) == "invented")
    check("and empty input does not raise", S.expand("", r11) == "" and S.expand("x", "") == "x")


def test_no_question_quotes_a_request_it_will_be_asked_about():
    print("\n[leakage] a prompt that illustrates itself with a request's own words gets the "
          "EXAMPLE back as the answer")
    from tests.bench.rungs import RUNGS

    questions = {name: getattr(S, name) for name in dir(S)
                 if name.endswith("_Q") and isinstance(getattr(S, name), str)}
    check(f"there are questions to check ({sorted(questions)})", len(questions) >= 4)

    # Any run of 4+ words shared between a question and a rung is a phrase, not a coincidence.
    def phrases(text: str, n: int = 4):
        words = [w.strip(".,'\"—-").lower() for w in text.split() if w.strip(".,'\"—-")]
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}

    leaks = []
    for rung in RUNGS:
        for wording in filter(None, (rung.goal, rung.paraphrase)):
            said = phrases(wording)
            for name, question in questions.items():
                shared = said & phrases(question)
                if shared:
                    leaks.append(f"{name} quotes rung {rung.n}: {sorted(shared)[0]!r}")

    # MEASURED: NAMES_Q once contained rung 11's own wording, and the model returned that
    # phrase for a request about CLONING. The example became the answer, rung 11 was handed
    # its own solution, and a whole measurement was void before anyone noticed.
    check(f"no question quotes any rung, in either wording (found {leaks})", not leaks)


# ── 7 · gates 1 and 2, on declarations ────────────────────────────────────────────────
def test_gate_1_asks_about_what_the_request_never_said():
    print("\n[gate 1] every NAME and every VALUE must trace to the request; the attribute "
          "came from a closed enum and could not have been invented")
    from tests.bench.twopass import gates12 as G
    board = Board()
    r = "ping every vm and stop the ones that do not answer"

    clean = [S.declare_from("every vm", "vm_set", {}, S.EXISTING, board),
             S.declare_from("the ones that do not answer", "vm_set", {"alive": False},
                            S.EXISTING, board)]
    check(f"a correct reading is NOT accused (got {G.gate1(clean, r)})", not G.gate1(clean, r))
    check("a boolean value is not treated as a quotation",
          not any(f.kind == "invented-value" for f in G.gate1(clean, r)))

    made_up = [S.declare_from("quarantine", "vm_set", {"label": "urgent"}, S.NEW, board)]
    found = G.gate1(made_up, r)
    check(f"an invented NAME is caught (got {found})",
          any(f.kind == "invented" for f in found))
    check("and an invented VALUE is caught separately",
          any(f.kind == "invented-value" for f in found))
    check("and it ASKS rather than repairing — nothing is changed",
          all("?" in f.says or "did you" in f.says for f in found))


def test_gate_2_asks_what_the_world_cannot_hold():
    print("\n[gate 2] legality against the manifest — no lab required")
    from tests.bench.twopass import gates12 as G
    board = Board()

    check("a legal declaration passes",
          not G.gate2([S.declare_from("stopped ones", "vm_set", {"status": "stopped"},
                                      S.EXISTING, board)], board))
    check("an illegal VALUE is caught against the manifest's closed set",
          any(f.kind == "illegal-value" for f in G.gate2(
              [S.declare_from("x", "vm_set", {"status": "powered on"}, S.EXISTING, board)],
              board)))
    check("an attribute the kind does not have is caught",
          any(f.kind == "no-such-attribute" for f in G.gate2(
              [S.declare_from("x", "network", {"alive": True}, S.EXISTING, board)], board)))

    # ⇒ THE ONE THAT MATTERS: a set decided by asking the machines cannot be CREATED.
    residual_new = [S.declare_from("the ones that do not answer", "vm_set", {"alive": False},
                                   S.NEW, board)]
    check("a probe-defined set declared NEW is refused — you can only go and look",
          any(f.kind == "cannot-be-made" for f in G.gate2(residual_new, board)))
    check("and the same set declared EXISTING is fine",
          not G.gate2([S.declare_from("the ones that do not answer", "vm_set",
                                      {"alive": False}, S.EXISTING, board)], board))


def test_neither_gate_repairs_anything():
    print("\n[gates] they ask; they never decide for the operator")
    from tests.bench.twopass import gates12 as G
    board = Board()
    rows = [S.declare_from("quarantine", "vm_set", {"status": "powered on"}, S.NEW, board)]
    before = [(r.name, dict(r.where), r.existence) for r in rows]
    out = G.report(rows, "stop the machines", board)
    after = [(r.name, dict(r.where), r.existence) for r in rows]
    check("the declarations are untouched by being judged", before == after)
    check("findings arrive as questions", len(out["asks"]) == len(out["findings"]))
    check("and an illegal table is marked illegal", out["legal"] is False)
    check("a clean table is marked legal",
          G.report([S.declare_from("every vm", "vm_set", {}, S.EXISTING, board)],
                   "ping every vm", board)["legal"] is True)
    check("the world arm is skipped when there is no world",
          G.conflicts(rows, None, board) == [])


# ── 8 · anchor and scan ───────────────────────────────────────────────────────────────
def test_the_code_reads_the_phrase_the_model_only_points_at():
    print("\n[scan] the model points at an anchor; the enumerator, comparator, kind and "
          "modifiers are READ off the request")
    from tests.bench.twopass.scan import scan
    board = Board()

    got = scan("alpha", "create a vm named alpha", board)
    check(f"a bare anchor recovers its whole phrase (got {got.span!r})",
          got.span == "a vm named alpha")
    check("the enumerator becomes a count", got.count == 1)
    check("the noun becomes the kind, from the manifest", got.kind == "vm")
    check("and what is left over is the modifier", got.modifiers == "named alpha")

    # THE COUNT WAS NEVER ASKED FOR BY PASS 1 AT ALL, so half the rungs could not be
    # expressed however good the other answers were.
    check("a digit enumerator counts", scan("vms", "create 5 vms, put them all in a network",
                                            board).count == 5)
    check("and a quantifier reads as 'all'",
          scan("vm", "ping every vm and stop the rest", board).count == "all")

    # ⇒ THE COMPARATOR IS IN THE ENUMERATOR REGION, and it is the (eq, 3) a program needs.
    exactly = scan("machines", "make sure there are exactly two machines left", board)
    check("a one-word comparator is read", (exactly.comparator, exactly.count) == ("eq", 2))
    atmost = scan("vms", "there should be at most three vms with the test label", board)
    check("and a two-word one", (atmost.comparator, atmost.count) == ("max", 3))
    check("comparator words do not leak into the modifiers",
          "most" not in atmost.modifiers)

    # A SPAN MAY NEVER CROSS A CLAUSE BOUNDARY. Without this, "create 5 vms, put them all in
    # a network" scanned as a single phrase.
    check("a comma stops the scan",
          scan("vms", "create 5 vms, put them all in a network", board).span == "5 vms")

    # ⇒ THE KIND IS TAKEN AT OR BEFORE THE ANCHOR, NEVER AFTER. A noun precedes its modifiers,
    #   so reaching rightward answers with the next clause's noun.
    check("a bare name gets NO kind rather than the wrong one — the lab decides",
          scan("golden", "clone golden into 3 new vms and launch all of them",
               board).kind is None)
    check("a two-word noun is matched before a one-word one",
          scan("restore point", "make a restore point for each machine", board).kind
          == "snapshot")
    check("an anchor that is not in the request returns nothing",
          scan("wombat", "ping every vm", board) is None)

    # ⇒ EVERY OCCURRENCE, AND THE FIRST ONE DECLARES. `scan` alone saw only the first, so a
    #   reference was invisible — the operator's ordering rule applied to spans.
    from tests.bench.twopass.scan import scan_all
    both = scan_all("web", "create a network called lab and a vm named web, "
                           "then put web on lab", board)
    check(f"a name mentioned twice is scanned twice (got {len(both)})", len(both) == 2)
    check("the first occurrence carries the phrase that declares it",
          both[0].span == "a vm named web" and both[0].kind == "vm")

    # COLLISION IS THE FOLD SIGNAL, AND IT NEEDS NO KEY ATTRIBUTE.
    r3 = "create a network called lab and a vm named web, then put web on lab"
    check("two anchors on one phrase collide — provably the same object",
          scan("lab", r3, board).collides(scan("network", r3, board)))
    check("and two anchors on different phrases do not",
          not scan("lab", r3, board).collides(scan("web", r3, board)))
    # ⇒ THE TRAP: in "then put web on lab" BOTH references scan to the same clause, so they
    #   collide while being different objects. Compare FIRST occurrences only.
    check("references to different things share a clause and would falsely collide",
          scan_all("web", r3, board)[1].collides(scan_all("lab", r3, board)[1]))


def test_a_possessive_is_not_a_plural():
    print("\n[set-ness] 'ones' is a set; \"one's\" is one that is — the apostrophe decides")
    from tests.bench.twopass.pass1 import _is_group, _plural, _possessive

    class Span:
        def __init__(self, span, count=None):
            self.span, self.count = span, count

    check("a plural pronoun makes a group", _is_group(Span("the ones that do not answer")))
    # ⇒ WITHOUT THIS, "the machine's network" WAS DECLARED A GROUP OF MACHINES. Every word
    #   ending in s counted as plural, and a possessive ends in s.
    check("a possessive does NOT", not _is_group(Span("the machine's network")))
    check("nor does a possessive pronoun", not _is_group(Span("one's own network")))
    check("a plural noun still does", _is_group(Span("three machines")))
    check("and a singular phrase does not", not _is_group(Span("a vm named alpha")))
    check("the apostrophe is what is being read", _possessive("machine's")
          and not _possessive("machines"))
    check("and short words are never plurals", not _plural("its") and not _plural("was"))


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "two-pass schema")


if __name__ == "__main__":
    sys.exit(main())
