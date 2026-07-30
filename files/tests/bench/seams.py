"""seams.py — the two injected seams, backed by the sim. ONE authority.

`select` answers registry queries and `holds` evaluates predicates. In the orchestrator
those are filled by the Active Library and the findings ledger (`planner/program.py`);
here they read `SimWorld`. Nothing about the language changes — that is the whole point of
injecting them.

WHY THIS MODULE EXISTS. There were TWO sim-backed copies, and the divergence was not
cosmetic. `run_program.seams` filtered on `label` / `status` / `name` only — no `not`, no
`in`, no `any`/`all` groups — so **a carve-out was silently ignored**: a program saying
"every vm EXCEPT db" got every vm, and the seam reported success. Its `holds` returned
`"disjoint not evaluated in the bench"`, so the shape rung 8 ends on was not evaluated at
all. Meanwhile the copy in `author_probe` had grown all of it, one bug at a time.

That is the 2026-07-30 SSOT finding in miniature, and it pointed the same way every time:
the BENCH copy was richer and the other was the stale twin. The fix that lasts is not a
better copy — it is ONE AUTHORITY PER FACT, which is why this is a module and not a
docstring telling the next reader to keep two functions in step.

The production pair in `planner/program.py` is deliberately NOT unified with this one: it
reads different sources. What must not drift is the QUESTION the two answer, and
`test_medusa_invariants` holds them to that directly, query by query.
"""
from orchestrator.ai.planner.ir import config, methods as _methods, observe, refs


