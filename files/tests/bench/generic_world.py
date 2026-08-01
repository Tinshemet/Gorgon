"""generic_world.py — a world driven entirely by a manifest. NO DOMAIN ANYWHERE IN THIS FILE.

The operator's claim (2026-08-01): the harness is a UNIVERSAL TRANSLATION MEDIUM, and what
it translates TO is a role it is handed — today the Gorgon executor or Medusa, tomorrow
something else entirely. This is the test of that claim rather than an argument for it.

`SimWorld` knows about `vms`, `nets` and `snapshots` — it is the VM target's adapter, and it
is right that it exists. This is the same thing with the domain removed: state is
`{kind: {key: {attributes}}}`, and `execute` is derived from the manifest's own
`create` / `setters` / `unsetters` / `delete` rows. Nothing here mentions a machine, a
recipe, or anything else.

WHAT THIS PROVES, IF IT WORKS. The ghost writer, `effects`, and the whole plan-and-lower
machinery were written against VMs and tested on VMs. If a manifest for an unrelated domain
— with no new code — produces correct programs through the identical writer, then the
domain was never in the code. That is a much stronger statement than "it looks generic".

WHAT IT DOES NOT PROVE. A real target needs a real executor: this one just updates a dict.
Swapping in a genuine backend means writing that adapter, exactly as `SimWorld` stands in for
the executor here. The claim under test is about the WRITER, not about the world.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from orchestrator.ai.planner.ir import config as _config
from orchestrator.ai.planner.ir import observe as _observe


def _single(spec: Dict[str, Any], setter: Dict[str, Any]) -> bool:
    """Is this attribute single-valued? DERIVED, not declared.

    An attribute with an ENUMERATION takes one of its values — `status` is running or
    stopped, never both — while one without is a collection: a machine carries several
    labels and sits on several networks. So `attr_values` already answers the question, and
    a hand-written `single` flag beside it would be a second authority to drift from the
    first. An explicit flag still wins where a manifest needs to say otherwise.
    """
    if "single" in setter:
        return bool(setter["single"])
    return setter["attr"] in (spec.get("attr_values") or {})


class Ledger(dict):
    """What has been ASKED and answered. A dict, plus the `has` the real ledger offers.

    `observe.value` asks `ledger.has(fact)` — the interface production's ledger provides —
    while `_findings_of` and the reporter treat findings as a mapping. A plain dict failed
    the first and a bespoke object would fail the second, so it is both. THE POINT IS THAT
    `unknown` AND `false` STAY DIFFERENT: nobody asked is not the same as it said no, which
    is decision 6 and the reason `reach` demands an answer rather than a success flag.
    """

    def has(self, fact) -> bool:
        return fact in self


class World:
    """State as `{kind: {key: {attr: value}}}`, and a manifest that says how to change it."""

    def __init__(self, kinds: Dict[str, Any]):
        self.kinds = kinds
        self.state: Dict[str, Dict[str, Dict[str, Any]]] = {k: {} for k in kinds}
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self.findings: Ledger = Ledger()

    # ── the executor, derived ──────────────────────────────────────────────────────────
    def execute(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Do what the manifest says this tool does. Every branch is a manifest row.

        MULTI-VALUED ATTRIBUTES ARE A SET, always. A member can carry several labels and sit
        on several networks, and a recipe's dish can hold several ingredients — the shape is
        the same, so storing every attribute a setter writes as a set means no domain has to
        declare which of its attributes happen to be plural.
        """
        self.calls.append((tool, args))
        for kind, spec in self.kinds.items():
            key = spec.get("key")
            rows = self.state.setdefault(kind, {})

            # ASKING — the branch that was missing, and the manifest declares it like any
            # other. `observed.<fact>.by` names the tool; without this an observer tool fell
            # through to "unknown tool" and wrote nothing, so a `reach` goal could never be
            # satisfied against this world and every one of them promoted to tree.
            #
            # A MODEL ASSUMES ITS PROBES ARE ANSWERED, and says so here rather than
            # pretending to know. This world cannot ping anything; what it is for is deciding
            # whether a plan WOULD close its goals. The real run overwrites these with real
            # answers, and the program's own closing ENSURE is what catches the difference —
            # which is exactly why the writer grounds every goal it plans.
            for fact_name, o in (spec.get("observed") or {}).items():
                if tool != o.get("by"):
                    continue
                member = args.get(key)
                if member not in rows:
                    return {"success": False, "error": f"no {kind} {member}"}
                fact = _config.fact_key(kind, fact_name, member)
                if fact is not None:
                    self.findings[fact] = True
                return {"success": True, key: member, fact_name: True}

            if tool == spec.get("create"):
                name = args.get(key)
                if name is None or name in rows:
                    return {"success": False, "error": "exists or unnamed"}
                rename = {v: k for k, v in (spec.get("create_args") or {}).items()}
                row = dict(spec.get("create_defaults") or {})
                for a, v in args.items():
                    if a != key:
                        row[rename.get(a, a)] = v
                rows[name] = row
                return {"success": True, key: name}

            if tool == spec.get("delete"):
                return ({"success": True} if rows.pop(args.get(key), None) is not None
                        else {"success": False, "error": "no such member"})

            for setter_tool, s in (spec.get("setters") or {}).items():
                if tool != setter_tool:
                    continue
                member = args.get(s["member_arg"])
                if member not in rows:
                    return {"success": False, "error": f"no {kind} {member}"}
                value = args.get(s["value_arg"]) if "value_arg" in s else s.get("value")
                if _single(spec, s):
                    rows[member][s["attr"]] = value
                else:
                    held = rows[member].get(s["attr"])
                    if not isinstance(held, set):
                        # A SCALAR WHERE A SET WAS EXPECTED is a manifest inconsistency —
                        # a `create_defaults` entry for an attribute a multi-valued setter
                        # also writes. Absorb it rather than crash: the world's job is to be
                        # a world, and a backend that raises destroys the plan around it for
                        # the same reason a seam may not raise.
                        held = set() if held is None else {held}
                    held.add(value)
                    rows[member][s["attr"]] = held
                return {"success": True}

            for unset_tool, u in (spec.get("unsetters") or {}).items():
                if tool != unset_tool:
                    continue
                member = args.get(u["member_arg"])
                if member not in rows:
                    return {"success": False, "error": f"no {kind} {member}"}
                held = rows[member].get(u["attr"])
                if isinstance(held, set):
                    held.discard(args.get(u["value_arg"]))
                elif held == args.get(u.get("value_arg")):
                    rows[member].pop(u["attr"], None)
                return {"success": True}

        return {"success": False, "error": f"unknown tool {tool}"}

    @property
    def seams(self):
        """The target names its own adapter, so the writer never has to know which it is."""
        return seams(self)

    def names(self) -> set:
        return {n for rows in self.state.values() for n in rows}


