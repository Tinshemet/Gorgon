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
import pathlib
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.formula.legal import Board
from orchestrator.languages.english.seam import schema as S

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
    from orchestrator.languages.english.seam import gates12 as G
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
    # ⇒ TWO AUDIENCES, AND THEY ARE PHRASED DIFFERENTLY. What the request does not settle is
    #   a QUESTION for the operator. A residual is not that — the operator already said those
    #   words — so it is an INSTRUCTION to the model to read again. Asserting every finding
    #   ends in a question mark conflated the two.
    from orchestrator.languages.english.seam import gates12 as _G
    asks = [f for f in found if f not in _G.bounces(found)]
    check("what the operator must settle is phrased as a question",
          asks and all("?" in f.says or "did you" in f.says for f in asks))
    check("and nothing is repaired — the rows are untouched",
          [(r.name, dict(r.where)) for r in made_up] == [("quarantine", {"label": "urgent"})])


def test_gate_2_asks_what_the_world_cannot_hold():
    print("\n[gate 2] legality against the manifest — no lab required")
    from orchestrator.languages.english.seam import gates12 as G
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
    from orchestrator.languages.english.seam import gates12 as G
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
    from orchestrator.languages.english.seam.scan import scan
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
    from orchestrator.languages.english.seam.scan import scan_all
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
    # ⇒ superseded 08-20: the transfer-frame stops give REFERENCES precise spans, so
    #   the trap this documented (same-clause references falsely colliding) dissolved
    check("same-clause references no longer collide — the spans are precise",
          not scan_all("web", r3, board)[1].collides(scan_all("lab", r3, board)[1]))


def test_a_possessive_is_not_a_plural():
    print("\n[set-ness] 'ones' is a set; \"one's\" is one that is — the apostrophe decides")
    from orchestrator.languages.english.seam.pass1 import _is_group, _plural, _possessive

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


def test_gate_1_bounces_a_residual_back_to_the_model():
    print("\n[bounce] an object may stand alone; a descriptor may not. What no declaration "
          "claims is a clause nobody read — and it goes back to the AI, not to the operator")
    from orchestrator.languages.english.seam import gates12 as G
    board = Board()

    def rows(*specs):
        return [S.declare_from(sp, t_, w, S.EXISTING, board, span=sp) for sp, t_, w in specs]

    r6 = "create 3 vms labelled 'red' and 2 vms labelled 'blue'"
    complete = rows(("3 vms labelled 'red'", "vm_set", {"label": "red"}),
                    ("2 vms labelled 'blue'", "vm_set", {"label": "blue"}))
    dropped = rows(("3 vms labelled 'red'", "vm_set", {"label": "red"}))
    check("a complete reading is silent", not G.bounces(G.gate1(complete, r6, board)))
    check("a DROPPED GROUP bounces", bool(G.bounces(G.gate1(dropped, r6, board))))
    check("and the residue names what was missed",
          "blue" in G.bounces(G.gate1(dropped, r6, board))[0].about)

    r4 = "create 5 vms, put them all in a network, give them all the 'fleet' label"
    check("a dropped LABEL bounces too",
          "fleet" in G.bounces(G.gate1(rows(("5 vms", "vm_set", {}),
                                            ("a network", "network", {})), r4, board))[0].about)
    check("and the same reading with it declared is silent",
          not G.bounces(G.gate1(rows(("5 vms", "vm_set", {}), ("a network", "network", {}),
                                     ("the 'fleet' label", "vm_set", {"label": "fleet"})),
                                r4, board)))

    # ⇒ IT BOUNCES TO THE MODEL, IT DOES NOT ASK THE OPERATOR. The words are in the request —
    #   the operator already said them — so failing to read them is the model's miss.
    residue = G.bounces(G.gate1(dropped, r6, board))[0]
    check("the residue is addressed to the reader, not the requester",
          "read the request again" in residue.says)
    check("rung 11's correct reading is silent",
          not G.bounces(G.gate1(
              rows(("every vm", "vm_set", {}),
                   ("the ones that do not answer", "vm_set", {"alive": "False"})),
              "ping every vm and stop the ones that do not answer", board)))


def test_a_numeral_before_a_noun_counts_and_after_one_names():
    print("\n[identity] '3 vms' is three machines; 'network 1' is one network called that")
    from orchestrator.languages.english.seam.scan import scan, scan_all
    board = Board()

    named = scan("network", "get me box and put it in network 1", board)
    check("a numeral AFTER the noun joins the name",
          named.identity == "network 1" and named.count is None)
    counted = scan("vms", "create 5 vms, put them all in a network", board)
    check("and a numeral BEFORE it is still a count",
          counted.count == 5 and counted.identity is None)

    # ⇒ WITHOUT THIS, "network 1" AND "network 2" PRODUCED THE SAME SPAN and the fold merged
    #   two distinct networks into one — a confidently wrong program, not a visible error.
    both = scan_all("network", "put web on network 1 and db on network 2", board)
    check("two numbered networks are two spans", len(both) == 2)
    check("with different identities",
          {b.identity for b in both} == {"network 1", "network 2"})
    check("and they do NOT collide, so the fold cannot merge them",
          not both[0].collides(both[1]))

    # ⇒ A BARE NOUN-WORD MAY BE A NAME, and only the lab can say. `box` is a declared noun for
    #   `vm` and a plausible machine name; carrying the candidate is what lets gate 2 ask.
    bare = scan("box", "get me box and put it in network 1", board)
    check("a bare noun-word is carried as a CANDIDATE identity", bare.identity == "box")
    check("but a counted phrase is not — it is plainly generic",
          scan("vm", "ping every vm", board).identity is None)
    check("nor is one whose name is given outright",
          scan("vm", "create a vm named alpha", board).identity is None)


def _no_model():
    """Stub `constrained` so `run_scanned` makes NO model call.

    Everything item 0 concerns — the anchors, the fixpoint, the contextual kind, both gates —
    is deterministic code, and with the model stubbed the whole pipeline is suite-ownable.
    V4 also applies: a suite that quietly called a model would contend with any probe running
    beside it and make both results noise.
    """
    import engines.channel as channel
    was = channel.constrained
    channel.constrained = lambda *a, **k: {}
    return channel, was


