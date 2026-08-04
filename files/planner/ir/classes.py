"""classes.py — every KIND is a class, and its methods are derived from the manifest.

THE OPERATOR'S DESIGN: *"make each vm, and each network a class, this way each vm and network
have their own methods, so calling a reach would be per network … i think it will make it
easier for the ai not to mess up and also allow more expression and abilities down the line"*

THE ARGUMENT IS ERROR-AVOIDANCE, NOT ELEGANCE. A method on an object cannot be asked about
the wrong scope, because THE SCOPE IS THE RECEIVER. Most of what goes wrong in this language
is scope: which set, which members, which network.

    today      REACH(SELECT vm)     — of what? every vm? on which network?
    classes    lab.reach()          — the members of `lab`, by construction

IT DISSOLVES #38 RATHER THAN DECIDING IT. Production's `reach` checked liveness; the bench's
also demanded a shared network, and the two seams each looked correct while disagreeing.
Neither was wrong — production was implementing `vm.reach()` and the bench was implementing
`network.reach()`. ONE FREE-FLOATING PREDICATE WAS DOING TWO JOBS UNDER ONE NAME, which is
why "REACH of what?" had no good answer. Split by receiver the ambiguity stops existing, and
that is the first concrete evidence for the error-avoidance claim: the scope error was not
the model's, it was IN THE LANGUAGE.

NOTHING NEW IS DECLARED. The manifest already carries, per kind, the tool that CREATES it,
the one that DELETES it, every SETTER and UNSETTER with the attribute it writes, and every
OBSERVED fact with the tool that establishes it. That is a constructor, a destructor,
accessors and a probe — a class in everything but name. So the methods are DERIVED, and the
standing care from the design note is met by construction: *"methods must not become a second
vocabulary"*. A method that drifted from the manifest is not expressible, because there is
nowhere to write one down.

WHAT THIS DELIBERATELY DOES NOT DO is put a class's interface in the whole-program prompt.
That was the first attempt and it was MEASURED at 64/78 -> 48/78, with model-layer failures
going 1 -> 12 and rungs unrelated to reach collapsing. The design that replaced it is a black
box — the author never sees inside, and choosing a method is its own small call blinded to
everything else. This module is the half that needs no model at all.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config, effects

# WHAT A METHOD IS FOR, in the four shapes a manifest row can take. The verb is derived from
# the row rather than written here, so a kind that grows a setter grows a method the same day.
MAKE = "make"          # the constructor — the kind's own creator
UNMAKE = "unmake"      # the destructor
SET = "set"            # a setter: give this member an attribute
UNSET = "unset"        # an unsetter: take one away
ASK = "ask"            # an observation: establish a fact by asking
ACT = "act"            # something you DO to it, whose effect the manifest cannot name

# WHY `ACT` HAD TO EXIST, and it is the operator's request that forced it: *"to vm add:
# modify, getters about os_types, etc… kill, etc… everything"*, and *"its to replace the
# straight forward tool calls"*.
#
# THIRTY-FOUR OF THE LAB'S FIFTY-THREE TOOLS WERE UNREACHABLE FROM MEDUSA. Almost every one
# takes `name` — a receiver — so almost every one is a method that had nowhere to be
# declared: the manifest could say a tool CREATES, DELETES, WRITES AN ATTRIBUTE or ANSWERS A
# QUESTION, and `open_shell`, `run_guest_command`, `resize_disk` and `update_config` are none
# of those. They act, and what they change is not a fact the language names.
#
# AND THAT IS EXACTLY WHY AN ACT PROMISES NOTHING. `postcondition` returns None for one,
# which the writer already reads as "this tool proves nothing" — the safe reading, and the
# honest one. An act is reachable, auditable and gated like any call; what it is NOT is
# evidence. A program that acts still has to ENSURE.


class Method:
    """One thing you can do to a member of a kind. A tool call, with a receiver.

    IT IS A TOOL CALL AND THAT IS THE POINT. Tool-calling fidelity is what this model class
    is measurably best at — zero decode failures in 404 leaf emissions — so a class's public
    surface is the surface with the best track record in the system. Nothing here invents a
    new kind of thing for the model to learn.
    """

    def __init__(self, kind: str, name: str, verb: str, tool: str,
                 receiver_arg: Optional[str] = None, value_arg: Optional[str] = None,
                 attr: Optional[str] = None, value: Any = None, doc: str = "",
                 takes: Optional[List[str]] = None,
                 fixed: Optional[Dict[str, Any]] = None,
                 into: Optional[str] = None):
        self.kind = kind
        self.name = name
        self.verb = verb
        self.tool = tool
        # WHAT ELSE THE CALL TAKES, in the order it is written. A setter takes one thing and
        # says so with `value_arg`; `set_resource_limits(cpu_percent, memory_mb)` takes two
        # and `open_shell()` takes none, so the general shape is a LIST and `value_arg` is
        # the first of it. Positional, like every other method here — the manifest already
        # says which slot each value goes into, so naming them at the call site would be the
        # caller repeating what the class knows.
        self.takes = list(takes) if takes else ([value_arg] if value_arg else [])
        # ARGUMENTS THE METHOD ALWAYS SENDS AND THE CALLER NEVER CHOOSES. `$vm.kill()` is
        # `stop_vm(force: true)` — the same tool as `$vm.stop()`, distinguished by an
        # argument that IS the method's meaning rather than a parameter of it.
        self.fixed = dict(fixed or {})
        # THE OBJECT ARGUMENT THIS METHOD'S VALUES GO INSIDE, when the tool takes one.
        self.into = into
        # WHICH ARGUMENT NAMES THE RECEIVER. `add_vm_to_network` takes `vm_name` where
        # `add_label` takes `name`, and a class that assumed one spelling would be a second
        # authority for something the manifest already states per setter.
        self.receiver_arg = receiver_arg
        self.value_arg = value_arg
        self.attr = attr
        self.value = value
        self.doc = doc

    def call(self, receiver: str, *values: Any) -> tuple:
        """`(tool, args)` — the call this method IS, for one member.

        THE SAME PAIR THE WRITER ALREADY PLANS AND THE EXECUTOR ALREADY RUNS. A method that
        produced something else would need a second runtime, and the whole argument for
        deriving these is that there is nothing new underneath.

        A VALUE NOT SUPPLIED IS NOT SENT, rather than sent as null. Most of these arguments
        are optional in the tool that receives them — `get_vm_logs(lines)`, `resize_disk
        (disk_index)` — and a null in an optional slot is a caller saying "none of them"
        where they meant "you choose".
        """
        args: Dict[str, Any] = {}
        if self.receiver_arg:
            args[self.receiver_arg] = receiver
        for slot, value in zip(self.takes, values):
            if value is None:
                continue
            # A VALUE THAT GOES INSIDE AN OBJECT ARGUMENT. `update_config` takes `updates`,
            # an OBJECT, and Medusa has no object literal — so `$vm.modify(memory_mb=8192)`
            # could only ever hand it a string, which is a method that always fails. Declared
            # per act with `into`, the value is placed where the tool wants it and the caller
            # writes what they mean: `$vm.memory(8192)`.
            if self.into:
                args.setdefault(self.into, {})[slot] = value
            else:
                args[slot] = value
        args.update(self.fixed)
        return self.tool, args

    def __repr__(self) -> str:
        return f"<{self.kind}.{self.name}() -> {self.tool}>"


def _verb(tool: str, kind: str, setter: Dict[str, Any]) -> str:
    """The method name for a fixed-value setter: its own verb, stripped of the kind.

    `launch_vm` -> `launch`, `stop_vm` -> `stop`, `mark_as_template` -> `template`. The kind
    is already the receiver, so repeating it in the name is exactly the noise a class removes
    — and the leading `mark_as`/`add`/`set` is the same: what the method DOES to the receiver
    is the attribute it writes, once the verb has told you which of several writers it is.
    """
    name = tool.replace(f"_{kind}", "").replace(f"{kind}_", "")
    for lead in ("mark_as_", "set_", "add_", "make_"):
        if name.startswith(lead):
            name = name[len(lead):]
    return name.strip("_") or setter.get("attr") or tool


def _spec(kind: str, kinds=None) -> Dict[str, Any]:
    return (effects._K(kinds) or {}).get(kind) or {}


def methods(kind: str, kinds=None) -> Dict[str, Method]:
    """The public surface of one kind, derived. `{name: Method}`.

    THE NAME IS THE ATTRIBUTE OR THE VERB, never the tool. `add_label` becomes `vm.label()`
    and `launch_vm` becomes `vm.launch()`, because a method is named for what it DOES to the
    receiver — the receiver is already known, so repeating its kind in the name is the noise
    a class exists to remove.

    A FIXED-VALUE SETTER IS ITS OWN METHOD. `stop_vm` writes `status = stopped` and takes no
    value, so it is `vm.stop()` rather than `vm.status('stopped')` — the manifest says which
    by carrying `value` instead of `value_arg`, and reading that is what keeps this derived
    rather than decided.
    """
    spec = _spec(kind, kinds)
    key = spec.get("key")
    out: Dict[str, Method] = {}
    if not key:
        return out

    # EVERY WAY A KIND CAN BE MADE, not just the default one. `creators` is where a second
    # constructor lives — `clone_vm` builds a machine FROM another — and reading only
    # `create` left it off the surface entirely: a class that offered some of what a kind can
    # do, wearing a complete-looking name.
    for cname, c in (spec.get("creators") or {}).items():
        if c.get("tool"):
            out[cname] = Method(kind, cname, MAKE, c["tool"],
                                receiver_arg=c.get("key") or key,
                                value_arg=c.get("from"),
                                doc=(f"bring a {kind} into being"
                                     + (f", copying the one named" if c.get("from") else "")))
    if spec.get("create") and "create" not in out:
        out["create"] = Method(kind, "create", MAKE, spec["create"], receiver_arg=key,
                               doc=f"bring a {kind} into being")
    if spec.get("delete"):
        out["delete"] = Method(kind, "delete", UNMAKE, spec["delete"], receiver_arg=key,
                               doc=f"remove this {kind}")

    for tool, s in (spec.get("setters") or {}).items():
        # A SETTER WHOSE VALUE IS ANOTHER KIND'S KEY IS NOT THIS KIND'S METHOD. `refs` says
        # the row describes a RELATION, and a relation has one receiver — the operator ruled
        # on 2026-08-04 that it is the thing being joined, not the thing joining:
        # `$lab.add_vm($web)`, never `$web.network($lab)`.
        #
        # WHY THAT END. The scope error a class exists to prevent is "which network?", and
        # a method cannot be asked about the wrong scope because the scope IS the receiver.
        # It also settles a question that has no other answer: ONE tool call has ONE
        # rendering, so if both ends offered a method the renderer would have to pick, and
        # the form it did not pick would be a spelling you could type and never save.
        if s.get("refs"):
            continue
        # THE VERB WHEN THERE IS ONE, THE ATTRIBUTE WHEN THERE IS NOT. `stop_vm` and
        # `launch_vm` both write `status`, so naming both `status` would collide — the tool's
        # own verb is what distinguishes them, and it is already in its name.
        # A FIXED-VALUE SETTER IS NAMED FOR ITS VERB, a valued one for its ATTRIBUTE.
        # `stop_vm` and `launch_vm` both write `status`, so the attribute cannot tell them
        # apart and the tool's own verb can; `add_label` writes any label, so the attribute
        # is what the caller is choosing.
        name = s["attr"] if "value_arg" in s else _verb(tool, kind, s)
        out[name] = Method(kind, name, SET, tool, receiver_arg=s.get("member_arg"),
                           value_arg=s.get("value_arg"), attr=s.get("attr"),
                           value=s.get("value"),
                           doc=(f"set this {kind}'s {s['attr']}"
                                + (f" to {s['value']}" if "value" in s else "")))

    for tool, s in (spec.get("unsetters") or {}).items():
        if s.get("refs"):
            continue                  # the other end's, exactly as for a setter
        name = "un" + (s.get("attr") or tool)
        out[name] = Method(kind, name, UNSET, tool, receiver_arg=s.get("member_arg"),
                           value_arg=s.get("value_arg"), attr=s.get("attr"),
                           doc=f"take this {kind}'s {s.get('attr')} away")

    # THE OTHER END OF EVERY RELATION THAT POINTS HERE. Derived, like everything else: a row
    # elsewhere saying `refs: network` IS the statement that a network can be joined, so the
    # method falls out of it and there is nothing new to declare. `add_vm` / `remove_vm` —
    # named for what is being joined, because the receiver already says what it joins.
    #
    # THE ARGUMENTS SWAP AND THAT IS THE WHOLE INVERSION. `add_vm_to_network` names the
    # member with `vm_name` and the network with `net_name`; called on the network, the
    # receiver is `net_name` and the value is `vm_name`. Both spellings come from the same
    # row, so neither end can drift from the tool.
    for other, ospec in (effects._K(kinds) or {}).items():
        if other == kind:
            continue
        for verb, rows in ((SET, ospec.get("setters")), (UNSET, ospec.get("unsetters"))):
            for tool, s in (rows or {}).items():
                if s.get("refs") != kind or not s.get("value_arg"):
                    continue
                name = f"{'add' if verb == SET else 'remove'}_{other}"
                out[name] = Method(kind, name, verb, tool,
                                   receiver_arg=s["value_arg"],
                                   value_arg=s.get("member_arg"),
                                   attr=s.get("attr"),
                                   doc=(f"{'add a' if verb == SET else 'take a'} {other} "
                                        f"{'to' if verb == SET else 'out of'} this {kind}"))

    # THINGS YOU DO TO IT. Keyed by METHOD rather than by tool, which is the one place this
    # map differs from `setters` and it is what lets `stop` and `kill` be the same tool told
    # apart by an argument. The row names the tool, which argument is the receiver, what else
    # it takes in order, and anything it always sends.
    for mname, a in (spec.get("acts") or {}).items():
        if not a.get("tool"):
            continue
        out[mname] = Method(kind, mname, ACT, a["tool"],
                            receiver_arg=a.get("member_arg") or key,
                            takes=a.get("takes"), fixed=a.get("args"),
                            into=a.get("into"),
                            doc=a.get("doc") or f"act on this {kind}")

    for fact, o in (spec.get("observed") or {}).items():
        if o.get("by"):
            # THE MANIFEST'S OWN WORDS WHEN IT HAS ANY. `vm.alive` is documented where it is
            # declared — *"whether the machine answers its guest agent"* — and generating a
            # sentence beside it would be a second description of one row, in worse English
            # than the row already has ("ask this vm for its alive").
            out[fact] = Method(kind, fact, ASK, o["by"], receiver_arg=key, attr=fact,
                               doc=(str(o.get("doc") or "").split(".")[0].strip()
                                    or f"ask this {kind} for its {fact}"))
    return out


def surface(kinds=None) -> Dict[str, Dict[str, Method]]:
    """Every kind as a class. `{kind: {method: Method}}`."""
    return {k: methods(k, kinds) for k in (effects._K(kinds) or {})}


def public(kind: str, kinds=None) -> str:
    """THE PUBLIC PROMPT OF THE CLASS — its methods and what each is for, and nothing else.

    The operator's design in one function: *"we basically only give it the 'public prompt of
    the class' which is its methods (tool calls, and their descriptions), so when the AI has
    to choose something about a class, we blind it to the outside world to select the
    method."*

    IT IS NOT IN THE WHOLE-PROGRAM PROMPT AND MUST NOT BE. The first attempt at classes put
    the interface where every author on every call paid for it, and was measured at
    64/78 -> 48/78 with model-layer failures going 1 -> 12. This string is for a call that
    has ALREADY been narrowed to one receiver — small by construction, because it sees one
    class and nothing else.
    """
    got = [m for m in methods(kind, kinds).values() if m.verb != MAKE]
    if not got:
        return ""
    # THE CONSTRUCTORS ARE NOT OFFERED, and the operator put the reason best: *"the vm/
    # network doesnt exist before the call"*. This string answers "what do I do to THIS one",
    # and there is no `this one` to make itself — a call that has been narrowed to a receiver
    # has, by definition, already got the thing. Offering `create` here would be offering the
    # one method whose precondition is that the receiver does not exist.
    return f"{kind}:\n" + "\n".join(
        f"  .{m.name}({', '.join(m.takes)}) — {m.doc}"
        for m in sorted(got, key=lambda x: x.name))


# ── the one question the parser and the renderer both ask ──────────────────────────────
def receiver(tool: str, args: Dict[str, Any], binds: Dict[str, str],
             kinds=None) -> Optional[tuple]:
    """`(var, method, values)` when this call IS a method on a bound receiver. Else None.

    ONE AUTHORITY, TWO READERS, and they must agree or the language is not writable. The
    RENDERER prints `$box.launch()` wherever this answers, and the PARSER refuses the long
    form wherever this answers — so what Gorgon prints is exactly what Gorgon accepts, by
    construction rather than by two functions kept in step. Written once here for the same
    reason `asks_reach` is written once: the day they disagree, a saved program stops
    reading back as itself and the failure surfaces three layers away.

    THE ARGUMENTS MUST MATCH EXACTLY, and that is the safety property. `launch_vm(name:
    $box, display: none)` is NOT `$box.launch()` — the method form would silently drop
    `display`, so it stays a long call. Asking the method to REBUILD the call and comparing
    is what makes the resugaring lossless: a form that would lose an argument never appears.

    A CONSTRUCTOR IS NOT A METHOD ON AN INSTANCE. `NEW CALL create_vm(...)` is how a thing
    comes into being — the operator's own instruction, unchanged — and `$box.create()` would
    be asking a machine to make itself.
    """
    if not isinstance(args, dict):
        return None
    hits = []
    for kind, ms in surface(kinds).items():
        for m in ms.values():
            if m.tool != tool or m.verb == MAKE or not m.receiver_arg:
                continue
            raw = args.get(m.receiver_arg)
            if not isinstance(raw, str) or not raw.startswith(config.SIGIL):
                continue
            var = raw[len(config.SIGIL):]
            if binds.get(var) != kind:
                continue
            # A TRAILING ARGUMENT NOBODY PASSED IS NOT WRITTEN. `get_vm_logs(name: $b)` is
            # `$b.logs()` and `get_vm_logs(name: $b, lines: 50)` is `$b.logs(50)`; the values
            # are read in the method's own order and the empty tail is dropped, so the two
            # print differently and both rebuild exactly.
            nest = args.get(m.into) if m.into else None
            held = nest if isinstance(nest, dict) else args
            values = [held.get(slot) for slot in m.takes]
            while values and values[-1] is None:
                values.pop()
            if m.call(raw, *values) == (tool, args):
                hits.append((var, m.name, values))
    if not hits:
        return None
    # ONE CALL, ONE RENDERING. Two methods can rebuild the same call — `$vm.stop()` and a
    # would-be `$vm.kill()` differ only by an argument, and a row that forgot to say so would
    # make the printed form depend on dictionary order. The SHORTEST spelling wins and ties
    # break by name, so the choice is stable and the parser's answer cannot drift from it.
    hits.sort(key=lambda h: (len(h[2]), h[1]))
    return hits[0]


# ── reach, split by receiver — the whole of #38 ────────────────────────────────────────
def reaches(kind: str, kinds=None) -> Optional[str]:
    """What `reach` MEANS for this kind, or None if it means nothing.

        vm.reach()       can THIS MACHINE be pinged        — per-member liveness
        network.reach()  are all its members CONNECTED     — membership and topology

    DERIVED, LIKE EVERYTHING ELSE HERE. A kind that can be ASKED something has a liveness
    reading; a kind that other members REFER TO — a network is the value of a vm's `network`
    attribute — has a topology reading. Both fall out of rows the manifest already carries,
    so neither is a decision this module makes.

    THE TWO WERE ONE PREDICATE AND THAT WAS THE BUG. #38 asked which of the two behaviours
    was right and the honest answer is both, of different receivers.
    """
    spec = _spec(kind, kinds)
    if spec.get("observed"):
        return "liveness"
    for other in (effects._K(kinds) or {}).values():
        for s in (other.get("setters") or {}).values():
            if s.get("refs") == kind:
                return "membership"
    return None
