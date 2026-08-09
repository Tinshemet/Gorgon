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
    # ⇒ TWO AUDIENCES, AND THEY ARE PHRASED DIFFERENTLY. What the request does not settle is
    #   a QUESTION for the operator. A residual is not that — the operator already said those
    #   words — so it is an INSTRUCTION to the model to read again. Asserting every finding
    #   ends in a question mark conflated the two.
    from tests.bench.twopass import gates12 as _G
    asks = [f for f in found if f not in _G.bounces(found)]
    check("what the operator must settle is phrased as a question",
          asks and all("?" in f.says or "did you" in f.says for f in asks))
    check("and nothing is repaired — the rows are untouched",
          [(r.name, dict(r.where)) for r in made_up] == [("quarantine", {"label": "urgent"})])


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


def test_gate_1_bounces_a_residual_back_to_the_model():
    print("\n[bounce] an object may stand alone; a descriptor may not. What no declaration "
          "claims is a clause nobody read — and it goes back to the AI, not to the operator")
    from tests.bench.twopass import gates12 as G
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
    from tests.bench.twopass.scan import scan, scan_all
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
    from tests.bench.twopass import gates12 as G, pass1 as P
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
    from tests.bench.twopass import pass1 as P

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
    from tests.bench.twopass import pass1 as P, residue as R
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
        check("junk beside an attribute word becomes a condition VALUE",
              any(r.where.get("network") == "wibblesome" for r in promoted))
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
    from tests.bench.twopass import gates12 as G, pass1 as P, residue as R
    board = Board()
    channel, was = _no_model()
    try:
        bound = "create 3 vms labelled 'edge' and put the edge ones on a network"
        rows = P.run_scanned(bound, board=board)
        check("a value quoted earlier in the request BOUNCES",
              [r.verdict for r in R.report(rows, bound, board)] == [R.BOUNCE])
        report = G.report(rows, bound, board)
        check("so it reaches the model, not the operator",
              any(f.kind == "unread-value" for f in report["bounces"]))
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
    from tests.bench.twopass import scan as SC
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
    from tests.bench.twopass import gates12 as G, pass1 as P
    from tests.bench.twopass.effects import Operation, conditions_after, flatten
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
    from tests.bench.twopass import pass1 as P
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
    from tests.bench.twopass import pass1 as P, pass2 as P2
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
    from tests.bench.twopass import pass2 as P2
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
    from tests.bench.twopass import gate3 as G3, pass1 as P, pass2 as P2
    from tests.bench.twopass.effects import Operation
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
        check("every step of the ping mesh is illegal", len(G3.check(mesh, t9, board)) == 4)
        check("so the request is REFUSED, not half-served", G3.refused(mesh, t9, board))
        check("and the reason names what is missing",
              "nothing says what" in G3.check(mesh, t9, board)[0].says)

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
        check("and a run-time set is a perfectly legal target",
              not G3.check([Operation("stop_vm", "not_alive_vms", None)], t11, board))

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


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "two-pass schema")


if __name__ == "__main__":
    sys.exit(main())