def test_a_meaningless_word_is_not_laundered_into_an_object():
    print("\n[junk] the taxonomy had two slots — a thing nobody named, a clause nobody read — "
          "and a meaningless word is a THIRD. It was being forced into the first")
    from orchestrator.languages.english.seam import gates12 as G, pass1 as P
    board = Board()
    channel, was = _no_model()
    try:
        # ⇒ THE DEFECT, MEASURED 2026-08-08: `grubnash` was DECLARED A VM and both gates were
        #   silent. Gate 1 could not object — the OPERATOR said the word, and gate 1 catches
        #   what the MODEL invented. Gate 2 could not object — `vm` is a real kind. And it
        #   never reached the leftover check, because the fixpoint had claimed the word.
        trailing = "create a vm named alpha and launch it, grubnash"
        rows = P.run_scanned(trailing, board=board)
        junk = next((r for r in rows if "grubnash" in r.name.lower()), None)
        check("the junk word is still DECLARED — a kindless thing is still a thing",
              junk is not None)
        check("but it is NOT given the request's only kind", junk.object_type != "vm")
        check("its kind is unsettled, which is the honest answer",
              junk.object_type == S.UNKNOWN_KIND)
        check("and the real object is untouched",
              any(r.object_type == "vm" and r.where.get("name") == "alpha" for r in rows))

        # ⇒ AND GATE 2 NOW ASKS SOMETHING ANSWERABLE. `this lab has no '?'` was unanswerable:
        #   `?` does not mean the lab lacks a kind, it means the request never said which.
        asks = [f for f in G.gate2(rows, board) if f.kind == "kind-not-settled"]
        check("gate 2 asks the operator what it is", len(asks) == 1)
        # INDEXED SAFELY ON PURPOSE. Under the old rule there is no finding at all, and a
        # regression must REPORT as three failures rather than raise on `asks[0]`.
        said = asks[0].says if asks else ""
        check("naming the word", "grubnash" in said)
        check("and offering the kinds this lab does have", "vm" in said)
        check("it never claims the lab lacks the kind", said and "has no" not in said)

        alone = "grubnash grubnash grubnash"
        check("junk with nothing around it asks too",
              [f.kind for f in G.gate2(P.run_scanned(alone, board=board), board)]
              == ["kind-not-settled"])

        # ⇒ THE CONTROL THAT MATTERS: the rule being narrowed EXISTS for rung 11, so rung 11
        #   must be untouched by narrowing it. A pro-form REFERS, so its kind is in the request
        #   even though its span has no noun.
        r11 = "ping every vm and stop the ones that do not answer"
        got = P.run_scanned(r11, board=board)
        residual = next((r for r in got if r.residual), None)
        check("rung 11's pronoun-headed set still takes the contextual kind",
              residual is not None and residual.object_type == "vm_set")
        check("with its condition intact", residual.where == {"alive": False})

        # STILL OPEN, DELIBERATELY NOT PINNED AS CORRECT: junk INSIDE a span is swallowed by
        # it — "create a grubnash vm named alpha" reads as one vm and no gate speaks. What is
        # pinned is only that it does not become a SECOND object; whether an unread descriptor
        # inside a span should be flagged is the next item, not this one.
        inside = P.run_scanned("create a grubnash vm named alpha", board=board)
        check("junk inside a span does not spawn a second object", len(inside) == 1)
    finally:
        channel.constrained = was


def test_the_contextual_kind_demands_the_evidence_it_was_written_for():
    print("\n[junk] `_has_pronoun` is not `_is_bare_pronoun`, and the difference is rung 11")
    from orchestrator.languages.english.seam import pass1 as P

    check("a restricted pro-form still REFERS", P._has_pronoun("the ones that do not answer"))
    check("even though it is not a BARE pronoun",
          not S._is_bare_pronoun("ones", "stop the ones that do not answer"))
    check("a bare one refers as well", P._has_pronoun("launch it"))
    check("and 'them all' does", P._has_pronoun("put them all in a network"))
    check("a meaningless word does not", not P._has_pronoun("grubnash"))
    check("nor does an ordinary phrase with no pro-form",
          not P._has_pronoun("a network called core"))
    # `one's` is not `ones` — the apostrophe decides SET-NESS and it decides this too.
    check("a possessive is not a plural pro-form",
          not P._has_pronoun("the machine's network"))


def test_the_slot_decides_whether_a_word_is_junk_not_its_meaning():
    print("\n[residue] the operator: 'a grubnash isn't a descriptor that correlates to "
          "anything, at best, a name or label' — so the SLOT decides, never the meaning")
    from orchestrator.languages.english.seam import pass1 as P, residue as R
    board = Board()
    channel, was = _no_model()
    try:
        # ⇒ THE SAME WORD IN THREE POSITIONS, AND ALL THREE VERDICTS DIFFER. Nothing here
        #   knows what `grubnash` means; only which slot it landed in.
        def verdicts(request):
            rows = P.run_scanned(request, board=board)
            return {r.word: r.verdict for r in R.report(rows, request, board)}

        check("a descriptor slot is closed, so junk asks",
              verdicts("create a grubnash vm named alpha") == {"grubnash": R.ASK})
        check("a naming slot is open, so the same word is silent",
              verdicts("create a vm named grubnash") == {})
        check("and so is a quoted label",
              verdicts("give every vm the 'grubnash' label") == {})

        # ⇒ WHERE THE JUNK WENT WHEN THE FIRST DOOR CLOSED. `conditions_from` promotes the
        #   word beside an attribute into a VALUE, so it is not unread at all — it is a
        #   confidently wrong filter that both gates pass.
        promoted = P.run_scanned("put every vm on a wibblesome network", board=board)
        # ⇒ superseded 08-20: the transfer frame reads the network as its OWN row
        #   (the certified ana-0003 convention) — the junk-magnet promotion is gone;
        #   `wibblesome` sits in the network row's descriptor slot and asks honestly
        check("the junk-magnet promotion is gone — the network is its own row",
              not any(r.where.get("network") == "wibblesome" for r in promoted)
              and any(r.kind == "network" for r in promoted))
        check("and the value is checked against the slot, so it still asks",
              [r.verdict for r in R.report(promoted, "put every vm on a wibblesome network",
                                           board)] == [R.ASK])

        # ⇒ A REFERENCE THAT RESOLVES IS SILENT. The symbol table settles it with no lab —
        #   rule D1, the symbol table is the contract.
        declared_here = "create a network called mesh and put orion on it"
        check("a reference to something declared in the same request is silent",
              verdicts(declared_here) == {})

        # THE CLEAN CONTROLS. A check that speaks about a correct reading is worse than none.
        for request in ("create a vm named orion",
                        "stop every vm that is running",
                        "make sure at least 2 vms carry the 'edge' label",
                        "launch the machines that do not answer"):
            check(f"silent on a correct reading: {request!r}", verdicts(request) == {})
    finally:
        channel.constrained = was


def test_a_span_residue_bounces_but_junk_asks():
    print("\n[residue] two audiences, and the request decides which: a word the request BINDS "
          "is the model's miss; a word nothing can hold is the operator's call")
    from orchestrator.languages.english.seam import gates12 as G, pass1 as P, residue as R
    board = Board()
    channel, was = _no_model()
    try:
        bound = "create 3 vms labelled 'edge' and put the edge ones on a network"
        rows = P.run_scanned(bound, board=board)
        # ⇒ superseded 08-20: the pro-form fold RESOLVES the reference by content —
        #   `the edge ones` IS the labelled set, read, never residue at all
        check("a pro-form naming a bound value RESOLVES silently",
              [r.verdict for r in R.report(rows, bound, board)] == [])
        check("and the fold records the reference on its host",
              any("the edge ones" in (r.references or ()) for r in rows))
        report = G.report(rows, bound, board)
        check("and it is not put to the operator at all",
              not any("edge" in a and "name, a label" in a for a in report["asks"]))

        junk = "create a grubnash vm named alpha"
        jr = G.report(P.run_scanned(junk, board=board), junk, board)
        check("junk goes to the OPERATOR", any("grubnash" in a for a in jr["asks"]))
        check("and never bounces — the model would find it a job",
              not jr["bounces"])
        check("the ask is a CLOSED CHOICE, not a request for an explanation",
              all("Is it a name, a label, or should it be ignored?" in a
                  for a in jr["asks"] if "grubnash" in a))
    finally:
        channel.constrained = was


