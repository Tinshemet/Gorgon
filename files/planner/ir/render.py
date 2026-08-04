"""
render.py — the operator's view: SQL-shaped text, one direction only.

It exists so a human can READ a program before signing it — which is what makes a signed
procedure reviewable rather than a blob of JSON.

"ONE DIRECTION ONLY" HAS NOT BEEN TRUE SINCE `parse.py`, and a `.medusa` file IS its own
program now, so this half has an obligation it did not have when it was written: EVERY
LINE IT PRINTS MUST READ BACK AS THE STATEMENT IT CAME FROM. `verify_file` checks exactly
that on every save. Where a call is a method on a bound receiver it must therefore print
the method form, because the parser refuses the long one — `classes.receiver` is the one
place that decides, and both sides ask it.

It renders UNVALIDATED model output, so nothing here may raise. A renderer that crashes
on a malformed program hides the very thing you opened it to look at — it did exactly
that once, on a predicate holding a number where a set belonged.
"""

from typing import Any, Dict, Optional

from . import config
from .validate import coerce_body, one_check


# "NOT BOUND" IS NOT "BOUND TO NOTHING" — the loop restores whatever it found, and `None` is
# a legal thing to have found. Same sentinel, same reason, as the parser's.
_ABSENT = object()


def _w(key: str) -> str:
    """A printed keyword, from the surface table.

    Every word the renderer emits comes from here, so renaming one is a data change and
    the stored form never moves — which is what "syntax is a VIEW" was supposed to mean.
    Two of seven ops had an entry before test_medusa_invariants asked, and `fetch` had one
    the renderer ignored in favour of a literal.
    """
    return config.SURFACE.get(key, key.upper())


def render(program: Any) -> str:
    """A program as readable text.

    SQL keywords in upper case, C-family braces for blocks. The braces are not decoration:
    every construct coming next — IF/ELSE, IFAILS — carries a statement LIST, and
    DO … END does not nest legibly. Getting the shape right before those land is cheaper
    than migrating procedures that were already written.
    """
    body = coerce_body(program) or []
    out = []
    named = isinstance(program, dict) and bool(program.get("name"))
    if named:
        out.append(_signature(program) + " {")
    if isinstance(program, dict):
        pre = []
        for imp in (program.get("imports") or []):
            v = f" @{imp['version']}" if isinstance(imp, dict) and imp.get("version") else ""
            pkg = imp.get("package") if isinstance(imp, dict) else imp
            pre.append(f"{'  ' if named else ''}{_w('import')} {pkg}{v};")
        if pre:
            out += pre + [""]

    indent = "  " if named else ""
    # WHAT EACH NAME IS, built as the walk goes — the renderer's half of the parser's
    # `_Cursor.binds`, filled in the same order from the same statements. It is flat and
    # program-wide because the parser's is: a `$box` bound inside an IF is still `$box`
    # afterwards, and printing under a different scoping rule than the one that reads it
    # back is how a program stops being its own text.
    binds: Dict[str, str] = {}
    for st in body:
        out += _statement(st, indent, binds)
    if named:
        out.append("}")
    return "\n".join(out)


