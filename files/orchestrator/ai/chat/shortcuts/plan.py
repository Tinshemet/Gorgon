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

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        request = ui.strip()[len(_PREFIX):].strip()
        dry = False
        for flag in ("--dry", "-n"):
            if request.lower().startswith(flag + " "):
                dry, request = True, request[len(flag):].strip()

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
        from orchestrator.ai.planner import procedures as _procs
        from orchestrator.ai.planner.ir import intent as _intent
        keep_as, request = _procs.declared_in(request)

        # AN AUTHORING REQUEST NEEDS NO RUNG, because nothing runs. The engine plans exactly
        # as it would to act and the program is kept instead — so there is no authority being
        # granted and no question worth asking. Asking anyway is the prompt-that-fires-on-
        # ordinary-requests failure in its politest form: a question whose answer changes
        # nothing, in front of every snippet the operator ever writes.
        granted = (None if keep_as
                   else _intent.resolve(request, asked=self._ask_intent))
        request = _intent.strip_prefix(request)

        # IMPORTED HERE, NOT AT MODULE LOAD. A shortcut registers itself at class-definition
        # time, so every import in this file is paid by every chat session that never types
        # `plan`. The engine layer pulls in the planner, the manifest and the tool registry;
        # none of that should cost a session that is not using it.
        from orchestrator.ai.engines import insession as _insession
        from orchestrator.ai.engines import rig as _rig
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
            return _insession.Verdict(step.kind)

        # THE MOUNT LIVES IN `engines/rig.py` so a TEST CAN BUILD THE SAME ONE. Four
        # capabilities shipped this session with their seam left at `None` — invisible,
        # because a feature that does not run also does not fail.
        # A DRY RUN NEEDS NO CONSENT SURFACE, because it never reaches the world — and
        # offering one would train the operator to answer a question that decides nothing.
        result = _rig.build(guarded, narrate=not dry, decide=decide,
                            consent=None if dry else self._ask_consent).handle(
                                request, intent=granted, procedure=keep_as)

        if offered:
            console.print("\n[bold]what it would do[/bold]" if dry
                          else "\n[bold]what it did[/bold]")
            for st in offered:
                mark = f"  · {st.why or 'node'}: {st.cost} call(s)"
                if st.destroys:
                    # NAMED, NOT COUNTED. "7 deletions" and "deletes vm-orchestrator" are
                    # different sentences, and only one of them stops a person.
                    gone = ", ".join(sorted(str(list(a.values())[0]) if a else "?"
                                            for _, a in st.destroys))
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
