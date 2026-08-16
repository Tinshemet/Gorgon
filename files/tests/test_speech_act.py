"""test_speech_act.py — the interrogative reader, pinned against a key written before it.

`orchestrator/seam/speech_act.py` reads WHAT KIND OF THING was said — an order, a question, a
piece of teaching — from closed classes plus one manifest lookup. Its bar is not *"does it
catch questions"*; it is **does it never read a question as an instruction**, because that is
the one direction that cannot be taken back.

The pins, in order of what matters:

    1  THE FOUR LIVE FAILURES of 2026-08-14 read as questions — including the one that came
       back as `add_label(fleet_vms, fleet)`
    2  the polite imperative is still an ORDER, which is the case the model got 0/14 on
    3  the arm table holds at 56/56, and the controls at their measured floor
    4  the key and the reader still name the types with the same strings
    5  IT ROUTES NOTHING — the seam must not import it yet

⚠ AND THE CEILING: every sentence here is one I wrote. This pins the RULES against
  regression; it is not evidence about English. A1 on the open list is.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.seam import speech_act as SA
from planner.formula.legal import Board
from tests.bench import sentence_key as KEY
from tests.bench.twopass import mood_probe

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_the_four_that_failed_live():
    """2026-08-14, through the live chain: four questions, none read as one.

    The fourth is the one that matters — *"how many machines carry the 'fleet' label"* came
    back `act` with `add_label(fleet_vms, fleet)` attached. A question answered by labelling
    things is the false serve this whole item exists to prevent.
    """
    board = Board()
    for q in ("how many vms are there",
              "list the vms",
              "which vms are running",
              "how many machines carry the 'fleet' label"):
        check(f"a question reads as one — {q!r}", SA.verdict(q, board) == SA.QUESTION)


def test_the_polite_imperative_is_an_order():
    """The single case that defeats every lexical rule, and the model's worst arm — 0 of 14.

    ⇒ `is alpha running?` is the twin that keeps the rule honest: identical inversion,
      identical absence of a wh-word, and a manifest verb in both. Only the SUBJECT differs.
    """
    board = Board()
    for order in ("can you delete the vms?",
                  "could you please stop every vm?",
                  "would you mind stopping the web server",
                  "will you launch alpha for me",
                  "i'd like you to take a snapshot of db"):
        check(f"a polite imperative is an order — {order!r}",
              SA.verdict(order, board) == SA.ORDER)
    check("but the same inversion over a LAB THING is a question — 'is alpha running?'",
          SA.verdict("is alpha running?", board) == SA.QUESTION)
    check("and an existential inversion is too — 'are there any stopped vms?'",
          SA.verdict("are there any stopped vms?", board) == SA.QUESTION)


def test_every_interrogative_form_is_read():
    """THE WHOLE TAXONOMY, one pin per form — the operator's ask, 2026-08-15.

    Polar and wh are the two everyone names. The rest are where an interrogative wears a
    declarative's clothes, and each needs its own closed-class signal:

        alternative   inverted, closed answer set        falls out of the polar rule
        declarative   no inversion, no wh                the MARK, read last
        tag           declarative + inverted tag         the mark again, after the split
        echo          wh IN SITU                         the mark again
        elliptical    no verb at all                     the mark again
        embedded      SYNTACTICALLY NOT A QUESTION       recipient · `whether` · subordinate wh
        exclamative   a wh-word and NOT a question       wh with no predicate
    """
    board = Board()
    forms = [
        ("alternative", "is alpha running or stopped?", SA.QUESTION),
        ("deliberative", "should i delete db or keep it?", SA.QUESTION),
        ("rising declarative", "alpha is running?", SA.QUESTION),
        ("tag", "alpha is running, isn't it?", SA.QUESTION),
        ("echo", "you deleted what?", SA.QUESTION),
        ("elliptical", "and the network?", SA.QUESTION),
        ("embedded · recipient", "show me the vms", SA.QUESTION),
        ("embedded · wh", "tell me how many vms are running", SA.QUESTION),
        ("embedded · whether", "check whether alpha is running", SA.QUESTION),
        ("embedded · first person", "i want to know which vms are stopped", SA.QUESTION),
        ("exclamative", "what a mess", SA.NEITHER),
    ]
    for name, text, want in forms:
        check(f"{name}: {text!r} -> {want}", SA.verdict(text, board) == want)
    # ⇒ AND THE ORDERS THAT WEAR THE SAME CLOTHES ARE UNMOVED. Each is the near-twin of a line
    #   above, and the pair is what proves the rule is structural rather than a mark-detector.
    for text in ("can you delete the vms?", "stop the vms", "give them the fleet label"):
        check(f"and its twin is still an order — {text!r}",
              SA.verdict(text, board) == SA.ORDER)


def test_the_question_decides_the_shape_of_its_answer():
    """A QUESTION READ IS NOT A QUESTION ANSWERED.

    Every asked goal was `shape: count`, so *"which vms are running"* would have come back
    **3** — a number, to a question that asked for a list. The wh-word already says which is
    wanted, and it is the same nine closed words read for a second purpose.

    ⇒ **AND `None` IS THE VALUE THAT MATTERS MOST.** A bare *"how do i create a vm?"* wants a
      PROCEDURE. Neither a count nor a list is that, so no goal is produced, `queryable` stays
      false, and `answer_not_act` reaches its honest branch — *"there is no answerable form of
      it to offer instead"* — rather than confidently answering a different question.
    """
    board = Board()
    for text, want in [("how many vms are there", SA.COUNT),
                       ("tell me how many vms are running", SA.COUNT),
                       ("is alpha running?", SA.COUNT),          # polar: has it any members
                       ("which vms are running", SA.MEMBERS),
                       ("what is on the lab network", SA.MEMBERS),
                       ("list the vms", SA.MEMBERS),
                       ("show me the vms", SA.MEMBERS),
                       ("how do i create a vm named alpha?", None),
                       # ⇒ THE THREE WH-WORDS WHOSE ANSWERS THIS SYSTEM CANNOT PRODUCE: a
                       #   place, a time, a reason. `where` was listed as a member-word and
                       #   routed *"where is alpha"* to a select — answering a different
                       #   question confidently, which is worse than declining.
                       ("where is alpha", None),
                       ("when did you stop it?", None),
                       ("why did db stop", None)]:
        check(f"{text!r} wants {want}", SA.answer_shape(text, board) == want)

    # ⇒ AND THE TWO SHAPES REACH THE WRITER AS DIFFERENT PROGRAMS — a number and the machines
    #   themselves. `render` has always been able to say both; nothing ever asked for the set.
    import importlib
    render = importlib.import_module("planner.ir.render")
    counted = render._statement(
        {"op": "query", "var": "answer1", "count": {"kind": "vm", "status": "running"}}, "", {})[0]
    listed = render._statement(
        {"op": "query", "var": "answer1", "select": {"kind": "vm", "status": "running"}}, "", {})[0]
    check("a count question renders as COUNT(...)", "COUNT(" in counted)
    check("a members question renders as a plain SELECT", "COUNT(" not in listed and "SELECT" in listed)



    from planner.ghost_writer import as_program, queryable
    check("both shapes are answerable",
          queryable({"shape": "count", "select": {"kind": "vm"}})
          and queryable({"shape": "members", "select": {"kind": "vm"}}))
    check("and a shape with no query form still is not",
          not queryable({"shape": "reach", "select": {"kind": "vm"}}))

    # ⇒⇒ **AND IT VALIDATES AND RUNS AND RETURNS THE RIGHT ANSWER.** The operator asked
    #   directly — *"does the pipeline work end to end, even at the medusa level?"* — and
    #   until this ran, the honest answer was that a program had been EMITTED and never
    #   executed. Rendering the right text is not the same claim as answering the question.
    #
    #   ⇒ ⚠ **AGAINST THE SIMULATED WORLD, WHICH IS THE LIMIT OF THE CLAIM.**
    #     `planner.model_world.World` is a real IR interpreter over a world that cannot
    #     refuse. Real QEMU has never executed a program from this layer (I13), and the
    #     simulator says yes to things QEMU does not.
    import importlib
    from planner.ir import config as _config
    from planner.model_world import World
    _exec = importlib.import_module("planner.ir.execute")

    world = World(kinds=_config.KINDS)
    for nm, status in (("a", "running"), ("b", "running"), ("c", "stopped")):
        world.state.setdefault("vm", {})[nm] = {"name": nm, "status": status}
    select, holds = world.seams

    def _answer(shape):
        prog = as_program([], [{"shape": shape, "select": {"kind": "vm", "status": "running"},
                                "asks": True}], world=None, witness=False)
        ok, problems = importlib.import_module("planner.ir.validate").validate(prog)
        out = _exec.run(prog, world.execute, select=select, holds=holds)
        return ok and not problems, out

    ok_c, ran_c = _answer("count")
    ok_m, ran_m = _answer("members")
    check("both query programs VALIDATE", ok_c and ok_m)
    check(f"a count question answers with the number — {ran_c.get('scope')}",
          ran_c["ok"] and ran_c["scope"].get("answer1") == 2)
    check(f"a members question answers with the machines — {ran_m.get('scope')}",
          ran_m["ok"] and ran_m["scope"].get("answer1") == ["a", "b"])

    # ⇒⇒ **AND THE WHOLE WAY THROUGH TO A PROGRAM, WHICH IS THE ONLY VERSION THAT COUNTS.**
    #   The emitter was changed to honour the shape and NOT run end to end for an hour — the
    #   built-and-never-called shape, introduced by the person who had spent the morning
    #   writing about it. A goal that produces the right dict and no program answers nobody.
    def _text(shape):
        prog = as_program([], [{"shape": shape, "select": {"kind": "vm", "status": "running"},
                                "asks": True}], world=None, witness=False)
        return render.render(prog)

    counted_prog, listed_prog = _text("count"), _text("members")
    check("a count question becomes STORE … = QUERY COUNT(…); PUBLISH(…)",
          "QUERY COUNT(SELECT vm WHERE status = 'running')" in counted_prog
          and "PUBLISH(answer1)" in counted_prog)
    check("a members question becomes STORE … = QUERY SELECT …; PUBLISH(…)",
          "QUERY SELECT vm WHERE status = 'running'" in listed_prog
          and "COUNT(" not in listed_prog and "PUBLISH(answer1)" in listed_prog)


def test_a_subordinate_wh_is_not_a_question():
    """*"when you get a chance, take a snapshot"* is an ORDER with a courtesy on the front.

    ⇒⇒ **THIS IS [[gorgon-courtesy-escalates-intent]] IN THE OTHER DIRECTION.** That one had a
      pleasantry GRANT write authority; this one had a pleasantry REMOVE it — `when you get a
      chance` is one of the `filler` arm's openers, and reading its `when` as interrogative
      turned three polite orders into questions. Same defect class: a courtesy deciding what
      the sentence is for.

    ⇒ **AND IT WAS MASKED BY A SECOND BUG.** `get` looked like an acting verb, so the clause
      hit the addressee-order branch and came out an ORDER — right answer, wrong reason. Fixing
      `effects.askers` removed the accident and this surfaced. A corrected lookup earning its
      keep by breaking something.
    """
    board = Board()
    for text in ("when you get a chance, take a snapshot of every running vm",
                 "when you get a chance, make sure exactly 3 vms carry the 'prod' label",
                 "if you don't mind, stop every vm"):
        check(f"a courtesy adjunct leaves the order an order — {text[:44]!r}",
              SA.verdict(text, board) == SA.ORDER)
    # ⇒ AND THE INVERTED TWIN IS STILL A QUESTION. The pair is what proves it is inversion
    #   doing the work rather than the word `when`.
    check("but an INVERTED `when` still asks — 'when did you stop it?'",
          SA.verdict("when did you stop it?", board) == SA.QUESTION)
    check("and a wh-phrase that IS the subject still asks — 'how many vms are there'",
          SA.verdict("how many vms are there", board) == SA.QUESTION)


def test_an_instruction_not_to_act_holds_the_program():
    """N3 — the operator, 2026-08-14: *"'good morning doorman, dont start any changes, but how
    do i create a new machine?' might trigger the AI to act even though its not the intent."*

    Verified that day: `mood_of` returned `do` for that sentence AND for the bare imperative
    `create a new machine` — byte-identical. The instruction NOT to act was read as one to act.

    ⇒ **META-CONTROL IS THE ONE NON-DIRECTIVE TYPE THAT NEEDED NO NEW STORE.** An assertive
      needs the Encyclopedia (zero code); a declaration needs an amendment filed. This one
      REMOVES AN OPTION, which is the other way a rung closes.

    ⇒ AND THE DISCRIMINATOR IS THE OBJECT, NOT A WORD LIST: `stop the vms` takes a kind the
      manifest knows; `don't start any changes` takes `changes`, which is not a kind.
    """
    from orchestrator.seam import gate4
    from orchestrator.seam.effects import Operation
    board = Board()
    acts = [Operation("create_vm", "alpha", None)]

    for said in ("don't start any changes, but create a vm named alpha",
                 "don't do anything yet, but create a vm named alpha",
                 "don't touch the lab, but create a vm named alpha"):
        check(f"a program is held when told not to act — {said[:34]!r}",
              gate4.told_not_to_act(acts, said, board))

    check("and a plain order is untouched",
          not gate4.told_not_to_act(acts, "create a vm named alpha", board))
    check("`stop the vms` is an ORDER, not a conversation control — it names a kind",
          not gate4.told_not_to_act(acts, "stop the vms", board))
    check("a read-only program is not held either — nothing would change",
          not gate4.told_not_to_act([Operation("vm_status", "vms", None)],
                                    "don't start any changes", board))

    # ⇒ THE LADDER CONTROL, MEASURED RATHER THAN ASSUMED: no rung carries a meta-control
    #   clause, so this cannot cost a SERVE on the corpus.
    from tests.bench.rungs import RUNGS
    noisy = [r.n for r in RUNGS if gate4.told_not_to_act(acts, r.goal, board)]
    check(f"silent on every literal rung — {noisy or 'all 14'}", not noisy)


def test_a_statement_does_not_build_anything():
    """*"a jumpbox is a vm"* came back with `create_vm(jumpbox)` attached.

    ⇒⇒ **TELLING THE SYSTEM WHAT A WORD MEANS WOULD HAVE BUILT A MACHINE CALLED `jumpbox`.**
      An assertive is the highest-value input this system can receive — the only channel that
      teaches without more corpus — and it was being answered with a creation. Found by
      pointing the `--seam` door at it, ten minutes after the door existed.

    ⇒ THE THIRD OF ONE FAMILY, each guarding a different sentence type and all three asking
      rather than refusing: answer_not_act · told_not_to_act · statement_not_act.
    """
    from orchestrator.seam import gate4
    from orchestrator.seam.effects import Operation
    board = Board()
    acts = [Operation("create_vm", "jumpbox", None)]

    check("a statement beside an acting program is asked about",
          gate4.statement_not_act(acts, "a jumpbox is a vm", board))
    check("an ORDER is untouched",
          not gate4.statement_not_act(acts, "create a vm named jumpbox", board))
    check("a QUESTION is untouched — answer_not_act owns that one",
          not gate4.statement_not_act(acts, "how many vms are there", board))
    check("and a read-only program is not held — nothing would change",
          not gate4.statement_not_act([Operation("vm_status", "vms", None)],
                                      "a jumpbox is a vm", board))

    # ⇒ THE LADDER CONTROL: no rung is read as a statement, so this cannot cost a SERVE.
    from tests.bench.rungs import RUNGS
    noisy = [r.n for r in RUNGS if gate4.statement_not_act(acts, r.goal, board)]
    check(f"silent on every literal rung — {noisy or 'all 14'}", not noisy)


def test_the_manifest_says_which_tools_only_read():
    """`askers` held TWO tools and should have held fifteen — found 2026-08-15.

    It read only `observed.<fact>.by`, so its complement `actors` claimed every enumerator and
    every read-back in the manifest. Two live consequences: `produces()` called a `vm_status`
    program `act`, and `show me the vms` read as an ORDER at the front seam.

    ⇒ IT COULD NOT BE DERIVED — `state` (*"ask the process what state it is in"*) and `kill`
      (*"stop it NOW"*) are structurally identical in the manifest and differ only in prose.
      So it is DECLARED at the tool, `"reads": true`, and read from there.
    """
    from planner.ir import config as _config, effects as _effects
    asking = _effects.askers(_config.KINDS)
    acting = _effects.actors(_config.KINDS)
    for tool in ("vm_status", "show_config", "get_vm_logs", "snapshot_list", "check_disk",
                 "print_command", "fingerprint_vm", "monitor_vm", "list_vms", "guest_ping"):
        check(f"{tool} only reads", tool in asking and tool not in acting)
    # ⇒ AND THE CONSERVATIVE HALF: anything that EXECUTES or ATTACHES stays acting, whatever
    #   its doc says it does. Calling a mutating tool a reader is what would let a fetch change
    #   the lab, so doubt resolves toward acting.
    for tool in ("guest_probe", "open_shell", "open_display", "send_monitor_cmd",
                 "run_guest_command", "stop_vm", "delete_vm"):
        check(f"{tool} still acts", tool in acting and tool not in asking)

    from orchestrator.seam.pipeline import produces
    from orchestrator.seam.effects import Operation
    check("a program that only reads is not an act",
          produces([Operation("vm_status", "vms", None)], []) != "act")
    check("and one that stops machines still is",
          produces([Operation("stop_vm", "vms", None)], []) == "act")


def test_the_manifest_decides_where_grammar_cannot():
    """`list the vms` and `stop the vms` are the same sentence. Only the operation differs."""
    board = Board()
    check("`list the vms` asks — its operation cannot touch anything",
          SA.verdict("list the vms", board) == SA.QUESTION)
    check("`stop the vms` acts — same grammar, opposite operation",
          SA.verdict("stop the vms", board) == SA.ORDER)
    check("and the split is read from the manifest, not listed",
          SA.changes_the_world("list", board) is False
          and SA.changes_the_world("stop", board) is True)


def test_a_question_governs_the_clauses_it_frames():
    """*"how do i create a vm and then launch it?"* is ONE question, not a question and an order.

    The clause split cuts it in half and order-wins then eats it — 7/14 on both question arms
    before the scope rule, every miss a false serve.
    """
    board = Board()
    check("a wh-question about an act governs what follows it",
          SA.verdict("how do i create a vm named beta and then launch it?", board) == SA.QUESTION)
    check("a COMPLETE question does not — the order after it is real",
          SA.verdict("how many vms are there, and stop the stopped ones", board) == SA.ORDER)


def test_the_arm_table_holds():
    """56/56 on the four arms. The regression half — and it is the easy half."""
    board = Board()
    tally, misses = mood_probe.arms(board)
    for arm, (right, total) in tally.items():
        check(f"arm {arm} reads {KEY.ARM_VERDICT[arm]} {right}/{total}", right == total)
    check("no arm cell regressed", not misses)


def test_the_controls_hold_at_their_measured_floor():
    """46/48 projection, 36/48 type — MEASURED 2026-08-15 over the FULL interrogative taxonomy.

    ⇒⇒ **THE TWO MISSES ARE NAMED RATHER THAN ROUNDED AWAY, AND BOTH FAIL TOWARD ASKING.**

        "make me a vm"          `me` is a BENEFACTIVE here, not a recipient of information,
                                and the recipient rule cannot tell them apart. The rule buys
                                `show me the vms` — an embedded question that used to be
                                CARRIED OUT — and this is its price.
        "n1 is the jumpbox,     `pass2.clauses_of` rejoins it: a piece with no manifest verb
         so put it on core"     is treated as a list member, which is the rule that keeps
                                "n1, n2 and n3" whole. Belongs to the splitter's owner, not to
                                a second splitter here.

    ⇒ **NEITHER IS A FALSE SERVE, AND THAT IS THE PROPERTY WORTH PINNING.** A false avoid costs
      a question; a false serve cannot be taken back. If a future change trades one of these
      away, it must not trade it for the other kind.
    """
    board = Board()
    rows, proj, typed, _unsettled = mood_probe.controls(board)
    check(f"controls · projection {proj}/{len(KEY.CONTROLS)} (floor 46)", proj >= 46)
    check(f"controls · type {typed}/{len(KEY.CONTROLS)} (floor 36)", typed >= 36)
    # ⇒ AND NO MISS MAY BE A FALSE SERVE — a keyed question read as an order.
    served = [k.text for k, got, _acts, ok, _ in rows
              if not ok and k.says == KEY.QUESTION and got == KEY.ORDER]
    check(f"no keyed QUESTION is read as an ORDER — {served or 'none'}", not served)


def test_the_key_and_the_reader_still_agree():
    """Declared twice on purpose — production may not import `tests/`, and a key may not
    import what it grades. Agreement by value is the price, and it is asserted."""
    check("key and reader name the types identically", not mood_probe._vocabularies_agree())


def test_where_it_is_wired():
    """⇒⇒ **THE READER HAS TWO CALLERS AND THIS NAMES BOTH.** Step 2 pinned the opposite — that
    NOTHING imported it — because a reader wired to nothing cannot move the ladder, which is
    what made it safe to land before the operator had decided what a question should DO.

    Step 3 wired it, so the pin flips from *nowhere* to *exactly here*:

        gate4.asked_goals     a question becomes a queryable goal, so `produces()` can
                              return `ask` — the branch that shipped with nothing to feed it
        gate4.answer_not_act  the information-intent trigger the file's own note asked for,
                              replacing residue as a stand-in
        gate4.told_not_to_act an instruction not to act holds the program
        pass1.consume_meta_control   a clause about the conversation declares nothing
        pipeline              the leftover exemption for meta-control's own words
        shortcuts/plan.py     `plan --seam <request>` — the opt-in door
        archive.taught_by     an ASSERTIVE offers a knowledge entry
        governing.rules_from  a DECLARATION proposes a rule
        door.facts            N1 — the reading is a fact the regime ladder reads. **AND THIS
                              PIN IS WHY THE ADDITION IS RECORDED**: `door.py` is the first
                              caller that is not part of the seam, and it reads the speech act
                              BEFORE anything decides a request belongs to the seam at all

    ⇒ **A NAMED LIST, NOT A COUNT.** [[gorgon-built-and-never-called]] is this project's
      dominant defect class and its mirror is a thing called from more places than anyone
      knows. A new caller has to be added here deliberately.

    ⇒ ⚠ **IT COUNTS IMPORTS, NOT MENTIONS, AND THE FIRST VERSION DID NOT.** A sentence naming
      `speech_act.answer_shape` in a `ghost_writer` comment tripped it — the pin was measuring
      whether the string appears, which makes documenting a seam look like coupling to it and
      would teach the reader to stop writing the comment.
    """
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = subprocess.run(
        ["grep", "-rlnE", "--include=*.py",
         r"^\s*(from [.a-z_]* import .*speech_act|import .*speech_act|from \. import.*speech_act)",
         os.path.join(root, "orchestrator"), os.path.join(root, "planner"),
         os.path.join(root, "engines")],
        capture_output=True, text=True).stdout
    callers = {os.path.basename(p) for p in out.split() if not p.endswith("speech_act.py")}
    check(f"the reader's importers are exactly the seven named here — {sorted(callers)}",
          callers == {"gate4.py", "pass1.py", "pipeline.py", "plan.py", "archive.py",
                      "governing.py", "door.py"})


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "speech act")


if __name__ == "__main__":
    sys.exit(main())