def _statement(st: Any, indent: str, binds: Optional[Dict[str, str]] = None) -> list:
    """One statement, as one or more lines. Blocks recurse, so nesting indents itself."""
    if not isinstance(st, dict):
        return [f"{indent}<not a statement: {st!r}>"]
    if binds is None:
        binds = {}
    op = st.get("op")

    if op == "new":
        n = st.get("amount", 1)
        # "NEW 5 vm(...)" reads the way the request does — "create 5 vms". A trailing
        # multiplier had to be decoded, and a $parameter one silently vanished entirely.
        # AMOUNT(5) rather than a bare 5: it reads as a count instead of an argument that
        # happens to be a number, and it mirrors COUNT(...) on the predicate side.
        if isinstance(n, dict) and isinstance(n.get("minus"), list):
            # The shortfall, printed as the subtraction it is. A reader has to be able to
            # see that this creates the DIFFERENCE and not the target — it is the one
            # line where "5" would be actively misleading about how many machines appear.
            many = f"{config.SURFACE['amount']}({n['minus'][0]} - {n['minus'][1]}) "
        else:
            many = (f"{config.SURFACE['amount']}({n}) "
                    if (isinstance(n, str) and n.startswith(config.SIGIL))
                    or (isinstance(n, int) and n != 1) else "")
        extra = _args(st.get("args")) if st.get("args") else ""
        # FROM has to show. A clone reads almost identically to a fresh create, and the
        # difference — whether this copies something that exists — is exactly what an
        # operator is deciding about when they read the line.
        src = f" FROM {st['from']}" if st.get("from") else ""
        # `NEW CALL create_vm(…)`, NOT `NEW vm(…)`. The operator's decision, 2026-08-02:
        # *"how you create a new object/class its with the tool call that creates them, IE
        # NEW CALL create_vm"*. Now that a kind is a CLASS, its creation is a constructor
        # call and should say so — `NEW` marks it a creation rather than an invocation, and
        # the call names WHICH constructor instead of leaving the kind to imply it.
        maker = _creator(st)
        head = f"{_w('new')} {many}" + (f"{config.SURFACE.get('call', 'CALL')} {maker}"
                                        if maker else f"{st.get('kind')}")
        # THE BINDING IS OPTIONAL, and the operator struck it on sight: *"you dont need the
        # STORE golden = NEW CALL … just fold it to a NEW CALL … because all you are doing is
        # marking it as a template you dont need to store it."* A name is worth having when
        # something REFERS to it; binding a result nobody reads is noise on the one line where
        # a reader is trying to see what the program touches.
        lead = f"{config.SURFACE['bind']} {st['var']} = " if st.get("var") else ""
        # AND THE NAME NOW MEANS SOMETHING TO THE REST OF THE WALK. This is the only
        # statement that binds a name to a KIND, which is what makes every later line able
        # to print as a method on it.
        if st.get("var") and st.get("kind"):
            # ONE OR SEVERAL — the parser's rule, mirrored, because the two halves decide the
            # same thing and a printed program has to read back as itself.
            binds[str(st["var"])] = (st["kind"] if st.get("amount", 1) == 1
                                     else _classes().set_of(str(st["kind"])))
        return _with_tail([f"{indent}{lead}{head}"
                           f"{f'({extra})' if extra else ''}{src};"], st, indent, binds)

    if op == "break":
        return [f"{indent}{_w('break')};"]

    if op == "publish":
        # THE ONE STATEMENT WHOSE EFFECT IS ON THE CONVERSATION. It names the fact and never
        # a value — the engine supplies what it actually observed — so a reader can tell at a
        # glance that the program is REPORTING rather than asserting.
        # `PUBLISH(vm)` — the operator's form. A publication names a THING, and parentheses
        # say it is being handed over rather than declared.
        return _with_tail([f"{indent}{_w('publish')}({st.get('fact')});"], st, indent)

    if op == "call":
        # A grafted result reads as a binding, the same LET that binds a resource —
        # because naming a result and naming a resource are the same act.
        #
        # AND THE KEYWORD LEADS. An invocation is the one statement that reaches the world,
        # and printing it bare made the ACTING lines the only ones on the page without a word
        # in front of them — the quietest thing in a program, where they should be the
        # loudest. `CALL create_vm(...)` reads the way `ENSURE` and `ACHIEVE` do: what the
        # line does, then what it touches.
        #
        # WHERE THE BINDING GOES. `STORE $x = CALL probe(...)` — the keyword belongs to the
        # invocation, not to the statement, so it sits after the `=` where the value comes
        # from rather than in front of the name being bound.
        verb = config.SURFACE.get("call")
        lead = f"{config.SURFACE['bind']} {st['graft']} = " if st.get("graft") else ""
        head = f"{verb} " if verb else ""
        # A CALL ON SOMETHING THIS PROGRAM HOLDS IS A METHOD ON IT, and printing the long
        # form would print text the parser refuses — the operator's ruling of 2026-08-04:
        # *"the only way you can access a vm's method is through calling it with the
        # method"*. `classes.receiver` answers only when the method rebuilds this call
        # EXACTLY, so nothing is ever lost to the shorter spelling.
        got = _receiver(st.get("tool"), st.get("args"), binds)
        if got:
            var, method, values = got
            shown = ", ".join(_arg(v) for v in values)
            return _with_tail([f"{indent}{lead}{config.SIGIL}{var}.{method}({shown});"],
                              st, indent, binds)
        return _with_tail([f"{indent}{lead}{head}{st.get('tool')}({_args(st.get('args'))});"],
                          st, indent, binds)

    if op == "foreach":
        inner = st.get("call") if isinstance(st.get("call"), dict) else {}
        src = (_select(st.get("select")) if st.get("select") is not None
               else _setlit(st.get("in")))
        # The loop variable is printed as what it IS. It used to print `x` while the body
        # referenced $item — two names for one thing, in the one place a reader most needs
        # to follow the binding.
        member = f"{config.SIGIL}{config.LOOP_VAR}"
        par = f" {_w('async')}" if st.get("async") else ""
        # A block body prints as its statements; the single-call shorthand prints as the
        # one call. Both wear the same braces, so the shorthand is invisible to a reader —
        # which is the point of having it.
        # THE LOOP VARIABLE IS A MEMBER OF WHAT THE LOOP RANGES OVER, and inside the body it
        # is a receiver like any other. Bound for the body and restored after — the parser
        # scopes it exactly here and for exactly this reason, and the two halves have to
        # agree or a printed loop stops reading back as itself.
        kind = (st.get("select") or {}).get("kind") if isinstance(st.get("select"), dict) \
            else (_classes().in_set(binds.get(str(st.get("in")).lstrip(config.SIGIL)))
                  if isinstance(st.get("in"), str) else None)
        had = binds.get(config.LOOP_VAR, _ABSENT)
        if kind:
            binds[config.LOOP_VAR] = kind
        body = []
        if isinstance(st.get("do"), list):
            for kid in st["do"]:
                body += _statement(kid, indent + "  ", binds)
        else:
            body = _statement({"op": "call", **inner}, indent + "  ", binds)
        if had is _ABSENT:
            binds.pop(config.LOOP_VAR, None)
        else:
            binds[config.LOOP_VAR] = had
        return _with_tail([f"{indent}{_w('foreach')} {member} {_w('in')} {src}{par} {{"]
                          + body + [f"{indent}}}"], st, indent, binds)

    if op == "fetch":
        # A PLAIN SELECT BINDS A SET; a COUNT binds a number and so binds nothing here.
        if st.get("select") and st.get("var"):
            kind = (st["select"] or {}).get("kind")
            if kind:
                binds[str(st["var"])] = _classes().set_of(str(kind))
        q = st.get("count") or st.get("select")
        inner = _select(q)
        body = f"{_w('count')}({inner})" if st.get("count") else inner
        return [f"{indent}{config.SURFACE['bind']} {st.get('var', '?')} = "
                f"{_w('fetch')} {body};"]

    if op in ("ensure", "achieve"):
        # The keyword comes from the surface table, so a word renamed there is renamed
        # here — the reason the surface is data in the first place.
        word = config.SURFACE.get(op, op.upper())
        # `_with_tail` HERE TOO, and its absence was a silent data loss: an ENSURE carrying
        # an IFAILS parsed correctly and rendered WITHOUT it, so the block vanished on the
        # first round trip — and `verify_file` compares the render against the file, so the
        # program that loaded was not the program on disk.
        return _with_tail([f"{indent}{word} {_pred(st.get('predicate'))};"], st, indent, binds)

    if op == "if":
        out = [f"{indent}{_w('if')} {_pred(st.get('cond'))} {{"]
        for inner in (st.get("then") or []):
            out += _statement(inner, indent + "  ", binds)
        if st.get("else"):
            out.append(f"{indent}}} {_w('else')} {{")
            for inner in st["else"]:
                out += _statement(inner, indent + "  ", binds)
        out.append(f"{indent}}}")
        return out

    return [f"{indent}<unknown op {op!r}>"]


