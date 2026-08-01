"""_execute.py — running a plan that has already been granted. No decisions here.

The one place a Medusa program meets the world, and everything it is handed was decided
somewhere else: the intent by the operator, the consent by the operator, the verdict by the
orchestrator. What is left is a ledger line per call and an honest reading of what came back.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...planner import ghost_writer as _gw
from ...planner import tree_keeper as _keeper
from ...planner.ir import lower as _lower
from ...planner.ir import observe as _observe
from ...planner.ir import config as _config
from ...planner.ir import consent as _consent
from ...planner.ir import render as _render
from ...planner.ir import run as _run
from ...planner.ir import effects as _effects
from ...planner.ir import validate as _validate
from ._shared import _MAX_OPENINGS, _MAX_WAITS, _findings_of, _prose_of


class _ExecuteMixin:
    def _execute_plan(self, planned: Dict[str, Any],
                      components: List[Dict[str, Any]],
                      session=None) -> Dict[str, Any]:
        """Run a plan that has already been granted. No decisions are made here.

        THE SESSION, NOT ITS EVENT LOG. This took `session_events` and therefore could not
        answer the two questions `run()` asks before it touches anything — what was the
        operator's INTENT, and have they CONSENTED — so it answered them itself, with
        `consent=True, intent="achieve"`. That is the maximum of both: every program granted
        the top of the ladder, and grounding waved through unasked, on the one path that
        reaches the real lab. The session has carried the real answers since it was written.
        """
        session_events = getattr(session, "events", None)
        world = self._world
        program = planned["program"]
        # DOES THIS PROGRAM CHANGE ANYTHING AT ALL — computed from the manifest, not read off
        # the op names.
        #
        # `consent.survey` counts a `CALL` as acting, and it is right to: it reads an artifact
        # alone and cannot know what the tool behind the word does. The ENGINE can, because it
        # holds the manifest, and the two answers differ exactly on a probe — a program of four
        # `guest_ping`s "acts" four times by the artifact's reading and changes nothing.
        #
        # MEASURED THE MOMENT CONSENT STOPPED BEING HARDCODED: rung 11 and every opened leaf of
        # rung 4 were refused for carrying no witness to work they never did. Asking a person
        # to consent to a program that only asks questions is how a consent prompt becomes
        # noise, which is the failure `consent.py`'s own docstring set out to avoid.
        changes = [c for c in planned.get("plan") or ()
                   if c[0] in _effects.actors(self.manifest)]
        select, holds = _gw._seams_of(world)
        if session_events is not None:
            session_events.program(f"{len(program.get('body') or ())} statement(s)",
                                   _render(program))

        def watched(tool, args):
            """The engine's executor, with a ledger line per call.

            WRAPPED RATHER THAN RECONSTRUCTED FROM THE RESULT. Filing these afterwards would
            give every call the same timestamp and lose the ones that ran before a failure —
            which are the calls you most want to see.
            """
            out = self._execute(tool, args)
            if session_events is not None:
                bad = not (out or {}).get("success", True)
                session_events.file(
                    self.name, "world",
                    f"{tool}({', '.join(f'{k}={v}' for k, v in (args or {}).items())})",
                    "call failed: " + str((out or {}).get("error")) if bad else "call",
                    level="error" if bad else "info")
            return out

        result = _run(program, watched, select=select, holds=holds,
                      known_names=world.names(),
                      known_tools=_effects.tools_of(self.manifest) or None,
                      # THE SESSION'S, NOT THIS ENGINE'S. `run()` re-checks the whole program
                      # statement by statement, which is finer than what the in-session can
                      # see: the step gate refuses a node that ACTS above its rung, and this
                      # also catches a FETCH that judges. Both read `intent._PERMITS`, so the
                      # two gates cannot disagree — a second gate judging by a different
                      # standard is worse than one, because the disagreement is silent.
                      # A PROGRAM THAT CHANGES NOTHING HAS NOTHING TO CONSENT TO, and that is
                      # computed above rather than assumed — the answer, not a bypass.
                      consent=(getattr(session, "consent", None) if changes else True),
                      intent=getattr(session, "intent", None),
                      # WHICH OF THE KNOWN TOOLS CHANGE SOMETHING. The engine holds the
                      # manifest, so the ladder gets the exact answer about a `CALL` rather
                      # than the safe one — which is the difference between a `fetch` that
                      # can ask a question and one that cannot.
                      acting_tools=_effects.actors(self.manifest))
        result = self._correct(program, result, select, holds, watched, session)
        survey = _consent.survey(program)
        # A CHECK THAT SAYS NO IS AN ANSWER, NOT A FAILURE.
        #
        # `run` reports an unsatisfied ENSURE as `failed: unsatisfied`, which is right for an
        # ACHIEVE — there the assertion is a precondition the plan was built on, and its
        # falsity means the plan was wrong. Under an `ensure` the assertion IS THE REQUEST,
        # and reporting "count is 4, wanted == 9" as a failed run tells the operator their
        # question broke rather than answering it.
        #
        # SOUND ONLY BECAUSE OF THE LINE ABOVE. This can be read as the verdict precisely
        # because a non-acting program contains nothing but the checks the operator asked
        # for — no preconditions, no corrections, nothing whose falsity would mean something
        # else. Under an ACHIEVE the two are genuinely indistinguishable from here, and the
        # branch is not taken.
        corrects = self._corrects(session)
        verdict = None
        if not corrects and result.get("failed") == "unsatisfied":
            verdict = {"fact": "holds", "value": False, "why": result.get("why") or ""}
        elif not corrects and result.get("ok") and survey["asserts"]:
            verdict = {"fact": "holds", "value": True, "why": result.get("why") or ""}
        if verdict is not None:
            return {"ok": True, "calls": result.get("calls") or [],
                    "findings": (_findings_of(world, {"ok": True, **result}) or []) + [verdict],
                    # NAMED, NOT LEFT TO BE RECOGNISED IN A LIST. `_joined` rebuilds findings
                    # from the world's LEDGER, which is right for observations and wrong for
                    # this: a verdict is something the engine DETERMINED, not something the
                    # world was asked. Without its own key it was dropped on every path that
                    # joins nodes — so an ENSURE answered correctly and reported nothing.
                    "verdict": verdict,
                    "published": result.get("published") or [],
                    "program": program, "rendered": _render(program),
                    "grounded": survey["grounded"], "vacuous": survey["vacuous"],
                    "why": verdict["why"]}
        return {"ok": bool(result.get("ok")),
                "calls": result.get("calls") or [],
                # WHAT WAS OBSERVED, kept apart from what was DONE. The reporter is handed
                # findings and nothing else, so an engine that returned its calls under this
                # name would be handing the narrator a list of INTENTIONS to describe as
                # results — which is the difference between "three machines answered" and
                # "I asked three machines".
                "findings": _findings_of(world, result),
                # WHAT THE PROGRAM ASKED TO SUBMIT, in its own words. The engine used to
                # decide on its own what was worth saying by scraping the findings ledger,
                # which meant the PROGRAM — the artifact an operator reads and could have
                # written — never mentioned the one thing they were waiting for. A `PUBLISH`
                # line makes the report part of the code rather than a side effect of it.
                "published": result.get("published") or [],
                "program": program,
                "rendered": _render(program),
                "grounded": survey["grounded"],
                "vacuous": survey["vacuous"],
                # THE PROMOTION REQUEST, IF THE CORRECTOR MADE ONE. `derive` returning None
                # is the doorway to ACHIEVE's second engine, and the orchestrator is the only
                # thing that may open it — dropping the key here would leave a refusal that
                # said "unmet" where the truth is "this needs a regime I was not granted".
                **({"promote": result["promote"]} if result.get("promote") else {}),
                "why": result.get("why") or result.get("failed")}

