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


class Method:
    """One thing you can do to a member of a kind. A tool call, with a receiver.

    IT IS A TOOL CALL AND THAT IS THE POINT. Tool-calling fidelity is what this model class
    is measurably best at — zero decode failures in 404 leaf emissions — so a class's public
    surface is the surface with the best track record in the system. Nothing here invents a
    new kind of thing for the model to learn.
    """

    def __init__(self, kind: str, name: str, verb: str, tool: str,
                 receiver_arg: Optional[str] = None, value_arg: Optional[str] = None,
                 attr: Optional[str] = None, value: Any = None, doc: str = ""):
        self.kind = kind
        self.name = name
        self.verb = verb
        self.tool = tool
        # WHICH ARGUMENT NAMES THE RECEIVER. `add_vm_to_network` takes `vm_name` where
        # `add_label` takes `name`, and a class that assumed one spelling would be a second
        # authority for something the manifest already states per setter.
        self.receiver_arg = receiver_arg
        self.value_arg = value_arg
        self.attr = attr
        self.value = value
        self.doc = doc

    def call(self, receiver: str, value: Any = None) -> tuple:
        """`(tool, args)` — the call this method IS, for one member.

        THE SAME PAIR THE WRITER ALREADY PLANS AND THE EXECUTOR ALREADY RUNS. A method that
        produced something else would need a second runtime, and the whole argument for
        deriving these is that there is nothing new underneath.
        """
        args: Dict[str, Any] = {}
        if self.receiver_arg:
            args[self.receiver_arg] = receiver
        if self.value_arg is not None and value is not None:
            args[self.value_arg] = value
        elif self.value is not None and self.value_arg is None and self.verb == SET:
            pass                      # a fixed-value setter takes no value argument
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
        name = "un" + (s.get("attr") or tool)
        out[name] = Method(kind, name, UNSET, tool, receiver_arg=s.get("member_arg"),
                           value_arg=s.get("value_arg"), attr=s.get("attr"),
                           doc=f"take this {kind}'s {s.get('attr')} away")

    for fact, o in (spec.get("observed") or {}).items():
        if o.get("by"):
            out[fact] = Method(kind, fact, ASK, o["by"], receiver_arg=key, attr=fact,
                               doc=f"ask this {kind} for its {fact}")
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
    got = methods(kind, kinds)
    if not got:
        return ""
    return f"{kind}:\n" + "\n".join(f"  .{m.name}() — {m.doc}"
                                    for m in sorted(got.values(), key=lambda x: x.name))


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