def _creator(st) -> str:
    """The tool that makes this kind — read from the manifest, never written in the line.

    A `new` statement carries its KIND; which constructor that implies is a manifest fact,
    and `FROM` picks the copying one where a kind declares two.
    """
    # THE AUTHOR'S OWN CHOICE FIRST, when the statement carries one.
    if st.get("tool"):
        return st["tool"]
    spec = (config.KINDS or {}).get(st.get("kind")) or {}
    if st.get("from"):
        for c in (spec.get("creators") or {}).values():
            if c.get("from") and c.get("tool"):
                return c["tool"]
    return spec.get("create") or ""


def _classes():
    """`classes`, imported late — `render` is reached from inside it during a resugar."""
    from . import classes
    return classes


def _receiver(tool, args, binds):
    """`classes.receiver`, asked safely. None whenever it cannot answer.

    NOTHING HERE MAY RAISE — this file renders unvalidated model output, and a renderer
    that crashes hides the very thing it was opened to look at.
    """
    try:
        from . import classes
        return classes.receiver(tool, args, binds)
    except Exception:
        return None


def _with_tail(lines: list, st: dict, indent: str,
               binds: Optional[Dict[str, str]] = None) -> list:
    """Append `IFAILS { … }` to a statement's rendering, if it carries one."""
    recov = st.get("ifails")
    if not recov:
        return lines
    lines = list(lines)
    lines[-1] = (lines[-1].rstrip(";") + f"; {_w('ifails')} {{" if lines[-1].endswith(";")
                 else lines[-1] + f" {_w('ifails')} {{")
    for inner in recov:
        lines += _statement(inner, indent + "  ", binds)
    lines.append(f"{indent}}}")
    return lines


