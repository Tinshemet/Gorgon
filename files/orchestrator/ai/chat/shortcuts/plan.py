"""plan.py — `plan <request>`: route one request through the ENGINE ARCHITECTURE.

OPT-IN, AND DELIBERATELY NOT THE DEFAULT. The architecture behind this is measured — the
ghost writer covers 13/13 rungs and 1932/2000 generated cases, across two unrelated domains,
with no model in the loop. What is NOT measured is the front seam: the extractor turns
English into components at 6/39, so making this the default would replace a chat flow that
works with one that mistranslates two requests in three.

That is the "if everything works" clause not being met, and shipping anyway would be the
exact failure of 2026-07-31 — a mechanism believed good because the parts around it were.

SO IT SITS HERE, WHERE IT CAN EARN THE SWAP. Typing `plan …` exercises the whole pipeline
against real requests and prints what each stage did, which is how the extractor gets real
evidence instead of thirteen rungs. The default path stays exactly as it was.

WHAT IT SHOWS, and why the printing matters as much as the running: each stage is named, so a
wrong answer says WHICH half was wrong. Under the old path a bad program could mean the goal
was misread or the writing fumbled and nothing distinguished them — a day went into that
ambiguity. Here `UNTRANSLATED` and `UNMET` are different words.
"""
from typing import List

from shared.display import console

from .base import Shortcut

_PREFIX = "plan "