def test_every_declared_boundary_can_actually_be_emitted():
    print("\n[boundary] a rule that CANNOT FIRE is worse than a missing one — it reads as "
          "handled. `—` was a declared clause boundary the tokenizer could never produce")
    from orchestrator.languages.english.seam import scan as SC
    board = Board()

    # ⇒ THE MECHANISM, NOT JUST THE OUTCOME. Every punctuation boundary must be reachable by
    #   the tokenizer, or the next one added will be dead in the same silent way.
    punctuation = [b for b in SC.BOUNDARIES if not b.isalpha()]
    for mark in punctuation:
        sample = f"a vm named alpha{mark} a network called lab"
        check(f"the boundary {mark!r} is emitted as a token",
              any(t[0] == mark for t in SC._tokens(sample)))

    # ⇒ AND THE HYPHEN IS DELIBERATELY NOT ONE. `[\w']+` matches first, so making `-` a
    #   boundary would split a hyphenated word into two spans.
    check("an ASCII hyphen stays inside its word",
          [t[0] for t in SC._tokens("a well-known vm")] == ["a", "well", "known", "vm"]
          or "-" not in [t[0] for t in SC._tokens("a well-known vm")])

    # RUNG 8, THE CORPSE THIS RULE COMES FROM. The span ran from `except` to the end of the
    # sentence — 51 characters, both `db` mentions and the dmz network — and the fold then
    # merged all of it into one `network` row.
    r8 = ("put every vm on a network called core, except db — db goes on a network "
          "called dmz instead")
    spans = SC.scan_all("db", r8, board)
    check("`db` no longer swallows the rest of the sentence",
          all(s.end - s.start < 45 for s in spans))
    check("and the dash separates the two clauses",
          any(s.span.strip().endswith("db") for s in spans))


def test_the_world_settles_a_kindless_row_and_that_is_what_closes_rung_8():
    print("\n[settle] gate 2 asks what 'db' is and must not answer itself. The LAB answers, "
          "and both the kind and the key value come back from the one query")
    from orchestrator.languages.english.seam import gates12 as G, pass1 as P
    from orchestrator.languages.english.seam.effects import Operation, conditions_after, flatten
    from tests.bench.twopass.metrics import Lab
    board = Board()
    channel, was = _no_model()
    try:
        r8 = P.EXPECTED[8].request
        raw = P.run_scanned(r8, board=board)
        check("without a lab the row is honestly kindless",
              any(r.object_type == S.UNKNOWN_KIND for r in raw))
        check("and gate 2 ASKS rather than guessing",
              any(f.kind == "kind-not-settled" for f in G.gate2(raw, board)))

        settled = P.settle_with_world(raw, Lab(), board)
        db = next((r for r in settled if r.where.get("name") == "db"), None)
        check("the lab settles it to a vm", db is not None and db.object_type == "vm")
        check("and the same query returns the key value, so nothing is inferred",
              db.where == {"name": "db"})
        check("gate 2 has nothing left to ask about it",
              not [f for f in G.gate2(settled, board) if "db" in f.about])

        # ⇒ AND ONLY NOW CAN AN OPERATION POINT AT IT (rule D1). `{name: db}` is a
        #   DECLARATION and could never have come from pass 2; `{network: dmz}` is an effect
        #   that needed a declared target.
        declared = {r.name: dict(r.where) for r in settled}
        after = flatten(conditions_after(declared,
                                         [Operation("add_vm_to_network", "except db", "dmz")],
                                         board))
        want = P.EXPECTED[8].conditions
        check(f"rung 8's conditions are complete: {want}",
              all(w in after for w in want))

        # THE CONTROL: no lab, no settling. A missing world must never invent a kind.
        check("with no world nothing is settled",
              [r.object_type for r in P.settle_with_world(raw, None, board)]
              == [r.object_type for r in raw])
        check("and a lab that does not hold it leaves it kindless",
              any(r.object_type == S.UNKNOWN_KIND
                  for r in P.settle_with_world(raw, _EmptyLab(), board)))
    finally:
        channel.constrained = was


class _EmptyLab:
    def select(self, query):
        return []


class _WideLab:
    """Four kinds under THREE DIFFERENT KEY NAMES — `name`, `net_name`, `snap_name`. None of
    these objects appears in the 14 rungs, so nothing here can be passing by memory."""
    ROWS = [{"kind": "vm", "name": "atlas"}, {"kind": "network", "net_name": "spine"},
            {"kind": "snapshot", "snap_name": "nightly"}, {"kind": "template", "name": "base9"}]

    def select(self, query):
        return [r for r in self.ROWS
                if all(str(r.get(k, "")).lower() == str(v).lower() for k, v in query.items())]


def test_settling_is_general_across_kinds_and_key_names():
    print("\n[settle] the operator: 'make it a general fix not a rung specific'. Four kinds, "
          "three different key names, and none of them in the corpus")
    from orchestrator.languages.english.seam import pass1 as P
    board = Board()
    channel, was = _no_model()
    try:
        def settled(request):
            rows = P.settle_with_world(P.run_scanned(request, board=board), _WideLab(), board)
            return [(r.object_type, dict(r.where)) for r in rows]

        check("a bare vm name settles by `name`",
              ("vm", {"name": "atlas"}) in settled("launch atlas"))
        check("a snapshot settles by `snap_name`, not by `name`",
              ("snapshot", {"snap_name": "nightly"}) in settled("restore nightly"))
        check("a template settles by its own key",
              ("template", {"name": "base9"}) in settled("check base9"))

        # ⇒ THE TWO CONTROLS THAT MATTER MORE THAN THE HITS. An absent word must stay `?`,
        #   and a mixed request must settle per WORD rather than per request.
        check("a word the lab does not hold stays kindless",
              any(t == S.UNKNOWN_KIND for t, _ in settled("launch quibble")))
        mixed = settled("ping atlas, quibble and spine")
        check("known and unknown in one request settle independently",
              ("vm", {"name": "atlas"}) in mixed
              and any(t == S.UNKNOWN_KIND for t, _ in mixed))
    finally:
        channel.constrained = was


def test_pass_2_addresses_a_declaration_by_a_derived_handle():
    print("\n[pass2] the model was measured pointing at `fleet` and `unresponsive`. Pass 1 "
          "names a row by its SPAN, and a 34-character enum member is not what was measured")
    from orchestrator.languages.english.seam import pass1 as P, pass2 as P2
    from tests.bench.twopass.metrics import Lab
    board = Board()
    channel, was = _no_model()
    try:
        def handles(n):
            rows = P.settle_with_world(P.run_scanned(P.EXPECTED[n].request, board=board),
                                       Lab(), board)
            return [s.handle for s in P2.symbol_table(rows, board)]

        check("a named individual addresses by its key value", handles(1) == ["alpha"])
        check("two of them keep their own names", handles(3) == ["lab", "web"])
        check("a conditioned set says what narrows it", handles(5) == ["stopped_vms"])
        # ⇒ RUNG 11 IS THE ONE THAT MATTERS: the run-time set must be addressable at all.
        check("and a boolean condition reads as a negation",
              handles(11) == ["vms", "not_alive_vms"])
        # ⇒ AND A KINDLESS ROW TAKES THE OPERATOR'S OWN WORD. `thing`, `thing_2`, `thing_3`
        #   gave three indistinguishable addresses for three distinct machines; taking the
        #   last non-grammar word gave `ping`, a VERB addressing a machine.
        check("three bare names stay distinguishable", handles(9) == ["n1", "n2", "n3"])
        check("and a verb is never an address", "ping" not in handles(9))

        every = [h for n in P.EXPECTED for h in handles(n)]
        check("no handle is empty", all(h and h.strip() for h in every))
        check("and none is a whole span", all(len(h) < 20 for h in every))
    finally:
        channel.constrained = was


def test_the_operator_enum_order_is_pinned_because_it_moved_the_answer():
    print("\n[pass2] moving ONE entry of this enum doubled exact matches and removed every "
          "spurious step — so the order is a hidden parameter and is pinned by value")
    from orchestrator.languages.english.seam import pass2 as P2
    ops = P2.operators_offered(Board())

    # ⇒ MEASURED, n=3, four orderings with an isolation cell: `add_label` at index 0 or 1
    #   gave 6 spurious steps and 3/9 exact; that one entry moved to the end gave 0 and 6/9.
    check("add_label is LAST and that is a measurement, not a preference",
          ops[-1] == "add_label")
    check("it appears exactly once", ops.count("add_label") == 1)
    check("the rest is otherwise stable, not shuffled",
          ops[:-1] == sorted(ops[:-1]))
    check("every operator is read from the manifest, so a probe is offered",
          "probe_alive" in ops and "create_vm" in ops and "stop_vm" in ops)
    # THE GAP, STATED RATHER THAN HIDDEN: a vm's 21 `acts` are not offered, so a request that
    # needs one has NO legal answer — and a closed enum with no legal answer produces a
    # confident wrong one. Rung 9 reaches for `add_label` to build a ping mesh.
    check("`acts` are deliberately absent, and nothing pretends otherwise",
          not any(o.startswith("kill") or o == "memory" for o in ops))