def seams(world):
    """Registry query + predicate evaluation over `world`. Returns `(select, holds)`."""
    def select(sel, scope=None):
        kind = sel.get("kind")
        alias = (config.KINDS.get(kind) or {}).get("aliases") or {}

        def _matches(name, vm, filters, scope=None):
            """One member against one set of filters. The SAME function answers both the
            include and the exclude side, so a carve-out cannot drift from the selection
            it carves out of — the exact bug that made `iso_lab` match `id=iso_lab2` in
            the network attach, arriving in a second place."""
            # GROUPS FIRST — `any` is OR, `all` an explicit AND, each branch a filter
            # set answered by this same function, so a group can never mean something the
            # flat form does not.
            for group, combine in (("any", any), ("all", all)):
                kids = filters.get(group)
                if isinstance(kids, list) and kids:
                    if not combine(_matches(name, vm, k, scope) for k in kids):
                        return False
            f = {alias.get(k, k): v for k, v in filters.items()
                 if k not in ("not", "any", "all")}
            # MEMBERSHIP — the attribute is ANY of these. Resolved through the same refs
            # the rest of the language uses, so a bound set works beside a literal list.
            for attr in list(f):
                spec = f[attr]
                if isinstance(spec, dict) and "in" in spec:
                    want = spec["in"]
                    if isinstance(want, str):
                        want = refs.resolve(want, scope or {})
                    want = want if isinstance(want, (list, tuple, set)) else [want]
                    got = (name if attr == "name" else vm.get(attr))
                    if attr == "label":
                        carried = vm["labels"] | vm.get("flags", set())
                        if not (carried & set(want)):
                            return False
                    elif attr == "network":
                        if not (vm.get("nets", set()) & set(want)):
                            return False
                    elif got not in want:
                        return False
                    f.pop(attr)
            # A NON-SCALAR FILTER CANNOT MATCH, and must not raise. The validator now
            # refuses `label = '$vms'` where $vms holds a set, but a value can still
            # arrive non-scalar at run time — a parameter supplied at invocation is not
            # knowable statically. Before this, `f["label"] not in {...}` hit a list, and
            # an unhashable type took down a 13-rung run at rung 9 with a TypeError
            # instead of failing one program. A seam that crashes destroys the
            # measurement around it, which is the same reason render.py may not raise.
            if any(isinstance(v, (list, dict, set, tuple)) for v in f.values()):
                return False
            # OBSERVED attributes are read out of the findings ledger, never off the
            # record — that is the whole of decision 6. Delegated to `observe.matches` so
            # the rule that `unknown` matches neither `true` nor `false` lives in one
            # place: a seam that reimplemented it would be free to get it wrong, and the
            # way it gets it wrong is by treating unprobed as dead.
            for attr, wanted in f.items():
                if observe.matches(world.findings, kind or "vm", attr, name, wanted) is False:
                    return False
            if "label" in f and f["label"] not in (vm["labels"] | vm.get("flags", set())):
                return False
            if "status" in f and vm["status"] != f["status"]:
                return False
            if "name" in f and name != f["name"]:
                return False
            if "os_type" in f and vm.get("os_type") != f["os_type"]:
                return False
            # Membership, not equality: a machine sits on a SET of networks. Written as
            # equality (`network = 'core'`) because that is how the operator says it —
            # "is it on core" — and the query language should not make a reader learn
            # which attributes happen to be multi-valued.
            if "network" in f and f["network"] not in vm.get("nets", set()):
                return False
            return True

        if kind == "network":
            return sorted(world.nets)
        carve = sel.get("not") or {}
        return [n for n, vm in sorted(world.vms.items())
                if _matches(n, vm, sel, scope)
                and not (carve and _matches(n, vm, carve, scope))]

    def _class_of(name):
        """Which class a bound name belongs to, asked of the world rather than guessed."""
        if name in world.nets:
            return "network"
        if name in world.vms:
            return "vm"
        return None

    def _method(pred, scope):
        """A predicate asked OF an instance — dispatched on the receiver's class.

        THIS IS THE SPLIT #38 DISSOLVED INTO. One `reach` was doing two jobs, so two
        correct implementations could disagree: production answered per-member liveness,
        the bench answered shared-topology. They are two METHODS, and which one runs is
        decided by what you asked.

            $web.reach()    can this machine be pinged
            $lab.reach()    are all this network's members connected AND answering
        """
        who = refs.resolve(pred["on"], scope or {})
        if isinstance(who, str) and refs.names(who):
            return False, f"{pred['on']} is not bound, so there is nothing to ask"
        name = who if isinstance(who, str) else None
        if name is None:
            return False, f"{pred['on']} holds a set; a method is asked of ONE thing"
        kind = _class_of(name)
        if kind is None:
            return False, f"there is no vm or network named {name!r}"
        if not _methods.has(kind, pred.get("shape")):
            return False, (f"a {kind} has no {pred.get('shape')}() — it answers "
                           f"{', '.join(sorted(_methods.methods(kind))) or 'nothing'}")
        if kind == "vm":
            # A MACHINE'S OWN REACH IS ITS LIVENESS, read from the findings ledger and
            # never inferred from a tool's success flag — unverified is not done.
            state = observe.value(world.findings, "vm", "alive", name)
            if state == observe.unknown():
                return False, f"{name} has not been probed, so its reach is unestablished"
            return state != observe.FALSE, f"{name} {'answered' if state != observe.FALSE else 'did not answer'}"
        members = sorted(n for n, vm in world.vms.items() if name in vm.get("nets", set()))
        if not members:
            return False, f"network {name} has no members, so nothing reaches anything"
        unknown = [m for m in members
                   if observe.value(world.findings, "vm", "alive", m) == observe.unknown()]
        if unknown:
            return False, (f"{len(unknown)} of {len(members)} on {name} have not been "
                           f"probed ({', '.join(unknown[:3])})")
        dead = [m for m in members
                if observe.value(world.findings, "vm", "alive", m) == observe.FALSE]
        if dead:
            return False, f"no answer from {', '.join(dead)} on {name}"
        return True, f"all {len(members)} member(s) of {name} answered"

    def holds(pred, scope):
        if _methods.is_method_call(pred):
            return _method(pred, scope)
        shape = pred.get("shape")
        if shape == "count":
            n = len(select(pred.get("select") or {}))
            for c, op in (("eq", "=="), ("gte", ">="), ("lte", "<=")):
                if c in pred:
                    good = {"==": n == pred[c], ">=": n >= pred[c], "<=": n <= pred[c]}[op]
                    return good, f"count is {n}, wanted {op} {pred[c]}"
            return False, "no comparator"
        if shape == "reach":
            # Members come from the SAME select() the rest of the language uses. Reading
            # only `tag` meant REACH(SELECT vm) — no filter, every vm, a perfectly legal
            # set — looked up the label None and found nobody. A predicate that ignores
            # its own operand's filters answers a different question than it was asked.
            #
            # A5, CLOSED 2026-07-30 BY TIGHTENING RATHER THAN BY ANNOTATING. The bench asked
            # only whether the members share a network. Production asks something else
            # entirely: every member must have been PROBED and must have ANSWERED, because
            # reachability is a FINDING and never an inference from a tool's success flag —
            # unverified is not done. So a program could pass a reach rung here and come
            # back `reach is unestablished` against the real lab, and that loophole is
            # exactly what made rung 4's 16-call program look cheapest than the 21-call one
            # that probes.
            #
            # THE TWO SEAMS DIVERGED IN TWO DIRECTIONS, NOT ONE, and the second was found
            # while fixing the first: production ignores network topology completely. So
            # this now asks for BOTH — the floor, a shared network, and a live answer from
            # every member — which is strictly stronger than either side was. A bench that
            # is stricter than production can only produce pessimistic rungs; one that is
            # weaker silently certifies programs the real lab would refuse.
            #
            # Whether production SHOULD ignore topology is a separate question and is not
            # decided here.
            members = select(pred.get("select") or {})
            floor = int(pred.get("min", 2))
            if len(members) < floor:
                return False, f"reach over {len(members)} member(s), floor {floor}"
            unknown = [m for m in members
                       if observe.value(world.findings, "vm", "alive", m)
                       == observe.unknown()]
            if unknown:
                return False, (f"reach is unestablished: {len(unknown)} of {len(members)} "
                               f"have not been probed ({', '.join(sorted(unknown)[:3])})")
            dead = [m for m in members
                    if observe.value(world.findings, "vm", "alive", m) == observe.FALSE]
            if dead:
                return False, f"no answer from {', '.join(sorted(dead))}"
            if not world.common_networks(members):
                return False, (f"all {len(members)} answered, but they share no network — "
                               f"reach here also means a path between them")
            return True, f"all {len(members)} member(s) answered and share a network"
        if shape == "disjoint":
            # DECLARED SINCE DAY ONE, NEVER EVALUABLE. The manifest lists it, the schema
            # offers it, the validator accepts it and the renderer prints it — and this
            # seam fell through to "unevaluated shape disjoint", which a postcondition
            # then counts as FAILED. So `ACHIEVE DISJOINT($reds, $blues)` — a correct
            # statement of rung 6's goal — could not hold in any world, and burned three
            # revision rounds saying so. Exactly the shape of the composite-predicate bug
            # found earlier, in a third predicate, because nothing asserts that every
            # declared shape has an evaluator.
            #
            # Its operand is `sets`: names of sets the program bound, not a query. Each
            # resolves through the same refs the rest of the language uses, so a set built
            # by `new` (a list) and one bound by `fetch` both work.
            raw = pred.get("sets") or []
            resolved, unknown = [], []
            for ref in raw:
                val = refs.resolve(ref, scope) if isinstance(ref, str) else ref
                if isinstance(val, str) and refs.names(val):
                    unknown.append(ref)          # never bound — still a $token
                    continue
                resolved.append({val} if isinstance(val, str) else set(val or ()))
            if unknown or len(resolved) < 2:
                return False, (f"disjoint needs two or more bound sets; "
                               f"{', '.join(unknown) or 'too few'} not in scope")
            overlap = set()
            for i, a in enumerate(resolved):
                for b in resolved[i + 1:]:
                    overlap |= (a & b)
            return (not overlap), (f"disjoint over {len(resolved)} sets -> "
                                   + ("no shared member"
                                      if not overlap else
                                      f"shared: {', '.join(sorted(overlap))}"))
        return False, f"unevaluated shape {shape}"

    return select, holds
