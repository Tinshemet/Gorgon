"""effects.py — what a tool MAKES TRUE, as a Medusa predicate.

A tool's postcondition, written in the language the GOALS are written in. That last part is
the whole point: once a tool can say "after me, `COUNT(SELECT vm WHERE name = X) = 1`", a
deterministic writer can chain tools toward a goal by matching postconditions against it,
and `derive()` closes whatever gap is left. Nothing here calls a model.

WHY THIS IS NOT `TOOL_EFFECTS`. The executor already carries an `effect` per tool, and
`create_vm`'s is `["vm_reload"]` — a CACHE INVALIDATION HINT. It says the registry should be
re-read, not what became true. Useful, and a different fact; conflating them would give the
writer a hint where it needs a claim.

MOST POSTCONDITIONS ARE DERIVED, NOT DECLARED. The manifest already says, per kind, which
tool CREATES it, which DELETES it, and what its KEY is — so a creator's postcondition is a
consequence of facts already recorded, and writing it out again would be a second authority
to drift from the first. Only the SETTERS needed new data (`kinds.<k>.setters`), because
which attribute a tool writes was genuinely nowhere.

THE TEST THAT MATTERS is not that these parse. It is that they are TRUE: run the tool
against the sim, evaluate the predicate through the same seams the language uses, and it must
hold. A postcondition that is merely well-formed is the 2026-07-31 failure mode one level up
— a mechanism that looks wired and asserts nothing.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import config


def _K(kinds):
    """The manifest in force. A TARGET is a manifest plus a world that can read and act;
    everything else here is domain-free and always was.

    AN EMPTY MANIFEST MEANS "THE ONE IN FORCE", not "a domain with no kinds". An engine
    running on Gorgon's own manifest carries `{}` — it has nothing of its own to declare —
    and reading that literally answered every question with silence: no tools, no kinds, no
    deleters. Silence is the dangerous default here, because the caller asking "what would
    this destroy?" got "nothing".
    """
    return kinds if kinds else (config.KINDS or {})


def _kind_of(tool: str, kinds=None) -> Optional[str]:
    """Which kind this tool acts on, from the manifest alone."""
    for kind, spec in _K(kinds).items():
        if tool == spec.get("create") or tool == spec.get("delete"):
            return kind
        if tool in (spec.get("setters") or {}):
            return kind
        if any(c.get("tool") == tool for c in (spec.get("creators") or {}).values()):
            return kind
    return None


def _exists(kind: str, key_attr: str, value: Any, count: int = 1) -> Dict[str, Any]:
    return {"shape": "count", "select": {"kind": kind, key_attr: value}, "eq": count}


def postcondition(tool: str, args: Dict[str, Any], kinds=None) -> Optional[Dict[str, Any]]:
    """The predicate that must hold after `tool` succeeds, or None if unknown.

    NONE MEANS UNKNOWN AND MUST STAY THAT WAY — the writer treats an unknown postcondition as
    "this tool proves nothing", which is the safe reading. Guessing one would let a solver
    believe a goal was reached because a tool it does not understand returned ok, which is
    precisely the "unverified is not done" rule the language is built on, broken from the
    inside.
    """
    kind = _kind_of(tool, kinds)
    if not kind:
        return None
    spec = _K(kinds).get(kind) or {}
    key = spec.get("key")

    setter = (spec.get("setters") or {}).get(tool)
    if setter:
        member = args.get(setter.get("member_arg"))
        value = (args.get(setter["value_arg"]) if "value_arg" in setter
                 else setter.get("value"))
        if member is None or value is None:
            return None
        # BOTH halves, because either alone is satisfiable by the wrong world: the member
        # filter without the attribute says only that the machine exists, and the attribute
        # without the member says only that SOMETHING carries it.
        return {"shape": "count",
                "select": {"kind": kind, key: member, setter["attr"]: value},
                "eq": 1}

    # CREATORS AND DELETERS, derived from the manifest. `creators` may name a different key
    # argument (clone_vm writes `new_name`), so it is read rather than assumed.
    for c in (spec.get("creators") or {}).values():
        if c.get("tool") == tool:
            name = args.get(c.get("key") or key)
            return _exists(kind, key, name) if name is not None else None
    if tool == spec.get("create"):
        name = args.get(key)
        return _exists(kind, key, name) if name is not None else None
    if tool == spec.get("delete"):
        name = args.get(key)
        # NOT the negation of "exists" — a count of ZERO. Medusa has `not` for selects, and
        # writing it that way would make the deleter's claim a different shape from the
        # creator's for no reason. Same predicate, different number.
        return _exists(kind, key, name, count=0) if name is not None else None
    return None


def _mint_required(spec: Dict[str, Any], args: Dict[str, Any], kinds) -> None:
    """Fill in a REQUIRED host nobody named. Mutates `args`.

    "Search the web for X" says nothing about a browser or a machine, and a search cannot
    exist without either — so the writer names them, exactly as it names the machines behind
    "create 5 vms". Declared per kind with `create_requires` and NEVER INFERRED: minting for
    an optional reference would grow a program work nobody asked for.

    IT BELONGS TO BOTH CREATOR BRANCHES. `invert` reaches a creator two ways — a goal naming
    only the key ("a search for X exists") and one naming attributes too — and putting this
    in the second alone meant the commonest shape of all, a bare identity, silently skipped
    its own requirements.
    """
    rename = spec.get("create_args") or {}
    for req in (spec.get("create_requires") or ()):
        # A REQUIREMENT IS A KIND, or a kind plus what must be true of it.
        need = req["kind"] if isinstance(req, dict) else req
        arg = rename.get(need, need)
        if args.get(arg) is not None:
            continue
        ref_spec = _K(kinds).get(need) or {}
        if ref_spec.get("key"):
            args[arg] = f"{need}1"


def precondition(tool: str, args: Dict[str, Any], kinds=None) -> list:
    """What must ALREADY be true for `tool` to succeed. Derived, never declared.

    A setter acts on a member, so that member must exist; and where the value it writes is
    the KEY OF ANOTHER KIND (`refs`), that entity must exist too. Both fall out of the
    manifest — no second table to keep in step with the first.

    THIS IS WHERE ORDER COMES FROM, and it is worth being explicit that nothing else
    supplies it. The prompt currently spends 77 characters telling the model "order matters —
    a foreach over {tag:red} only finds VMs already labelled". A writer does not need to be
    told: `add_vm_to_network` requires `lab` to exist, so the tile that creates `lab` is
    placed first because the dependency says so, not because a model remembered a sentence.
    """
    kind = _kind_of(tool, kinds)
    spec = _K(kinds).get(kind) or {}
    out = []

    # A CREATOR'S ARGUMENTS CAN NAME OTHER THINGS, and until now none of them were
    # requirements. A snapshot is OF a machine and a search runs IN a browser; those members
    # must exist before the creator runs, and `precondition` only ever looked at setters —
    # so `snapshot_create(snap_name: s1)` planned with no machine anywhere, and the Camoufox
    # package's three-level chain stopped after one.
    #
    # THE TIE IS THE ATTRIBUTE'S NAME, which is this codebase's stated convention and not a
    # new one: "a snapshot's `vm`, a page's `crawl` — the tie is an attribute of the thing
    # being made, named for the thing it belongs to" (`extract._link_between`). Guarded on
    # the name being a DECLARED KIND, so an ordinary attribute never becomes a dependency.
    if tool == spec.get("create"):
        rename = spec.get("create_args") or {}
        # WHAT A REQUIREMENT DEMANDS BEYOND EXISTING. A browser needs a machine that is
        # RUNNING, not merely one that has been created — a process cannot start on a host
        # that is switched off, and requiring only existence produced a program that made a
        # machine and then tried to run something inside it.
        demands = {}
        for req in (spec.get("create_requires") or ()):
            if isinstance(req, dict) and req.get("kind"):
                demands[req["kind"]] = req.get("must") or {}
        for attr in (spec.get("attrs") or ()):
            ref_spec = _K(kinds).get(attr)
            if not ref_spec or not ref_spec.get("key"):
                continue
            value = args.get(rename.get(attr, attr))
            if value is not None:
                need = _exists(attr, ref_spec["key"], value)
                need["select"].update(demands.get(attr) or {})
                out.append(need)
        return out

    setter = (spec.get("setters") or {}).get(tool)
    if not setter:
        return out
    member = args.get(setter.get("member_arg"))
    if member is not None and spec.get("key"):
        out.append(_exists(kind, spec["key"], member))
    ref_kind = setter.get("refs")
    if ref_kind and "value_arg" in setter:
        ref_spec = _K(kinds).get(ref_kind) or {}
        value = args.get(setter["value_arg"])
        if value is not None and ref_spec.get("key"):
            out.append(_exists(ref_kind, ref_spec["key"], value))
    return out


def invert(pred: Dict[str, Any], kinds=None, internal: bool = False) -> Optional[tuple]:
    """Given a predicate, the tool that MAKES IT TRUE, and with what arguments.

    The tile-selection step, and it needs no search: for the `count` shapes these tiles
    produce, the mapping is a direct inversion of `postcondition`. A select carrying only
    the kind's key names a member that must EXIST, which is the creator's job; one carrying
    the key AND an attribute names an attribute that must be SET, which is a setter's; a
    count of zero is the deleter's.

    Returns None when no tile makes it true — the honest answer, and the one that tells a
    writer to decompose rather than to invent a step.
    """
    if not isinstance(pred, dict) or pred.get("shape") != "count":
        return None
    sel = pred.get("select") or {}
    kind = sel.get("kind")
    spec = _K(kinds).get(kind) or {}
    key = spec.get("key")
    if not key or key not in sel:
        return None                       # no named member — a set-level goal, not a tile
    member = sel[key]
    rest = {k: v for k, v in sel.items() if k not in ("kind", key)}

    if pred.get("eq") == 0:
        if not rest:
            return (spec["delete"], {key: member}) if spec.get("delete") else None
        # "THIS MEMBER MUST NOT CARRY THIS VALUE" — the unsetter, and the reason it is a
        # separate table from `setters`: taking a label off is not writing a different label,
        # and a writer that reached for `add_label` to satisfy a removal would add noise
        # while the count stayed wrong.
        if len(rest) == 1:
            attr, value = next(iter(rest.items()))
            for tool, u in (spec.get("unsetters") or {}).items():
                if u["attr"] == attr and "value_arg" in u:
                    return (tool, {u["member_arg"]: member, u["value_arg"]: value})
        return None
    if pred.get("eq") != 1:
        return None                       # counts other than 0/1 are derive()'s territory
    if not rest:
        creator = spec.get("create")
        if not creator:
            return None
        args = dict((spec.get("create_defaults") or {}))
        args[key] = member
        _mint_required(spec, args, kinds)
        return (creator, args)
    if len(rest) == 1:
        attr, value = next(iter(rest.items()))
        for tool, s in (spec.get("setters") or {}).items():
            if s["attr"] != attr:
                continue
            # CONSTANT ARGUMENTS THE MANIFEST ATTACHES TO A SETTER, and `internal_args`
            # only when the call is the PROGRAM'S OWN rather than the operator's.
            #
            # `launch_vm` takes a DISPLAY MODE and the shipped default opens a graphical
            # window. WHO THE MACHINE IS FOR decides: an operator who asked to launch a
            # machine wants to see it, and a machine started so a package can work inside it
            # wants a shell and nothing else — a VNC session there is cost with no reader.
            # The writer knows which it is placing, so the manifest states the fact and the
            # writer states the provenance; neither has to know the other's business.
            fixed = dict(s.get("args") or {})
            if internal:
                fixed.update(s.get("internal_args") or {})
            if "value_arg" in s:
                return (tool, {**fixed, s["member_arg"]: member, s["value_arg"]: value})
            if s.get("value") == value:
                return (tool, {**fixed, s["member_arg"]: member})

    # NO SETTER WRITES IT — SO IT IS SET AT BIRTH. A snapshot's `vm` is not an attribute
    # anyone changes later; it is what the snapshot IS, supplied when it is created. So a
    # goal naming a member that does not exist yet, with attributes no setter owns, is the
    # creator's call with those attributes as arguments. Guarded on the attributes being
    # real ones of the kind, so a typo becomes None rather than a call with an invented
    # argument.
    attrs = set(spec.get("attrs") or ())
    if spec.get("create") and rest and set(rest) <= attrs:
        args = dict(spec.get("create_defaults") or {})
        args[key] = member
        # ATTRIBUTE -> ARGUMENT, where the manifest says they differ. A snapshot's `vm` is
        # queried as `vm` and passed as `name`; without the mapping the call carried an
        # argument the tool ignored and the snapshot was taken of nothing.
        rename = spec.get("create_args") or {}
        for a, v in rest.items():
            args[rename.get(a, a)] = v
        _mint_required(spec, args, kinds)
        return (spec["create"], args)


def forbids(tool: str, args: Dict[str, Any], kinds=None) -> list:
    """What must NOT already be true for `tool` to be placeable. Never satisfiable by acting.

    A creator cannot run on a name that already exists, and that is a different kind of
    requirement from a precondition: a precondition is something to GO AND ACHIEVE, while
    this is a condition on the world that the writer must accept or give up on. Conflating
    them is dangerous in one specific way — "x must not exist" is satisfiable by DELETING x,
    so a writer that treated it as an ordinary goal would destroy a machine to make room for
    one it was asked to create. It must refuse instead.

    Found 2026-07-31: with creators able to take attributes, `COUNT(SELECT vm WHERE name=x
    AND os_type=windows) = 1` against an existing linux `x` inverted to `create_vm(name=x,
    os_type=windows)` — a call the world would reject, for a goal nothing can reach, because
    no tool CHANGES os_type after birth.
    """
    kind = _kind_of(tool, kinds)
    spec = _K(kinds).get(kind) or {}
    key = spec.get("key")
    if not key or tool != spec.get("create") or args.get(key) is None:
        return []
    # ALWAYS, for any creator — no special case for the with-attributes form. A creator
    # cannot run on a name that is taken, full stop, and the simpler rule is also the true
    # one. It costs nothing on a plain creation goal: `count == 1` already holds when the
    # member exists, so the writer never reaches the tile to be stopped by this.
    #
    # The first version tried to fire only when extra attributes were named, and excluded
    # anything in `create_defaults` — which cancelled the guard exactly where it was needed,
    # because os_type IS a default. Narrowing a guard to the case you have in mind is how a
    # guard ends up not guarding.
    return [_exists(kind, key, args[key], count=0)]
    return None


def setter_for(kind: str, attr: str, value: Any, kinds=None) -> Optional[tuple]:
    """The tool that writes `attr = value` on a member of `kind`, or None.

    Split out of `invert` because a SET goal needs the same lookup without a member to bind
    it to — "make every stopped machine running" picks the tool once and applies it many
    times.
    """
    spec = _K(kinds).get(kind) or {}
    for tool, s in (spec.get("setters") or {}).items():
        if s["attr"] != attr:
            continue
        if "value_arg" in s:
            return (tool, s["member_arg"], s["value_arg"], None)
        if s.get("value") == value:
            return (tool, s["member_arg"], None, s["value"])
    return None


def complement(kind: str, attr: str, value: Any, kinds=None) -> Optional[Any]:
    """The other value `attr` can take, when there is exactly one. Otherwise None.

    "No machine may be stopped" is only actionable if the writer knows what a machine should
    be INSTEAD, and `attr_values` answers that when the attribute is a two-state one. With
    three or more it is genuinely ambiguous — the goal did not say which — and returning
    None makes the solver stop and say so rather than pick. That is
    [[gorgon-deterministic-rules]]: compute, and decline when unsure.
    """
    enum = (_K(kinds).get(kind) or {}).get("attr_values", {}).get(attr)
    others = [v for v in (enum or ()) if v != value]
    return others[0] if len(others) == 1 else None


def probe_for(kind: str, fact: str, kinds=None) -> Optional[str]:
    """The tool that ESTABLISHES an observed fact — from `kinds.<k>.observed`.

    Reachability is a FINDING, never an inference from a tool's success flag (decision 6,
    and A5 tightened the bench's `reach` on exactly this). So a goal that speaks about an
    observed attribute has a precondition nothing else can supply: somebody has to ask. The
    manifest already records who — `observed.alive.by` — so this is read, not declared twice.
    """
    obs = (_K(kinds).get(kind) or {}).get("observed", {}).get(fact) or {}
    return obs.get("by")


def tools_of(kinds=None) -> set:
    """Every tool the manifest names — the engine's own registry, derived.

    `validate` checks statements against KNOWN TOOLS, and until an engine could supply its
    own that check silently meant "known to the VM executor". A kitchen's `create_dish` is
    not a Gorgon tool and never will be, so validating it against Gorgon's registry rejected
    a correct program. The manifest already names every tool it uses; asking it is one loop.
    """
    out = set()
    for spec in _K(kinds).values():
        for field in ("create", "delete"):
            if spec.get(field):
                out.add(spec[field])
        out |= set(spec.get("setters") or {})
        out |= set(spec.get("unsetters") or {})
        out |= {c["tool"] for c in (spec.get("creators") or {}).values() if c.get("tool")}
        out |= {o["by"] for o in (spec.get("observed") or {}).values() if o.get("by")}
    return out


def deleters(kinds=None) -> Dict[str, str]:
    """Every tool that DESTROYS a member, mapped to its kind. Derived, never listed.

    The manifest already names each kind's deleter, so a hand-kept list of "dangerous tools"
    would be a second source that drifts the first time a kind is added — and it would drift
    SILENTLY, in the direction of calling a destructive tool safe.
    """
    return {spec["delete"]: kind for kind, spec in _K(kinds).items() if spec.get("delete")}


def declared(kinds=None) -> Dict[str, str]:
    """Every tool that carries a postcondition, mapped to its kind — for drift tests."""
    out: Dict[str, str] = {}
    for kind, spec in _K(kinds).items():
        for t in (spec.get("setters") or {}):
            out[t] = kind
        for c in (spec.get("creators") or {}).values():
            if c.get("tool"):
                out[c["tool"]] = kind
        for field in ("create", "delete"):
            if spec.get(field):
                out[spec[field]] = kind
    return out