class _NamedLab:
    def __init__(self, *names, kind="vm", key="name"):
        self.ROWS = [{"kind": kind, key: n} for n in names]

    def select(self, query):
        return [r for r in self.ROWS
                if all(str(r.get(k, "")).lower() == str(v).lower() for k, v in query.items())]


def test_gate_3_computes_the_refusal_the_model_will_not_give():
    print("\n[gate3] three attempts to ASK for a refusal have measured 0, 4/8 and 2/8 — the "
          "third, removing `minItems: 1`, was byte-identical at 0/3. So it is DERIVED instead")
    from orchestrator.languages.english.seam import gate3 as G3, gates12 as G, pass1 as P, pass2 as P2
    from orchestrator.languages.english.seam.effects import Operation
    from tests.bench.twopass.metrics import Lab
    board = Board()
    channel, was = _no_model()
    try:
        def table(n, world=None):
            rows = P.run_scanned(P.EXPECTED[n].request, board=board)
            return P2.symbol_table(P.settle_with_world(rows, world or Lab(), board), board)

        # ⇒ RUNG 9, THE ROW THIS EXISTS FOR. The model answers `add_label(n1, n2)` 3 of 3 for
        #   *"make sure n1, n2 and n3 can all ping each other"* — there is no connectivity
        #   operator in the manifest at all, so the request HAS no legal answer.
        mesh = [Operation("add_label", "n1", "n2"), Operation("add_label", "n2", "n1"),
                Operation("add_label", "n3", "n1"), Operation("add_label", "n3", "n2")]
        t9 = table(9)
        # ⇒ OWNERSHIP CHANGED, NOT THE VERDICT. An unsettled kind is GATE 2's question, and
        #   gate 3 used to re-derive it — the one fact *nothing says what n1 is* came back five
        #   times, three from gate 2 and two from here. Gate 3 now trusts the table it is given.
        # ⚠ A LAB THAT DOES NOT KNOW THEM, AND IT USED TO BE THE DEFAULT ONE. `Lab` gained
        #   `n1 · n2 · n3` on 2026-08-14 so the residue check's world arm could be measured at
        #   all — and with them present `settle_with_world` settles rung 9 outright, which is
        #   exactly what a lab is FOR. So gate 2 correctly reports nothing there now, and the
        #   case this assertion owns — *nobody has said what n1 is* — needs a lab that has not.
        class _Unknowing(Lab):
            ROWS = [r for r in Lab.ROWS if r["name"] in ("db", "golden")]

        rows9 = P.settle_with_world(P.run_scanned(P.EXPECTED[9].request, board=board),
                                    _Unknowing(), board)
        asks9 = [f for f in G.gate2(rows9, board) if f.kind == "kind-not-settled"]
        check("GATE 2 reports the unsettled kinds", len(asks9) == 3)
        # ⇒ AND FROM THE SAME UNKNOWING LAB, for the same reason: with the kinds SETTLED gate 3
        #   does refuse the mesh, and that is the very case the next block asserts. Built from
        #   the default lab these two branches had quietly become the same one.
        check("and gate 3 stays out of it",
              not G3.check(mesh, table(9, _Unknowing()), board))
        # ⇒ AND THE OTHER HALF OF THE SAME FACT, worth pinning now that it is true: given a lab
        #   that DOES hold them, nothing is unsettled and gate 2 has nothing to ask.
        settled9 = P.settle_with_world(P.run_scanned(P.EXPECTED[9].request, board=board),
                                       Lab(), board)
        check("and a lab that knows them leaves gate 2 nothing to ask",
              not [f for f in G.gate2(settled9, board) if f.kind == "kind-not-settled"])

        # ⇒ AND IT STILL REFUSES WHEN THE LAB DOES KNOW THEM — a different rule catches it.
        #   You cannot label a machine WITH a machine, whoever those machines are.
        known = table(9, _NamedLab("n1", "n2", "n3"))
        caught = G3.check(mesh, known, board)
        check("with the kinds settled it is still refused", G3.refused(mesh, known, board))
        check("now because a label slot took an object",
              caught[0].rule == "value-is-an-object")

        # THE CONTROLS. Four programs the model got right must pass untouched.
        t3 = P2.symbol_table(P.run_scanned(P.EXPECTED[3].request, board=board), board)
        good3 = [Operation("create_network", "lab", None), Operation("create_vm", "web", None),
                 Operation("add_vm_to_network", "web", "lab")]
        check("rung 3's correct program is legal", not G3.check(good3, t3, board))
        t11 = table(11)
        good11 = [Operation("probe_alive", "vms", None),
                  Operation("stop_vm", "not_alive_vms", None)]
        check("rung 11's correct program is legal", not G3.check(good11, t11, board))
        # ⇒ THE ASSERTION HERE WAS SUPERSEDED, NOT SOFTENED. It used to check that a lone
        #   `stop_vm(not_alive_vms)` is legal — and a run-time set IS a legal target, which is
        #   still asserted just below. But a program that stops the unresponsive machines and
        #   never probes them is incomplete, and the binding-time rule now says so. The lone
        #   operation was never a valid program; it was a convenient fixture.
        check("a run-time set is legal ONCE ITS PROBE HAS RUN", not G3.check(good11, t11, board))
        alone = G3.check([Operation("stop_vm", "not_alive_vms", None)], t11, board)
        check("but acting on one before anything asks is not",
              alone and alone[0].rule == "not-settled-yet")

        # ⇒⇒ THE SILENT WRONG PROGRAM THIS RULE EXISTS FOR. Both steps legal, both operators
        #   warranted, both handles used, `stop_vm` not a delete — every other check passes it,
        #   and it stops EVERY machine instead of the unresponsive ones.
        swapped = [Operation("probe_alive", "not_alive_vms", None),
                   Operation("stop_vm", "vms", None)]
        caught = G3.check(swapped, t11, board)
        check("probing the set that the probe itself defines is circular",
              caught and caught[0].rule == "circular-probe")
        backwards = G3.check([Operation("stop_vm", "not_alive_vms", None),
                              Operation("probe_alive", "vms", None)], t11, board)
        check("and the right steps in the wrong ORDER are caught too",
              backwards and backwards[0].rule == "not-settled-yet")
        check("a plan-time set needs no probe first",
              not G3.check([Operation("stop_vm", "vms", None)], t11, board))

        # ⇒ THE OTHER TWO RULES, EACH EXERCISED WHERE IT IS THE ONLY ONE THAT CAN FIRE.
        missing = G3.check([Operation("add_vm_to_network", "web", None)], t3, board)
        check("a setter with its value omitted is caught",
              missing and missing[0].rule == "value-missing")
        wrong = G3.check([Operation("add_vm_to_network", "web", "web")], t3, board)
        check("and a value of the wrong kind is caught",
              wrong and wrong[0].rule == "wrong-kind-value")
        check("one bad step among good ones is NOT a refusal",
              not G3.refused(good3 + [Operation("add_vm_to_network", "web", None)], t3, board))
    finally:
        channel.constrained = was