def _signature(program: dict) -> str:
    """`PROCEDURE name(p TYPE, ...) AS` — only for a NAMED program.

    A bare goal renders as plain statements, because that is what an ad-hoc run is. The
    signature appears once there is something to store and sign, which is the point at
    which the parameters matter.
    """
    name = program.get("name")
    if not name:
        return ""
    # TYPE FIRST — (INT X), the way a declaration reads in C, Java and Dart. It puts the
    # kind of thing before its name, which is what you want when scanning a signature.
    args = ", ".join(f"{config.PARAM_TYPES.get(v, {}).get('sql', str(v).upper())} {k}"
                     for k, v in (program.get("params") or {}).items())
    # THE SCHEDULE, WHEN THERE IS ONE. A routine is a procedure that also says WHEN, and that
    # is the only fact about a stored program the body cannot state for itself — a contract is
    # readable off the creations, a schedule follows from nothing. It rides in the header
    # because it is not a step the program takes; it is a fact about when the program is taken.
    tail = ""
    if program.get("every"):
        tail += f" {_w('every')} {program['every']}"
    if program.get("when"):
        tail += f" {_w('when')} {_pred(program['when'])}"
    # No trailing AS: the brace already opens the block, and two openers is one
    # more thing to get wrong when writing by hand.
    return f"{_w('procedure')} {name}({args}){tail}"


def _setlit(src) -> str:
    """A bound reference prints as itself; a literal list prints as a list."""
    if isinstance(src, (list, tuple)):
        return "[" + ", ".join(str(x) for x in src) + "]"
    return str(src)


def _args(args) -> str:
    if not isinstance(args, dict):
        return f"<not args: {args!r}>" if args is not None else ""
    return ", ".join(f"{k}: {_arg(v)}" for k, v in args.items())


