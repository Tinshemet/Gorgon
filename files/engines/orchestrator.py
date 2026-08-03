"""orchestrator.py — route a request to an engine, run a session, answer.

    user -> [ /sync -> route -> IN-SESSION: engine <-> orchestrator, until done ] -> answer

THE OPERATOR SEES THE ENDS, NEVER THE MIDDLE. Everything between the prompt and the answer is
the IN-SESSION: the engine reports what it could and could not close, the orchestrator decides
whether to grant more, and that repeats — a tree — until the work is done or abandoned. The
record of it comes back under `in_session` so a wrong result can be traced to the stage that
caused it, and so that nothing user-facing renders it by accident.

It knows three things and none of them are domain knowledge: who is mounted, who claims a
request, and what to do when an engine asks for help. It never learns what a VM is, what a
snapshot costs, or how a program is written.

WHERE THE MODEL APPEARS — three times, never in the middle:
    routing        which engine (a closed choice over a short list)
    translation    English -> components, through the channel
    reporting      findings -> English

Between those points nothing probabilistic touches the work. That is the entire architecture,
and it is why the router can be a small model with a 71-token view of the system: it decides
WHO and HOW HARD, never HOW.

THE ORCHESTRATOR OWNS THE BUDGET, which is the reason promotion is a request rather than an
act. An engine asked whether it would like more resources will always say yes.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from . import insession as _insession
from .channel import Channel
from .registry import Registry
from .session import Session



def _parameterise(program: Dict[str, Any]) -> None:
    """Turn the MEMBER NAMES the request supplied into parameters, in place.

    WITHOUT THIS EVERY STORED PROCEDURE IS A MACRO WITH A LIBRARY'S FILING SYSTEM. `_unify` is
    total, so a contract reading `count(vm where name='box1') = 1` covers exactly one goal —
    the one it was written from — and `covering()` passes it over for every other. Measured
    2026-08-02: Gorgon authored `webcrawler` end to end and reached for NEITHER stored
    procedure, because both named literal members and the chain had invented its own.

    A `$param` BINDS WHATEVER THE GOAL HAS THERE, which is what makes one procedure serve any
    request of that shape. The fixture that predates all of this already had it —
    `vm_disk_builder(STRING box)` achieving `count(vm where name = $box) = 1` — so this is the
    authoring path catching up with a contract the language always supported.

    EVERY SELECTOR, NOT JUST A TOP-LEVEL ONE. A procedure written for two goals advertises
    `{"all": [...]}`, which has no `select` of its own — the first version of this function
    checked for one, found none, and silently did nothing for exactly the programs that need it
    most. The crawler was one: `{"all": [count(search where query=…), observe(search)]}`.

    THE KEY ONLY, AND THAT NARROWNESS IS THE POINT. Promoting `os_type` too would let a
    procedure that builds LINUX match a request for WINDOWS and quietly serve it: `_unify` would
    bind the parameter and the body would carry on with its own value. A name is the one slot
    where "whatever you called it" is always the right reading. Same rule, same reason, as
    `procedures.contract()` advertising the identity and nothing else.

    DETERMINISTIC AND MODEL-FREE: the goal states the kind, the manifest states its key, and the
    value in that slot is what the operator named. Nothing is guessed.
    """
    from planner.ir import config as _cfg

    goal = program.get("achieves")
    if not isinstance(goal, dict):
        return

    def _selectors(node):
        """Every `select` in a goal, however it is nested."""
        if isinstance(node, list):
            for kid in node:
                yield from _selectors(kid)
        elif isinstance(node, dict):
            for field, val in node.items():
                if field == "select" and isinstance(val, dict):
                    yield val
                elif isinstance(val, (dict, list)):
                    yield from _selectors(val)

    # ONE PARAMETER PER DISTINCT NAME, so a program naming the same machine twice binds it
    # once — two parameters for one thing would let a caller pass values that disagree.
    promoted: Dict[str, str] = {}
    taken: set = set(program.get("params") or {})
    for sel in _selectors(goal):
        key = ((_cfg.KINDS or {}).get(sel.get("kind")) or {}).get("key")
        named = sel.get(key) if key else None
        if not isinstance(named, str) or not named.strip():
            continue
        if named.startswith(_cfg.SIGIL) or named in promoted:
            sel[key] = promoted.get(named, named)
            continue
        param = key if str(key).isidentifier() else "name"
        while param in taken:
            param += "_"
        taken.add(param)
        promoted[named] = f"{_cfg.SIGIL}{param}"
        sel[key] = promoted[named]

    if not promoted:
        return
    # EVERY PLACE THE BODY WROTE THAT LITERAL. A contract promising `$query` while the body
    # still searches for the original string would be a procedure that LIES about what it does
    # — worse than the macro it replaces, because the lie is checkable and wrong.
    for st in program.get("body") or ():
        args = st.get("args")
        if isinstance(args, dict):
            for arg, val in list(args.items()):
                if isinstance(val, str) and val in promoted:
                    args[arg] = promoted[val]
        if isinstance(st.get("from"), str) and st["from"] in promoted:
            st["from"] = promoted[st["from"]]
        # THE CLOSING WITNESS TOO. `as_program` appends an ENSURE over the deliverable AFTER
        # the body is planned, and it carries a SELECTOR rather than args — so a parameterised
        # program still checked the ORIGINAL string: search for `$query`, then assert something
        # about "how fast is lightning". The check would pass only for the one request the
        # procedure was written from, which is the very failure being fixed.
        for sel in _selectors(st.get("predicate")):
            key = ((_cfg.KINDS or {}).get(sel.get("kind")) or {}).get("key")
            if key and isinstance(sel.get(key), str) and sel[key] in promoted:
                sel[key] = promoted[sel[key]]
        # A FACT EMBEDS THE NAME RATHER THAN EQUALLING IT — `answer(how fast is lightning)`
        # comes from the kind's own `fact` template, so this is a substring, not a value.
        fact = st.get("fact")
        if isinstance(fact, str):
            for literal, ref in promoted.items():
                if literal in fact:
                    st["fact"] = fact = fact.replace(literal, ref)
    program["params"] = {**(program.get("params") or {}),
                         **{ref.lstrip(_cfg.SIGIL): "string" for ref in promoted.values()}}


def _declare(program: Dict[str, Any], declared: Optional[Dict[str, str]],
             stood_in: Optional[Dict[str, str]] = None) -> List[str]:
    """Bind the parameters the OPERATOR declared into the program the writer just planned.

    THREE PASSES NOW, AND THE NEW ONE IS FIRST. `stood_in` maps the stand-in identities
    `planner/stand_in.py` put into the request before translation back to the parameters
    they came from — see that module for why a declared `$name` cannot cross the goal layer
    as itself. Restoring by PROVENANCE is unconditional where the two passes below are
    careful, because a minted identity can only be somewhere the operator put it.

    THE RULE, IN TWO PASSES, AND THE SPLIT BETWEEN THEM IS THE WHOLE SAFETY ARGUMENT:

      1. IN A CREATION ONLY, an argument whose name matches a declared parameter becomes
         that parameter. `create_vm(os_type: linux, name: box1)` under
         `test(STRING name, STRING os_type)` becomes `create_vm(os_type: $os_type,
         name: $name)`. The literal it replaced is REMEMBERED.
      2. ELSEWHERE, only a literal PASS 1 REMEMBERED is replaced, and only in an argument of
         the same name. So `add_label(name: box1)` follows the machine it labels, and
         `delete_vm(name: web3)` — a machine this program never created — does not move.

    WHY IT IS NOT ONE PASS, MEASURED THE HARD WAY 2026-08-02. The first version substituted
    into every matching argument. `create a vm` translated to an UNFILTERED `count(vm) = 1`,
    the writer planned EIGHT deletions to get a nine-machine lab down to one, and every one
    of them had its target rewritten to `$name` — eight specific machines the planner had
    chosen became "delete whatever the caller passes, eight times". A creator's arguments
    describe WHAT TO MAKE; every other tool's arguments name something that already exists,
    which the planner picked by reading the world. Those are not the same thing and a
    parameter may only touch the first.

    IT IS THE SAME DISCIPLINE `_parameterise` ALREADY KEEPS — promote a literal the request
    supplied, then follow that literal through the body — applied to a declaration instead
    of to the contract's key.

    EXACT MATCH, AND IT DECLINES RATHER THAN GUESSES. `STRING os` does NOT bind, because the
    argument is spelled `os_type`. An alias table mapping `os` -> `os_type` would be a
    vocabulary keyed to nouns, which is the thing the language exists to delete — and it
    would need a row per kind per synonym, maintained by whoever remembers. Being strict
    costs the operator one word and costs nobody a maintenance burden.

    A PARAMETER THAT MATCHED NOTHING IS STILL DECLARED. It goes into the signature and binds
    no argument — the operator said the procedure takes it, and silently dropping it would
    mean the signature they read back is not the one they wrote. The unbound ones are
    RETURNED rather than written onto the program, because the program is about to be
    rendered and parsed back: a field the parser cannot produce would fail the round-trip
    check the save now runs. It is not an error either — a parameter used only by a later
    hand edit is a legitimate thing to declare — so it is reported and nothing more.

    THE CONTRACT MOVES TOO, and it has to. `achieves` is what the WRITER matches a future
    goal against, so a procedure whose body takes `$os_type` while its contract still claims
    `os_type = 'linux'` would advertise a promise narrower than it keeps — and would never
    be reached for on any other OS. Same argument `_parameterise` makes for the key.

    IT RUNS BEFORE `_parameterise`, which promotes the KEY of any selector still holding a
    literal. Order matters: a declared `name` should be the operator's parameter, not one
    the promoter minted, and running second would leave two parameters for one value.
    """
    if not declared:
        return []
    # IMPORTED IN THE BODY, like `_parameterise`'s, and for the reason `qemu.py:52` gives:
    # `use_kinds` is a DYNAMIC SCOPE, so a config value captured at module load is a value
    # from a different world than the one authoring is happening in.
    from planner.ir import config as _cfg
    from planner.ir import effects as _effects
    from planner import stand_in as _stand_in
    refs = {p: f"{_cfg.SIGIL}{p}" for p in declared}
    makers = set(_effects.creators())
    # PASS 0 — THE STAND-INS THE OPERATOR'S OWN `$p` BECAME, put back before either pass
    # below runs. It goes first because it is the one substitution that needs no rule about
    # WHERE it is safe: `stand_in.restore` matches a value this run minted, so every
    # occurrence is one the operator wrote. Passes 1 and 2 then find their arguments already
    # holding `$p` and skip them, which is what the `startswith(SIGIL)` guard is for.
    used: set = set(_stand_in.restore(program, stood_in or {}))
    # THE LITERAL EACH PARAMETER REPLACED IN A CREATION, so pass 2 can follow that one value
    # and nothing else. `{"box1": "$name", "linux": "$os_type"}`.
    minted: Dict[str, str] = {}

    def _walk(statements, creating_only: bool):
        for st in statements or ():
            args = st.get("args")
            is_creation = st.get("op") == "new" or st.get("tool") in makers
            if isinstance(args, dict):
                for arg in list(args):
                    if arg not in refs or not isinstance(args[arg], str):
                        continue
                    if str(args[arg]).startswith(_cfg.SIGIL):
                        continue
                    if creating_only:
                        if is_creation:
                            minted[args[arg]] = refs[arg]
                            args[arg] = refs[arg]
                            used.add(arg)
                    elif args[arg] in minted and minted[args[arg]] == refs[arg]:
                        args[arg] = refs[arg]
                        used.add(arg)
            # A BLOCK'S BODY IS PART OF THE PROGRAM. A parameter that bound only outside a
            # FOREACH would substitute in some of the places the operator's value appears
            # and not others, which is worse than binding nowhere.
            for block in ("do", "then", "else", "ifails"):
                _walk(st.get(block), creating_only)

    _walk(program.get("body"), True)
    _walk(program.get("body"), False)

    def _bind_goal(node) -> None:
        if isinstance(node, list):
            for kid in node:
                _bind_goal(kid)
        elif isinstance(node, dict):
            for field, val in node.items():
                if field == "select" and isinstance(val, dict):
                    for attr in list(val):
                        if attr in refs and isinstance(val[attr], str) \
                                and not str(val[attr]).startswith(_cfg.SIGIL):
                            val[attr] = refs[attr]
                            used.add(attr)
                elif isinstance(val, (dict, list)):
                    _bind_goal(val)

    _bind_goal(program.get("achieves"))
    program["params"] = {**(program.get("params") or {}), **declared}
    return sorted(set(declared) - used)


class Orchestrator:
    """One registry, one channel, and the loop between them."""

    def __init__(self, registry: Registry, channel: Optional[Channel] = None,
                 route: Optional[Callable] = None, budget: Optional[int] = None,
                 narrate: Optional[Callable] = None,
                 decide: Optional[Callable] = None,
                 forward: Optional[Callable] = None,
                 consent: Optional[Callable] = None,
                 permit: Optional[Callable] = None):
        self.registry = registry
        self.channel = channel or Channel()
        self.budget = budget
        # `consent(question) -> bool`: the operator's answer to the ONE question consent.py
        # asks — *this program changes the world and nothing checks it, run it anyway?* It
        # travels on the session because the engine is what meets the world.
        #
        # NOT THE SAME SEAM AS `decide`, and the split is deliberate. `decide` rules on a NODE
        # — cost, destruction, whether to open it — and it is the orchestrator's own judgement.
        # This is the OPERATOR's, about a property of the program itself, and folding them
        # would let a policy function answer a question only a person can.
        #
        # DEFAULT None IS NOBODY THERE, and `consent.granted` reads that as no. Every grounded
        # program is unaffected — the question is only asked of one that vouches for nothing.
        self._consent = consent
        # `permit(banned) -> bool`: the operator LIFTING A RED LINE, by proving they are the
        # operator. A THIRD seam rather than a flag on `consent`, because it answers a
        # different question — `consent` asks whether a person agrees, this asks WHO they
        # are — and a callable that could answer both would let an agreement stand in for an
        # identity. Absent, a red line simply refuses; see `consent.permitted`.
        self._permit = permit
        # THE REPORTER'S CHANNEL, separate from the extractor's and deliberately so. It is
        # handed findings and NOTHING ELSE — never the request, never the program — because a
        # model that can see what was asked writes a fluent answer to the question, and one
        # that sees only what was found can describe the evidence. Absent, findings come back
        # raw and the caller narrates them or does not.
        self._narrate = narrate
        # `route(request, menu, engines) -> name | None`. Injected because it is the one
        # decision a model makes here, and injecting it means the whole orchestrator is
        # testable with a function that picks the first claimant — the same discipline that
        # let the ghost writer be proven with hand-written goals.
        self._route = route or self._first_claimant
        # `decide(step, session) -> Verdict`: the verdict on ONE act, inside the in-session.
        # The default grants what the engine proposed, and that is not a formality — the
        # budget has already refused anything unaffordable before this is reached, so what
        # is left is the seam where a consent gate or a destructive-act policy hangs. It is
        # injected for the same reason routing is: the whole loop stays testable without one.
        self._decide = decide or self._grant
        # `forward(publication, session) -> bool`: does this claim reach the OPERATOR, or is
        # it kept internal? The default forwards everything, and that is not laziness — an
        # engine that publishes has CHOSEN to say something, and silently keeping it would
        # make the act a no-op. Suppression is a policy someone has to write down.
        self._forward = forward or (lambda pub, session: True)

    @staticmethod
    def _first_claimant(request, menu, engines):
        return engines[0].name if engines else None

    @staticmethod
    def _grant(step, session):
        return _insession.Verdict(step.kind)

    def sync(self, capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.registry.sync(capabilities)

    def handle(self, request: str, intent: Optional[str] = None,
               components: Optional[List[Dict[str, Any]]] = None,
               regime: Optional[str] = None,
               procedure: Optional[str] = None,
               declared: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """One request, start to finish.

        `procedure` IS A DISPOSITION, NOT A GOAL. Named, the engine plans exactly as it would
        to act and the program is KEPT instead of run — same components, same writer, same
        world, one step withheld. It arrives from the operator (`procedure build_box: …`)
        rather than from the model, because the model was measured filling that field 0 times
        in 2 while the blinder that offered it fired on 5 of 7 ordinary requests.

        `intent` IS THE OPERATOR'S, AND IT IS ENFORCED — see `ir/intent.py`. A `fetch` or an
        `ensure` may not change the lab, and a step that would is refused in the in-session
        before the decider is consulted.

        IT DEFAULTS TO `None`, MEANING NOBODY SAID, and nothing is refused. That is not a hole
        left open — it is `intent.violations`' own reading of absence, and the reason is that
        the safe default belongs in ONE place: `intent.resolve`, at the front seam, where
        there is an operator to ask. A default of `ensure` here was worse than either: it
        GRANTED an authority nobody had asked for, and read as deliberate.

        `regime` OVERRIDES what the intent would choose. It exists because the regime is a
        real dial — the promotion path already turns it — and a caller that wants a tree
        session should be able to ask for one by name rather than reaching into a Session.
        It cannot go DOWN what the intent allows; that is `may_promote`'s job and this does
        not bypass it.

        `components` may be supplied directly — that is the stubbed channel, and it is how
        every result so far was measured. When absent the channel is asked, which is the only
        place English becomes structure.
        """
        # HOST ENGINES ONLY. Medusa turns the prompt into action; QEMU provides the box.
        # A guest capability — a crawler, a vision engine — is something a Medusa PROGRAM
        # calls once it has a machine, never somewhere the orchestrator sends a request.
        claimants = self.registry.claimants(request)
        if not claimants:
            # NOBODY CLAIMS IT, and that reaches the operator as an answer rather than a
            # crash. "Nothing mounted can do that" is useful; routing to the general engine
            # and failing three steps later is not.
            return {"outcome": "UNCLAIMED", "engine": None, "regime": None,
                    "why": "no mounted host engine claims this request",
                    "mounted": [e.name for e in self.registry.engines],
                    "capabilities": [p.name for p in self.registry.capabilities()]}

        # SYNC THE RELEVANT ENGINES — the claimants, not all of them and not just the one
        # about to be routed to.
        #
        # THE ORDER IN THE FLOW IS "/sync THEN ROUTE" AND THAT ORDER IS THE POINT: a router
        # choosing between engines needs to know what each actually holds, and syncing only
        # the winner means the choice was made blind and then informed. Syncing EVERY mounted
        # engine would be the context overflow of 2026-07-31 one level up — it grows with the
        # number of engines while nothing recomputes the budget — but the CLAIMANT list is
        # short by construction, because claiming is a cheap manifest question asked first.
        state = self.registry.sync([e.name for e in claimants])

        chosen = self._route(request, self.registry.menu(), claimants)
        engine = self.registry.get(chosen) if chosen else None
        if engine is None:
            return {"outcome": "UNROUTED", "engine": None, "regime": None,
                    "why": f"the router named {chosen!r}, which is not mounted",
                    "mounted": [e.name for e in self.registry.engines]}

        # THE REST OF THE CLAIMANTS ARE FALLBACKS, in the order the registry mounted them.
        # The router picks first; being wrong about that is a routing mistake, not a dead end.
        order = [engine] + [e for e in claimants if e.name != engine.name]
        if procedure:
            # AN AUTHORING REQUEST GOES TO SOMETHING THAT CAN WRITE. `floor_first` sends every
            # request to the executor, which inverts one goal into one call and has no program
            # to hand over — so the first real "keep this as a snippet" died on
            # `'ExecutorEngine' object has no attribute '_plan'`. Routing is about who serves
            # a request; this is about who can produce the ARTIFACT, and they are not the same
            # question.
            order = [e for e in order if getattr(e, "authors", False)]
            if not order:
                from .session import Session
                return Session(request, engine, intent=intent).close(
                    "REFUSED", f"nothing mounted can write a program down: "
                               f"{[e.name for e in claimants]}")
        return self._serve(request, order, state, intent, components, regime,
                           procedure, declared)

    def _serve(self, request, order, state, intent, components, regime=None,
               procedure=None, declared=None):
        """Try each claimant in turn until one serves it, refuses it, or all are spent.

        REROUTING HAPPENS ON INABILITY, NEVER ON REFUSAL, and the distinction is the whole
        design. An engine that CANNOT do something has said nothing about whether the request
        should happen; an engine that WON'T has, and letting the next engine overturn that
        would make every gate advisory — ask enough engines and one will say yes.

        THE BUDGET IS SHARED ACROSS ATTEMPTS. Giving each engine a fresh one would mean
        mounting a third engine silently tripled what a request may spend.
        """
        spent, attempts, last, tried = 0, [], None, []
        for engine in order:
            tried.append(engine.name)
            session = Session(request, engine, intent=intent,
                              budget=None if self.budget is None
                              else max(0, self.budget - spent),
                              consent=self._consent, permit=self._permit)
            if regime:
                session.regime = regime
                session.record(f"regime set to {regime} by the caller")
            for who, note in attempts:
                # FILED BY THE ENGINE THAT COULD NOT, caught by the orchestrator. Recorded
                # into the NEXT engine's ledger, so defaulting the sender to "this session's
                # engine" attributed the executor's refusal to Medusa — the misattribution
                # this ledger exists to prevent, in its own first line.
                session.record(note, filed_by=who, caught_by="orchestrator",
                               executed=f"{who}: cannot serve", level="warn")
            session.record(f"routed to {engine.name} · regime {session.regime}",
                           filed_by="orchestrator", caught_by=engine.name,
                           executed=f"route -> {engine.name}")
            session.record(f"{len(state)} claimant(s) synced",
                           filed_by="registry", caught_by="orchestrator",
                           executed="sync(claimants)", data=state)
            out = self._attempt(request, engine, session, components, procedure,
                                declared)
            spent += len(out.get("calls") or [])
            last = out
            # DONE and REFUSED both END IT. So does an unanswerable translation: the request
            # never became one, and asking a second engine to translate the same English
            # would be asking the same channel the same question.
            if out["outcome"] in ("DONE", "REFUSED", "UNTRANSLATED"):
                return self._name_the_route(out, tried)
            attempts.append((engine.name,
                             f"{engine.name} could not: {out.get('why') or out['outcome']}"))
        return self._name_the_route(last, tried)

    @staticmethod
    def _name_the_route(out, tried):
        """WHICH ENGINES WERE TRIED, on success as well as failure.

        An earlier version attached this only when everything failed, so a reroute that
        WORKED left no trace outside the log — and the log is internal. A result that says
        `engine: medusa` while the router chose `thin` is a result that quietly rewrote its
        own history; the operator's answer is the same either way, but anyone debugging the
        router needs to know it was overruled.
        """
        if out is not None and len(tried) > 1:
            out["tried"] = list(tried)
        return out

    def _author(self, engine, session, name, components, declared=None, stood_in=None):
        """Write a named program for these goals and KEEP it. Nothing runs.

        THE ENGINE PLANS EXACTLY AS IT WOULD TO ACT, which is what makes the artifact worth
        keeping: it is the program that would have run, against the world as it actually is.

        `achieves` IS THE GOAL ITSELF, and that is the line between a library and a macro. A
        procedure written to make something true is a procedure that makes that thing true,
        and saying so in the goal's own vocabulary is what lets the WRITER match it later —
        so the operator's snippet enters a future plan without the operator being in the room.
        """
        from planner import procedures as _procs
        from planner.ir.render import render as _render

        # THE ENGINE'S KINDS, HELD FOR THE WHOLE OF AUTHORING. `_attempt` enters this scope
        # around planning and leaves it before here, so `validate` — called by `save` — ran
        # with only the core manifest and refused a perfectly good crawl program with
        # "unknown kind 'browser'". THE WRITER HAD JUST PLANNED IT USING THAT KIND.
        #
        # FOURTH AND FIFTH INSTANCES OF ONE DEFECT, on the same day: a value read outside the
        # dynamic scope is a value from a different world. The world now answers for its own
        # packages, which fixes the planning half; this fixes the KEEPING half, which no world
        # is involved in.
        from planner.ir import config as _config
        with _config.use_kinds(getattr(engine, "manifest", None)):
            return self._author_within(engine, session, name, components, _procs, _render,
                                       declared, stood_in)

    def _author_within(self, engine, session, name, components, _procs, _render,
                       declared=None, stood_in=None):
        if not _procs.legal_name(name):
            return session.close("REFUSED",
                                 f"{name!r} is not a legal procedure name — it is written "
                                 f"into programs, so it must be an identifier")
        # THE NAME BEING WRITTEN, so the writer does not cover this goal with a PREVIOUS
        # version of the very procedure it is authoring.
        session.authoring = name
        planned = engine._plan(components, session)
        program = planned.get("program")
        if not program:
            return session.close("UNMET", planned.get("why") or "nothing could be written")

        program = dict(program)
        program["name"] = name
        # ONE GOAL OR THE CONJUNCTION OF ALL OF THEM. A snippet may not advertise more than
        # it does: written for three goals, it claims all three or the match is a lie.
        program["achieves"] = (components[0] if len(components) == 1
                               else {"all": list(components)})
        unused = _declare(program, declared, stood_in)
        _parameterise(program)
        rendered = _render(program)
        at = _procs.LIBRARY.save(program, rendered)
        session.record(f"kept as {name}", filed_by=engine.name, caught_by="orchestrator",
                       executed=f"PROCEDURE {name}", data={"at": at})
        if unused:
            # SAID, NOT SWALLOWED. A declared parameter that bound nothing means the writer
            # never placed an argument by that name — usually a spelling (`os` where the
            # argument is `os_type`). The procedure is still kept, because the signature is
            # the operator's to state; but a parameter silently doing nothing is exactly the
            # kind of quiet wrongness a signature is supposed to prevent.
            session.record(f"declared but unused: {', '.join(unused)}",
                           filed_by="orchestrator", caught_by="operator",
                           executed="declare", data={"unused": unused})
        session.events.program(f"THE MEDUSA PROCEDURE — {name}", rendered)
        out = session.close("DONE", f"written and kept as {name}")
        out["procedure"] = {"name": name, "at": at, "rendered": rendered,
                            "unused_params": unused}
        return out

    def _attempt(self, request, engine, session, components, procedure=None,
                 declared=None):
        """One engine's whole turn: translate, run the in-session, close."""
        stood_in: Dict[str, str] = {}
        if components is None:
            # A DECLARED `$p` CANNOT CROSS THE GOAL LAYER AS ITSELF — `planner/stand_in.py`
            # has the measurement. It travels as an ordinary name nothing can match and is
            # restored by `_declare`. Only under a declaration: with no signature there is
            # nothing to stand in for, and `$anything` is residue exactly as it was.
            from planner import stand_in as _stand_in
            request, stood_in, unknown = _stand_in.substitute(request, declared or {})
            if stood_in:
                session.record(
                    "stood in for " + ", ".join(f"${p}" for p in sorted(stood_in.values())),
                    filed_by="orchestrator", caught_by="channel", executed="stand in",
                    data=stood_in)
            if unknown:
                # SAID, NOT GUESSED. `$foo` under a signature that never declared `foo` is a
                # typo, and it is about to be silently stripped as residue — the operator
                # would read a program missing the value they thought they had placed.
                session.record(
                    "referred to but never declared: " + ", ".join(f"${u}" for u in unknown),
                    filed_by="orchestrator", caught_by="operator", executed="declare",
                    data={"undeclared": unknown}, level="warn")
            session.record("English -> goals", filed_by="orchestrator",
                           caught_by="channel", executed=f"ask({request[:40]!r})")
            # TRANSLATE UNDER THE ROUTED ENGINE'S MANIFEST. The extractor builds its schema
            # and its prompt from the manifest IN FORCE, so asking outside this scope offers
            # the model the DEFAULT kinds — and a package's kinds, which joined the engine's
            # manifest when it was loaded, stay invisible to the front seam.
            #
            # THAT IS THE WHOLE OF "a capability that cannot be requested is not mounted".
            # The writer could plan a search, the engine could run one, and the model could
            # not say the word.
            from planner.ir import config as _config
            with _config.use_kinds(getattr(engine, "manifest", None)):
                answer = self.channel.ask(request, engine.world())
            session.record(f"{len(answer.components or ())} goal(s)",
                           filed_by=answer.source or "channel", caught_by="orchestrator",
                           executed="translate", data=answer.components,
                           level="warn" if not answer else "info")
            if not answer:
                # A REQUEST NOBODY COULD TRANSLATE IS NOT A FAILED REQUEST — it is one that
                # never became a request. Naming the stage matters: this is the front seam,
                # and confusing it with an engine failure is how a day gets spent debugging
                # the wrong half.
                return session.close("UNTRANSLATED", answer.why)
            lost = list(getattr(answer, "dropped", ()) or ())
            if lost:
                # A PARTIAL READ, SAID OUT LOUD. `to_goals` refuses components for reasons
                # that are each correct, and the request is then served in part — which the
                # ledger could not show and the outcome word cannot express. Recorded here
                # so a DONE that covers half a request is at least visibly half.
                session.record("could not read: " + "; ".join(lost),
                               filed_by=answer.source or "extractor",
                               caught_by="operator", executed="translate",
                               data={"dropped": lost}, level="warn")
            components = answer.components
            # A DECLARED NAME WINS; the channel's is a fallback nothing currently fills.
            procedure = procedure or getattr(answer, "procedure", None)

        # AUTHORING, NOT ACTING. The operator asked for a reusable snippet, so the engine
        # WRITES the program for these goals and the orchestrator keeps it — nothing runs.
        # Doing otherwise is what put a machine called `default` on the lab in answer to a
        # request for a script.
        #
        # PLANNED, NOT SIMULATED: the real writer against the real world, so the artifact is
        # one that would actually work. Only the last step — doing it — is withheld.
        #
        # OUTSIDE THE TRANSLATION BRANCH, and it was inside it. So a caller supplying
        # `components` directly — which is every measured result to date, and the only shape a
        # test can drive without a model — could not author at all: the one path this feature
        # can be PROVEN on was the one path it did not reach.
        if procedure:
            return self._author(engine, session, procedure, components, declared, stood_in)

        result = _insession.drive(engine, components, session, self._decide)
        session.calls = result.get("calls") or []

        # THE PROMOTION REQUEST, heard here and nowhere else — and then ACTED ON.
        #
        # This used to record the promotion and RE-RUN THE SAME ENGINE WITH THE SAME
        # COMPONENTS, which fails identically by construction. A recorded-but-inert
        # escalation is worse than none: the log says "promoted to tree" and nothing
        # happened, which is the shape of every defect this project has spent a week on.
        #
        # What a tree session actually is: the engine could not close a gap, so the gap goes
        # ON THE CHANNEL as its own question. Not the original request — that was already
        # translated, and asking it again gets the same answer. The GAP is a different and
        # much smaller question: "nothing reaches COUNT(SELECT vm WHERE ...) — what would?"
        while result.get("promote"):
            to = result["promote"]
            if not session.promote(to, result.get("why", "")):
                return session.close("PROMOTION_DECLINED", result.get("why", ""))
            if not session.rounds_left():
                return session.close("ABANDONED", "the gap did not close in the rounds "
                                                  "this session was allowed")
            gap = {"gap": result.get("why", ""), "request": request,
                   "have": components}
            answer = self.channel.ask(gap, engine.world())
            session.record(f"in-session asked about the gap -> {answer.source}: "
                           f"{len(answer.components)} component(s)")
            if not answer:
                # NOBODY COULD ANSWER THE GAP, so the session ends saying so rather than
                # looping. An escalation with no answerer behind it is a slower refusal, and
                # naming it as one is the only honest close.
                return session.close("UNMET", f"no answer for the gap: "
                                              f"{result.get('why', '')}")
            # THE NEW COMPONENTS ARE ADDED, NOT SUBSTITUTED. The original goals are still
            # what was asked; the answer is what unblocks them, and dropping the first would
            # quietly change the request.
            components = list(components) + [c for c in answer.components
                                             if c not in components]
            result = _insession.drive(engine, components, session, self._decide)
            session.calls = result.get("calls") or []

        if result.get("refused") or result.get("failed") == "forbidden":
            # A REFUSAL IS NOT A FAILURE. The engine asked, something here said no, and that
            # is the system working — so it closes under its own name rather than being filed
            # with the gaps nothing could close. Whatever ran before the refusal is reported
            # as run, because those calls are facts.
            #
            # A RED LINE IS THE SAME KIND OF ANSWER AND CLOSED `UNMET` UNTIL 2026-08-02.
            # UNMET is a GAP — something nothing could close — and it is what invites the
            # next regime to try. A forbidden tool is not a gap: no engine, no promotion and
            # no better program will make it allowed, and filing it with the gaps would send
            # the request up the ladder looking for a way around the ban.
            return session.close("REFUSED", str(result.get("why") or ""))
        if not result.get("ok"):
            return session.close("UNMET", str(result.get("why") or ""))

        # PUBLICATIONS BECOME FINDINGS ONCE THEY ARE FORWARDED, and that is the only place
        # the two vocabularies meet: a publication is what an ENGINE SAID, a finding is what
        # the OPERATOR IS TOLD, and the orchestrator is what stands between them.
        kept, forwarded = [], []
        for pub in session.published:
            (forwarded if self._forward(pub, session) else kept).append(pub)
        if kept:
            session.record(f"kept {len(kept)} publication(s) internal")
        # PUBLICATIONS ARE THE FINDINGS WHEN THERE ARE ANY, not an addition to them. Both
        # carry the same facts — an engine publishes what it observed and also returns it —
        # so adding them handed the reporter `reachable(alpha)` twice and would have let a
        # narrator say "both machines answered, twice". The engine's own list is the fallback
        # for an engine that returns findings and publishes nothing.
        session.findings = ([p.as_finding() for p in forwarded] if forwarded
                            else (result.get("findings") or []))
        out = session.close("DONE", result.get("why") or "")
        if session.published:
            out["published"] = [p.as_finding() for p in session.published]
            out["kept"] = len(kept)
        out["rendered"] = result.get("rendered", "")
        out["grounded"] = result.get("grounded")
        # THE TREE'S OWN VERDICT TRAVELS LIKE GROUNDING DOES — beside the answer, not inside
        # it. A run served against a set that changed underneath a split succeeded and is not
        # the same thing as one served against a set that held still, and the reporter must
        # not be the thing that decides whether to mention it: it is handed findings only.
        if result.get("tree"):
            out["tree"] = result["tree"]
            out["tree_report"] = result.get("tree_report", "")
        if self._narrate is not None:
            from . import reporter as _reporter
            said = _reporter.report(session.findings, self._narrate)
            out["answer"] = said["answer"]
            # THE VERDICT TRAVELS WITH THE SENTENCE. An answer whose claims are not supported
            # is still returned — suppressing it leaves silence where there was an answer —
            # but it never arrives looking clean.
            out["answer_grounded"] = said["grounded"]
            out["answer_unsupported"] = said["unsupported"]
        return out