def seams(world: World):
    """`select` and `holds` over a manifest-driven world. The same two questions, no domain.

    Deliberately the SAME PAIR the VM target injects, because the language is defined by the
    questions it asks and not by who answers them. A target that answered a different
    question would be a different language wearing the same words.
    """
    def _match(row: Dict[str, Any], name: str, key: str, filters: Dict[str, Any]) -> bool:
        for attr, want in filters.items():
            if attr in ("kind", "not"):
                continue
            got = name if attr == key else row.get(attr)
            if isinstance(got, set):
                if want not in got:
                    return False
            elif got != want:
                return False
        return True

    def select(sel, scope=None):
        kind = sel.get("kind")
        spec = (world.kinds or {}).get(kind) or {}
        key = spec.get("key")
        rows = world.state.get(kind) or {}
        carve = sel.get("not") or {}
        return sorted(n for n, row in rows.items()
                      if _match(row, n, key, sel)
                      and not (carve and _match(row, n, key, carve)))

    def _shared_value(kind, members):
        """A value of the CONNECTIVE attribute that every member holds, or None.

        What connects members is a manifest fact — the setter whose value `refs` another
        kind — not the word "network". Derived here for the same reason the writer derives
        it: a world method only one world implements is a dependency, not a seam.
        """
        spec = (world.kinds or {}).get(kind) or {}
        link = next((s_ for s_ in (spec.get("setters") or {}).values()
                     if s_.get("refs")), None)
        if not link or not members:
            return None
        connector, ref_kind = link["attr"], link["refs"]
        for cand in select({"kind": ref_kind}):
            on = select({"kind": kind, connector: cand})
            if all(m in on for m in members):
                return cand
        return None

    def holds(pred, scope=None):
        if pred.get("shape") == "reach":
            # THE SAME TWO DEMANDS PRODUCTION MAKES: every member has ANSWERED, and there is
            # a path between them. A5 tightened this once already because the bench and
            # production had drifted — a checker weaker than the runtime silently certifies
            # programs the real lab refuses.
            kind = (pred.get("select") or {}).get("kind")
            members = select(pred.get("select") or {})
            floor = int(pred.get("min", 2))
            if len(members) < floor:
                return False, f"reach over {len(members)} member(s), floor {floor}"
            unknown = [m for m in members
                       if _observe.value(world.findings, kind, "alive", m)
                       == _observe.unknown()]
            if unknown:
                return False, (f"reach is unestablished: {len(unknown)} of {len(members)} "
                               f"have not been probed")
            dead = [m for m in members
                    if _observe.value(world.findings, kind, "alive", m) == _observe.FALSE]
            if dead:
                return False, f"no answer from {', '.join(sorted(dead))}"
            spec = (world.kinds or {}).get(kind) or {}
            connective = any(s_.get("refs") for s_ in (spec.get("setters") or {}).values())
            if connective and not _shared_value(kind, members):
                return False, (f"all {len(members)} answered, but they share no "
                               f"connection — reach also means a path between them")
            return True, f"all {len(members)} member(s) answered and are connected"
        if pred.get("shape") == "count":
            n = len(select(pred.get("select") or {}))
            for c, op in (("eq", "=="), ("gte", ">="), ("lte", "<=")):
                if c in pred:
                    good = {"==": n == pred[c], ">=": n >= pred[c],
                            "<=": n <= pred[c]}[op]
                    return good, f"count is {n}, wanted {op} {pred[c]}"
        return False, f"unevaluated shape {pred.get('shape')}"

    return select, holds