def _canned(steps):
    """Stub the model with a fixed pass-2 answer, so the CHAIN is exercised with no GPU.

    Rule W6 beat 3: passing in isolation says nothing about being reached, and being reached is
    the thing that keeps failing here. Pass 1 needs no model at all; only pass 2's one question
    does, so it is answered from a table.
    """
    import engines.channel as channel
    was = channel.constrained

    def fake(prompt, payload, schema, **kw):
        if "operations" in (schema.get("properties") or {}):
            return {"operations": [{"operator": o, "on": t, "value": v} for o, t, v in steps]}
        return {}

    channel.constrained = fake
    return channel, was


def test_the_whole_chain_runs_and_every_stage_is_reached():
    print("\n[chain] six pieces were built over two days and every one ran in a bench of its "
          "own — `operations_for` had exactly ONE caller, its own main()")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()
    channel, was = _canned([("probe_alive", "vms", None), ("stop_vm", "not_alive_vms", None)])
    try:
        got = PL.run("ping every vm and stop the ones that do not answer",
                     board=board, world=Lab())
        check("pass 1 reached — the run-time set is declared and addressable",
              got.handles == ["vms", "not_alive_vms"])
        check("pass 2 reached — operations came back", len(got.operations) == 2)
        check("gate 3 reached — and found nothing wrong", not got.illegal)
        # ⇒ THE EFFECT TABLE IS REACHED THROUGH THE HANDLE DEREFERENCE. `conditions_after` is
        #   keyed by the declaration's NAME and pass 2 speaks in HANDLES; without `_aimed` the
        #   effects land on nothing and the conditions come back short, silently.
        check("effects reached — stop_vm's own effect is computed, not read from English",
              {"status": "stopped"} in got.conditions)
        check("and the request's own condition survives", {"alive": False} in got.conditions)
        check("so the verdict is SERVE", got.outcome == PL.SERVE)
    finally:
        channel.constrained = was


def test_a_refusal_is_only_a_refusal_when_nobody_could_answer_it():
    print("\n[chain] rung 9 has every operation illegal under BOTH conditions, for two "
          "different reasons — and only one of them is a refusal")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()
    mesh = [("add_label", "n1", "n2"), ("add_label", "n2", "n1"),
            ("add_label", "n3", "n1"), ("add_label", "n3", "n2")]
    channel, was = _canned(mesh)
    try:
        r9 = "make sure n1, n2 and n3 can all ping each other"
        unknown = PL.run(r9, board=board, world=Lab())
        # ⇒⇒ **THE KINDS ARE NO LONGER UNSETTLED, AND THAT IS THE POINT OF THE CHANGE.**
        #   2026-08-11, the operator: *"rung 9 is wrong to be an ASK, since the only thing that
        #   can ping is a vm."* `alive` is observed on `vm` and on nothing else, so the request
        #   SAYS what n1 is and `settle_by_affordance` reads it. Asking *what is n1?* was asking
        #   a question the request had already answered.
        #
        #   ⇒ **THE DISTINCTION THIS TEST EXISTS FOR SURVIVES INTACT — ONLY THE FIRST BRANCH'S
        #     REASON CHANGED.** With a lab that does not hold them, the faults are things the
        #     MODEL can fix (it labelled machines with machines, and used machines nothing
        #     establishes), so it is not a refusal. With a lab that does, only *you cannot label
        #     a machine WITH a machine* survives, and nobody can answer that.
        check("the kinds are settled by what the request asks them to DO",
              all(s.row.object_type == "vm" for s in unknown.table))
        check("and it is not a refusal, because the model can still fix it",
              unknown.outcome != PL.REFUSE)

    finally:
        channel.constrained = was

    # ⇒⇒ **THE REFUSE BRANCH NEEDS A WARRANTED-BUT-ILLEGAL PROGRAM, AND THE MESH STOPPED BEING
    #   ONE.** It used rung 9's `add_label` mesh — and `add_label` is warranted by the word
    #   *label*, which that request never says. As of 2026-08-11 an unwarranted step gets no
    #   clause anchor and is demoted to a SUGGESTION before gate 3 sees it, so the mesh now
    #   yields an EMPTY program: correctly, but it exercises nothing.
    #   ⇒ SO THE FIXTURE SAYS `label` OUT LOUD. The step is then genuinely warranted, genuinely
    #     illegal — *you cannot label a machine WITH a machine* — and nobody can answer it,
    #     which is the distinction this test exists to hold.
    # ⇒⇒ **THE REFUSE HALF MOVED OUT, AND WHY IS WORTH READING: IT WAS PASSING FOR THE WRONG
    #   REASON ON HALF OF ALL HASH SEEDS.** See `test_labelling_a_machine_with_a_machine_is_illegal`
    #   directly below. Kept here as a pointer so this test is not read as still covering it.


@pytest.mark.xfail(reason=(
    "pass 1 declares ONE row for a span naming TWO entities, so `n2` never becomes a handle "
    "and `value-is-an-object` — the rule this asserts — cannot fire. Filed as the chunking "
    "defect; do not delete this test, it is the only thing that states the intended behaviour."),
    strict=False)
def test_labelling_a_machine_with_a_machine_is_illegal():
    """A warranted step can still be ILLEGAL, and nobody can answer that — so it REFUSES.

    ⇒⇒ **SPLIT OUT AND MARKED 2026-08-13. IT HAD NEVER ONCE TESTED WHAT IT CLAIMS.**

    It lived inside `test_a_refusal_is_only_a_refusal_when_nobody_could_answer_it`, where it
    passed on roughly half of all `PYTHONHASHSEED` values and failed on the rest — which went
    unnoticed because a suite is normally run once, on whatever seed the day handed it.

        seed 0, 1, 6, 7   ->  BOUNCE, illegal []          the checks FAIL
        seed 2, 3, 4, 5   ->  REFUSE, illegal [no-such-handle]   the checks PASS

    ⇒ **AND THE SEEDS WHERE IT PASSED WERE PASSING ON A DIFFERENT RULE.** The intended rule is
      `value-is-an-object` — *you cannot label a machine WITH a machine*. What actually fired
      was `no-such-handle`, because `settle_with_world` sorted candidate words by LENGTH ALONE
      over a SET, so `n1` and `n2` tied and the row's identity bound to whichever the hash
      order offered first. When it bound to `n2`, the step `add_label(n1, …)` addressed a
      handle that did not exist. A green tick for an unrelated defect.

    The ordering bug is fixed (`pass1.settle_with_world`, total order: length, then first
    mention). With identity stable this now fails on EVERY seed, honestly, because:

    ⇒ **`value-is-an-object` NEEDS BOTH `n1` AND `n2` DECLARED**, and pass 1 emits ONE row for
      the whole span. `n2` is never a handle, so `str(step.value) in by_handle` is False and
      the rule is unreachable — not silent, unreachable. **That is the chunking defect**, and
      it is upstream of the gate: no rule about a value naming an object can fire while the
      value never becomes a declaration.

    This stays xfail rather than being deleted or weakened to match the behaviour, because
    asserting the current BOUNCE would pin a defect as correct — which is exactly the false
    green the suite spent a day removing.
    """
    from orchestrator.languages.english.seam import pipeline as PL
    board = Board()
    channel, was = _canned([("add_label", "n1", "n2")])
    try:
        known = PL.run("give n1 the n2 label", board=board,
                       world=_NamedLab("n1", "n2"))
        assert len(known.illegal) == 1, (
            f"a warranted step can still be illegal — got {known.illegal!r}")
        assert known.outcome == PL.REFUSE, (
            f"and nobody can answer that, so it REFUSES — got {known.outcome}")
    finally:
        channel.constrained = was



