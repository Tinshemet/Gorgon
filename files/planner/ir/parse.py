"""parse.py — text back to IR, so the file a person reads IS the file that runs.

THE OPERATOR'S REASON, 2026-08-02: *"i dont want it there because it makes the snippet have 2
SSOTs."* A stored procedure carried its own IR in a `-- medusa:ir` trailer, and that is worse
than duplication: every consumer read the JSON, so the text was DECORATIVE. The file the
operator was invited to read, edit and share was not the file that ran, and an edit to it did
nothing at all. One of the two sources of truth was a lie, and this module is what removes it.

IT IS THE INVERSE OF `render.py` AND NOTHING ELSE. Not a second surface, not a friendlier
dialect — the same seven ops, read back. Every keyword comes from `config.SURFACE` and every
predicate from `config.PREDICATES`, the same tables the renderer prints from, so a word
renamed there is renamed on both sides at once. **That is the whole defence against this
becoming a second vocabulary**, which is the failure [[gorgon-procedure-language]] was written
to end (33 regex vocabularies, all drifting separately).

NO REGEX IN THE GRAMMAR. The previous `parse.py` was DELETED for a regex backtracking hang and
never rebuilt, which is why the IR trailer existed in the first place. This one scans
characters into tokens and then descends, so there is no backtracking to hang on: every
decision is made from the next token, and the grammar is small and closed enough for that to
be sufficient.

WHAT ROUND-TRIPS EXACTLY is asserted in `tests/test_parse.py` against the programs the ladder
actually produces, because a parser that is correct on invented examples and wrong on real
ones is worse than none. Two places are LOSSY BY CONSTRUCTION and are documented rather than
hidden:

  * `render` prints a `new`'s CONSTRUCTOR, not its kind — `NEW CALL create_vm(...)`, because
    the operator's object model says a creation is a constructor call. The kind is recovered
    from the manifest by `effects._kind_of`, which is exact for every tool a kind declares
    and returns None for a tool no kind claims.
  * ARGUMENT TYPES. `_args` prints `k: v` with no quotes, so `3` and `"3"` render identically.
    Values are coerced back on the rule that what looks like a number is one — the same rule
    `extract._coerce` uses, so at least the two seams agree. A member literally named `3`
    round-trips to the integer, and that is a real limit, not an oversight.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import config


class ParseError(ValueError):
    """A text that is not a program, with WHERE it stopped being one.

    THE POSITION IS THE POINT. A parser that says "invalid" about a file a human wrote is
    telling them to re-read the whole thing; one that says "line 3: expected ')'" is telling
    them where the mistake is. This surface exists to be hand-written, so the failure has to
    be as usable as the success.
    """

    def __init__(self, message: str, line: int = 0, text: str = ""):
        self.line = line
        where = f"line {line}: " if line else ""
        super().__init__(f"{where}{message}" + (f"\n  {text}" if text else ""))


# ── tokens ─────────────────────────────────────────────────────────────────────────────
WORD, NUM, STR, PUNCT, END = "word", "num", "str", "punct", "end"

# "NOT BOUND" IS NOT THE SAME AS "BOUND TO NOTHING", and a loop that restores the binding it
# found has to tell them apart — `None` is a legal thing to have been bound to.
_ABSENT = object()

# THE ONLY MULTI-CHARACTER OPERATORS, longest first so `>=` is never read as `>` then `=`.
_LONG = (">=", "<=", "==", "!=")
_SINGLE = set("(){}[],;:=@.<>-+*/")


class _Tok:
    __slots__ = ("kind", "value", "line", "pos", "end")

    def __init__(self, kind: str, value: Any, line: int, pos: int = 0, end: int = 0):
        self.kind, self.value, self.line = kind, value, line
        # WHERE THIS TOKEN CAME FROM IN THE SOURCE. Carried so that a free-text run can be
        # read back as the ORIGINAL CHARACTERS rather than re-joined from tokens — see
        # `_args`, where guessing the spaces mangled every URL it saw.
        self.pos, self.end = pos, end

    def __repr__(self) -> str:
        return f"<{self.kind} {self.value!r} @{self.line}>"


def _tokens(text: str) -> List[_Tok]:
    """Characters to tokens, in one forward pass.

    ONE PASS, NO BACKTRACKING, which is the entire reason this is hand-written rather than a
    regex table. A comment runs to end of line; a quoted string runs to its closing quote; a
    word runs while the characters are word characters. Nothing here can re-scan what it has
    already consumed, so nothing here can hang.
    """
    out: List[_Tok] = []
    i, line, n = 0, 1, len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        # A COMMENT IS `--` TO END OF LINE, which is also how the IR trailer was written — so
        # a file still carrying one parses fine and simply ignores it. That matters for the
        # migration: every procedure already on disk has the trailer, and none of them should
        # have to be deleted to be readable.
        if c == "-" and i + 1 < n and text[i + 1] == "-":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c in "'\"":
            start = i
            quote, i, buf = c, i + 1, []
            while i < n and text[i] != quote:
                # A BACKSLASH ESCAPES THE NEXT CHARACTER, so a name containing a quote is
                # sayable. The renderer never emits one today; a hand-written file may.
                if text[i] == "\\" and i + 1 < n:
                    i += 1
                buf.append(text[i])
                i += 1
            if i >= n:
                raise ParseError("unterminated string", line)
            out.append(_Tok(STR, "".join(buf), line, start, i + 1))
            i += 1
            continue
        two = text[i:i + 2]
        if two in _LONG:
            out.append(_Tok(PUNCT, two, line, i, i + 2))
            i += 2
            continue
        if c in _SINGLE:
            out.append(_Tok(PUNCT, c, line, i, i + 1))
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < n and (text[j].isdigit() or text[j] == "."):
                j += 1
            raw = text[i:j]
            out.append(_Tok(NUM, float(raw) if "." in raw else int(raw), line, i, j))
            i = j
            continue
        # A WORD, AND `$` STARTS ONE. `$item` is a single token rather than a sigil plus a
        # name, because it is a single thing to a reader and splitting it makes every use site
        # re-join it.
        j = i
        if c == config.SIGIL:
            j += 1
        while j < n and (text[j].isalnum() or text[j] in "_" + config.SIGIL):
            j += 1
        if j == i:
            # ANY OTHER CHARACTER IS PUNCTUATION, NOT AN ERROR. The tokeniser is TOTAL on
            # purpose: argument values are unquoted free text — `CALL camoufox_search(query:
            # how fast is lighting?)` — so a `?`, an accent or an emoji can appear in the
            # middle of a perfectly legal program. Rejecting characters here rejected the
            # operator's own search request, and it rejected it in the SCANNER, where the
            # message could not say which argument was at fault.
            #
            # Nothing is lost by being permissive: the grammar below only ever asks for
            # specific punctuation, so an unexpected one still fails — one layer up, where
            # there is enough context to say what was expected instead.
            out.append(_Tok(PUNCT, c, line, i, i + 1))
            i += 1
            continue
        out.append(_Tok(WORD, text[i:j], line, i, j))
        i = j
    out.append(_Tok(END, None, line, n, n))
    return out


# ── the vocabulary, read from the SAME tables the renderer prints from ──────────────────
def _word(key: str) -> str:
    return config.SURFACE.get(key, key.upper())


def _keywords() -> Dict[str, str]:
    """`{PRINTED WORD: ir key}` — built from the surface table, never written out here.

    IF THIS WERE A LITERAL DICT IT WOULD BE THE SECOND VOCABULARY. Deriving it means a word
    changed in `SURFACE` cannot be changed in only one direction, which is the specific way
    the old regex vocabularies rotted.
    """
    out = {}
    for key, val in (config.SURFACE or {}).items():
        if isinstance(val, str) and not key.startswith("_"):
            out[val.upper()] = key
    return out


def _coerce(v: str) -> Any:
    """`'3'` -> 3, `'true'` -> True, everything else itself.

    THE SAME RULE `extract._coerce` USES, deliberately. Two seams disagreeing about what `3`
    means is the kind of thing that reads as a model failure for a week.
    """
    s = str(v).strip()
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("none", "null"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


class _Cursor:
    """The token stream, with the three operations a recursive descent needs."""

    def __init__(self, toks: List[_Tok], src: str = ""):
        self.toks, self.i = toks, 0
        # WHAT KIND EACH BOUND NAME HOLDS, so `source.launch()` can be resolved against the
        # right class. Filled by `_new` as the program is read, which is the only place a
        # binding's kind is stated — and it is stated BEFORE any method call on it can appear,
        # because a name has to be bound before it is used.
        self.binds: Dict[str, str] = {}
        # THE ORIGINAL TEXT, kept so a free-text value can be sliced out of it verbatim.
        self.src = src

    @property
    def tok(self) -> _Tok:
        return self.toks[self.i]

    def at(self, value: str) -> bool:
        """Is the next token this word or punctuation? Case-insensitive for words."""
        t = self.tok
        if t.kind == WORD:
            return str(t.value).upper() == value.upper()
        return t.kind == PUNCT and t.value == value

    def take(self, value: str = None) -> _Tok:
        t = self.tok
        if value is not None and not self.at(value):
            raise ParseError(f"expected {value!r}, found {t.value!r}", t.line)
        self.i += 1
        return t

    def accept(self, value: str) -> bool:
        if self.at(value):
            self.i += 1
            return True
        return False

    def done(self) -> bool:
        return self.tok.kind == END


# ── the grammar ────────────────────────────────────────────────────────────────────────
def parse_many(text: str) -> List[Dict[str, Any]]:
    """Every top-level program in one file. A CLASS IS A FILE WITH SEVERAL OF THEM.

    `render_stored` prints a class as one `PROCEDURE Class.method` block per method, joined —
    so a class file is not one program and `parse` would refuse it as trailing input. That is
    the correct behaviour for `parse`, whose contract is one program; this is the reader for
    a FILE, which may hold more.
    """
    cur = _Cursor(_tokens(text), text)
    out = []
    while not cur.done():
        out.append(_program(cur))
    return out


def parse(text: str) -> Dict[str, Any]:
    """A rendered program, back as IR. `{name?, params?, imports?, body: [...]}`.

    A NAMED PROCEDURE AND A BARE PROGRAM ARE THE SAME GRAMMAR, differing only in whether a
    signature and braces wrap the statements — exactly as `render` treats them, because an
    ad-hoc run and a stored procedure are the same object with and without a name.
    """
    cur = _Cursor(_tokens(text), text)
    out = _program(cur)
    if not cur.done():
        raise ParseError(f"trailing input at {cur.tok.value!r}", cur.tok.line)
    return out


def _program(cur: _Cursor) -> Dict[str, Any]:
    """One program — a signature and a block, or bare statements to the end of the input."""
    out: Dict[str, Any] = {}
    named = False
    if cur.at(_word("procedure")):
        cur.take()
        # A DOTTED NAME IS ONE NAME. A class renders one block per method, each headed
        # `PROCEDURE Class.method(…)` — reading a single token stopped at the class and left
        # the `.` where a `(` was expected, so every class file on disk failed to load.
        name = str(cur.take().value)
        while cur.at("."):
            cur.take(".")
            name += "." + str(cur.take().value)
        out["name"] = name
        out["params"] = _params(cur)
        if not out["params"]:
            out.pop("params")
        # THE SCHEDULE, read back off the header. `EVERY` takes a span the manifest already
        # knows how to read; `WHEN` takes an ordinary predicate, so a trigger is expressed in
        # the same check vocabulary as everything else rather than in a second one.
        while not cur.at("{"):
            if cur.accept(_word("every")):
                span = str(cur.take().value)
                # `1h` SCANS AS A NUMBER AND A WORD, because the tokeniser has no notion of a
                # unit — and should not, since a span is one of several manifest types rather
                # than a special case in the scanner.
                if cur.tok.kind == WORD and cur.tok.pos == cur.toks[cur.i - 1].end:
                    span += str(cur.take().value)
                out["every"] = span
            elif cur.accept(_word("when")):
                out["when"] = _predicate(cur)
            else:
                raise ParseError(f"expected a schedule or '{{', found {cur.tok.value!r}",
                                 cur.tok.line)
        cur.take("{")
        named = True

    imports = []
    while cur.at(_word("import")):
        cur.take()
        pkg = str(cur.take().value)
        # `@version` IS OPTIONAL AND IS KEPT WHEN PRESENT, because a package pinned to a
        # version and one that floats are different declarations and the file says which.
        if cur.accept("@"):
            imports.append({"package": pkg, "version": str(cur.take().value)})
        else:
            imports.append(pkg)
        cur.take(";")
    if imports:
        out["imports"] = imports

    body = []
    while not cur.done() and not cur.at("}"):
        body.append(_statement(cur))
    if named:
        cur.take("}")
    out["body"] = body
    return out


def _params(cur: _Cursor) -> Dict[str, str]:
    """`(INT n, STRING name)` -> `{n: 'int', name: 'string'}`. TYPE FIRST, as declared."""
    cur.take("(")
    out: Dict[str, str] = {}
    sql_to_key = {v.get("sql", k.upper()): k for k, v in (config.PARAM_TYPES or {}).items()}
    while not cur.at(")"):
        typ = str(cur.take().value).upper()
        name = str(cur.take().value)
        out[name] = sql_to_key.get(typ, typ.lower())
        if not cur.accept(","):
            break
    cur.take(")")
    return out


def signature(text: str) -> Dict[str, str]:
    """`"(STRING name, INT n)"` -> `{name: 'string', n: 'int'}`. Raises `ParseError`.

    THE SAME READER THE FILE USES, exposed so a signature can be declared somewhere OTHER
    than a `.medusa` — specifically in the operator's request
    (`procedure test(STRING name, STRING os_type): …`). A second reader would be a second
    spelling of a signature, and the two would disagree the day a type was added: the
    operator would write what the reference showed them and the request would refuse it.

    SO WHAT IS TYPED IN A REQUEST AND WHAT IS READ BACK OUT OF A FILE ARE ONE GRAMMAR, which
    is also what makes the round trip honest — the signature the operator declared is
    rendered into the file and parsed back by this same function.

    AND THE TYPE IS CHECKED HERE, WHERE `_params` DOES NOT CHECK IT. Reading a file,
    `_params` accepts an unknown type word and lower-cases it, which is the right
    forgiveness for an artifact that already exists — refusing to load a program over a type
    name would lose the program. A DECLARATION BEING TYPED FOR THE FIRST TIME is the
    opposite case: `procedure t(STIRNG name)` is a typo, and accepting it would mint a
    parameter of type `stirng` that nothing will ever check. A declaration nobody can check
    is not a declaration.
    """
    got = _params(_Cursor(_tokens(text), text))
    known = {k: v.get("sql", k.upper()) for k, v in (config.PARAM_TYPES or {}).items()}
    for param, typ in got.items():
        if typ not in known:
            raise ParseError(
                f"{param}: there is no type {typ.upper()!r}. "
                f"Declared types are {', '.join(sorted(known.values()))}")
    return got


def _statement(cur: _Cursor) -> Dict[str, Any]:
    """One statement, and its `IFAILS` tail if it has one."""
    st = _bare_statement(cur)
    # `IFAILS { … }` BELONGS TO THE STATEMENT, NOT TO THE BLOCK, which is why it is read here
    # rather than in each branch: every acting statement can carry one and none of them should
    # have to know that.
    if cur.at(_word("ifails")):
        cur.take()
        cur.take("{")
        recov = []
        while not cur.at("}"):
            recov.append(_statement(cur))
        cur.take("}")
        st["ifails"] = recov
    return st


def _bare_statement(cur: _Cursor) -> Dict[str, Any]:
    t = cur.tok
    if t.kind != WORD:
        raise ParseError(f"expected a statement, found {t.value!r}", t.line)
    head = str(t.value).upper()

    if head == _word("bind").upper():
        return _bound(cur)
    # AN UNBOUND CREATION. `NEW CALL mark_as_template(…)` makes something nothing refers to,
    # so there is no name to give it and inventing one would put a variable in the program
    # that no line reads.
    if head == _word("new").upper():
        return _new(cur, None)
    # A METHOD ON A BOUND NAME — `source.launch();`. SUGAR, and deliberately nothing more: it
    # DESUGARS to the call the class already says it is, so there is no second execution path
    # and no method that can mean something a tool call cannot. `classes.py` derives the whole
    # mapping from the manifest, so a kind that grows a setter grows a method the same day and
    # this reads it without an edit.
    if cur.toks[cur.i + 1].kind == PUNCT and cur.toks[cur.i + 1].value == ".":
        return _method(cur)
    if head == _word("publish").upper():
        cur.take()
        cur.take("(")
        # THE FACT IS A SLICE, NOT A TOKEN. A kind's `fact` template embeds the member —
        # `answer(how fast is lightning)`, and once parameterised `answer($query)` — so it
        # carries spaces AND its own parentheses. Reading one token took `answer` and then
        # failed on the `(` that followed, which made every published deliverable unparseable
        # the moment it stopped being a bare word like `done`.
        start = cur.tok.pos
        end, depth = start, 0
        while not cur.done():
            if depth == 0 and cur.at(")"):
                break
            t = cur.take()
            if t.kind == PUNCT and t.value in "([{":
                depth += 1
            elif t.kind == PUNCT and t.value in ")]}":
                depth -= 1
            end = t.end
        fact = cur.src[start:end].strip()
        cur.take(")")
        cur.take(";")
        return {"op": "publish", "fact": fact}
    if head == _word("call").upper():
        return _call(cur, graft=None)
    if head == _word("foreach").upper():
        return _foreach(cur)
    if head in (_word("ensure").upper(), _word("achieve").upper()):
        cur.take()
        op = "ensure" if head == _word("ensure").upper() else "achieve"
        pred = _predicate(cur)
        cur.take(";")
        return {"op": op, "predicate": pred}
    if head == _word("if").upper():
        return _if(cur)
    raise ParseError(f"not a statement: {t.value!r}", t.line)


def _bound(cur: _Cursor) -> Dict[str, Any]:
    """`STORE x = …` — the three things that can follow the `=`, told apart by one token."""
    cur.take()                                   # STORE
    var = str(cur.take().value)
    cur.take("=")
    if cur.at(_word("new")):
        return _new(cur, var)
    if cur.at(_word("fetch")):
        cur.take()
        st: Dict[str, Any] = {"op": "fetch", "var": var}
        if cur.at(_word("count")):
            cur.take()
            cur.take("(")
            st["count"] = _select(cur)
            cur.take(")")
        else:
            st["select"] = _select(cur)
        cur.take(";")
        return st
    if cur.at(_word("call")):
        return _call(cur, graft=var)
    raise ParseError(f"expected NEW, FETCH or CALL after '{var} ='", cur.tok.line)


def _new(cur: _Cursor, var: str) -> Dict[str, Any]:
    """`NEW [AMOUNT(n)] CALL tool(args) [FROM src]`.

    THE KIND IS NOT IN THE LINE and that is the operator's object model, not an omission: a
    creation is a CONSTRUCTOR CALL, so the line names the constructor and the kind follows
    from it. Recovering it is a manifest lookup, which is exact — `_kind_of` answers from the
    same `create`/`creators` rows `render._creator` printed from.
    """
    from . import effects
    cur.take()                                   # NEW
    st: Dict[str, Any] = {"op": "new"}
    if var is not None:
        st["var"] = var
    if cur.at(_word("amount")):
        cur.take()
        cur.take("(")
        first = cur.take().value
        # `AMOUNT(5 - 2)` IS A SHORTFALL, printed as the subtraction it is so a reader can see
        # the program creates the DIFFERENCE rather than the target.
        if cur.accept("-"):
            st["amount"] = {"minus": [first, cur.take().value]}
        else:
            st["amount"] = first
        cur.take(")")
    if cur.accept(_word("call")):
        tool = str(cur.take().value)
        kind = effects._kind_of(tool, None)
        if not kind:
            raise ParseError(f"no kind is created by {tool!r}", cur.tok.line)
        st["kind"] = kind
        # KEEP WHICH CONSTRUCTOR, BUT ONLY WHEN IT CANNOT BE DERIVED. A vm can be copied two
        # ways — `clone_vm` from another machine, `create_vm(template: …)` from a golden image
        # — so `FROM` alone is ambiguous and re-deriving picks whichever creator is listed
        # first. The author wrote the tool on the line, so the ambiguity is already resolved
        # in the text and this keeps that resolution.
        #
        # RECORDED ONLY WHEN IT ADDS SOMETHING. Storing it unconditionally would put a field in
        # every `new` that the renderer would have worked out anyway — noise in the IR, and it
        # breaks `parse(render(ir)) == ir` for every program written before this existed.
        st["written_tool"] = tool
    else:
        # THE BARE FORM IS STILL READ. A kind with no declared creator renders as `NEW vm(…)`,
        # and a hand-written file may use it; refusing it here would make the parser stricter
        # than the renderer, which is the asymmetry this module exists to remove.
        st["kind"] = str(cur.take().value)
    if cur.at("("):
        st["args"] = _args(cur)
    written = st.pop("written_tool", None)
    if cur.accept("FROM"):
        # SLICED FROM THE SOURCE, not taken as one token. `FROM template-windows` is THREE
        # tokens — the tokeniser splits on `-` because `--` opens a comment — and reading one
        # of them silently yielded `template`, a name that does not exist. Every template in
        # the lab is hyphenated (`template-kali`, `template-ubuntu`, `template-windows`), so
        # this was not an edge case; it was the only case.
        start = cur.tok.pos
        end = start
        while not cur.done() and not cur.at(";"):
            end = cur.take().end
        st["from"] = cur.src[start:end].strip()
    if written and written != _derived_creator(st):
        st["tool"] = written
    cur.take(";")
    if var:
        cur.binds[var] = st.get("kind")
    return st


def _method(cur: _Cursor) -> Dict[str, Any]:
    """`$var.method(args)` -> the call that method IS, with `$var` as the receiver.

    THE RECEIVER IS THE POINT AND THE WHOLE ARGUMENT FOR CLASSES: a method cannot be asked
    about the wrong scope, because the scope is what it is called on. `classes.Method.call`
    returns the same `(tool, args)` pair the writer already plans and the executor already
    runs, so nothing new exists underneath this line.
    """
    from . import classes
    raw = str(cur.take().value)
    # THE SIGIL IS REQUIRED, because a receiver IS a reference and `$` is what a reference
    # looks like everywhere else in the language. It used to be optional, and an optional
    # spelling here is not a kindness: `render` prints `$v.launch()`, so a file written
    # `v.launch()` parsed to the right program and then failed `verify_file`'s round trip —
    # a form you can type and never save, which is the exact defect the method form was
    # made the only way in to remove.
    if not raw.startswith(config.SIGIL):
        raise ParseError(f"a receiver is a reference — write "
                         f"{config.SIGIL}{raw}.{cur.toks[cur.i + 1].value}()", cur.tok.line)
    var = raw[len(config.SIGIL):]
    cur.take(".")
    name = str(cur.take().value)
    kind = cur.binds.get(var)
    if not kind:
        raise ParseError(f"{var!r} is not bound to anything, so {name!r} has no receiver",
                         cur.tok.line)
    surface = classes.methods(kind)
    method = surface.get(name)
    if method is None:
        raise ParseError(f"{kind} has no method {name!r} — it has "
                         f"{sorted(surface)}", cur.tok.line)
    # POSITIONAL, NOT NAMED. `v.label(prod)` — the manifest already says which argument that
    # value goes into, so naming it at the call site would be the caller repeating what the
    # class knows. That is the whole economy of a method: the receiver and the argument names
    # are both implied by WHAT IT IS CALLED ON.
    values = []
    if cur.at("("):
        cur.take("(")
        while not cur.at(")"):
            start, end = cur.tok.pos, cur.tok.pos
            quoted = cur.tok.kind == STR
            while not cur.done() and not cur.at(",") and not cur.at(")"):
                t = cur.take()
                end = t.end
                quoted = quoted and (cur.at(",") or cur.at(")"))
            raw = cur.src[start:end].strip()
            values.append(raw[1:-1] if quoted and len(raw) >= 2 else _coerce(raw))
            if not cur.accept(","):
                break
        cur.take(")")
    cur.take(";")
    # AS MANY VALUES AS THE METHOD TAKES. `label(prod)` writes one, `limit(80, 4096)` writes
    # two, `launch()` writes a fixed one the manifest already names and so takes none.
    if len(values) > len(method.takes):
        raise ParseError(
            f"{kind}.{name}() takes {len(method.takes)} "
            f"({', '.join(method.takes) or 'nothing'}), not {len(values)}", cur.tok.line)
    tool, args = method.call(f"{config.SIGIL}{var}", *values)
    return {"op": "call", "tool": tool, "args": args}


def _derived_creator(st: Dict[str, Any]) -> Optional[str]:
    """Which constructor `render` would work out for this statement, with no `tool` recorded.

    THE INVERSE OF `render._creator`, and it exists so the parser can stay silent about
    anything the renderer already knows. Written out rather than imported to keep `render`
    free of a dependency on its own reader.
    """
    spec = (config.KINDS or {}).get(st.get("kind")) or {}
    if st.get("from"):
        for c in (spec.get("creators") or {}).values():
            if c.get("from") and c.get("tool"):
                return c["tool"]
    return spec.get("create")


def _call(cur: _Cursor, graft: Optional[str]) -> Dict[str, Any]:
    cur.take()                                   # CALL
    # A TOOL NAME IS ONE IDENTIFIER. It briefly accepted a dotted one, for
    # `CALL NetworkSetup.attach(...)` — the namespace class, deleted 2026-08-04. A method now
    # has a RECEIVER and reaches `_method` long before this, so nothing legal is dotted here
    # and accepting it would only let a typo through to fail as an unknown tool.
    tool = str(cur.take().value)
    args = _args(cur) if cur.at("(") else {}
    line = cur.tok.line
    cur.take(";")
    # THE LONG FORM IS NOT A SECOND WAY IN. The operator's ruling, 2026-08-04: *"the only
    # way you can access a vm's method is through calling it with the method"*. Where this
    # program HOLDS the thing being acted on, the method form is the form — and refusing
    # the other one is what makes that true, rather than merely preferred.
    #
    # IT BITES ONLY ON A BOUND RECEIVER, which is the whole of the rule and also its limit:
    # `CALL launch_vm(name: web)` names a machine this program does not hold, and
    # `CALL launch_vm(name: $box)` where `$box` is a STRING PARAMETER is a procedure acting
    # on a name it was handed. Neither has a receiver to go through, so neither is refused.
    from . import classes
    got = classes.receiver(tool, args, cur.binds)
    if got:
        var, method, values = got
        shown = ", ".join(str(v) for v in values)
        raise ParseError(
            f"{tool} acts on the {cur.binds[var]} this program holds — write "
            f"{config.SIGIL}{var}.{method}({shown})", line)
    st: Dict[str, Any] = {"op": "call", "tool": tool, "args": args}
    if graft:
        st["graft"] = graft
    return st


def _foreach(cur: _Cursor) -> Dict[str, Any]:
    cur.take()                                   # FOREACH
    cur.take()                                   # $item — the loop variable is fixed
    cur.take(_word("in"))
    st: Dict[str, Any] = {"op": "foreach"}
    if cur.at("["):
        cur.take("[")
        items = []
        while not cur.at("]"):
            items.append(_coerce(str(cur.take().value)))
            if not cur.accept(","):
                break
        cur.take("]")
        st["in"] = items
    elif cur.at("SELECT"):
        st["select"] = _select(cur)
    else:
        st["in"] = str(cur.take().value)
    if cur.accept(_word("async")):
        st["async"] = True
    cur.take("{")
    # THE LOOP VARIABLE IS A MEMBER OF WHATEVER THE LOOP RANGES OVER, so inside the body it
    # is a receiver like any other: `FOREACH $item IN SELECT vm { $item.stop(); }`. The kind
    # is READ — off the select, or off the binding when the loop walks a set an earlier line
    # made — and a loop over a literal list binds nothing, because a list of strings says
    # what its members are called and not what they are.
    #
    # BOUND FOR THE BODY AND RESTORED AFTER, which is the one place this parser scopes
    # anything. `$item` does not exist outside the loop, and leaving it bound would let a
    # later line print as a method on a variable the runtime has nothing for.
    kind = (st.get("select") or {}).get("kind") if isinstance(st.get("select"), dict) else None
    if kind is None and isinstance(st.get("in"), str):
        kind = cur.binds.get(str(st["in"]).lstrip(config.SIGIL))
    had = cur.binds.get(config.LOOP_VAR, _ABSENT)
    if kind:
        cur.binds[config.LOOP_VAR] = kind
    do = []
    while not cur.at("}"):
        do.append(_statement(cur))
    if had is _ABSENT:
        cur.binds.pop(config.LOOP_VAR, None)
    else:
        cur.binds[config.LOOP_VAR] = had
    cur.take("}")
    st["do"] = do
    return st


def _if(cur: _Cursor) -> Dict[str, Any]:
    cur.take()                                   # IF
    st: Dict[str, Any] = {"op": "if", "cond": _predicate(cur)}
    cur.take("{")
    then = []
    while not cur.at("}"):
        then.append(_statement(cur))
    cur.take("}")
    st["then"] = then
    if cur.accept(_word("else")):
        cur.take("{")
        other = []
        while not cur.at("}"):
            other.append(_statement(cur))
        cur.take("}")
        st["else"] = other
    return st


def _args(cur: _Cursor) -> Dict[str, Any]:
    """`(k: v, k2: v2)` — and a value runs to the next top-level `,` or `)`.

    ARGUMENT VALUES ARE UNQUOTED AND MAY CONTAIN SPACES. `_args` prints `k: v` bare, so a
    Camoufox search renders as `CALL camoufox_search(query: how fast is lighting?)` — the
    value is a sentence, with a `?` in it. Reading token-by-token to a delimiter is what makes
    that legible; a rule that stopped at whitespace would truncate every query in the system.
    """
    cur.take("(")
    out: Dict[str, Any] = {}
    while not cur.at(")"):
        key = str(cur.take().value)
        cur.take(":")
        # THE VALUE IS THE ORIGINAL CHARACTERS, sliced from the source between the delimiters
        # — not the tokens re-joined. Re-joining meant inventing the whitespace back, and a
        # heuristic that reads `how fast is lighting?` correctly turns `https://x.com/a?b=1`
        # into `https://x.com/a? b = 1`. There is no rule that separates a sentence from a URL,
        # because the difference is not in the characters; it is that ONE OF THEM WAS NEVER
        # SPLIT IN THE FIRST PLACE. Keeping each token's source span means the value never has
        # to be reassembled at all.
        start = cur.tok.pos
        end = start
        depth = 0
        quoted = cur.tok.kind == STR
        while not cur.done():
            if depth == 0 and (cur.at(",") or cur.at(")")):
                break
            t = cur.take()
            if t.kind == PUNCT and t.value in "([{":
                depth += 1
            elif t.kind == PUNCT and t.value in ")]}":
                depth -= 1
            end = t.end
            quoted = quoted and (cur.at(",") or cur.at(")"))
        raw = cur.src[start:end].strip()
        # A QUOTED VALUE STAYS A STRING, unconditionally. Quotes are the author saying "this is
        # text", and coercing `'3'` back to 3 would overrule them.
        out[key] = raw[1:-1] if quoted and len(raw) >= 2 else _coerce(raw)
        if not cur.accept(","):
            break
    cur.take(")")
    return out


def _value(cur: _Cursor) -> Any:
    """One value in a selector. QUOTES MEAN TEXT, and that is not a formality.

    `render._select` prints EVERY term as `k = 'v'`, so every value here arrives quoted — and
    coercing them all on the "what looks like a number is one" rule silently rewrote the ones
    that matter. `template = 'true'` became the BOOLEAN true where the manifest says that
    setter writes the STRING "true", so a selector that reads correctly on the page stopped
    matching anything in the world. `name = '3'` had the same problem one type over.

    FOUND BY HAND-WRITING A PROCEDURE, not by the round-trip suite, because the corpus had no
    selector whose value looked like something else. The case is in the suite now.
    """
    t = cur.take()
    return t.value if t.kind == STR else _coerce(str(t.value))


def _select(cur: _Cursor) -> Dict[str, Any]:
    """`SELECT kind [WHERE a = 'x' AND …] [INCLUDE k = [..]] [EXCEPT a = 'x']`."""
    cur.take("SELECT")
    sel: Dict[str, Any] = {"kind": str(cur.take().value)}
    if cur.accept(_word("where")):
        while True:
            if cur.at(_word("include")):
                break
            attr = str(cur.take().value)
            cur.take("=")
            sel[attr] = _value(cur)
            if not cur.accept("AND"):
                break
    while cur.at(_word("include")):
        cur.take()
        attr = str(cur.take().value)
        cur.take("=")
        if cur.accept("["):
            members = []
            while not cur.at("]"):
                members.append(_coerce(str(cur.take().value)))
                if not cur.accept(","):
                    break
            cur.take("]")
            sel[attr] = {"in": members}
        else:
            sel[attr] = {"in": str(cur.take().value)}
    if cur.accept(_word("except")):
        carve: Dict[str, Any] = {}
        while True:
            attr = str(cur.take().value)
            cur.take("=")
            carve[attr] = _value(cur)
            if not cur.accept("AND"):
                break
        sel["not"] = carve
    return sel


def _predicate(cur: _Cursor) -> Dict[str, Any]:
    """A check, read from `config.PREDICATES` rather than from a list written here.

    THE MANIFEST IS THE AUTHORITY ON BOTH SIDES. `render._pred` prints from these rows and
    this reads from them, so a predicate added to the JSON parses without an edit here — the
    same property the renderer's docstring claims for itself, which is only true of the pair.
    """
    t = cur.tok
    word = str(t.value).upper()
    shape = _shape_named(word)
    if shape is None:
        raise ParseError(f"unknown check {t.value!r}", t.line)
    cur.take()
    spec = config.PREDICATES.get(shape) or {}
    cur.take("(")

    if spec.get("operand") == "of":
        if spec.get("arity") == "value":
            # A DOTTED REFERENCE IS ONE OPERAND — the SECOND time this exact bug has been
            # found. `PROCEDURE Class.method` had it and every class file on disk failed to
            # load; here it is `IS($answer.alive)`, which the RENDERER emits and the parser
            # could not read, so any program that branched on a call's result rendered
            # correctly, VALIDATED, and then failed `verify_file`'s round-trip on the way
            # back in. Result-branching has been in the language and unusable.
            #
            # `refs` ALREADY DEFINES THIS SHAPE — `$answer.reachable` is one reference whose
            # root is `answer` — so reading a single token was the parser disagreeing with
            # the module that owns what a reference means.
            of = str(cur.take().value)
            while cur.at("."):
                cur.take(".")
                of += "." + str(cur.take().value)
            cur.take(")")
            out: Dict[str, Any] = {"shape": shape, "of": of}
            return _comparator(cur, spec, out)
        kids = [_predicate(cur)]
        while cur.accept(","):
            kids.append(_predicate(cur))
        cur.take(")")
        # `NOT` TAKES ONE AND STORES IT AS ONE. The renderer unwraps a one-element list
        # through `one_check` on the way out; storing a bare dict on the way in is the same
        # normalisation from the other side.
        return {"shape": shape, "of": kids[0] if spec.get("arity") == "one" else kids}

    if spec.get("operand") == "sets":
        sets = [str(cur.take().value)]
        while cur.accept(","):
            sets.append(str(cur.take().value))
        cur.take(")")
        return {"shape": shape, "sets": sets}

    inner = _select(cur)
    cur.take(")")
    return _comparator(cur, spec, {"shape": shape, "select": inner})


def _comparator(cur: _Cursor, spec: Dict[str, Any], out: Dict[str, Any]) -> Dict[str, Any]:
    """The `= 1` after a check, or nothing where the manifest allows nothing.

    A MISSING COMPARATOR IS LEGAL WHERE `comparators_optional` SAYS SO — `reach` declares it,
    and a bare `REACH(SELECT vm)` means "these can reach each other" at the default floor.
    The renderer already had to learn this; refusing it here would make a program that prints
    correctly fail to read back.
    """
    comparators = spec.get("comparators") or {}
    sym_to_key = {}
    for key, sym in comparators.items():
        sym_to_key.setdefault(sym, key)
    # `=` AND `==` ARE THE SAME COMPARATOR. The renderer prints `=`; a person writing this by
    # hand will type `==` about half the time, and rejecting it would be pedantry with no
    # meaning behind it.
    if "=" in sym_to_key:
        sym_to_key.setdefault("==", sym_to_key["="])
    t = cur.tok
    if t.kind == PUNCT and str(t.value) in sym_to_key:
        cur.take()
        out[sym_to_key[str(t.value)]] = _coerce(str(cur.take().value))
        return out
    if comparators and not spec.get("comparators_optional"):
        raise ParseError(f"expected one of {sorted(set(comparators.values()))}"
                         f" after {out['shape'].upper()}(…)", t.line)
    return out


def _shape_named(word: str) -> Optional[str]:
    """`AND` -> `all`, `COUNT` -> `count`. Combinators are named in `SURFACE`, checks are not.

    TWO TABLES BECAUSE THERE ARE TWO KINDS OF NAME. A combinator's printed word is a surface
    decision (`all` prints as `AND`); a check's is its own shape, upper-cased. Reading both
    from where they are declared is what stops this function becoming the list of predicates.
    """
    for shape, printed in (config.SURFACE.get("combinators") or {}).items():
        if printed.upper() == word:
            return shape
    low = word.lower()
    return low if low in (config.PREDICATES or {}) else None
