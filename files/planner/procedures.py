"""procedures.py — a named Medusa program, kept, and reachable again.

THE OPERATOR'S TEST, and it is a better one than "can it write a snippet": *"the reason I
want to build this snippet is to also test if it can call those snippets when it's done."*
Writing an artifact proves the writer works. USING it later proves the system has a memory
that is made of its own code.

WHAT WAS ALREADY THERE and what was not. A program has carried `name` and typed `params`
since the language was designed, `render` prints `PROCEDURE name(INT x)`, and `run` binds
parameters. So DEFINING one was never the gap. The gap was that nothing kept it, nothing
could call it, and the writer did not know it existed — `PROCEDURE` was a keyword with a
renderer and no home, which is exactly what task #75 records.

THREE THINGS, AND THE THIRD IS THE POINT:

    KEEP      a named program is written to ~/.gorgon/procedures as BOTH the readable
              .medusa text and the IR it was rendered from
    CALL      `CALL setup_temp_vm(template: ...)` — the same keyword a tool takes, because
              A PROCEDURE IS A TOOL YOU WROTE. Medusa is bash for Gorgon and this is a
              shell function; giving it a second keyword would say it was a different kind
              of thing, and it is not
    TILE      a procedure DECLARES WHAT IT ACHIEVES, so the ghost writer can cover a goal
              with it exactly as it covers one with `create_vm`

The third is what makes this reuse rather than replay. Without it, calling a procedure means
somebody naming it — which is a macro. With it, the writer reaches for the operator's snippet
because the snippet is the better move, and the system's own library becomes part of how it
plans. That is also the honest form of "it can call what it wrote": nobody had to tell it to.

WHAT A PROCEDURE MAY NOT DO IS SKIP THE GAUNTLET. Its body is statements like any other, run
by the same visitor through the same guarded executor. Storing a program does not bless it —
a stored `delete_vm` meets the same commit gate it met the day it was written.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# WHERE THEY LIVE. Under the storage home rather than in the repo: a procedure is something
# the OPERATOR accumulated, not something that ships, and a checkout should not carry one
# lab's library into another.
def _home() -> str:
    base = os.environ.get("GORGON_HOME") or os.path.expanduser("~/.gorgon")
    return os.path.join(base, "procedures")


_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[a-z][a-z0-9_]*)?$")

# A CLASS IS A FILE WITH SEVERAL ENTRY POINTS, and that is the only thing separating it from
# a procedure. The operator's example is the right size:
#
#     NetworkSetup.medusa
#       attach(vms, net_name)   ·  add(vm, net_name)  ·  remove(vm, net_name)
#
# EACH METHOD IS A PROCEDURE, so nothing downstream learns a new word: `names()` lists
# `NetworkSetup.attach`, `covering()` may reach for it, `validate` accepts the call, and
# `run` executes the body through the same visitor. A class that needed its own lookup,
# its own validator and its own call op would be three mechanisms for one idea.
#
# WHAT IS DELIBERATELY NOT BUILT: the three-layer prompt machinery — a separate
# intermediate vocabulary a model consults to CHOOSE a method. Its argument was that
# authoring is where everything fails and tool calling is where nothing does, which was
# true and is now beside the point: the writer is deterministic and covers 13/13 with no
# model, while the model-authoring path measures 7/78. The design note's own instruction
# was not to build the machinery until an experiment answered; the architecture answered
# it instead.
_METHODS = "methods"

# WHERE THE PROGRAM RIDES, after the text a person reads. A comment line, because a `.medusa`
# should still look like one to anything that opens it.
_IR_MARK = "\n-- medusa:ir "

# `procedure build_box: make a machine from a template` — the operator DECLARING that this
# request is to be kept rather than done, and what to call it.
#
# THE FIRST VERSION INFERRED IT and that is why this exists. A word blinder looked for
# {procedure, snippet, script, reusable, save, store, keep, reuse} and switched the prompt on
# a hit — which fires on "save a snapshot of web", "keep the vm running" and "store the iso
# on disk": 5 of 7 realistic requests. And what it bought never worked; asked outright to
# "create a reusable medusa procedure called vm_disk_builder", the model answered
# `procedure: null` twice out of two.
#
# So the whole authoring path hung on a sniffer with a measured false-positive rate feeding a
# schema field that had never once been filled. DECLARE, DON'T INFER — the same answer the
# intent ladder reached, spelled the same way, and it costs no prompt text, no schema surface
# and no model call.
# `procedure NAME[(SIGNATURE)]: the request`. The signature is captured RAW and handed to
# `parse.signature`, so the types live in the manifest and not in this regex — a pattern
# listing type words here would be the 34th vocabulary, in the one file arguing against them.
_PREFIX = re.compile(r"^\s*procedure\s+([A-Za-z][\w]*)\s*(\([^)]*\))?\s*:\s*(.*)$",
                     re.I | re.S)


def declared_in(request: str):
    """`(name, params, the rest)`, or `(None, {}, request)` when nothing was declared.

    A NAME THAT IS NOT LEGAL IS STILL A DECLARATION. It comes back so the caller can refuse
    it by name — silently treating `procedure My Thing:` as an ordinary request would run
    the very work the operator asked to have kept.

    THE SIGNATURE IS OPTIONAL AND IT IS DECLARED, NOT INFERRED:

        procedure test: a linux machine
        procedure test(STRING name, STRING os_type): a machine with those parameters

    WHY IT IS TYPED HERE RATHER THAN TRANSLATED. A parameter is a fact about the PROCEDURE,
    not about the world, and the extractor turns English into goals about the world — so
    "take a name and os type from the user" has nothing for it to translate and it does what
    it always does with open prose: it puts the words in a slot. Measured 2026-08-02, from
    the operator's own request: `create_vm(os_type: user input os type, name: $name)`.

    SO THE OPERATOR WRITES THE SIGNATURE AND THE MODEL NEVER SEES IT. That is
    [[gorgon-declare-dont-infer]] for the seventh time, and it is the same move that made
    `procedure NAME:` itself work — the word blinder it replaced fired on 5 of 7 ordinary
    requests to buy a schema field the model filled 0 of 2 times.

    IT IS THE SAME GRAMMAR THE FILE USES. `parse.signature` is the reader `.medusa` files go
    through, so what the operator types is what they will read back, and a type added to the
    manifest is available in both places at once.

    A MALFORMED SIGNATURE IS NOT SILENTLY AN ORDINARY REQUEST. `procedure t(STIRNG x): …`
    raises, because the alternative is running the work the operator asked to have KEPT —
    the same reason an illegal name comes back rather than being ignored.
    """
    m = _PREFIX.match(str(request or ""))
    if not m:
        return (None, {}, request)
    from .ir.parse import signature
    sig = (m.group(2) or "").strip()
    return (m.group(1), signature(sig) if sig else {}, m.group(3).strip())


# A SPAN, IN THE FORM THE MANIFEST ALREADY DECLARES. `param_types.duration` says it in as
# many words — *"a span — 30s, 15m, 1h, 7d. What a ROUTINE's schedule and a timeout are"* —
# so the type was named for this before anything could use it. Read from the manifest rather
# than restated, which is what stops a second spelling appearing the first time somebody
# wants weeks.
_SPAN = re.compile(r"^\s*(\d+)\s*([smhd])\s*$", re.I)
_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def seconds(span: Any) -> Optional[int]:
    """`"1h"` -> 3600. `None` when it is not a span at all.

    None RATHER THAN A GUESS. A schedule nobody can read must not become "every zero
    seconds" — that is a routine that runs on every sweep forever, which is the loudest
    possible reading of a typo.
    """
    m = _SPAN.match(str(span or ""))
    return int(m.group(1)) * _SECONDS[m.group(2).lower()] if m else None


def _consent():
    from .ir import consent
    return consent


def contract(program: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What a procedure ADVERTISES — read out of its body, never stored beside it.

    THE OPERATOR SETTLED THIS ON 2026-08-02, and the reason is worth keeping: I proposed a new
    keyword so a procedure could declare its contract in the header, and the answer was *"in
    this scenario we dont even need the achieve … because new should cover it in the internal
    achieve it has."* Which is right. A creation ALREADY SAYS WHAT IT MAKES — `NEW CALL
    create_vm(os_type: linux, name: $box)` states that afterwards a linux vm called `$box`
    exists — so a second declaration would be the same fact written twice, and the two would
    disagree the day someone edited one of them.

    THIS IS NOT THE INFERENCE `declare, don't infer` WARNS ABOUT. Nothing is being guessed
    from prose or from a name: the body is a declaration, and this reads it. The rule that
    matters is the one already built into `consent` — a `new` vouches for its own creation and
    for nothing else — applied from the other direction.

    TWO SOURCES, IN ORDER:
      * A TRAILING `ensure`/`achieve` WINS. A procedure that ends by checking something is
        saying that is the thing it is for, and the operator's placement rule says exactly
        where such a check goes: after the code whose result has to hold.
      * OTHERWISE, THE CREATIONS. A body that only makes things advertises what it made.

    A PROCEDURE THAT DOES NEITHER ADVERTISES NOTHING, and that is the honest outcome rather
    than a defect: it stays callable by name and simply cannot be REACHED FOR.
    """
    body = program.get("body") or []
    for st in reversed(body):
        if st.get("op") in ("ensure", "achieve") and st.get("predicate"):
            return st["predicate"]
    news = [st for st in body if st.get("op") == "new"]
    if not news:
        return None
    kinds = {st.get("kind") for st in news}
    if len(kinds) != 1:
        # SEVERAL KINDS MADE IS NOT ONE CONTRACT, and picking one of them would advertise
        # half of what the procedure does. Declining is what `covering` is built to handle.
        return None
    kind = news[0].get("kind")
    from .ir import config
    key = ((config.KINDS or {}).get(kind) or {}).get("key")
    select = {"kind": kind}
    if len(news) == 1 and key and key in (news[0].get("args") or {}):
        # THE KEY, AND DELIBERATELY NOT THE OTHER ATTRIBUTES. A creation sets more than an
        # identity — this vm is also linux — and advertising all of it looked more honest
        # until you follow it through `_unify`, which is TOTAL in both directions.
        #
        # A CONTRACT NARROWER THAN THE GOAL IS THE DANGEROUS DIRECTION and #78 measured what
        # it costs: a procedure covering PART of a goal becomes a tile the goal can never get
        # past, permanently shadowing the primitive that would have worked. A contract WIDER
        # than the goal does not block — it makes the goal true and more besides — but it only
        # IMPLIES the goal here because `name` is the key and a kind has one member per key.
        # For a non-key attribute the implication fails outright: "exactly one linux vm" says
        # nothing about how many vms there are.
        #
        # So the contract is the identity the creation establishes, which is exactly what the
        # hand-written `achieves` in the store has always said. A goal that asks for MORE than
        # the identity is passed over and planned from primitives — the honest consequence the
        # module already accepts, and the safe side of a rule whose unsafe side blocks.
        select[key] = news[0]["args"][key]
    total = sum(st.get("amount", 1) if isinstance(st.get("amount"), int) else 1
                for st in news)
    return {"shape": "count", "select": select, "eq": total}


