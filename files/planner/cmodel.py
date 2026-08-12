"""cmodel.py — THE COMPUTATIONAL MODEL: what a program DOES, before anyone chooses a language.

⇒⇒ **THE MIDDLE OF THREE LAYERS, AND THE ONLY ONE THAT IS ALLOWED TO BE PERMANENT.**

    SCAFFOLD              HIGH-LEVEL CODE POINTS — the operator's phrase, 2026-08-13. Not prose
                          about the request and not code: the points a program must hit.
                          `create_vm(alpha)` · `launch_vm(alpha)`
    COMPUTATIONAL MODEL   THIS. Language-independent: what happens, in what order, over what.
    CODE                  Medusa today, PYTHON TOMORROW. The engine emits it.

The operator: *"it should first be computed to a computational model — this way today it's
Medusa, tomorrow it's Python … then we give the computational model and it turns into code in
the engine."*

⇒ **WHY THIS IS NOT MEDUSA'S IR RENAMED.** `planner/ir` is a fine IR and its ops are MEDUSA's:
  they carry `ifails`, `graft`, `cleanup`, `var` — machinery that belongs to one language's
  error handling and binding. This keeps the COMPUTATION and treats every domain operation as
  OPAQUE, so a second emitter calls the same executor through the same names without inheriting
  the first language's grammar.

⇒ **FIVE NODES, CHOSEN BECAUSE THEY ARE THE MEASURED CORE.** The manifest already declares which
  ops the no-model path emits — `new · publish · call · ensure · foreach` — so this is not a
  fresh taxonomy, it is the five that survived. Each maps to both targets, which is the whole
  portability claim and is asserted by the emitters, never argued:

      MAKE   bring a thing about        new      / a constructor call
      DO     invoke a named operation   call     / a function call
      EACH   repeat over a set          foreach  / a for loop
      HOLD   an assertion that must be true   ensure / an assert
      TELL   report a fact upward       publish  / a return

⇒ **BINDING IS BY NAME AND NOTHING ELSE.** A step may `bind` a name; a later step refers to it.
  No scopes, no mutation, no aliasing — the properties that make a model hard to emit into an
  unfamiliar language. A name is written once, which is what lets an emitter choose between a
  variable, a register or a pipeline stage.

⇒ **AND IT CARRIES NO ENGLISH.** Everything here is already a decision. If a reader of this file
  would have to consult the request to know what a node means, the layer above did not finish
  its job — that is the test for whether the scaffold is code points or a description.
"""
from typing import Any, Dict, List, NamedTuple, Optional

MAKE, DO, EACH, HOLD, TELL = "make", "do", "each", "hold", "tell"


class _Ref(str):
    """A NAME, not a string value — `on=it` rather than `on='it'`.

    ⇒ A SUBCLASS OF `str` SO EVERY EXISTING READER KEEPS WORKING, and `repr` is what tells the
      two apart. An emitter that quoted a reference would produce a program that acts on the
      literal text of a variable name, which is the loop bug in a second costume.
    """
    __slots__ = ()

    def __repr__(self):
        return str(self)

KINDS = (MAKE, DO, EACH, HOLD, TELL)


class Node(NamedTuple):
    """One step. `kind` decides which fields mean anything — deliberately one type rather than
    five, so a traversal cannot forget a case and an emitter must handle `kind` exhaustively."""
    kind: str
    # MAKE
    of: Optional[str] = None            # what kind of thing to bring about
    count: Any = None                   # how many; None means one
    # DO
    op: Optional[str] = None            # the OPAQUE operation name — the executor's, not ours
    args: Dict[str, Any] = {}
    # EACH
    over: Optional[str] = None          # a bound name holding a set
    body: List["Node"] = ()
    item: str = "item"                  # the name each member takes inside `body`
    # HOLD
    must: Optional[Dict[str, Any]] = None   # a predicate, in the IR's own shape
    # TELL
    fact: Optional[str] = None
    # every node may name its result
    bind: Optional[str] = None

    def __repr__(self):
        if self.kind == MAKE:
            return f"{self.bind or '_'} = make {self.count or 1} {self.of}"
        if self.kind == DO:
            return f"{(self.bind + ' = ') if self.bind else ''}do {self.op}({self.args})"
        if self.kind == EACH:
            return f"each {self.item} in {self.over}: {list(self.body)}"
        if self.kind == HOLD:
            return f"hold {self.must}"
        return f"tell {self.fact}"