def _arg(v) -> str:
    """A value, quoted ONLY where leaving it bare would make the line ambiguous.

    BARE IS THE DEFAULT AND SHOULD STAY THAT WAY — `os_type: linux` reads better than
    `os_type: 'linux'`, and every argument in the system is bare today. Two cases are not
    readable bare, and both were found by round-tripping rather than by inspection:

      * A VALUE CONTAINING A COMMA IS INDISTINGUISHABLE FROM TWO ARGUMENTS. `c: a, b` cannot
        be read back as one value by any parser, including a person — the renderer was
        emitting programs that are not programs.
      * A STRING THAT LOOKS LIKE A NUMBER LOSES ITS TYPE. `n: 3` is `3` and `'3'` printed the
        same way, so a machine named `3` came back as an integer. Quoting is what says which.

    THIS IS THE SURFACE CHANGING, SLIGHTLY, and it is worth being explicit about that: some
    values that used to print bare now print quoted. Nothing that was legible becomes less so,
    and something that was AMBIGUOUS becomes exact.
    """
    # A BOOLEAN PRINTS LOWERCASE. `str(True)` is Python's spelling, not Medusa's — a file
    # written with `unattended: true` re-rendered as `unattended: True`, so a round trip
    # changed the operator's text without changing its meaning. Harmless until someone diffs
    # a stored procedure against what they wrote.
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None or isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    needs = any(c in s for c in ",()") or s.strip() != s or not s
    if not needs:
        low = s.lower()
        needs = low in ("true", "false", "none", "null") or _numeric(s)
    return f"'{s}'" if needs else s


def _numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _select(sel) -> str:
    if not isinstance(sel, dict):
        return f"<not a set: {sel!r}>"
    kind = sel.get("kind", "?")

    def _term(k, v):
        # MEMBERSHIP reads as INCLUDE, positioned like EXCEPT — the two are mirrors and a
        # reader who knows one should recognise the other on sight.
        if isinstance(v, dict) and "in" in v:
            m = v["in"]
            listed = ", ".join(str(x) for x in m) if isinstance(m, (list, tuple)) else m
            return (f"{_w('include')} {k} = [{listed}]" if isinstance(m, (list, tuple))
                    else f"{_w('include')} {k} = {listed}")
        # QUOTED IS A STRING, BARE IS A VALUE, and this printed everything quoted. A REAL
        # boolean in a selector — `alive: False`, which is what an observed attribute holds —
        # came out as `alive = 'False'` and read back as the four-letter string, so a program
        # the writer emitted was not the program it was: rung 11 asserted a machine whose
        # liveness was the word "False".
        #
        # THE ASYMMETRY IS THE FIX AND IT IS ALREADY THE PARSER'S RULE. `alive = false` reads
        # back a boolean and `template = 'true'` reads back the string the manifest writes —
        # so quoting only what IS a string is what makes the two directions meet. Everything
        # else stays quoted, which is what keeps `name = '3'` a name.
        if isinstance(v, bool):
            return f"{k} = {'true' if v else 'false'}"
        # AND A REAL NUMBER, for the same reason. `memory_mb` and `cpu_cores` became
        # selectable the day the machine's own record stopped being half-hidden, and
        # `memory_mb = '8192'` reads back as the four-character string — so a goal about
        # memory would compare a string to an integer and match nothing, for ever, quietly.
        # `name = '3'` still keeps its quotes and stays a name.
        if isinstance(v, (int, float)):
            return f"{k} = {v}"
        return f"{k} = '{v}'"

    groups = []
    for group, word in (("any", "OR"), ("all", "AND")):
        kids = sel.get(group)
        if isinstance(kids, list) and kids:
            inner = [" AND ".join(_term(k, v) for k, v in kid.items() if k != "kind")
                     for kid in kids if isinstance(kid, dict)]
            if inner:
                groups.append("(" + f" {word} ".join(inner) + ")")
    plain = [(k, v) for k, v in sel.items() if k not in ("kind", "not", "any", "all")]
    # WITHIN A SET THIS PROGRAM HOLDS reads as `IN $hosts` — the operator's own word for it,
    # and the shorter of the two spellings the parser used to accept. A set holds the NAMES
    # of its members, so "within this set" is membership of the KEY; membership of any OTHER
    # attribute is an ordinary INCLUDE and still prints as one.
    key = ((config.KINDS or {}).get(str(kind)) or {}).get("key")
    within = [v["in"] for k, v in plain
              if k == key and isinstance(v, dict)
              and isinstance(v.get("in"), str) and v["in"].startswith(config.SIGIL)]
    plain = [(k, v) for k, v in plain if not (k == key and v in
                                              [{"in": w} for w in within])]
    includes = [_term(k, v) for k, v in plain if isinstance(v, dict) and "in" in v]
    terms = [_term(k, v) for k, v in plain if not (isinstance(v, dict) and "in" in v)]
    terms += groups
    # The carve-out reads as EXCEPT, which is what the operator said out loud: "every vm
    # except db". Rendering it as another equality printed
    # `WHERE not = '{'name': 'db'}'` — a filter on an attribute called "not", against a
    # dict stringified into a quoted literal. Nobody could read that, and the whole point
    # of the written surface is that a human can check what the machine understood.
    out = f"SELECT {kind}" + (f" {_w('where')} {' AND '.join(terms)}" if terms else "")
    # INCLUDE follows WHERE and precedes EXCEPT, so the line reads in the order it is
    # said: this kind, narrowed by these conditions, restricted to these, minus those.
    if includes:
        out += " " + " ".join(includes)
    for held in within:
        out += f" {_w('in')} {held}"
    # EXCEPT is its OWN clause, not another WHERE term — `WHERE EXCEPT name = 'db'` is
    # not English and not SQL. It follows WHERE when both are present, so the sentence
    # reads in the order the operator said it: this set, minus these.
    carve = sel.get("not")
    if isinstance(carve, dict) and carve:
        out += f" {_w('except')} " + " AND ".join(f"{k} = '{v}'" for k, v in carve.items())
    return out