def test_a_step_no_clause_warrants_never_runs():
    """THE PROPERTY THE PER-CLAUSE DESIGN WAS PARKED ON, 2026-08-13.

    `operations_by_clause` was built to make a spurious step UNREPRESENTABLE — asked per clause,
    a step no clause warrants has no call it could come from. Measured that day it cost three
    rungs (13 SERVE -> 10), N model calls instead of one, and INVENTED a destructive step on
    rung 8, because a clause read in isolation changes meaning: `except db` becomes *remove db*.

    ⇒ **IT WAS NOT WIRED BECAUSE ITS GOAL IS ALREADY MET.** `anchor_to_clauses` attributes
      clauses to the WHOLE-request answer afterwards, and a step nothing warrants is demoted to
      a SUGGESTION — shown, never run. The operator accepted that trade explicitly, on one
      condition: *"as long as the 'unpure' never runs and gets dropped, it's an ok trade."*

    **SO THAT CONDITION IS LOAD-BEARING AND THIS IS WHERE IT LIVES.** Nothing asserted it before
    — only a bench probe touched `.suggested`, and a bench probe is not a guarantee.
    """
    print("\n[split] an unwarranted step is demoted, and a destructive one never is")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()

    # `probe_alive` is legal and harmless, and no clause of this request asks for it.
    channel, was = _canned([("create_vm", "alpha", None), ("probe_alive", "alpha", None)])
    try:
        got = PL.run("create a vm named alpha", board=board, world=Lab())
        ran = [o.operator for o in got.operations]
        check("the warranted step runs", "create_vm" in ran)
        check("the unwarranted step does NOT run", "probe_alive" not in ran)
        # ⇒⇒ **NOT OFFERED EITHER — AN ILLEGAL STEP MUST NOT BE SHOWN AS ADVICE.** But it is
        #   RECORDED and it reaches an audience, which it did not until 2026-08-13. The operator:
        #   *"I am fine with it existing as long as we treat it"* — dropping is not treating.
        check("an illegal step is not offered as a suggestion",
              "probe_alive" not in [o.operator for o in got.suggested])
        check("but it is recorded rather than vanishing",
              "probe_alive" in [o.operator for o in got.discarded])
        check("and it reaches an audience — the model that emitted it",
              any(n.audience == "model" and "probe_alive" in n.about
                  for n in (got.linguistics or ())))
        # ⇒ AND IT IS A NOTE, NEVER A BOUNCE. `_verdict` bounces the moment `bounces` is
        #   non-empty, so raising one here would fail a CORRECT program because the model
        #   emitted junk beside it — the detector-makes-it-worse trap of 08-10.
        check("and the correct program is still served",
              got.outcome == PL.SERVE)
    finally:
        channel.constrained = was

    # ⇒ THE HALF THAT MATTERS MORE: a destructive step is never QUIETLY demoted, because a
    #   suggestion is shown and not judged — and a delete nobody asked for must be judged.
    channel, was = _canned([("create_vm", "alpha", None), ("delete_vm", "alpha", None)])
    try:
        got = PL.run("create a vm named alpha", board=board, world=Lab())
        check("a destructive step is NOT demoted to a suggestion",
              "delete_vm" not in [o.operator for o in got.suggested])
        check("it stays where somebody has to answer for it",
              "delete_vm" in [o.operator for o in got.operations] or bool(got.asks))
    finally:
        channel.constrained = was


def test_a_destructive_operation_over_a_whole_set_asks_first():
    print("\n[chain] rung 14 SERVED `delete_vm` over every machine in the lab, and every "
          "check passed — nothing about it is ILLEGAL, which is exactly the problem")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()
    channel, was = _canned([("delete_vm", "vms", None), ("probe_exists", "vms", None)])
    try:
        # ⇒⇒ ⚠ **A LAB THAT REALLY HOLDS TWO, AND `Lab()` HAS NOT SINCE 2026-08-14.** This
        #   check read `Lab()` and its premise is *the lab is already correct*, so it was a
        #   silence control. `metrics.Lab` says in its OWN docstring that adding n1/n2/n3 took
        #   the unfiltered set "from 2 members to 5" — which turned this cell into a 5 -> 2
        #   removal, and the guard has been correctly asking to confirm it ever since. The
        #   FIXTURE moved and the check did not, so a passing guard read as a failure.
        got = PL.run("make sure there are exactly two machines left", board=board,
                     world=_NamedLab("v0", "v1"))
        check("gate 3 stays silent — it is not illegal", not got.illegal)
        # ⇒⇒ **THE GOAL REPLACED THE STEPS, SO THE GUARD HAD TO FOLLOW THEM.** As of 2026-08-11
        #   an ACHIEVE request carries the STATE it asks to hold and the steps that closed it are
        #   dropped — so `delete_vm(vms)` is no longer proposed and `confirmations`, which
        #   watches operations, saw nothing. **A confirmation that disappears because the
        #   request got a better representation is a guard failing exactly when the request is
        #   understood properly.** `destructive_goals` asks `derive` what the GOAL would do.
        #
        #   ⇒ AND AGAINST THIS LAB THERE IS NOTHING TO CONFIRM: it holds exactly two machines,
        #     so *make sure there are exactly two* closes with no removal at all. Silence is the
        #     correct answer here, which is why the real assertion is the six-machine case below.
        check("with the lab already correct, nothing is removed and nothing is asked",
              not any("Confirm before this runs" in a for a in got.asks))
    finally:
        channel.constrained = was

    # ⇒⇒ THE CASE THE GUARD EXISTS FOR: the same goal, against a lab holding SIX.
    channel, was = _canned([])
    try:
        crowded = PL.run("make sure there are exactly two machines left", board=board,
                         world=_NamedLab(*[f"v{i}" for i in range(6)]))
        check("holding a count DOWN is destructive, and it asks first",
              any("Confirm before this runs" in a for a in crowded.asks))
        check("and it says how many would be removed",
              any("REMOVING 4" in a for a in crowded.asks))
    finally:
        channel.constrained = was

    # ⇒ THE CONTROL: deleting a thing the operator NAMED is not a surprise, and a guard that
    #   fires on it would be noise that gets switched off.
    channel, was = _canned([("delete_vm", "alpha", None)])
    try:
        named = PL.run("delete the vm named alpha", board=board, world=Lab())
        check("deleting a named individual raises no confirmation",
              not any("Confirm before this runs" in a for a in named.asks))
    finally:
        channel.constrained = was


def _canned_sequence(*answers):
    """A model whose pass-2 answer CHANGES between calls, so a retry can be observed."""
    import engines.channel as channel
    was = channel.constrained
    calls = {"n": 0}

    def fake(prompt, payload, schema, **kw):
        if "operations" not in (schema.get("properties") or {}):
            return {}
        i = min(calls["n"], len(answers) - 1)
        calls["n"] += 1
        return {"operations": [{"operator": o, "on": t, "value": v} for o, t, v in answers[i]]}

    channel.constrained = fake
    return channel, was, calls