class Model(NamedTuple):
    """A whole program's worth of computation."""
    steps: List[Node] = ()
    name: Optional[str] = None          # set when the operator asked for a stored procedure

    def __repr__(self):
        return "\n".join(repr(n) for n in self.steps) or "(nothing to do)"


# ── the scaffold, compiled ────────────────────────────────────────────────────────────────

def from_scaffold(operations, declarations, makers=None, sets=None,
                  params=None) -> Model:
    """High-level code points -> computation. PLAIN DATA IN, so nothing imports the seam.

    ⇒ **THE INTERFACE IS TUPLES AND DICTS ON PURPOSE.** The scaffold is produced in the bench
      today and will move; a signature naming its types would make this layer un-runnable the
      moment the layer above it is refactored, which is the coupling this whole middle layer
      exists to prevent.

        operations    [(op, on, value)]         the code points, in order
        declarations  {name: {kind, is_set}}    what each handle refers to
        makers        {op: kind}                which operations BRING SOMETHING ABOUT
        sets          {name}                    which handles hold several things
        params        {op: (target, value)}     what the OPERATION calls its arguments

    ⇒⇒ **`params` EXISTS BECAUSE THE SCAFFOLD SPEAKS IN HANDLES AND A TOOL TAKES NAMED
      ARGUMENTS**, and the engine's validator said so on the first real run: *"statement 3:
      add_vm_to_network requires 'net_name'"*. The scaffold's `(on, value)` are the row and the
      thing it relates to; `net_name` is what the TOOL calls its second argument. Mapping the two
      is a manifest lookup, so it is PASSED IN rather than read here — this layer must not import
      a manifest any more than an emitter may.

    ⇒ AN OPERATION OVER A SET BECOMES AN `EACH`, and that is the one real decision here: the
      scaffold says *what*, and a set target is what turns a single point into iteration. It is
      read from the DECLARATION, never from the operation — the row already knows whether it is
      one thing or several ([[gorgon-slots-not-shapes]]).
    """
    makers = makers or {}
    sets = set(sets or ())
    steps: List[Node] = []
    for op, on, value in operations:
        target = str(on)
        made = makers.get(op)
        on_name, value_name = (params or {}).get(op) or ("on", "value")
        args = {on_name: target}
        if value not in (None, ""):
            args[value_name] = value
        if made:
            # ⇒ A CREATOR IS A `MAKE`, NOT A `DO`, even though the executor call is identical.
            #   The distinction is not cosmetic: an emitter for a language with constructors
            #   wants it, and a MAKE is the only node that may BIND A NAME NOBODY DECLARED.
            #
            # ⇒⇒ **AND A MAKE'S ARGUMENTS ARE THE DECLARATION'S, NEVER THE HANDLE.** The first
            #   cut passed `on=<handle>` as a creator argument and the ENGINE'S OWN VALIDATOR
            #   rejected it on the first real run: *"NEW vm also requires 'os_type' … NEW already
            #   calls create_vm; do NOT add a separate create_vm call."* Right on both counts —
            #   the handle is what this step BINDS, not something it takes, and what a creator
            #   takes is what the request SAID about the thing, which the row already holds in
            #   `where`. Caught the moment the model met a real executor, which is the argument
            #   for wiring a layer to something that runs rather than to a second mock.
            row = declarations.get(target) or {}
            steps.append(Node(MAKE, of=made, op=op, args=dict(row.get("where") or {}),
                              bind=target, count=row.get("count")))
            continue
        if target not in sets:
            steps.append(Node(DO, op=op, args=args))
            continue
        # ⇒⇒ **THE LOOP MUST BIND, OR IT IS A LOOP OVER NOTHING.** The first cut emitted
        #   `FOREACH $it IN $vms { CALL add_vm_to_network(on='vms') }` — iterating the set while
        #   still naming the SET inside the body, so every pass did the same thing to the whole
        #   collection. Caught by reading the emitted source, which is the argument for shipping
        #   two emitters: a model you can only inspect as a dataclass hides this.
        item = "it"
        inner = dict(args)
        inner[on_name] = _Ref(item)
        steps.append(Node(EACH, over=target, item=item,
                          body=[Node(DO, op=op, args=inner)]))
    return Model(tuple(steps))


def holds(goals) -> List[Node]:
    """Goals -> assertions. A goal is already a predicate; it needs no translation, only a home."""
    return [Node(HOLD, must=g) for g in (goals or ())]