def _pred(p) -> str:
    """Rendered from the manifest, so a predicate added to JSON prints without an edit."""
    if not isinstance(p, dict):
        return f"<not a predicate: {p!r}>"
    shape = p.get("shape")
    spec = config.PREDICATES.get(shape)
    if spec is None:
        return f"<unknown check {shape!r}>"
    # NOT / AND / OR all take parentheses, so a reader never has to know precedence —
    # there is none to know. AND(a, b) reads the way NOT(a) does.
    if spec.get("arity") == "value":
        # IS($answer.reachable) = false — a grafted result, not a set.
        used = next((c for c in spec["comparators"] if c in p), None)
        sym = spec["comparators"].get(used, "?")
        val = p.get(used)
        lit = "true" if val is True else "false" if val is False else repr(val).strip("'\"") \
            if not isinstance(val, str) else f"'{val}'"
        return f"{shape.upper()}({p.get('of')}) {sym} {lit}"
    if spec["operand"] == "of":
        word = config.SURFACE["combinators"][shape]
        inner = p.get("of")
        if spec.get("arity") == "one":
            # `one_check`, so the renderer shows what the executor would RUN. It printed
            # `<not a predicate: [{...}]>` for a one-element list — the shape the schema
            # asks the model to produce — which made a legible program look malformed at
            # exactly the moment an operator was reading it to decide.
            return f"{word}({_pred(one_check(inner))})"
        parts = ", ".join(_pred(x) for x in (inner if isinstance(inner, list) else []))
        return f"{word}({parts})"
    if spec["operand"] == "sets":
        return f"{shape.upper()}({', '.join(str(x) for x in (p.get('sets') or []))})"
    # The symbol comes from the manifest beside the comparator it belongs to. It used to
    # be a dict here, so a comparator added to the JSON rendered as "?" — the language
    # extended in one place and printed wrong in another.
    used = next((c for c in spec["comparators"] if c in p), None)
    if used is None:
        # NO COMPARATOR IS LEGAL where the manifest says so — `reach` declares
        # comparators_optional, and a bare REACH(...) means "these can reach each other"
        # with the default floor. This printed `REACH(SELECT vm) ? None`, so a perfectly
        # valid statement read as malformed to the one person who has to approve it. The
        # renderer exists so a human can check what the machine understood; garbling a
        # legal program defeats the only thing it is for.
        return f"{shape.upper()}({_select(p.get('select'))})"
    sym = spec["comparators"].get(used, "?")
    return f"{shape.upper()}({_select(p.get('select'))}) {sym} {p.get(used)}"