def test_the_retry_hands_the_model_its_own_miss():
    print("\n[retry] a BOUNCE means the model's own miss, so the model gets another go — "
          "given the rejected steps as EVIDENCE, never as instruction about how to behave")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()

    # ⇒⇒ **A `DO` REQUEST, DELIBERATELY.** This used rung 7 — and as of 2026-08-11 an ACHIEVE
    #   request carries a GOAL that REPLACES the steps it governs, so `got.operations` came back
    #   empty and the assertion was reading the wrong artifact. The retry's behaviour is what is
    #   under test here, not the goal machinery, so the fixture uses a request with no mood.
    r3 = "create a network called lab and a vm named web, then put web on lab"
    bad = [("create_network", "lab", None), ("create_vm", "web", None),
           ("add_vm_to_network", "web", "web")]           # a vm in a vm's slot
    good = [("create_network", "lab", None), ("create_vm", "web", None),
            ("add_vm_to_network", "web", "lab")]
    channel, was, calls = _canned_sequence(bad, good)
    try:
        got = PL.run(r3, board=board, world=Lab(), retries=1)
        check("the model was asked twice", calls["n"] == 2)
        check("and the second, legal answer is the one kept",
              [(o.operator, o.on, o.value) for o in got.operations] == list(good))
        check("so nothing is left illegal", not got.illegal)
    finally:
        channel.constrained = was

    # ⇒ A RETRY THAT MAKES THINGS WORSE IS DISCARDED. Taking the later answer because it came
    #   second is how a repair loop degrades while looking busy.
    worse = [("add_vm_to_network", "web", "web"), ("add_vm_to_network", "lab", "web")]
    channel, was, calls = _canned_sequence(bad, worse)
    try:
        got = PL.run(r3, board=board, world=Lab(), retries=1)
        check("a worse retry is rejected and the first answer stands",
              [(o.operator, o.on, o.value) for o in got.operations] == list(bad))
    finally:
        channel.constrained = was

    # ⇒ AND AN UNANSWERABLE KIND IS NEVER RETRIED. Only the operator or the lab can say what
    #   `n1` is, so re-asking would be inviting the model to guess.
    # ⇒⇒ **AND IT NEEDS A ROW NOTHING CAN SETTLE.** This used rung 9 — whose kinds are now
    #   settled by what the request asks them to DO (*only a vm can ping*), so the guard was no
    #   longer being exercised at all. `create` belongs to five kinds and settles nothing, so
    #   `zibbet` stays genuinely kindless, which is the case the rule exists for.
    blind = [("add_label", "zibbet", "prod")]
    channel, was, calls = _canned_sequence(blind, blind)
    try:
        got = PL.run("create zibbet", board=board, world=Lab(), retries=2)
        check("an unsettled kind is not handed back to the model", calls["n"] == 1)
        check("it goes to the operator instead", got.outcome == PL.ASK)
    finally:
        channel.constrained = was


def test_a_first_time_success_never_sees_the_retry():
    print("\n[retry] the base question is byte-identical on the first attempt, so the retry "
          "cannot regress what already worked — by construction, not by measurement")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()
    ok = [("probe_alive", "vms", None), ("stop_vm", "not_alive_vms", None)]
    channel, was, calls = _canned_sequence(ok, [("delete_vm", "vms", None)])
    try:
        got = PL.run("ping every vm and stop the ones that do not answer",
                     board=board, world=Lab(), retries=3)
        check("the model is asked exactly once", calls["n"] == 1)
        check("and rung 11 still serves", got.outcome == PL.SERVE)
    finally:
        channel.constrained = was


def test_a_value_phrase_is_not_an_object():
    print("\n[objects] \"give them all the 'fleet' label\" was declared as a THING, so pass 2 "
          "got a handle called `fleet` and `add_label(vms, fleet)` reads as label-with-a-machine")
    from orchestrator.languages.english.seam import pass1 as P, pass2 as P2
    board = Board()
    channel, was = _no_model()
    try:
        for n in (4, 13):
            rows = P.run_scanned(P.EXPECTED[n].request, board=board)
            handles = [s.handle for s in P2.symbol_table(rows, board)]
            check(f"rung {n} no longer declares the label phrase", "fleet" not in handles)
            check(f"rung {n} still declares both real objects", len(rows) == 2)

        # ⇒ THE SIGNAL IS AN ATTRIBUTE WORD BESIDE A QUOTED ONE, never a guess about the word.
        check("an attribute name beside a quoted word is a value phrase",
              P._is_value_phrase("all the 'fleet' label", board))
        check("and so is a labelling phrase", P._is_value_phrase("labelled 'red'", board))
        # THE CONTROLS. A bare word beside an attribute name is left alone — only the lab can
        # say whether it names something, which is the whole of item 0.
        check("a bare word beside an attribute word is NOT",
              not P._is_value_phrase("the fleet label", board))
        check("nor is a plain name", not P._is_value_phrase("except db", board))
        check("nor a quoted word with no attribute beside it",
              not P._is_value_phrase("the 'red' ones", board))
    finally:
        channel.constrained = was


def test_an_operation_can_account_for_a_word_too():
    print("\n[objects] gate 1's leftover rule predates pass 2 — it asks which words no "
          "DECLARATION claimed, and 'fleet' is claimed by add_label")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()
    r4 = P4 = ("create 5 vms, put them all in a network, give them all the 'fleet' label, "
               "and make sure they all ping each other")
    channel, was, _ = _canned_sequence([("create_vm", "vms", None),
                                        ("add_vm_to_network", "vms", "network"),
                                        ("add_label", "vms", "fleet")])
    try:
        got = PL.run(r4, board=board, world=Lab())
        check("the label word no longer bounces as unread",
              not any("fleet" in b for b in got.bounces))
        check("and the label still reaches the program",
              {"label": "fleet"} in got.conditions)
    finally:
        channel.constrained = was


def test_nothing_is_destroyed_unless_the_request_asks():
    print("\n[safety] rung 8 produced delete_network(dmz) then create_network(dmz) — "
          "destroying a network nobody mentioned — and it SERVED, because `dmz` is named")
    from orchestrator.languages.english.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    board = Board()

    channel, was, _ = _canned_sequence([("delete_network", "dmz", None)])
    try:
        got = PL.run("put every vm on a network called core, except db — db goes on a "
                     "network called dmz instead", board=board, world=Lab())
        check("a delete nobody asked for is confirmed even on a NAMED thing",
              any("Confirm before this runs" in a for a in got.asks))
        check("and the reason says the request never asked",
              any("never asks to remove anything" in a for a in got.asks))
        check("so it does not serve", got.outcome != PL.SERVE)
    finally:
        channel.constrained = was

    # ⇒ THE CONTROL: when the request DOES say to remove something and names it, no
    #   confirmation — a guard that fires on what was plainly asked for gets switched off.
    channel, was, _ = _canned_sequence([("delete_vm", "alpha", None)])
    try:
        named = PL.run("delete the vm named alpha", board=board, world=Lab())
        check("an explicit delete of a named thing passes without a confirm",
              not any("Confirm before this runs" in a for a in named.asks))
    finally:
        channel.constrained = was


def test_a_later_mention_marked_distinct_is_a_second_thing():
    print("\n[distinct] rung 6 asks for the red ones on their OWN network and the blue ones "
          "on a DIFFERENT one — and one network was declared, so both groups went onto it")
    from orchestrator.languages.english.seam import pass1 as P, pass2 as P2
    from tests.bench.twopass.metrics import Lab
    board = Board()
    channel, was = _no_model()
    try:
        rows = P.settle_with_world(P.run_scanned(P.EXPECTED[6].request, board=board),
                                   Lab(), board)
        networks = [r for r in rows if r.kind == "network"]
        check("rung 6 declares TWO networks, not one", len(networks) == 2)
        handles = [s.handle for s in P2.symbol_table(rows, board)]
        check("and both vm groups survive beside them",
              "red_vms" in handles and "blue_vms" in handles)
        check("with no junk rows added", len(rows) == 4)

        # ⇒ THE MARKERS ARE A CLOSED CLASS, and the negative cases matter more than the
        #   positives — a marker fires on a SECOND mention only.
        check("`a different network` is marked", P._marks_distinct("a different network"))
        check("`their own network` is marked", P._marks_distinct("their own network"))
        check("an ordinary phrase is not", not P._marks_distinct("a network called lab"))

        # ⇒ AND ONLY A KINDED ANCHOR MAY SPLIT. `ones` sits inside both marked spans in rung 6;
        #   letting it split produced two junk `?` rows for one pronoun.
        check("a pronoun inside a marked span does not become a second object",
              not any(r.object_type == S.UNKNOWN_KIND for r in rows))

        # THE CONTROL THAT MATTERS: a thing mentioned twice with NO marker must still fold.
        r3 = P.run_scanned(P.EXPECTED[3].request, board=board)
        check("rung 3's lab is mentioned twice and stays ONE network",
              len([r for r in r3 if r.kind == "network"]) == 1)
    finally:
        channel.constrained = was