class Plan(Shortcut):
    """`plan create a vm named alpha` — the engine path, one request.

    `plan --dry <request>` plans and shows, WITHOUT ACTING. It exists because this path is
    pointed at a real lab: the first thing it did against one was compute that "exactly two
    machines" needs seven deletions, naming vm-orchestrator and vm-executor among them. That
    is a fine thing to be told and a poor thing to discover. A dry run answers the only
    question worth asking first — WHAT WOULD THIS DO — and the in-session already knows,
    because every step declares its cost and what it would destroy before the verdict.
    """

    def matches(self, ui: str) -> bool:
        return ui.strip().lower().startswith(_PREFIX) and len(ui.strip()) > len(_PREFIX)

    @staticmethod
    def _ask_intent(question: str):
        """The one question, when the operator's own words did not answer it.

        RETURNS None ON ANYTHING ELSE, which `resolve` reads as unanswered and floors to
        FETCH. A typo must not be a grant: reading a lab you meant to change wastes a run,
        and changing a lab you meant to read cannot be undone. AN ABSENT TERMINAL IS THE
        SAME ANSWER — `intent.py`'s own rule is that with nobody to ask, it is FETCH.
        """
        console.print(f"\n[bold]{question}[/bold]")
        try:
            said = console.input("[bold cyan]fetch / ensure / achieve:[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            return None
        return said.strip().lower() or None

    @staticmethod
    def names_destroyed(step) -> list:
        """The members a step would destroy, BY NAME. Never a count.

        *"7 deletions"* and *"deletes vm-orchestrator"* are different sentences and only one
        of them stops a person.
        """
        return sorted({str(list(a.values())[0]) if a else "?" for _, a in step.destroys})

    @staticmethod
    def ask_destroy(step) -> bool:
        """*This destroys these machines — go ahead?* Default NO.

        WHY THIS EXISTS, MEASURED 2026-08-02. `create a vm` translates to an UNFILTERED
        `count(vm) = 1`, and against a nine-machine lab that is a goal satisfied by DELETING
        EIGHT. The dry run named them — `vm-orchestrator` and `vm-executor` among them, the
        machines Gorgon itself runs on — and a real run did the same thing while printing
        the list AFTERWARDS, under the heading "what it did".

        NOTHING WAS WRONG WITH THE WRITER. `count(vm) = 1` genuinely means "one machine in
        total", and rung 14 pins that behaviour deliberately: *"make sure there are exactly
        two machines"* SHOULD delete three. Measured at n=3, the two requests translate to
        the SAME GOAL — `create a vm` and `make sure there are exactly two machines` differ
        only in the amount — so no rule downstream can tell an increment from a population
        target. The language cannot say the difference.

        SO THE FIX IS NOT A GUESS, IT IS A QUESTION, and it belongs here because this is the
        one place with a person in it. An absent terminal is a NO, which is the same rule
        `intent` and `consent` already keep: with nobody to ask, take the answer that
        changes nothing.
        """
        gone = Plan.names_destroyed(step)
        console.print(f"\n[warn]this destroys {len(gone)} machine(s): "
                      f"{', '.join(gone)}[/warn]")
        try:
            said = console.input("[bold cyan]go ahead? (y/n):[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            return False
        return said.strip().lower() in ("y", "yes")

    @staticmethod
    def ask_clarify(question, session=None):
        """*Part of this was not understood — what did you mean?* Returns their words, or "".

        THE ONE PLACE WITH A PERSON IN IT, which is the same argument `ask_destroy` makes one
        method up: when the language cannot tell two readings apart, the fix is not a guess,
        it is a question, and it belongs where somebody can answer.

        ⇒ WHAT IS ASKED IS THE GATE'S OWN SENTENCE, not a paraphrase of it. The gates were
        built to phrase their findings in the operator's terms — *"it makes a vm and a network
        and never connects them. Did you mean them to be connected, or to stay apart?"* —
        and re-wording that here would put a second author between the finding and the person.

        ⇒ AN ABSENT TERMINAL IS SILENCE, NOT A GUESS. `EOFError` is a piped stdin and
        `KeyboardInterrupt` is somebody declining; both return "" and the refusal that was
        already coming stands. Same rule `ask_destroy` and `consent` keep: with nobody to ask,
        take the answer that changes nothing.
        """
        console.print(f"\n[warn]{question}[/warn]")
        try:
            said = console.input("[bold cyan]say that part again "
                                 "(or press enter to cancel):[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            return ""
        return said.strip()

    @staticmethod
    def ask_banned(banned) -> bool:
        """*This program names a tool your agent forbids — password to lift it.* Default NO.

        THE OPERATOR'S RULING, 2026-08-02: *"procedures dont require operator password. ONLY
        WHEN IT CONTAINS BANNED TOOLS, then you require an operator password."* Everything
        else a procedure meets is a QUESTION — y/n at a terminal. This is the one place that
        asks WHO you are, because a red line is what the contract wrote down to stop this
        exact agent, and a walk-up to an unlocked terminal must not be able to answer it.

        THE SAME RE-AUTH THE HIGH-IMPACT CLI COMMANDS USE, deliberately: forging a contract,
        switching the active agent, enacting a referendum. Lifting a red line belongs in that
        list and nowhere weaker.

        IT DEGRADES OPEN ONLY WHERE AUTH CANNOT APPLY — no auth package, or no operators yet
        (pre-bootstrap) — which is `_require_operator_password`'s own rule, kept rather than
        re-decided. Anywhere else: a logged-in operator AND a correct password, or no.
        """
        console.print(f"\n[bold red]RED LINE[/bold red] — this program calls "
                      f"{', '.join(banned)}, which this agent is forbidden to use.")
        try:
            from orchestrator.auth import sessions as _sessions, store as _store
        except ImportError:
            # NO AUTH PACKAGE AT ALL. The same degrade-open arm the CLI keeps, and the same
            # reason: a checkout without auth cannot ask, and refusing every red line there
            # would make the feature untestable rather than safe.
            return True
        if not _store.operators_exist():
            return True
        user = _sessions.current_username()
        if not user:
            console.print("[bold red]Login required.[/bold red] Run "
                          "[cyan]gorgon login[/cyan] first — nothing was run.")
            return False
        import getpass
        try:
            pw = getpass.getpass("Operator password to lift the red line: ")
        except (EOFError, KeyboardInterrupt):
            # AN ABSENT TERMINAL IS A NO, the rule `intent`, `consent` and `ask_destroy` all
            # keep: with nobody to ask, take the answer that changes nothing.
            return False
        if _store.verify_password(user, pw):
            console.print("[warn]red line lifted for this run.[/warn]")
            return True
        console.print("[bold red]Password incorrect — nothing was run.[/bold red]")
        return False

    @staticmethod
    def _ask_consent(question: str) -> bool:
        """`consent.py`'s question — *this changes the world and nothing checks it, sure?*

        ASKED HERE BECAUSE THIS IS WHERE THE PERSON IS. The engine used to answer it with a
        hardcoded `True`, which is an unattended run granting itself the permission a person
        was supposed to give. Absent this seam the answer is NO, and that is the right way
        round: the question is only ever reached by a program that vouches for nothing.
        """
        console.print(f"\n[warn]{question}[/warn]")
        try:
            said = console.input("[bold cyan]Run it anyway? (y/n):[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            return False
        return said.strip().lower() in ("y", "yes")

    @staticmethod
    def _seam_world():
        """The real lab, shaped the way the seam asks for one: `select(query)` and `names()`.

        ⇒ **THE PRODUCTION REGISTRY, NOT A SECOND ONE.** `active_library.LIBRARY` is what the
          engine path already folds every call back into, and `program.make_select` is the
          selector the planner already evaluates its ENSUREs against. Building a third reader
          of the lab here would be a third answer to *what does the world hold*.

        ⇒ **NAMES OR ROWS, EITHER IS FINE** — `gate4._name_select` already normalises both, and
          says so at its own definition. Nothing has to be reshaped on the way in.

        ⇒ AND `None` IS A LEGITIMATE ANSWER. A client-only checkout has no orchestrator
          registry; the seam runs with no world at all, every bare name stays kindless, and
          gate 2 asks about each one. Degraded, honest, and identical to the bench's
          `--no-lab` arm — never a silent empty lab, which is the failure `qemu.names` records.
        """
        try:
            from orchestrator.ai.active_library import LIBRARY
            from planner.program import make_select
        except Exception:
            return None
        chooser = make_select(LIBRARY)

        class _Lab:
            def select(self, query):
                try:
                    return chooser(query) or []
                except Exception:
                    return []

            def names(self):
                try:
                    return set(LIBRARY.known_names())
                except Exception:
                    return set()

        return _Lab()

    def _read_with_seam(self, request: str, verbose: bool) -> None:
        """Run the two-pass seam over one request and print what each stage read.

        ⇒ **EVERY STAGE NAMED, WHICH IS THE WHOLE REASON THIS DOOR IS WORTH HAVING.** The
          argument this file makes for printing the engine path applies unchanged: *"a wrong
          answer says WHICH half was wrong. Under the old path a bad program could mean the
          goal was misread or the writing fumbled and nothing distinguished them."* Here the
          reading, the declarations, the steps and the verdict are four separate lines.
        """
        from planner.formula.legal import Board
        from orchestrator.seam import speech_act as _speech
        from orchestrator.seam.pipeline import run as _seam_run

        world = self._seam_world()
        console.print(f"\n[bold]the two-pass seam[/bold]"
                      f"{'' if world else '  ·  [warn]no lab — every bare name stays kindless[/warn]'}")
        # ⇒ THE READING FIRST, BECAUSE IT IS WHAT DECIDES WHETHER A PROGRAM SHOULD EXIST AT
        #   ALL. An order, a question, or neither — per clause, and printed per clause.
        for clause, act in _speech.read(request, Board(), world):
            console.print(f"    [dim]{str(act or 'unread'):16}[/dim] {clause.strip()}")
        console.print(f"    [bold]-> {_speech.verdict(request, Board(), world)}[/bold]")

        got = _seam_run(request, board=Board(), world=world)
        console.print(f"\n    declared   {', '.join(got.handles) or '—'}")
        console.print(f"    steps      "
                      f"{[(o.operator, o.on, o.value) for o in got.operations] or '—'}")
        if got.goals:
            console.print(f"    goals      {list(got.goals)}")
        if got.suggested:
            console.print(f"    suggested  "
                          f"{[(o.operator, o.on, o.value) for o in got.suggested]}")
        for note in got.notices:
            console.print(f"      [dim]NOTICE   {note}[/dim]")
        for a in got.asks:
            console.print(f"      [bold yellow]ASK[/bold yellow]      {a}")
        for b in got.bounces:
            console.print(f"      [dim]BOUNCE   {b}[/dim]")
        console.print(f"\n    [bold]{got.outcome}[/bold]   "
                      f"[dim]produces: {got.produces or '—'}[/dim]")
        # ⇒ SAID EVERY TIME, NOT ONCE IN A DOCSTRING. This door reads; it does not act, and an
        #   operator who typed a destructive request should be told plainly that nothing ran.
        console.print("[dim]    nothing was run — `--seam` reads and shows[/dim]")

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        request = ui.strip()[len(_PREFIX):].strip()
        dry = seam = False
        for flag in ("--dry", "-n"):
            if request.lower().startswith(flag + " "):
                dry, request = True, request[len(flag):].strip()
        for flag in ("--seam",):
            if request.lower().startswith(flag + " "):
                seam, request = True, request[len(flag):].strip()

        # ⇒⇒ **THE TWO-PASS SEAM, OPT-IN, AND IT RETURNS BEFORE ANYTHING ELSE HAPPENS.**
        #
        #   This file already argues the case for the default path, and the argument still
        #   holds: *"the extractor turns English into components at 6/39, so making this the
        #   default would replace a chat flow that works with one that mistranslates two
        #   requests in three"*, and shipping anyway would be *"the exact failure of
        #   2026-07-31 — a mechanism believed good because the parts around it were."*
        #
        #   ⇒ **THE SEAM HAS THE SAME PROBLEM ONE LEVEL UP.** It reads 12/14 of the rung
        #     corpus — a corpus it was designed against — and until today it had NO PRODUCTION
        #     CALLER AT ALL: five importers, every one a test or a bench. A month of
        #     measurement about a component nobody could type at.
        #
        #   ⇒ **SO IT EARNS THE SWAP THE WAY `plan` ITSELF DID.** This flag is the same move
        #     this file made for the engine path — sit beside the thing that works, take real
        #     requests, print what each stage did. Held-out prompts are the only evidence that
        #     settles whether 12/14 beats 6/39, and a door is how they get typed.
        #
        #   ⇒ **IT READS AND SHOWS. IT NEVER ACTS**, which is why it needs no intent grant and
        #     no consent prompt: the seam PROPOSES A SCAFFOLD and the engine is what runs one
        #     ([[gorgon-orchestrator-proposes-a-scaffold]]). Returning here rather than
        #     threading a flag through the engine path is also what keeps the default
        #     byte-identical — there is no branch below this line that can see `seam`.
        if seam:
            self._read_with_seam(request, verbose)
            return

        # THE OPERATOR'S INTENT, AND THIS IS WHERE IT IS SETTLED — the front seam, the one
        # place with a person to ask. `ir/intent.py` says so in as many words: the safe
        # default belongs where the operator is asked, not scattered through every consumer,
        # which is why `handle()` treats an absent intent as "nobody said" rather than
        # inventing one.
        #
        # THREE WAYS, CHEAPEST FIRST, and `resolve` walks them: a prefix the operator typed
        # (`achieve: …`), then the marker words they already used, then one question. Nothing
        # is guessed — a sentence using no marker is asked about, and a sentence nobody is
        # there to answer for falls to FETCH, the rung that can do no harm.
        #
        # UNTIL THIS EXISTED THE LADDER WAS DECORATIVE HERE. The engine ran every program with
        # `intent="achieve"` hardcoded, so a request to be TOLD something was authorised to
        # change the lab, and the module enforcing authority was never handed any.
        # `plan procedure build_box: make a machine from a template` — KEEP this, do not do
        # it. Declared for the same reason the intent is: the alternative was a word blinder
        # sniffing {save, store, keep, reuse, …} out of the sentence, which fires on "save a
        # snapshot of web" and on 5 of 7 realistic requests. An operator who wants a snippet
        # can say so in four characters.
        #
        # READ BEFORE THE INTENT, and the order is not cosmetic. `resolve` saw the whole
        # string — prefix included — found no marker word in it, and ASKED THE OPERATOR what
        # they wanted back. They had just said: they want it kept.
        from planner import procedures as _procs
        from planner.ir import intent as _intent
        # THE SIGNATURE COMES OFF WITH THE NAME, and is never handed to the translator — a
        # parameter is a fact about the PROCEDURE, not about the world. See `declared_in`.
        try:
            keep_as, declared, request = _procs.declared_in(request)
        except Exception as e:
            # A MALFORMED DECLARATION MUST NOT FALL THROUGH AND RUN. The operator asked for
            # this work to be KEPT; doing it instead is the one outcome they did not ask for.
            console.print(f"[warn]{e}[/warn]")
            return

        # AN AUTHORING REQUEST NEEDS NO RUNG, because nothing runs. The engine plans exactly
        # as it would to act and the program is kept instead — so there is no authority being
        # granted and no question worth asking. Asking anyway is the prompt-that-fires-on-
        # ordinary-requests failure in its politest form: a question whose answer changes
        # nothing, in front of every snippet the operator ever writes.
        # NEITHER A DRY RUN NOR AN AUTHORING REQUEST NEEDS A RUNG, and for one reason: NOTHING
        # RUNS. A dry run stops at the first step by construction and an authoring request
        # plans and keeps — so the question "what do you want back?" has an answer that
        # changes nothing, asked in front of every preview the operator ever takes.
        #
        # FOUND BY POINTING `plan --dry` AT THE REAL LAB, which is the second time that has
        # caught this exact shape today: the authoring branch asked it too, for the same
        # reason, and was fixed one branch over.
        granted = (None if (keep_as or dry)
                   else _intent.resolve(request, asked=self._ask_intent))
        request = _intent.strip_prefix(request)

        # IMPORTED HERE, NOT AT MODULE LOAD. A shortcut registers itself at class-definition
        # time, so every import in this file is paid by every chat session that never types
        # `plan`. The engine layer pulls in the planner, the manifest and the tool registry;
        # none of that should cost a session that is not using it.
        from engines import insession as _insession
        from engines import rig as _rig
        from orchestrator.pipeline import execute_tool

        def guarded(tool, args):
            # THE SAME DOOR. A program's statements reach the world through the gauntlet a
            # single tool call meets — legal filter, commit gate, contract tier, watchdog,
            # killswitch. Building a second executor here would quietly create a second door,
            # and the whole point of the engine layer is that there is one.
            result = execute_tool(tool, args, verbose=verbose)
            # AND THE SAME BOOKKEEPING, which "the same door" did not include and had to.
            #
            # `LIBRARY.apply` is the post-execution hook that folds a call's effect back into
            # the registry, and it was reached from the CHAT dispatch gate and nowhere else. So
            # a program's calls changed the lab and never told the registry — and the registry
            # is what the program's own ENSUREs are evaluated against.
            #
            # MEASURED, NOT REASONED: `set up a lab` put nine machines on a network and labelled
            # all nine, the lab shows every one of them, and the program closed UNMET with
            # `count is 0, wanted == 9`. It did the work and then reported that it had not. The
            # mirror of that failure is the one that matters — a DELETE whose count still reads
            # the pre-state can decide it has more to remove.
            #
            # `execute_tool` is deliberately left alone: it is the raw call, and a caller that
            # wants transaction logging should say so. What was wrong is that this caller
            # wanted it and did not ask.
            try:
                from orchestrator.ai.active_library import LIBRARY
                LIBRARY.apply(tool, args, result=result)
            except Exception:
                # A REFRESH FAILURE MUST NOT LOSE THE CALL'S RESULT. The world already moved;
                # swallowing the outcome here would leave the program unable to report what it
                # did. The stale registry that follows is caught by the ENSURE, which is what
                # it is for.
                pass
            return result

        offered = []

        def decide(step, session):
            offered.append(step)
            if dry:
                # STOPPING AT THE FIRST STEP IS THE WHOLE POINT. A dry run that granted the
                # first node and refused the second would have ACTED — half a program is not
                # a preview of one, it is a program.
                return _insession.Verdict(_insession.STOP, "dry run — nothing was done")
            # ASKED BEFORE, NOT REPORTED AFTER — see `ask_destroy`. The list was already
            # being computed and printed; it was printed under "what it did".
            if step.destroys and not self.ask_destroy(step):
                return _insession.Verdict(_insession.STOP, "not granted — nothing was done")
            return _insession.Verdict(step.kind)

        # THE MOUNT LIVES IN `engines/rig.py` so a TEST CAN BUILD THE SAME ONE. Four
        # capabilities shipped this session with their seam left at `None` — invisible,
        # because a feature that does not run also does not fail.
        # A DRY RUN NEEDS NO CONSENT SURFACE, because it never reaches the world — and
        # offering one would train the operator to answer a question that decides nothing.
        result = _rig.build(guarded, narrate=not dry, decide=decide,
                            clarify=Plan.ask_clarify,
                            consent=None if dry else self._ask_consent,
                            # A DRY RUN TOUCHES NOTHING, so there is nothing to lift and no
                            # password to ask for — offering one would teach the operator to
                            # type it at a prompt that decides nothing, which is how a re-auth
                            # stops meaning anything.
                            permit=None if dry else self.ask_banned).handle(
                                request, intent=granted, procedure=keep_as,
                                declared=declared)

        if offered:
            console.print("\n[bold]what it would do[/bold]" if dry
                          else "\n[bold]what it did[/bold]")
            for st in offered:
                mark = f"  · {st.why or 'node'}: {st.cost} call(s)"
                if st.destroys:
                    # NAMED, NOT COUNTED. "7 deletions" and "deletes vm-orchestrator" are
                    # different sentences, and only one of them stops a person.
                    gone = ", ".join(self.names_destroyed(st))
                    mark += f"  [warn]DESTROYS {len(st.destroys)}: {gone}[/warn]"
                console.print(mark)

        outcome = result.get("outcome")
        colour = {"DONE": "ok", "REFUSED": "warn"}.get(outcome, "warn")
        console.print(f"[{colour}]{outcome}[/{colour}]  {result.get('why') or ''}")

        kept = result.get("procedure")
        if kept:
            # THE ARTIFACT AND WHERE IT LIVES. An authoring request whose answer was "DONE"
            # and nothing else would be indistinguishable from one that ran — which is the
            # confusion that put a machine called `default` on the lab.
            console.print(f"\n[bold]kept as {kept['name']}[/bold]  [dim]{kept['at']}[/dim]")
            for line in (kept.get("rendered") or "").splitlines():
                console.print(f"  {line}")

        # THE LEDGER, NOT A SUMMARY. This path exists to be READ — it is where a wrong
        # answer gets traced to the stage that caused it — and a list of sentences cannot
        # say who asked whom. Every line names both ends, the program goes at the end whole,
        # and `-v` attaches the evidence each line carries.
        ledger = result.get("events")
        if ledger is not None:
            for line in ledger.render(show_data=verbose).splitlines():
                console.print(f"  [dim]{line}[/dim]" if line.startswith("2") else f"  {line}")
        else:
            for line in result.get("log", []):
                console.print(f"  [dim]{line}[/dim]")
        if result.get("rendered") and result.get("events") is None:
            # ONLY WHEN THERE IS NO LEDGER. The ledger already prints the program in full at
            # the end; printing it twice would teach the reader to skip one of them.
            console.print("\n[bold]the program it wrote[/bold]")
            for line in result["rendered"].splitlines():
                console.print(f"  {line}")
        tree = result.get("tree")
        if tree and tree.get("verdict") != "clear":
            # ONLY WHEN IT IS NOT CLEAR. A book keeper that printed a clean tree on every
            # request would train the reader to skip the line it exists to be read on.
            console.print(f"\n[warn]the tree was served against a moving world[/warn]  "
                          f"{tree['infected']} of {tree['nodes']} node(s)")
            for line in (result.get("tree_report") or "").splitlines()[1:]:
                console.print(f"  [dim]{line}[/dim]")
        if result.get("answer"):
            console.print(f"\n[bold]{result['answer']}[/bold]")
            if result.get("answer_grounded") is False:
                # RETURNED, BUT NEVER CLEAN. Suppressing it leaves silence where there was an
                # answer; returning it silently is the hallucination the reporter exists for.
                console.print(f"  [warn]unsupported by any finding: "
                              f"{result.get('answer_unsupported')}[/warn]")
        if result.get("grounded") is not None:
            console.print(f"\n  grounded: {result['grounded']} · "
                          f"{len(result.get('calls') or [])} call(s)")
        if outcome == "UNCLAIMED":
            console.print(f"  mounted: {result.get('mounted')} · "
                          f"callable capabilities: {result.get('capabilities')}")