def render_stored(program: Dict[str, Any]) -> str:
    """The readable artifact — one `PROCEDURE` block, or one per method of a class.

    A CLASS FILE IS STILL A `.medusa` A PERSON READS, which is the entire reason both forms
    are kept. Rendering the wrapper would print a header and no code.
    """
    from .ir.render import render as _render
    methods = program.get(_METHODS)
    if not methods:
        return _render(program)
    name = program.get("name")
    return "\n\n".join(_render({**spec, "name": f"{name}.{m}"})
                        for m, spec in methods.items())


def legal_name(name: str) -> bool:
    """A procedure name is an identifier — lowercase, underscores, no spaces.

    STRICTER THAN A MACHINE NAME ON PURPOSE. A machine is named by a person and may be
    called anything; a procedure name is written INTO PROGRAMS, so it has to survive being
    parsed, and a name with a space or a quote in it is a name that breaks the one artifact
    this module exists to keep readable.
    """
    return bool(name and _NAME.match(str(name)))


class Store:
    """The procedure library. A directory of `.medusa` files and their IR.

    ONE FILE PER PROCEDURE. The operator's instruction, and their question was the right one:
    *"why are there two files? shouldnt it be 1?"*

    IT WAS TWO, AND THE SECOND WAS A SYMPTOM. The `.medusa` was what a person reads and the
    `.json` was what ran — and NOTHING IN PRODUCTION EVER READ THE `.medusa`. So the file the
    operator was invited to read, edit and share was not the file that ran, and an edit to it
    did nothing at all. That is worse than duplication: it is an artifact that looks live.

    THE ROOT CAUSE IS THAT THERE IS NO PARSER — `render.py` goes IR -> text and nothing goes
    back. Until one exists the IR has to travel WITH the text rather than beside it, so it
    rides in a trailing block after the program a person reads.

    AND AN EDIT IS REPORTED RATHER THAN IGNORED. On read the IR is re-rendered and compared
    to the text above it; a mismatch means the operator changed the program and the runtime
    would otherwise have run the old one silently. `drifted()` names those. That converts the
    defect the two-file layout had into a visible one, which is the most that can be done
    honestly before the surface can be parsed.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or _home()
        # ONE READ PER FILE PER CHANGE, not one per goal. `covering()` is asked about EVERY
        # goal the writer covers and it sweeps the whole library each time, so without this
        # a five-procedure library costs five file reads per goal — on the writer's hot path,
        # for a feature most requests never touch.
        #
        # VALIDATED ON (mtime, size) RATHER THAN HELD FOREVER, because the operator is
        # expected to EDIT these files: they are the readable artifact, that is the entire
        # reason both forms are kept, and a cache that ignored an edit would run yesterday's
        # procedure while showing today's text. A stat is cheap; a stale answer is not.
        self._cache: Dict[str, Any] = {}
        # PROCEDURES THAT COULD NOT BE READ, by name. Reported rather than raised — see
        # `all()`.
        self.broken: List[str] = []
        # THE LAST SAVE'S POST-WRITE REPORT. Kept so a caller that wants to SHOW the
        # non-fatal findings can, without `save` having to return two things or refuse a
        # keep over a question about meaning. None until something has been saved.
        self.last_report: Optional[Dict[str, Any]] = None

    # ── keeping ──────────────────────────────────────────────────────────────
    def save(self, program: Dict[str, Any], rendered: str = "") -> str:
        """Write a named PROCEDURE — one program, one file. Returns the `.medusa` path.

        `achieves` RIDES ALONG IF IT IS THERE and is not invented here. A procedure that
        declares nothing is still callable by name; it simply cannot be REACHED FOR, which
        is the honest consequence of not saying what you do.

        A CLASS IS NOT KEPT THROUGH THIS DOOR — `save_class` is its own method, and that is
        the whole enforcement of *"the AI author does not make classes"* (operator, 2026-08-02).
        The authoring path calls `save`, so a class is something it CANNOT reach rather than
        something it happens not to emit. See `save_class` for why the rule is worth having.
        """
        if program.get(_METHODS):
            raise ValueError(
                f"{program.get('name')!r} is a CLASS, and a class is not authored — it is "
                f"written by a person, or kept deliberately through `save_class`. A class "
                f"promises 'verified once' to every caller of every method, and that promise "
                f"is the operator's to make")
        # A DOTTED NAME NAMES A METHOD, and it was only refused for a program that carried
        # methods — so `save({"name": "NetworkSetup.add"})` wrote a SECOND file whose stem had
        # a dot in it, sitting beside the class and shadowing nothing legibly.
        if "." in str(program.get("name") or ""):
            raise ValueError(f"{program.get('name')!r} names a method; save the CLASS it "
                             f"belongs to")
        # AND IT MAY NOT OVERWRITE ONE EITHER, which is the same rule from the other side:
        # `save` replaces the file at that name, so authoring `procedure NetworkSetup: …`
        # would have turned a class of four verified methods into a one-body procedure and
        # taken every caller of `NetworkSetup.add` with it. Refusing to MAKE a class while
        # allowing it to be flattened would be a rule with a door in the back of it.
        try:
            standing = self.get(program.get("name"))
        except Exception:
            # A FILE THAT CANNOT BE READ IS NOT A CLASS THIS GUARD CAN VOUCH FOR. `verify`
            # and `broken` are where an unreadable entry is reported; refusing the save here
            # would make a corrupt file permanently unreplaceable.
            standing = None
        if standing and standing.get(_METHODS):
            raise ValueError(
                f"{program.get('name')!r} is already a CLASS with "
                f"{len(standing[_METHODS])} method(s) — saving a procedure over it would "
                f"delete them. Choose another name, or remove the class deliberately")
        return self._keep(program, rendered)

    def save_class(self, program: Dict[str, Any], rendered: str = "") -> str:
        """Write a CLASS — one file, several entry points. Returns the `.medusa` path.

        SEPARATE FROM `save` BY THE OPERATOR'S INSTRUCTION, 2026-08-02: *"make it so that the
        medusa ai author cannot make classes."* The authoring path calls `save`; only a caller
        that says the word `class` gets to keep one. [[gorgon-declare-dont-infer]] — the door
        you walk through is the declaration, so the rule cannot be satisfied by accident and
        cannot be lost by a writer that one day learns to emit a `methods` dict.

        AND IT IS NOT ARBITRARY CAUTION. A class's contract is stronger than a procedure's: it
        offers a method SURFACE that other programs reach for, and every method carries its own
        verdict so a caller need not re-check. That is a promise about work done ONCE, made to
        callers who are not in the room — the kind of thing the operator writes, reads back and
        keeps, not the kind a translation of one English sentence should mint.
        """
        if not program.get(_METHODS):
            raise ValueError(f"{program.get('name')!r} has no methods, so it is a procedure "
                             f"and not a class — keep it with `save`")
        return self._keep(program, rendered)

    def _keep(self, program: Dict[str, Any], rendered: str = "") -> str:
        """The write itself, shared by both doors. Which door was used is decided above."""
        from .ir.validate import validate

        name = program.get("name")
        if not legal_name(name):
            raise ValueError(
                f"{name!r} is not a legal procedure name — a procedure is written into "
                f"programs, so its name must be an identifier: lowercase, digits, underscores")
        # KEEPING IT IS ALSO ACCEPTING IT. "Storing a program does not bless it" is about
        # PERMISSION — a saved `delete_vm` still meets the commit gate — and it was silently
        # doing duty for a second claim it does not make: that the thing being saved is a
        # program at all.
        #
        # NOTHING VALIDATED A PROCEDURE BODY, and the reference rules are the ones that bite:
        # a `$name` bound by nothing resolves to itself at run time, so a body referring to a
        # variable the CALLER had would create a machine literally called `$outer` and report
        # success. Measured, in the scope-isolation test — the isolation was correct and the
        # consequence was garbage in the lab.
        #
        # `params` IS THE SCOPE, and `validate` already reads it off the program: a procedure
        # may refer to what it declares and to what it binds, and to nothing else. That is
        # the same rule the caller's program lives under, applied at the moment the artifact
        # becomes reusable.
        methods = program.get(_METHODS)
        if methods:
            # A CLASS IS VALIDATED METHOD BY METHOD, because a class HAS no body — it is a
            # file where several programs live, and validating the wrapper would be
            # validating a container.
            if "." in str(name):
                raise ValueError(f"{name!r} names a method; save the CLASS it belongs to")
            for m, spec in methods.items():
                if not legal_name(m):
                    raise ValueError(f"{name}.{m}: a method name must be an identifier")
                ok, problems = validate({**spec, "name": f"{name}.{m}"})
                if not ok:
                    raise ValueError(f"{name}.{m} could not run, so the class is not kept: "
                                     f"{problems[0]}")
                # AND EVERY METHOD CARRIES ITS OWN VERDICT. This is the line between a class
                # and a bag of macros: a method that expands into tool calls and asserts
                # nothing inherits the false-success class the whole system refuses, and a
                # caller cannot trust its result without re-checking — which is exactly the
                # work a class exists to have done ONCE.
                if not _consent().survey(spec)["grounded"]:
                    raise ValueError(
                        f"{name}.{m} acts and vouches for nothing. A class method ends in an "
                        f"ENSURE or ACHIEVE over its own postcondition — that is what makes "
                        f"'verified once' a fact its callers can rely on")
        else:
            ok, problems = validate(program)
            if not ok:
                raise ValueError(
                    f"{name} is not a program that could run, so it is not kept: "
                    f"{problems[0]}")
        os.makedirs(self.path, exist_ok=True)
        if not rendered:
            rendered = render_stored(program)
        text_at = os.path.join(self.path, f"{name}.medusa")

        # WRITTEN BESIDE, VERIFIED, THEN MOVED INTO PLACE — and the order is the whole point.
        #
        # EVERYTHING ABOVE CHECKS THE IR THE CALLER HANDED IN. Nothing checked the FILE, and
        # the file is what every later reader loads: `_read` parses the text back, so a
        # renderer that emits something the parser cannot take, or takes differently, produces
        # an artifact that passed validation and is not the program that passed it. That gap
        # is invisible by construction — the only way to see it is to read the file back.
        #
        # AND A FAILED RE-SAVE MUST NOT DESTROY A WORKING PROCEDURE. Writing in place and
        # checking afterwards would leave the operator with neither the old program nor a
        # usable new one, on the one path where they are least able to recover it. The
        # temporary file is removed on failure and the previous version is never touched.
        tmp_at = text_at + ".writing"
        with open(tmp_at, "w") as fh:
            # THE TEXT, AND NOTHING UNDER IT. The operator, 2026-08-02: *"i dont want it there
            # because it makes the snippet have 2 SSOTs."* The `-- medusa:ir` trailer is gone,
            # and with it the arrangement where the file a person reads was decorative and the
            # JSON stapled beneath it was what ran.
            fh.write(rendered.rstrip() + "\n")
        try:
            report = self.verify_file(tmp_at, expected=program)
        except Exception:
            os.remove(tmp_at)
            raise
        if not report["ok"]:
            os.remove(tmp_at)
            bad = "; ".join(f"{c['check']}: {c['why']}" for c in report["checks"]
                            if not c["ok"] and c["fatal"])
            raise ValueError(
                f"{name} was written and did not read back as the program that was "
                f"written, so it is not kept: {bad}")
        os.replace(tmp_at, text_at)
        # THE READ CACHE IS KEYED ON (mtime, size) AND `os.replace` CHANGES BOTH, so the
        # next `get` re-reads. Dropped anyway rather than relied on: a same-second rewrite
        # of identical length is exactly the case a stat-based key cannot see.
        self._cache.pop(text_at, None)
        # THE OLD SIDECAR, REMOVED. A stale `.json` beside a one-file procedure would be read
        # by nothing and believed by anyone.
        stale = os.path.join(self.path, f"{name}.json")
        if os.path.exists(stale):
            os.remove(stale)
        # THE REFERENCE TRAVELS WITH THE LIBRARY. Written here rather than at install time
        # because this is the moment the folder is known to exist and to be worth opening —
        # and because it is generated, so a copy written once would be a copy going stale.
        try:
            self.write_reference()
        except Exception:
            # A SYNTAX GUIDE IS NOT WORTH LOSING A PROGRAM OVER. The save has already
            # succeeded at this point; failing here would throw away work over a doc.
            pass
        # THE REPORT'S NON-FATAL FINDINGS SURVIVE THE SAVE, on the store, for the caller that
        # wants to show them. They are about MEANING — does it still claim what it was asked
        # to claim, does it vouch for what it does — and a save must not be refused for
        # those: the crawler's contract genuinely does not survive the round trip today, and
        # blocking on that would stop authoring rather than report it.
        self.last_report = report
        return text_at

    # ── reading ──────────────────────────────────────────────────────────────
    def _read(self, at: str) -> Dict[str, Any]:
        """The IR, PARSED OUT OF THE TEXT. One file, one source of truth.

        NO FALLBACK TO A TRAILER, DELIBERATELY. Files written before 2026-08-02 still carry
        `-- medusa:ir …`, and the parser reads it as what it now is — a comment — so they load
        from their text like everything else. Reading the trailer when parsing failed would be
        a kinder migration and would put the second source of truth straight back: the file
        would run something other than what it says, exactly when the two disagree, which is
        the one moment it matters.
        """
        from .ir.parse import parse_many
        with open(at) as fh:
            body = fh.read()
        got = parse_many(body)
        if not got:
            raise ValueError(f"{at} holds no program")
        text = body.partition(_IR_MARK)[0].rstrip()
        if len(got) == 1:
            one = got[0]
            one["_text"] = text
            # THE CONTRACT IS COMPUTED, NOT STORED. It used to ride in the IR trailer; now it
            # is read out of the body every time, which is the only way it cannot disagree
            # with the code it describes.
            found = contract(one)
            if found:
                one["achieves"] = found
            return one
        # SEVERAL BLOCKS IN ONE FILE IS A CLASS, reassembled the way `render_stored` took it
        # apart: each block is named `Class.method`, so the class name and the method surface
        # both come back out of the names themselves rather than from anything stored beside.
        methods = {}
        owner = None
        for prog in got:
            whole, _, method = str(prog.pop("name", "")).partition(".")
            owner = owner or whole
            found = contract(prog)
            if found:
                prog["achieves"] = found
            methods[method or whole] = prog
        return {"name": owner, _METHODS: methods, "_text": text}

    # ── the reference that sits beside them ──────────────────────────────────
    def write_reference(self) -> str:
        """Write the syntax + examples guide into the procedures folder. Returns its path.

        BESIDE THE PROGRAMS, BECAUSE THAT IS WHERE THE PERSON IS. The `.medusa` files are
        meant to be opened and edited — that is the whole reason the text IS the program —
        and a grammar the operator has to go and look up somewhere else is a grammar they
        will guess at instead.

        `SYNTAX.md`, NOT `.medusa`, AND THAT IS LOAD-BEARING: `names()` lists every
        `*.medusa` in this directory, so a reference file with the language's own extension
        would arrive in the library as a program, be handed to the parser, and be reported
        as broken.

        GENERATED, AND REWRITTEN ON EVERY SAVE. It is derived from the language definition,
        so the alternative to overwriting it is letting it drift — and a stale syntax guide
        is worse than none, because it is believed.
        """
        from .ir.reference import render_reference
        os.makedirs(self.path, exist_ok=True)
        at = os.path.join(self.path, "SYNTAX.md")
        with open(at, "w") as fh:
            fh.write(render_reference())
        return at

    # ── reading it back, and asking whether it is what was written ───────────
    def verify_file(self, at: str, expected: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Re-READ a `.medusa` and report whether it is the program it claims to be.

        THE CHECKS ABOVE `save` ALL RAN AGAINST THE IR IN MEMORY. This one runs against the
        FILE, which is the only thing any later reader sees: `_read` parses the text back, so
        between "the IR validated" and "the artifact works" sits a renderer and a parser that
        nothing had ever been asked to agree.

        FIVE CHECKS, AND THEY SPLIT INTO TWO KINDS. The FATAL ones are about the WRITE — the
        file cannot be loaded, or loads as a different program. Those mean the save did not
        happen, whatever the disk says, and `save` rolls back on them. The REPORTED ones are
        about MEANING — does it still claim what it was asked to claim, does it vouch for
        what it does — and those must not block a save: the crawler's contract genuinely does
        not survive the round trip today, and refusing to keep it would stop authoring rather
        than tell anyone why.

            reads back              the parser takes it at all
            round trips             parse then render reproduces the file, so the text a
                                    person edits and the program that runs are one thing
            is the program saved    the text is the rendering of what the caller handed in,
                                    not of something else it also had
            validates               the RE-READ program could run — every tool real, every
                                    `$name` bound, every FROM source named
            keeps its contract      `achieves` survived the round trip. It does not always:
                                    the contract is RECOMPUTED from the body on read, which
                                    loses a goal that is more than its own last check
            vouches for what it does  it acts and something could fail. A body that changes
                                    the world and asserts nothing is the false-success class
                                    this system spends its time on

        `expected` is the IR that was saved. Without it — verifying a file the operator
        edited by hand — the two checks that need an original are skipped and SAID to be
        skipped, because a check that silently did not run reads exactly like one that passed.
        """
        checks: List[Dict[str, Any]] = []

        def note(check: str, ok: Optional[bool], why: str = "", fatal: bool = False) -> None:
            checks.append({"check": check, "ok": ok, "why": why, "fatal": fatal})

        try:
            got = self._read(at)
        except Exception as exc:
            note("reads back", False, f"{type(exc).__name__}: {exc}", fatal=True)
            return {"at": at, "name": None, "ok": False, "clean": False, "checks": checks}
        note("reads back", True)

        name = got.get("name")
        text = (got.get("_text") or "").strip()

        # ROUND TRIP. `parse(render(ir)) == ir` was named as the acceptance test for the
        # parser and only ever run over a corpus; this is the same equality, on every file
        # that is written, in the direction a reader actually travels.
        try:
            again = render_stored(got).strip()
        except Exception as exc:
            again = None
            note("round trips", False, f"re-rendering failed: {type(exc).__name__}: {exc}",
                 fatal=True)
        if again is not None:
            note("round trips", again == text,
                 "" if again == text else "the file does not render back to itself",
                 fatal=True)

        if expected is None:
            note("is the program saved", None, "skipped — nothing to compare against")
        else:
            try:
                wanted = render_stored(expected).strip()
            except Exception as exc:
                wanted = None
                note("is the program saved", False,
                     f"the saved program could not be rendered: {exc}", fatal=True)
            if wanted is not None:
                note("is the program saved", wanted == text,
                     "" if wanted == text else "the text on disk is not this program",
                     fatal=True)

        # EVERY BODY, AND A CLASS HAS SEVERAL. A class file is where several programs live,
        # so "does it validate" is asked once per method — the same split `save` already
        # makes, applied to what came back rather than to what went in.
        bodies = ([(f"{name}.{m}", spec) for m, spec in (got.get(_METHODS) or {}).items()]
                  or [(name, got)])

        from .ir.validate import validate
        bad = []
        for who, prog in bodies:
            ok, problems = validate({**prog, "name": who})
            if not ok:
                bad.append(f"{who}: {problems[0]}")
        note("validates", not bad, "; ".join(bad), fatal=True)

        # KEEPS ITS CONTRACT. Compared only where the saved program declared one — a
        # procedure that claims nothing has nothing to lose, and demanding a contract here
        # would be a different rule wearing this one's clothes.
        if expected is None:
            note("keeps its contract", None, "skipped — nothing to compare against")
        else:
            wanted_c = expected.get("achieves")
            if wanted_c is None:
                note("keeps its contract", None, "skipped — it declared none")
            else:
                same = got.get("achieves") == wanted_c
                note("keeps its contract", same,
                     "" if same else
                     f"declared {json.dumps(wanted_c, sort_keys=True)}, reads back as "
                     f"{json.dumps(got.get('achieves'), sort_keys=True)}")

        ungrounded = [who for who, prog in bodies
                      if not _consent().survey(prog)["grounded"]]
        note("vouches for what it does", not ungrounded,
             "" if not ungrounded else
             f"{', '.join(ungrounded)} act(s) and nothing could fail")

        return {"at": at, "name": name, "ok": not any(c["fatal"] and c["ok"] is False
                                                      for c in checks),
                "clean": not any(c["ok"] is False for c in checks),
                "checks": checks}

    def verify(self, name: str) -> Dict[str, Any]:
        """Verify a stored procedure BY NAME, as it sits on disk.

        THE ONE THAT CATCHES A HAND EDIT. The `.medusa` is the artifact the operator is
        invited to open and change, and an edit takes effect the moment it is saved — so the
        library can hold a file that no longer parses, or that quietly stopped asserting
        anything, and nothing would say so until a plan reached for it.
        """
        whole = str(name).partition(".")[0]
        at = os.path.join(self.path, f"{whole}.medusa")
        if not os.path.exists(at):
            return {"at": at, "name": name, "ok": False, "clean": False,
                    "checks": [{"check": "exists", "ok": False, "fatal": True,
                                "why": f"no procedure called {whole!r}"}]}
        report = self.verify_file(at)
        # THE NAME THE CALLER ASKED ABOUT, when the file could not be read. `verify_file`
        # takes the name out of the program, so a file that does not parse has none — and a
        # report headed `None` is unreadable exactly when somebody most needs to read it.
        report["name"] = report.get("name") or whole
        return report

    def verify_all(self) -> List[Dict[str, Any]]:
        """Every stored procedure, verified. A CLASS IS VERIFIED ONCE, as the file it is."""
        if not os.path.isdir(self.path):
            return []
        stems = sorted(f[:-7] for f in os.listdir(self.path) if f.endswith(".medusa"))
        return [self.verify(s) for s in stems]

    def drifted(self, name: str) -> bool:
        """Always False now, and the reason is the point: THERE IS NOTHING LEFT TO DRIFT FROM.

        This asked whether the readable half had been edited away from the program that ran —
        a real question while a file held both. Now the text IS the program: an edit to it
        changes what runs, which is what the operator was asking for. Kept as a named False
        rather than deleted so that a caller asking the question gets the answer *"that cannot
        happen any more"* instead of an AttributeError that reads like a missing feature.
        """
        return False

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """A stored program by name. `Class.method` reaches into a class file.

        A METHOD COMES BACK AS AN ORDINARY PROGRAM, named `Class.method`, so every consumer
        — the validator, the writer's tile search, the visitor — keeps asking the one
        question it already asked. A class is a FILE with several entry points, not a new
        kind of thing to look up.
        """
        whole, _, method = str(name).partition(".")
        if method:
            got = self.get(whole)
            spec = ((got or {}).get(_METHODS) or {}).get(method)
            return {**spec, "name": str(name)} if spec else None
        at = os.path.join(self.path, f"{str(name)}.medusa")
        try:
            stamp = os.stat(at)
        except OSError:
            return None
        key = (stamp.st_mtime_ns, stamp.st_size)
        hit = self._cache.get(at)
        if hit is not None and hit[0] == key:
            return hit[1]
        try:
            got = self._read(at)
        except Exception:
            # A CORRUPT ENTRY IS NOT AN EMPTY LIBRARY. Returning None here would make a
            # damaged file indistinguishable from a procedure nobody wrote — the same
            # unknown-versus-empty confusion the lab registry was bitten by.
            #
            # THAT REASONING HOLDS FOR A PROCEDURE ASKED FOR BY NAME and not for a sweep;
            # see `all()`, which is where it was costing the writer every goal.
            self._cache.pop(at, None)
            raise
        self._cache[at] = (key, got)
        return got

    def text(self, name: str) -> Optional[str]:
        """The readable half — what a person opens the file to see."""
        try:
            got = self.get(name)
        except Exception:
            return None
        return (got or {}).get("_text")

    def names(self) -> List[str]:
        """Every CALLABLE name — a procedure's own, and one per method of a class.

        A CLASS FILE'S OWN NAME IS NOT CALLABLE. `NetworkSetup` is not a program; it is
        where four of them live, and offering it as a tool would let a caller invoke a body
        that does not exist.
        """
        if not os.path.isdir(self.path):
            return []
        out, bad = [], []
        for f in os.listdir(self.path):
            if not f.endswith(".medusa"):
                continue
            stem = f[:-7]
            try:
                got = self.get(stem)
            except Exception:
                # A DAMAGED FILE IS SKIPPED AND NAMED, here rather than in `all()`, because
                # this is now the walk that opens them — a class has to be read before its
                # methods can be listed. Losing the name would make a corrupt library
                # indistinguishable from a small one.
                bad.append(stem)
                continue
            methods = (got or {}).get(_METHODS)
            out += [f"{stem}.{m}" for m in methods] if methods else [stem]
        self.broken = bad
        return sorted(out)

    def all(self) -> List[Dict[str, Any]]:
        """Every readable procedure. A damaged one is SKIPPED AND NAMED, never raised.

        `get` raises on a corrupt file and this propagated it, so ONE bad file in the
        directory crashed the ghost writer for EVERY goal — the library's failure mode was
        to take down planning entirely, including for the requests that need no procedure
        at all. A sweep looking for a match must survive an entry it cannot read.

        NAMED, THOUGH, in `broken`. Skipping quietly would make a damaged library
        indistinguishable from a small one, which is the confusion `get` refuses for a
        procedure asked for by name — and rightly, because there the caller said which one
        they meant.
        """
        out = []
        for n in self.names():          # `names()` records what it could not read
            try:
                got = self.get(n)
            except Exception:
                self.broken = sorted(set(self.broken) | {n})
                continue
            if got:
                out.append({**got, "name": n})
        return out

    # ── when it runs, if anything but a caller decides ───────────────────────
    def state(self, name: str) -> Dict[str, Any]:
        """What this procedure's SCHEDULE has seen. `{last_run, last_seen}` or empty.

        A SEPARATE FILE, and deliberately not a field on the program. The `.medusa` is the
        artifact the operator reads, edits and shares; when it last ran is not part of what
        it says, and writing run state into it would rewrite the operator's file behind them
        every sweep — and invalidate the read cache each time, which is the other half of the
        cost.

        `.state` RATHER THAN `.state.json`, because `names()` lists `*.json` and a run record
        would have arrived in the library as a procedure called `<name>.state`.
        """
        at = os.path.join(self.path, f"{str(name)}.state")
        try:
            with open(at) as fh:
                return json.load(fh) or {}
        except Exception:
            return {}

    def remember(self, name: str, **facts: Any) -> None:
        os.makedirs(self.path, exist_ok=True)
        got = {**self.state(name), **facts}
        with open(os.path.join(self.path, f"{str(name)}.state"), "w") as fh:
            json.dump(got, fh, indent=1)

    def due(self, now: float, holds=None) -> List[Dict[str, Any]]:
        """Which stored programs the CLOCK or the WORLD says to run, and why.

        TWO WAYS A PROGRAM RUNS WITHOUT ANYBODY CALLING IT, and they are one object with one
        extra field rather than two new kinds — a procedure is a tool you wrote, a ROUTINE is
        one the clock calls, a TRIGGER is one the world calls:

            every: "1h"          due when that long has passed since it last ran
            when:  <predicate>   due when the world MAKES it true, once per becoming

        `when` FIRES ON THE RISING EDGE, and that is the whole of why `last_seen` exists. A
        level-triggered rule fires on every sweep for as long as the condition holds, so
        "when a machine stops answering, snapshot it" would snapshot forever — the operator
        would learn to ignore it, which is the failure `consent.py` argues about one layer up.
        Becoming true is an event; being true is a state.

        `now` IS SUPPLIED, never read here. A module that read the clock could not be tested
        without waiting, and the sweep's caller is the thing that knows what time it is.

        A PREDICATE NOBODY CAN EVALUATE IS NOT A FIRING. `holds` absent, or raising, leaves
        `last_seen` untouched — unknown is not false, so the edge is still ahead of us rather
        than behind.
        """
        out: List[Dict[str, Any]] = []
        for proc in self.all():
            name = proc.get("name")
            if not name:
                continue
            seen = self.state(name)
            every = proc.get("every")
            if every:
                gap = seconds(every)
                last = seen.get("last_run")
                if gap is not None and (last is None or now - last >= gap):
                    out.append({"name": name, "why": (
                        f"every {every}, and it has never run" if last is None
                        else f"every {every}, last ran {int(now - last)}s ago"),
                        "procedure": proc})
                    continue
            when = proc.get("when")
            if when is not None and holds is not None:
                try:
                    now_true, why = holds(when, {})
                except Exception:
                    continue                       # unknown is not false — no edge either way
                was = seen.get("last_seen")
                self.remember(name, last_seen=bool(now_true))
                if now_true and not was:
                    out.append({"name": name, "why": f"became true: {why}",
                                "procedure": proc})
        return out

    def forget(self, name: str) -> bool:
        gone = False
        for ext in (".medusa", ".json", ".state"):
            at = os.path.join(self.path, f"{str(name)}{ext}")
            if os.path.exists(at):
                os.remove(at)
                gone = True
        return gone

    # ── reaching for one ─────────────────────────────────────────────────────
    def covering(self, goal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A stored procedure whose `achieves` matches this goal, or None.

        THIS IS THE WHOLE DIFFERENCE BETWEEN A LIBRARY AND A MACRO. A macro is expanded
        because somebody named it. A procedure found here is chosen because the writer was
        looking for something that makes the goal true and this makes the goal true — so the
        operator's own snippet enters the plan without the operator being in the room.

        MATCHED ON SHAPE AND SELECTOR, not on prose. `achieves` is a predicate in exactly the
        form a goal takes, so "does this cover that" is a comparison between two structures
        rather than a judgement about two sentences — which is the difference between this
        being deterministic and it being another place a model can be wrong.

        A PARAMETER MATCHES ANYTHING. `{"kind": "vm", "template": "$template"}` covers a goal
        naming any template, and the binding is returned so the caller can pass it. Without
        that a procedure would only ever match the exact world it was written against, which
        is a snippet that can be reused precisely once.

        AN EMPTY LIBRARY COSTS ONE STAT, which matters because this sits on the writer's hot
        path and most requests will never involve a procedure at all.
        """
        if not os.path.isdir(self.path):
            return None
        for proc in self.all():
            bound = _unify(proc.get("achieves"), goal, proc.get("params") or {})
            if bound is not None:
                return {"name": proc["name"], "params": bound, "procedure": proc}
        return None


def _unify(claim: Any, goal: Any, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Does `claim` describe `goal`? Returns the parameter bindings, or None.

    Structural and TOTAL IN BOTH DIRECTIONS: the two must state the same keys, with equal
    values, except that a `$param` in the claim binds whatever the goal has there.

    IT USED TO ALLOW THE GOAL TO CARRY MORE, on the reasoning that "a procedure guaranteeing
    a vm exists covers a goal that also wants a label, because the writer will cover the
    rest". The writer does not. `_achieve` places ONE tile per goal and returns, so a
    procedure that matched a goal it only half-closed became a tile the goal could never get
    past: the machine was created, the label was never applied, and the next round matched
    the SAME procedure again and appended nothing because it was already in the plan. The
    goal was then unreachable by any primitive — a stored procedure permanently shadowed the
    thing that would have worked.

    MEASURED, on the two-goal case in `test_procedures`: "a machine called web" plus "web
    carries the label prod" raised `lowering did not achieve it` with `add_label` nowhere in
    the plan.

    SO THE RULE IS THE ONE `effects.invert` ALREADY KEEPS: a tile is chosen because it makes
    the goal TRUE, not because it helps. A procedure that covers part of a goal is not a tile
    for that goal, and the honest consequence — it is passed over and the primitives are
    planned — is strictly better than one that half-covers and blocks.
    """
    if not isinstance(claim, dict) or not isinstance(goal, dict):
        # A `$param` on its own binds; anything else must be equal.
        if isinstance(claim, str) and claim.startswith("$"):
            return {claim[1:]: goal}
        return {} if claim == goal else None
    if set(claim) != set(goal):
        return None
    out: Dict[str, Any] = {}
    for key, want in claim.items():
        got = _unify(want, goal[key], params)
        if got is None:
            return None
        out.update(got)
    return out


# ONE STORE, so the writer, the runtime and the CLI are looking at the same library. A second
# instance pointed at the same directory would work; a second POINTED SOMEWHERE ELSE is how a
# procedure comes to exist for the thing that wrote it and not for the thing that runs it.
LIBRARY = Store()