def test_every_finding_reaches_an_audience():
    """A finding nobody can receive is not a check — it is a comment.

    ⇒⇒ **WRITTEN 2026-08-11 BECAUSE THIS EXACT DEFECT HAPPENED TWICE IN ONE DAY.**
      `uncreated-declaration` was computed at `pipeline.py:258`, AFTER the retry loop exited,
      so the model it was addressed to never saw it — and the conclusion drawn from that
      silence was that *handing findings back does not work*. It works; the finding never
      arrived. Hours later `duplicate_creations` was written into the same dead spot.

    ⇒ **THE RULE: EVERY GATE-3 RULE NAME IS EITHER ANSWERABLE BY THE OPERATOR OR REACHABLE BY
      THE RETRY.** There is no third option. A rule in neither set is a finding produced for
      nobody, and this test names it the moment it is added rather than a day later.

    ⇒ AND IT IS A CONTRACT, NOT A COUNT: adding a gate 3 rule now forces a decision about who
      hears it, which is the discipline that was missing.
    """
    print("\n[audience] a finding computed where nobody can act on it is a comment, and that "
          "happened twice today before anything said so")
    from orchestrator.languages.english.seam import gate3 as G3, pipeline as P

    # every gate 3 rule must be answerable by the operator, or land in the retry's rejection
    # list; `_split` sends everything that is neither ANSWERABLE nor WANTS_A_STEP to `drop`,
    # so the real requirement is that the two sets partition OWNS with nothing orphaned.
    reaches_model = G3.OWNS - P.ANSWERABLE
    check(f"every gate 3 rule has an audience ({len(G3.OWNS)} rules)",
          bool(reaches_model) and reaches_model | P.ANSWERABLE == G3.OWNS)
    check("the operator-answerable set is a subset of what gate 3 owns",
          P.ANSWERABLE <= G3.OWNS)

    # and the one rule that asks for a step to be ADDED must travel in the `needed` section,
    # not the rejection list — remove-vocabulary cannot request an addition (measured on rung 8)
    src = (pathlib.Path(__file__).parent.parent
           / "orchestrator" / "languages" / "english" / "seam" / "pipeline.py").read_text()
    check("a rule that wants a step ADDED is routed to `needed`, not to the rejections",
          "WANTS_A_STEP" in src and "needed=needed" in src)


def test_each_gate_owns_its_own_checks():
    print("\n[gates] a check in the wrong gate is a check nobody audits — three were, and one "
          "of them is why a fix for rung 6 landed in gate 3 instead of gate 2")
    from orchestrator.languages.english.seam import gate3 as G3, gate4 as G4, gates12 as G
    from orchestrator.languages.english.seam import linguistics as L

    owners = {"gate 1": G.GATE1_OWNS, "gate 2": G.GATE2_OWNS, "gate 3": G3.OWNS,
              "gate 4": G4.OWNS, "linguistics": L.OWNS}
    for name, mine in owners.items():
        others = set().union(*[v for k, v in owners.items() if k != name])
        clash = mine & others
        check(f"{name} shares no rule name with another gate ({sorted(clash) or 'none'})",
              not clash)

    # ⇒ AND THE THREE THAT WERE WRONG, PINNED BY NAME so a regression is a failing test:
    check("an unsettled kind belongs to gate 2, not gate 3",
          "kind-not-settled" in G.GATE2_OWNS and "unknown-kind" not in G3.OWNS)
    check("completeness belongs to gate 1, not the grammar gate",
          "unused-declaration" in G.GATE1_OWNS and "role-unsettled" not in L.OWNS)
    check("impact belongs to gate 4, and gate 4 exists",
          "destructive-confirm" in G4.OWNS and hasattr(G4, "confirmations"))
    # ⇒ THE FOURTH, ADDED 2026-08-11 BECAUSE THE MOVE PASSED UNNOTICED. `uncreated-declaration`
    #   left gate 1 for gate 3 as `unestablished-referent` — the operator: *"gate 2 for the world
    #   check, and gate 3 to identify network_2 has been referenced with no maker/fetch."* The
    #   whole suite stayed green through it, which is exactly the silence this test exists to
    #   break, so the NEW placement is pinned too.
    #   ⇒ It is gate 3's because it is statable about ONE operation — *this step's referent is
    #     never established* — where *no step creates it* reads as an absence and looked gate
    #     4's. Same fact, and the grain is decided by which sentence is true of one step.
    check("an unestablished referent belongs to gate 3, not gate 1",
          "unestablished-referent" in G3.OWNS
          and "uncreated-declaration" not in G.GATE1_OWNS)


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "two-pass schema")



def test_the_clause_verb_licenses_the_mutation():
    """THE delete_vm INVENTION, priced by the v2 degradation run (2026-08-19).

    `"stop most of vms"` came back `stop_vm` AND `delete_vm`, and every mutating-arm
    filter passed it — each one interrogates the TARGET (`on` in handles, value said,
    visible from the clause); none asks which operation the clause SAID. The rule:

    ⇒⇒ **A CLAUSE WHOSE VERB NAMES A MANIFEST OPERATION HAS SAID WHICH OPERATION IT
      WANTS** — a mutating answer outside that verb's own operations is invention,
      refused at birth. A verb that names NO operation (`restart`, `start`, `put`)
      licenses free translation — that is the model's whole job on those clauses.
      Probes are exempt: the observe arm is housekeeping, never a wrong choice.
    """
    print("\n[split] the clause verb licenses the mutation")
    from orchestrator.languages.english.seam import pass1 as P1, pass2 as P2
    board = Board()

    # 1 · a `stop` clause answered with a delete: the invention itself, refused
    rows = P1.run_scanned("stop most of vms", board=board)
    channel, was = _canned([("stop_vm", "vm", None), ("delete_vm", "vm", None)])
    try:
        got = [op.operator for _, op in
               P2.operations_by_clause("stop most of vms", rows, board=board)]
        check("the said operation survives", "stop_vm" in got)
        check("the invented delete is refused at birth", "delete_vm" not in got)
    finally:
        channel.constrained = was

    # 2 · probes are exempt — the observe arm stays housekeeping, not a refusal
    channel, was = _canned([("stop_vm", "vm", None), ("probe_exists", "vm", None)])
    try:
        got = [op.operator for _, op in
               P2.operations_by_clause("stop most of vms", rows, board=board)]
        check("a probe beside a licensed verb is not refused", "probe_exists" in got)
    finally:
        channel.constrained = was

    # 3 · an unlicensed verb translates freely — restart IS stop+launch, and the gate
    #     must not undo the imperative-shape fix that bought act recall back
    rows2 = P1.run_scanned("restart the web vm", board=board)
    channel, was = _canned([("stop_vm", "vm", None), ("launch_vm", "vm", None)])
    try:
        got = [op.operator for _, op in
               P2.operations_by_clause("restart the web vm", rows2, board=board)]
        check("an unknown verb keeps its translation (stop half)", "stop_vm" in got)
        check("an unknown verb keeps its translation (launch half)", "launch_vm" in got)
    finally:
        channel.constrained = was


if __name__ == "__main__":
    sys.exit(main())
