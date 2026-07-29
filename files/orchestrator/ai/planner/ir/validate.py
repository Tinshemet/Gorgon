"""
validate.py — is this program WELL-FORMED and GROUNDED?

Three questions are kept separate on purpose, because a run needs to know which failed:

    well-formed  right shape?                        here
    grounded     real tools, real kinds, no dangling refs?   here
    satisfiable  could this hold in ANY world?        here
    meaningful   does it say what the goal meant?     nowhere in code

The last is a human's job, or the ladder's. Answering it would need a second definition
of every goal, which is how a benchmark starts measuring its own grader.

`satisfiable` is separate from `meaningful` and much narrower — it asks only whether a
statement contradicts ITSELF, which needs no knowledge of the goal and no world. Rung 9
is why it exists: the author wrote REACH(SELECT vm WHERE name = 'n1') >= 3 three times.
A name identifies at most one machine, so a floor of three over it cannot hold in any
world that could ever exist — and the world happened to end up right, so the rung checker
said PASS over a program that did not mean its goal. A check that cannot pass is not a
weak check; it is a broken one, and it is exactly the false assurance this system refuses
everywhere else.

Every problem names the statement and what specifically was wrong, because this message
is not a log line — it is fed BACK to the model on a retry, and the design treats a
rejected program as a plan failure routed to revision, not a crash. A vague complaint
wastes the correction.

The rules come from ir/config, never from literals here: required fields per op, known
kinds, predicate shapes and their operands.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from . import config, refs

try:
    from executor.command_catalog import (KNOWN_TOOLS as _KNOWN_TOOLS,
                                          REQUIRED_FIELDS as _REQUIRED_FIELDS)
except ImportError:                                        # pragma: no cover
    _KNOWN_TOOLS, _REQUIRED_FIELDS = frozenset(), {}


def coerce_body(raw: Any) -> Optional[List[Any]]:
    """The statement list out of whatever the model actually handed back, or None.

    Not defensive clutter — it is what this model class DOES. Asked for `body` as an
    array, llama3.1 frequently returns the array SERIALISED:

        {"body": "[{\\"op\\": \\"foreach\\", ...}]"}

    `_first_tool_call` already unwraps a stringified `arguments`; this is the same trick
    one level deeper, on the field. Rejecting it scored three of four perfectly good
    programs as "emitted nothing" before this existed. Fix the reader, not the model.
    """
    if isinstance(raw, dict):
        raw = raw.get("body")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if isinstance(raw, dict):            # a lone statement, not wrapped in a list
        raw = [raw]
    return raw if isinstance(raw, list) and raw else None


def validate(program: Any, known_tools=None, known_names=None,
             bound: Optional[set] = None,
             sets: Optional[set] = None,
             census: Optional[Dict[str, int]] = None) -> Tuple[bool, List[str]]:
    """(ok, problems).

    `bound` is what is already in scope — passed when validating a nested block, so the
    block can see the names its enclosing statements bound. It is a COPY at every level,
    which gives block scoping for nothing: a name grafted inside a loop is not visible
    after it. That is the right rule and it is also the one rung 11 needed, from both
    sides — the body could not see `$item` (reported "never created" for the loop's own
    member), and the statement after the loop could see a per-iteration result it has no
    business reading.

    `known_names` is what the world already contains. Optional, because well-formedness
    must be answerable without a world — but when a caller HAS one, `FROM` can be
    grounded against it, and that is worth having: a program that read the label 'red' as
    a machine to clone from validated cleanly and then made fifteen failing calls.

    `sets` is which of those bound names hold a SET rather than one value. Tracked because
    the two are not interchangeable and the language has exactly one place that cares:
    a filter compares an attribute against ONE value, while `FOREACH ... IN` wants the
    whole set. Rung 9 walked straight into it — `STORE vms = FETCH SELECT vm WHERE ...`
    followed by `ENSURE REACH(SELECT vm WHERE label = '$vms')`. That validated, and then
    `refs.resolve` did exactly what it should (one token and nothing else keeps its type,
    which is what makes `IN $vms` iterate) and handed a LIST to a filter, which tried to
    hash it and took the whole 13-rung run down with a TypeError.
    """
    # `census` is HOW MANY OF EACH KIND THE LAB ALREADY HOLDS — {kind: n}. Distinct from
    # `known_names`, which is a flat list and cannot answer "are there already five vms".
    # Optional, because well-formedness must be answerable without a world; supplied, it
    # is what lets a counted creation be judged against what is already there.
    tools = _KNOWN_TOOLS if known_tools is None else known_tools
    body = coerce_body(program)
    if body is None:
        return False, ["program has no statements"]

    problems: List[str] = []
    # A $reference resolves against PARAMS first, then names bound by `new`. Params are
    # AUTHORED — only the author knows what varies per invocation — where `imports` are
    # DERIVED by the harness. Different provenance, so different halves of the header.
    params = program.get("params") if isinstance(program, dict) else None
    bound = set(bound or ())        # a COPY — see the docstring on scoping
    # Which bound names hold a CALL RESULT. Only those have fields, so only those may
    # carry a dotted path.
    grafted: set = set()
    sets = set(sets or ())          # of those, the ones holding several things
    # Names this program will bring into existence, so a SECOND creation of the same one
    # can be refused. See the duplicate-creation check in the `call` branch.
    created: set = set()
    # var -> the names its `new` mints, so `create_network(net_name: $net2)` is caught as
    # the duplicate it is. Keying only on LITERAL names missed the commoner form: the
    # model refers to the variable it just bound, not to the name behind it.
    created_by_var: Dict[str, List[str]] = {}
    everywhere = _all_bindings(body) | bound
    for name, typ in (params or {}).items():
        if typ not in config.PARAM_TYPES:
            problems.append(f"parameter {name!r}: unknown type {typ!r} "
                            f"(known: {', '.join(sorted(config.PARAM_TYPES))})")
        bound.add(str(name))
    for i, st in enumerate(body):
        where = f"statement {i + 1}"
        if not isinstance(st, dict):
            problems.append(f"{where}: not an object")
            continue
        op = st.get("op")
        spec = config.OPS.get(op)
        if spec is None:
            # A WORD IN THE WRONG PLACE IS NOT AN INVENTED WORD. Listing the legal ops is
            # right when the author made a word up, and actively misleading when it
            # reached for a real part of the language and misplaced it — `else` belongs to
            # the `if` above, and "expected one of new, fetch, call…" sends the author
            # hunting for a different construct. See config's _not_ops_doc.
            hint = config.NOT_OPS.get(op)
            problems.append(f"{where}: unknown op {op!r} — {hint}" if hint else
                            f"{where}: unknown op {op!r} "
                            f"(expected one of {', '.join(config.OPS)})")
            continue
        # A NAME YOU CAN BIND IS A NAME YOU CAN READ — checked once, for every op that
        # binds. `STORE red-net = NEW network` bound a name no reference can pronounce
        # (`$red-net` reads as `$red` plus the literal `-net`), so the next line was told
        # it referred to something "never created" one statement after creating it. Rung
        # 6's paraphrase hit this in three samples out of three. See refs.is_referenceable.
        for field in ("var", "graft"):
            nm = st.get(field)
            if nm is not None and not refs.is_referenceable(str(nm).lstrip(config.SIGIL)):
                problems.append(
                    f"{where}: {field} {nm!r} cannot be referred to — "
                    f"{config.SIGIL}{nm} reads as "
                    f"{config.SIGIL}{str(nm).lstrip(config.SIGIL).split('-')[0]} followed "
                    f"by text, because `-` composes names ({config.SIGIL}item-snap). Use "
                    f"letters, digits and underscores: "
                    f"{str(nm).lstrip(config.SIGIL).replace('-', '_')!r}.")
        for field in spec["required"]:
            if st.get(field) in (None, "", {}):
                problems.append(f"{where}: {op} is missing {field!r}")
        # A field this op does not declare is an ERROR, not something to ignore. Renaming
        # `count` to `amount` showed why: the old spelling was silently dropped and `new`
        # quietly created ONE resource instead of three — a program that looks right,
        # validates, and does a fifth of what it says. Any stale or mistyped field now
        # names itself instead.
        # `one_of` is a list of GROUPS, because an op can hold more than one either/or:
        # a foreach chooses its set (select | in) AND its body (call | do), and the two
        # choices are independent.
        groups = _one_of_groups(spec)
        known = set(spec["fields"]) | {f for g in groups for f in g} | {"op"}
        for extra in sorted(set(st) - known):
            problems.append(f"{where}: {op} has no field {extra!r} "
                            f"(it takes {', '.join(sorted(known - {'op'}))})")
        for alts in groups:
            present = [f for f in alts if st.get(f) not in (None, "", {})]
            if not present:
                problems.append(f"{where}: {op} needs one of "
                                f"{' or '.join(repr(f) for f in alts)}")
            elif len(present) > 1:
                problems.append(f"{where}: {op} says it twice "
                                f"({', '.join(present)}) — use one")

        if op == "new":
            kind = st.get("kind")
            if kind is not None and kind not in config.KINDS:
                problems.append(f"{where}: unknown kind {kind!r} "
                                f"(known: {', '.join(sorted(config.KINDS))})")
            n = st.get("amount", 1)
            if isinstance(n, dict):
                # THE SHORTFALL FORM: {"minus": [5, "$have"]} — create only what is
                # missing. Deliberately the ONLY arithmetic in the language: general
                # expressions are a large addition and this is the one subtraction the
                # top-up pattern needs. `NEW` still means new; only the count is computed.
                gap = n.get("minus")
                if (not isinstance(gap, list) or len(gap) != 2
                        or not isinstance(gap[0], int)):
                    problems.append(f"{where}: amount takes {{'minus': [N, '$have']}} — "
                                    f"a target and what you already have, got {n!r}")
                else:
                    for ref in refs.names(gap[1]):
                        if ref not in bound:
                            problems.append(f"{where}: amount refers to {config.SIGIL}"
                                            f"{ref}, which is never fetched or bound")
            elif isinstance(n, str) and n.startswith(config.SIGIL):
                # "create X vms" — the count is a parameter, resolved at invocation.
                if n[len(config.SIGIL):] not in bound:
                    problems.append(f"{where}: amount {n} is not a declared parameter")
            elif not isinstance(n, int) or n < 0:
                # ZERO IS LEGAL and creates nothing. It has to be: a top-up program run
                # against a world that is already satisfied computes a shortfall of zero,
                # and rejecting that would break the statement exactly when it is most
                # correct — the re-run case this whole shape exists for.
                problems.append(f"{where}: amount must be a non-negative integer or a "
                                f"$parameter, got {n!r}")
            created.update(_minted(st))
            if st.get("var"):
                created_by_var[str(st["var"]).lstrip(config.SIGIL)] = _minted(st)
                bound.add(str(st["var"]).lstrip(config.SIGIL))
                # An amount that is not literally one binds the LIST of what was made —
                # that is what lets `FOREACH ... IN $vms` act on machines before they have
                # an attribute to query by. A `$parameter` or a shortfall counts as
                # several, because neither is known to be one until it runs, and guessing
                # "probably one" is how a set reaches a filter.
                if st.get("amount", 1) != 1:
                    sets.add(str(st["var"]).lstrip(config.SIGIL))
            # The creator's OWN required fields are checked, read from the live catalog.
            # This is the extensibility claim paying off: the manifest names the creator,
            # the catalog declares what it needs, and `new` is validated for any kind
            # with no language code. It also catches a real hole — `NEW vm` was passing
            # only the name, while create_vm requires os_type, so a program that
            # validated could not have built a VM against the real executor.
            src = st.get("from")
            if src is not None:
                creators = config.KINDS.get(kind, {}).get("creators") or {}
                by_copy = next((c for c in creators.values() if c.get("from")), None)
                if by_copy is None:
                    problems.append(f"{where}: {kind} cannot be created by copying "
                                    f"(no creator takes a source)")
                elif not isinstance(src, str) or not src.strip():
                    problems.append(f"{where}: `from` names the resource to copy, got {src!r}")
                elif (known_names is not None and not refs.names(src)
                        and src not in known_names):
                    # A literal source has to EXIST. `NEW vm FROM red` — red being a
                    # label, not a machine — is the mistake worth catching, and it is
                    # only catchable here: `from` is the one field naming something the
                    # program does not create and cannot bind.
                    problems.append(
                        f"{where}: `from` copies an EXISTING {kind} — there is no {kind} "
                        f"named {src!r}. A label is not a source.")
            a = st.get("args")
            if a is not None and not isinstance(a, dict):
                problems.append(f"{where}: args must be an object")
            elif kind in config.KINDS:
                # NEW's ARGS ARE REFERENCE-CHECKED, exactly as a call's are. They were
                # not, and `_check_call` has always done it — so `NEW network(net_name:
                # $blue_net)` with nothing binding `blue_net` validated, the token
                # survived resolution, and the lab ended up holding a network literally
                # named `$blue_net` and machines named `$blues1`. The rung checker passed
                # it, because it inspects shape and not name sanity. Two statements that
                # both take `args` must both check them.
                for k, v in (a or {}).items():
                    for ref in refs.names(v):
                        if ref not in bound:
                            problems.append(
                                f"{where}: {k}={v} refers to {config.SIGIL}{ref}, "
                                f"which is never created")
                creator, supplied = _creator_for(kind, st, with_supplied=True)
                # The executor supplies the key and, when copying, the source — so those
                # are not the author's to pass. Demanding them would make every clone
                # statement carry two arguments the language already knows.
                need = set(_REQUIRED_FIELDS.get(creator) or []) - supplied
                missing = sorted(need - set((a or {}).keys()))
                if missing:
                    # NAME THE STATEMENT THE AUTHOR MUST EDIT, not the tool underneath it.
                    # This said "create_vm also requires 'os_type'", and the model did
                    # exactly what that sentence asks: it added a separate
                    # `create_vm(name: $item, os_type: linux)` call beside the NEW —
                    # creating everything twice — and the repair loop then re-rejected
                    # the untouched NEW twice more and gave up. Rungs 4 and 13 both died
                    # that way in the paraphrase column. The author writes MEDUSA; an
                    # objection phrased in terms of the tool sends them to write a call.
                    shown = ", ".join(f"{m}: ..." for m in missing)
                    problems.append(
                        f"{where}: NEW {kind} also requires "
                        f"{', '.join(repr(m) for m in missing)} — put them in this "
                        f"statement's own arguments, e.g. NEW {kind}({shown}). NEW "
                        f"already calls {creator}; do NOT add a separate {creator} call.")
        elif op == "fetch":
            # A read binds a name the same way a creation does — that is the whole point
            # of it, and the reason it is a statement rather than an expression.
            problems += _check_select(st.get("select") or st.get("count"), where, sets)
            if st.get("var"):
                bound.add(str(st["var"]).lstrip(config.SIGIL))
                # `count` binds a NUMBER, `select` binds the NAMES. The whole distinction
                # between the two forms, and the one that decides whether the result may
                # sit in a filter.
                if st.get("select") is not None:
                    sets.add(str(st["var"]).lstrip(config.SIGIL))

        elif op == "call":
            problems += _check_call(st, where, tools, bound, grafted)
            # CREATING SOMETHING THIS PROGRAM ALREADY CREATED IS ALWAYS WRONG. The model
            # writes `STORE lab = NEW network;` and then `create_network(net_name: lab)` —
            # NEW already calls the creator, so the second one is refused by the world
            # ("Network 'lab' already exists") and, with no ENSURE present, sinks the whole
            # program. Rung 3 died exactly this way under the `terse` mutation, and its
            # recovery was worse than the fault: revision 2 wrote `delete_vm(web)` followed
            # by `NEW vm FROM web`, cloning a machine it had just deleted, and the rung
            # ended with zero VMs.
            #
            # It was never diagnosed because the objection that says "NEW already calls
            # create_vm" only fires when a REQUIRED ARGUMENT is missing. Here the NEW was
            # perfectly valid, so nothing was said at all.
            made = _creator_tools().get(st.get("tool"))
            if made:
                kind, key = made
                nm = (st.get("args") or {}).get(key)
                # A reference to a var a `new` bound names what that `new` created.
                ref = refs.names(nm)[0] if isinstance(nm, str) and refs.is_reference(nm) \
                    and refs.names(nm) else None
                if ref and ref in created_by_var:
                    problems.append(
                        f"{where}: {st['tool']} creates {kind} {config.SIGIL}{ref}, which "
                        f"`new` already created — `new` calls the creator itself, so a "
                        f"separate call makes it twice and the second is refused. Drop "
                        f"this statement, or drop the `new`.")
                elif isinstance(nm, str) and nm and not refs.names(nm):
                    if nm in created:
                        problems.append(
                            f"{where}: {st['tool']} creates {kind} {nm!r}, which this "
                            f"program already creates — `new` calls the creator itself, so "
                            f"a separate call makes it twice and the second is refused. "
                            f"Drop this statement, or drop the `new`.")
                    created.add(nm)
        elif op == "foreach":
            if st.get("select") is not None:
                problems += _check_select(st.get("select"), where, sets)
                problems += _check_cardinality(st, where)
            src = st.get("in")
            if isinstance(src, list):
                # A literal set — the members are named outright. This is what a
                # CORRECTION needs: it acts on specific things the previous attempt left
                # behind, which no query describes and no earlier statement bound.
                bad = [x for x in src if not isinstance(x, str) or not x.strip()]
                if bad or not src:
                    problems.append(f"{where}: foreach `in` list must be non-empty names, "
                                    f"got {src!r}")
                # A SET WRAPPED IN A LIST IS NOT A LIST OF NAMES. `IN [$vms]` is one
                # element that happens to BE the whole set, so `$item` binds to the list
                # rather than to a member, and the first tool argument it reaches gets a
                # list where a name belongs. That is not a rejected call — it is a
                # TypeError out of the executor, which took a whole benchmark column with
                # it twice: `add_vm_to_network(vm_name: $item)` with $item = ['vm1', ...].
                #
                # The author is one bracket from correct, so the message says which
                # bracket. `IN $vms` iterates the set; `IN [$vms]` iterates a list of one.
                for x in src:
                    if isinstance(x, str) and any(n in sets for n in refs.names(x)):
                        problems.append(
                            f"{where}: foreach in [{x}] wraps a SET in a list, so $item "
                            f"binds to the whole set instead of a member. Drop the "
                            f"brackets: `in {x}`.")
            elif isinstance(src, str) and src.startswith(config.SIGIL):
                if src[len(config.SIGIL):] not in bound:
                    problems.append(f"{where}: foreach in {src} refers to something "
                                    f"never created")
            elif src is not None:
                problems.append(f"{where}: foreach `in` must be a ${'{'}name{'}'} "
                                f"reference or a list of names, got {src!r}")
            inner = st.get("call")
            if inner is not None and not isinstance(inner, dict):
                problems.append(f"{where}: foreach call must be an object")
            elif isinstance(inner, dict):
                # the loop binds its member, so it is in scope inside the body
                problems += _check_call(inner, f"{where} (foreach body)", tools,
                                        bound | {config.LOOP_VAR}, grafted)
            block = st.get("do")
            if block is not None:
                if not isinstance(block, list) or not block:
                    problems.append(f"{where}: `do` is a list of statements, got {block!r}")
                elif any(k.get("op") == "foreach" for k in _walk_stmts(block)):
                    # A LOOP INSIDE A LOOP REBINDS THE ONLY MEMBER NAME THERE IS. The
                    # language has one loop variable, so the inner `$item` shadows the
                    # outer and the outer member becomes unreachable for the rest of the
                    # body — which means the nesting cannot express anything the inner
                    # loop alone does not, while multiplying the work by the size of the
                    # outer set. Rungs 4 and 13 both wrote `FOREACH $item IN SELECT vm {
                    # FOREACH $item IN $vms { guest_ping } }` and issued 50 pings for 5
                    # machines, 66 calls in total. Rejected rather than silently run,
                    # because it validates, executes, and is never what anyone meant.
                    # NAME THE CONSTRUCT THAT DOES EXPRESS IT. The first version of this
                    # said "keep the inner loop and drop the outer, or put the two loops
                    # one after the other" — and neither is the fix when what the author
                    # actually wants is to relate every member to every OTHER member.
                    # Rung 4 wrote a pairwise loop for "make sure they all ping each
                    # other" and got a remedy that does not apply. Medusa has no pairwise
                    # iteration; a relation over a whole set is a PREDICATE, which is
                    # what REACH is for. That is a fact about the language, not about any
                    # one goal.
                    problems.append(
                        f"{where}: a foreach inside a foreach rebinds "
                        f"{config.SIGIL}{config.LOOP_VAR}, so the outer member is lost — "
                        f"the language has one loop variable. If you are relating every "
                        f"member to every OTHER member, that is a CHECK over the whole "
                        f"set, not nested loops — state it as one predicate (e.g. REACH "
                        f"over the set). Otherwise keep the inner loop and drop the "
                        f"outer, or put the two loops one after the other.")
                else:
                    _, sub = validate({"body": block}, tools, known_names,
                                      bound | {config.LOOP_VAR}, sets)
                    problems += [f"{where} (foreach body) → {x}" for x in sub]
        if op == "new" and census and st.get("amount") is not None and not st.get("from"):
            # NEW IS FOR WHAT DOES NOT EXIST YET. The operator's order: create only when
            # asked to create or when the thing is not there; otherwise FETCH, and fall
            # back to creating only if the fetch comes back empty.
            #
            # THE MOST EXPENSIVE DEFECT IN THE LADDER. Shown a lab holding five labelled
            # machines and asked to use five, the author writes `NEW AMOUNT(5)` and ends
            # with ten — it reads CURRENT STATE as background rather than as input. The
            # prompt has said "read first, then act on the difference" under `fetch` since
            # the op existed and it does not land there, so the objection is raised HERE,
            # at the statement, and names the count.
            #
            # NARROW BY CONSTRUCTION: only a COUNTED creation (`amount`), only of a kind
            # the lab already holds, and never a copy (`from` names an existing resource,
            # so copying one is exactly the case where creation IS the request). A named
            # single creation is already covered by the duplicate-creation rule.
            have = census.get(st.get("kind"), 0)
            reads = any(k.get("op") == "fetch" for k in body[:i]
                        if isinstance(k, dict))
            if have and not reads:
                problems.append(
                    f"{where}: the lab already holds {have} {st.get('kind')}(s) — "
                    f"AMOUNT makes {have} MORE, not {have} in total. FETCH first and "
                    f"create the difference, or state the end state with ACHIEVE COUNT.")
        elif op in ("ensure", "achieve"):
            problems += _check_predicate(st.get("predicate"), where, bound, everywhere, sets)
        elif op == "if":
            problems += _check_predicate(st.get("cond"), where, bound, everywhere, sets)
            for branch in ("then", "else"):
                kids = st.get(branch)
                if kids is None:
                    continue
                if not isinstance(kids, list) or not kids:
                    # AN EMPTY `then` IS AN UNSTATED INVERSION, and saying only "got []"
                    # is what let the repair loop guess. Measured on rung 11: the draft
                    # was `then: []` with the real work in an `else`, the repair folded
                    # that work up into `then` and left `cond` alone, and a correct intent
                    # became a program that stopped the machines that DID answer. Naming
                    # the identity gives the repair one obvious move instead of two, and
                    # it is an identity rather than a rule so it can be re-derived.
                    # ONE REASONING ERROR, THREE FORMS — and the objection has to correct
                    # the REASONING, not edit the symptom. The author enumerates outcomes:
                    # it asks "what happens when true? when false?" and reserves a slot for
                    # each, then leaves one empty because nothing goes there. Measured on
                    # rung 11, in three spellings of the identical thought:
                    #
                    #   then:[] + {"op":"else"} sibling     the original draft
                    #   then:[] + else:[Y]                  the shape the schema offers
                    #   IF X {} ; IF NOT(X) {Y}             after being taught to invert
                    #
                    # All three reduce to IF NOT(X) {Y}. Earlier wording here told the
                    # author to move the body, or to delete the statement — both are EDITS,
                    # and an edit answers the form rather than the habit, so the habit came
                    # back wearing the next form. Worse, "invert it" with no body to move
                    # got cargo-culted into `IF NOT(IS($answer.alive) = false) { }`.
                    #
                    # So the message states the principle: a check and its opposite are ONE
                    # decision, and only the acting side is ever written. An outcome with
                    # nothing to do does not need an empty statement, it needs no statement.
                    if branch == "then" and isinstance(kids, list):
                        work = st.get("else")
                        head = (f"{where}: `then` is empty. A check and its opposite are "
                                f"ONE decision, not two outcomes to fill in — nothing owes "
                                f"every case a statement. Write only the side that ACTS.")
                        if isinstance(work, list) and work:
                            problems.append(
                                f"{head} The work is sitting in `else`, so the condition "
                                f"you actually mean is its opposite: state that one and "
                                f"put the work in `then`, with no `else` at all. "
                                f"IF X THEN {{}} ELSE {{Y}} and IF NOT(X) THEN {{Y}} are "
                                f"the same program; only the second says what it means. "
                                f"Where cond is IS(...), setting eq to false says it more "
                                f"directly than wrapping it in NOT.")
                        else:
                            # NAME THE OTHER HALF WHEN IT IS VISIBLE. Generic advice here
                            # reads as "you forgot to fill this in", which is the very
                            # habit being corrected — and the author has usually already
                            # written the real decision one line away.
                            twin = _negated_sibling(st, body, i)
                            problems.append(
                                f"{head} Statement {twin} already checks the opposite and "
                                f"does the work — that statement IS the decision, whole. "
                                f"This one is not its other half; there is no other half "
                                f"to write."
                                if twin else
                                f"{head} Nothing acts here in either direction, so there "
                                f"is no decision being made. Either the work belongs in "
                                f"`then` under a condition you have not stated yet, or "
                                f"this statement should not exist.")
                    else:
                        problems.append(
                            f"{where}: `{branch}` is a list of statements, got {kids!r}"
                            + (" — an else that runs nothing is not a branch; drop the key."
                               if branch == "else" and isinstance(kids, list) else ""))
                else:
                    ok2, sub = validate({"body": kids}, tools, known_names, bound, sets)
                    problems += [f"{where} ({branch}) → {x}" for x in sub]
        # A grafted name is in scope from here on, and IFAILS carries statements wherever
        # it appears — both checked once, for every acting op, rather than per branch.
        if st.get("graft"):
            bound.add(str(st["graft"]).lstrip(config.SIGIL))
            grafted.add(str(st["graft"]).lstrip(config.SIGIL))
        recov = st.get("ifails")
        if recov is not None:
            if not isinstance(recov, list) or not recov:
                problems.append(f"{where}: `ifails` is a list of statements, got {recov!r}")
            else:
                _, sub = validate({"body": recov}, tools, known_names, bound, sets)
                problems += [f"{where} (ifails) → {x}" for x in sub]
    # THERE IS NO ACHIEVE-ORDERING CHECK, and its absence is the rule.
    #
    # Two used to live here: one ACHIEVE per program, and nothing may act after it. Both
    # came from reading ACHIEVE as "the goal, certified at the end". The operator's
    # correction is that it is not that at all — ENSURE asks "do you exist", ACHIEVE says
    # "MAKE SURE you exist", and once it is a MAKE rather than a CHECK you want it wherever
    # something has to be true before the rest of the program can work. A network must
    # exist before anything attaches to it; that is an ACHIEVE at statement 1 with all the
    # work after it, and it was rejected.
    #
    # "Nothing may act after achieve" was, in the operator's words, wishful thinking that
    # is not based in what we are seeing, and "one per program" was philosophically a wash:
    # if ACHIEVE means make-sure-of-this, a program can need several.
    #
    # THE RUNTIME ALREADY DOES THE RIGHT THING and always did — execute.py checks each
    # ACHIEVE in order and returns on the first failure, which IS the barrier: the run
    # cannot pass this point unless the thing is true. Only the validator forbade it. So
    # this is a restriction being removed, not a feature being added.
    problems += _check_precondition_is_not_the_goal(body)
    return (not problems), problems


def _creator_for(kind: str, st: Dict[str, Any], with_supplied: bool = False):
    """Which tool creates this resource — chosen by whether `from` is present.

    A kind may be made more than one way (a machine built fresh, or cloned). Selecting
    between them by the presence of a field rather than a keyword keeps the choice out of
    the language: adding a third way to create something stays a manifest row.
    """
    spec = config.KINDS.get(kind) or {}
    creators = spec.get("creators") or {}
    chosen, supplied = None, {spec.get("key")}
    if st.get("from"):
        chosen = next((c for c in creators.values() if c.get("from")), None)
    if chosen is None:
        chosen = creators.get("create") or {"tool": spec.get("create")}
    if chosen.get("key"):
        supplied.add(chosen["key"])
    if chosen.get("from"):
        supplied.add(chosen["from"])
    tool = chosen.get("tool") or spec.get("create")
    return (tool, {x for x in supplied if x}) if with_supplied else tool


def _one_of_groups(spec: Dict[str, Any]) -> List[List[str]]:
    """An op's either/or groups, normalised.

    Accepts the old flat form (`["select", "in"]`) as a single group so a manifest
    written either way means the same thing — this is the shape the schema generator
    reads too, and the two must not disagree about it.
    """
    alts = spec.get("one_of") or []
    if alts and isinstance(alts[0], str):
        return [list(alts)]
    return [list(g) for g in alts]


def _all_bindings(body: Any) -> set:
    """Every name the program binds ANYWHERE, nested blocks included.

    Used only to tell two diagnoses apart: a name bound in a scope that has closed
    (a loop-local result read after the loop) versus a name that is never bound at all.
    They are different mistakes with different fixes, and saying the wrong one sends the
    author to the wrong place.
    """
    out: set = set()
    for st in body or []:
        if not isinstance(st, dict):
            continue
        for field in ("var", "graft"):
            v = st.get(field)
            if isinstance(v, str) and v:
                out.add(v.lstrip(config.SIGIL))
        for field in ("do", "then", "else", "ifails"):
            kids = st.get(field)
            if isinstance(kids, list):
                out |= _all_bindings(kids)
        inner = st.get("call")
        if isinstance(inner, dict):
            out |= _all_bindings([inner])
    return out


def _check_cardinality(st, where: str) -> List[str]:
    """A FOREACH over a select that can only ever match ONE object.

    The operator's group argument, 2026-07-29, and it is the rule rung 8 breaks: singular,
    `any` and `all` are three sets, and how you ACT follows from which you hold. A key
    filter is singular BY CONSTRUCTION — `name = 'db'` can never match two — so it wants a
    plain call naming it, not a loop. And the test is construction, never today's count:
    *"a label that is filtered might only be singling out one object now but it's
    technically a set with currently 1 member."* So `label = 'prod'` stays a set and keeps
    its loop even on a day it matches one machine.

    THIS IS THE OTHER HALF OF rung 8's DEFECT. Statement 4 is `FOREACH $item IN SELECT ?
    WHERE name = 'db'` — a loop over one object, which is what let the missing `kind` exist
    at all. Named here, the author is told the thing that is actually wrong instead of
    `select must name a kind`, which is a symptom and sent two repair rounds to the wrong
    place.

    ADVISORY BY DESIGN — it appends an objection, it does not rewrite. Turning the loop into
    a call would change what the program SAYS, which is the line the sanitiser refuses to
    cross for exactly this reason.
    """
    from . import master
    sel = st.get("select")
    if not isinstance(sel, dict):
        return []
    if master.cardinality_of(sel) != "singular":
        return []
    kind = sel.get("kind")
    key = (config.KINDS.get(kind) or {}).get("key") or "name"
    return [f"{where}: this selects ONE {kind} by its {key}, so a loop over it is a loop of "
            f"one — write the action as a single call naming it instead of a foreach"]


# Ops that change the world — the same set consent.py counts, for the same reason.
_ACTS = {"new", "call", "foreach"}


def _check_select(sel: Any, where: str, sets: Optional[set] = None) -> List[str]:
    """A select names a known kind and filters on attributes that kind declares."""
    if sel is None:
        return []
    if not isinstance(sel, dict):
        return [f"{where}: select must be an object"]
    kind = sel.get("kind")
    if kind and kind not in config.KINDS:
        return [f"{where}: selects unknown kind {kind!r} "
                f"(known: {', '.join(sorted(config.KINDS))})"]
    if not kind:
        return [f"{where}: select must name a kind"]
    spec = config.KINDS[kind]
    # `config.queryable`, not `spec["attrs"]`. Registry attributes and OBSERVED ones (read
    # from the findings ledger — see the manifest's _observed_doc) are equally legal in a
    # WHERE, and asking one place means a manifest row cannot be accepted here while being
    # withheld from the schema the author actually sees.
    legal = config.queryable(kind)
    # `not` holds another set of filters — the carve-out. Checked with the same rules, so
    # an excluded attribute is validated exactly like an included one.
    out = []
    if "not" in sel:
        if not isinstance(sel["not"], dict) or not sel["not"]:
            out.append(f"{where}: `not` takes the filters to EXCLUDE, e.g. {{'name':'db'}}")
        # NOT OVER AN UNFILTERED WHOLE IS THE EMPTY SET. The operator's group argument,
        # 2026-07-29: a filter is definitionally subtractive, so it can only ever produce
        # `any` or a key-identified singular — never `all`. Which makes `NOT all` "none",
        # and a statement that can do no work should not validate. Detectable here and
        # nowhere else: it runs cleanly, loops zero times and reports success, which is the
        # exact shape `status = 'not running'` had (matched nobody, ran zero calls, said
        # ok) and the shape `disjoint` had for weeks. Silence is the failure mode.
        elif set(sel["not"]) == {"kind"} or sel["not"].get("kind") and len(sel["not"]) == 1:
            out.append(f"{where}: excluding a whole KIND leaves nothing — "
                       f"`not` names the members to leave out, not the kind itself")
        else:
            out += _check_select({"kind": kind, **sel["not"]}, where, sets)
    # GROUPS: `any` is OR, `all` an explicit AND. Each branch is a filter set in its own
    # right, checked by the same rules at every depth, so a group cannot smuggle in an
    # attribute the flat form would reject. Same words the predicate combinators use, on
    # purpose: one concept with two vocabularies is what this language exists to delete.
    for group in ("any", "all"):
        if group not in sel:
            continue
        kids = sel[group]
        if not isinstance(kids, list) or len(kids) < 2:
            out.append(f"{where}: `{group}` takes two or more filter sets, got {kids!r}")
            continue
        for kid in kids:
            if not isinstance(kid, dict) or not kid:
                out.append(f"{where}: each `{group}` branch is a filter set, got {kid!r}")
            else:
                out += _check_select({"kind": kind, **kid}, where, sets)
    # AN ATTRIBUTE WITH A CLOSED VOCABULARY IS POLICED AGAINST IT. `status` is running or
    # stopped; `alive` is true, false or unknown. Offered as bare strings, both were
    # invented: rung 5 wrote `status = 'not running'`, which matches nobody, ran zero
    # calls and reported ok — a program that looks right, validates, and does nothing.
    # `values_for` answers for registry and observed attributes alike, so this check does
    # not have to know which sort it is holding.
    for attr, val in sel.items():
        if attr in ("kind", "not", "any", "all"):
            continue
        legal_values = config.values_for(kind, attr)
        if legal_values is None or isinstance(val, dict):
            continue                       # open text — a name, a label
        if refs.names(val if isinstance(val, str) else ""):
            continue                       # a $reference resolves at run time
        if str(val).lower() not in legal_values:
            spec_obs = config.observed(kind).get(config.canonical(kind, attr))
            hint = ""
            if spec_obs:
                hint = (f" '{config.OBSERVED_UNKNOWN}' means nothing has asked yet; "
                        f"{spec_obs.get('by', 'a probe')} is what learns it.")
            out.append(f"{where}: {attr} is {' or '.join(legal_values)}, "
                       f"got {val!r}.{hint}")
    # A FILTER COMPARES ONE VALUE. Rung 9 is the case: `STORE vms = FETCH SELECT ...`
    # binds the NAMES, and the next line wrote `SELECT vm WHERE label = '$vms'`. Nothing
    # rejected it, `refs.resolve` correctly kept the list type — that is what makes
    # `FOREACH ... IN $vms` iterate rather than walk a string — and a list arrived at
    # `f["label"] not in {...}`, which cannot hash it. The run died with a TypeError at
    # rung 9 and took rungs 10-13 with it.
    #
    # Both halves are worth naming separately, because they are different mistakes: a
    # LITERAL list means the author wanted several members and reached for the only
    # syntax they had; a REFERENCE to a set means they had the set and put it in the
    # wrong position. The fix differs, so the message does.
    for attr, val in sel.items():
        if attr in ("kind", "not", "any", "all"):
            continue
        # MEMBERSHIP: {attr: {"in": [...]}} or {"in": "$set"} — the attribute is ANY of
        # these. A literal list names members outright, which is what rung 9's "n1, n2 and
        # n3" needed and what only `foreach` could say before; a bound set makes "the five
        # I just created" checkable by a predicate.
        if isinstance(val, dict) and "in" in val:
            members = val["in"]
            if isinstance(members, str):
                if not refs.is_reference(members):
                    out.append(f"{where}: {attr} IN expects a list of values or a "
                               f"{config.SIGIL}set, got {members!r}")
                elif sets and refs.names(members) and refs.names(members)[0] not in sets:
                    out.append(f"{where}: {attr} IN {members} — that name does not hold a "
                               f"set. Bind one with `fetch ... select`, or list the "
                               f"values outright.")
            elif not isinstance(members, list) or not members:
                out.append(f"{where}: {attr} IN takes a non-empty list of values, "
                           f"got {members!r}")
            elif [m for m in members if not isinstance(m, (str, int, bool))]:
                out.append(f"{where}: {attr} IN takes plain values, got "
                           f"{[m for m in members if not isinstance(m, (str, int, bool))][0]!r}")
            continue
        if isinstance(val, (list, dict, set, tuple)):
            out.append(f"{where}: {attr} compares against ONE value, got {val!r}. "
                       f"To name several, say MEMBERSHIP: "
                       f"{{'{attr}': {{'in': [...]}}}} — written "
                       f"INCLUDE {attr} = [a, b, c].")
            continue
        if sets:
            for ref in refs.names(val if isinstance(val, str) else ""):
                if ref in sets:
                    out.append(
                        f"{where}: {attr} = {config.SIGIL}{ref} puts a SET where one "
                        f"value belongs — {config.SIGIL}{ref} holds the members, not an "
                        f"attribute they share. Say MEMBERSHIP instead: "
                        f"{{'{attr}': {{'in': '{config.SIGIL}{ref}'}}}}, written "
                        f"INCLUDE {attr} = {config.SIGIL}{ref}.")
    unknown = [k for k in sel
               if k not in ("kind", "not", "any", "all") and k not in legal]
    # Aliases are accepted, not just tolerated: the harness has its own synonyms (`tag`
    # for a label, `os` for os_type) and a program written either way means the same
    # thing. Rejecting one spelling of one concept is the vocabulary problem in miniature.
    return out + [f"{where}: {kind} has no attribute {k!r} "
                  f"(queryable: {', '.join(sorted(legal))})" for k in unknown]


def _check_call(st: Dict[str, Any], where: str, tools, bound,
                grafted: Optional[set] = None) -> List[str]:
    """A call names a REAL tool, carries args, and references only what exists.

    `args` is checked here rather than left to the per-op required-field pass so it
    applies inside a `foreach` too: the first valid-looking program the model produced
    was a foreach calling `launch_vm()` with no arguments — it validated, and would have
    failed at execution against a tool that needs a name.
    """
    out = []
    tool = st.get("tool")
    if tool and tools and tool not in tools:
        out.append(f"{where}: no such tool {tool!r}")
    if not st.get("args"):
        out.append(f"{where}: call to {tool or '?'} has no args")
    # A call's REQUIRED arguments, read off the live catalog — the same check `new`
    # already got, and its absence here was an inconsistency: rung 12 emitted
    # snapshot_create without snap_name, validated, and both calls were rejected by the
    # world. Catching it before execution beats discovering it after.
    for miss in sorted(set(_REQUIRED_FIELDS.get(tool) or []) - set(st.get("args") or {})):
        out.append(f"{where}: {tool} requires {miss!r}")
    args = st.get("args")
    if args is not None and not isinstance(args, dict):
        return out + [f"{where}: args must be an object"]
    for k, v in (args or {}).items():
        # Every name the argument mentions, not just a whole-string one: `$item-snap`
        # refers to `item`, and rejecting it as a reference to `item-snap` blamed the
        # author for the language's missing composition.
        for ref in refs.names(v):
            if ref not in bound:
                out.append(f"{where}: {k}={v} refers to {config.SIGIL}{ref}, "
                           f"which is never created")
            elif grafted is not None and ref not in grafted and _dotted(v, ref):
                # A DOTTED PATH ONLY MEANS SOMETHING ON A CALL'S RESULT. Everything else
                # a program binds is a NAME (a string) or a set of them, and a string has
                # no fields. The model wrote `add_vm_to_network(net_name:
                # $item.networks[0], ...)`, inventing array indexing; `item` IS in scope,
                # so nothing objected, `resolve` left the token standing as written (it
                # does that on purpose, so a ledger row stays debuggable), and the literal
                # text `$item.networks[0]` was handed to the tool as a network name.
                out.append(f"{where}: {k}={v} reads a field off "
                           f"{config.SIGIL}{ref}, which is a NAME, not a call's result — "
                           f"only something bound by `graft` has fields. Select what you "
                           f"need instead, or graft the call whose answer you mean.")
    return out


def _check_precondition_is_not_the_goal(body: Any) -> List[str]:
    """An opening ENSURE that IS the goal makes the program's own work unreachable.

    ENSURE is a ground check, true where it is written, and a failed one STOPS the
    program — decision 3, and the reason it opens a procedure as a precondition
    ("checking your socks before you put on your shoes"). Assert the GOAL there and the
    shoes never go on:

        ENSURE COUNT(SELECT vm WHERE label = 'prod') = 3;   <- the goal, before any work
        FOREACH $item IN [four, one, three] { add_label(...); }
        ENSURE COUNT(SELECT vm WHERE label = 'prod') = 3;
            -> ran 0 calls

    Rungs 7 and 9 both did exactly this, and the model was arguably following
    instructions: intent.instruction(ACHIEVE) says "open with ENSURE if something must
    already be true", and the prompt says a ground check is used FIRST. It put the right
    shape around the wrong predicate.

    Detected, not guessed: the SAME predicate appears again later as a verdict, with
    acting statements in between. That is unambiguous — a check identical to the one that
    certifies the work cannot also be a precondition FOR the work.
    """
    stmts = [st for st in (body or []) if isinstance(st, dict)]
    out: List[str] = []
    for i, st in enumerate(stmts):
        if st.get("op") != "ensure":
            continue
        pred = st.get("predicate")
        for j in range(i + 1, len(stmts)):
            later = stmts[j]
            if later.get("op") not in ("ensure", "achieve"):
                continue
            if later.get("predicate") != pred:
                continue
            if not any(stmts[k].get("op") in _ACTS for k in range(i + 1, j)):
                continue
            out.append(
                f"statement {i + 1}: this ENSURE is the same check as statement {j + 1}, "
                f"with work in between — a ground check STOPS the program when it fails, "
                f"so asserting the goal before the work means the work never runs. Drop "
                f"this one and keep the check at the end, or open with a precondition the "
                f"work actually needs (that the thing you are about to change EXISTS).")
            break
    return out


def _creator_tools() -> Dict[str, tuple]:
    """Every tool that CREATES something -> (kind, the argument carrying its name).

    Read off the resource manifest, so a kind added there is covered here with no edit —
    the same extensibility rule the rest of the language follows.
    """
    out: Dict[str, tuple] = {}
    for kind, spec in config.KINDS.items():
        key = spec.get("key")
        for creator in (spec.get("creators") or {}).values():
            tool = creator.get("tool")
            if tool:
                out[tool] = (kind, creator.get("key") or key)
        if spec.get("create"):
            out.setdefault(spec["create"], (kind, key))
    return out


def _minted(st: Dict[str, Any]) -> List[str]:
    """The names a `new` statement will bring into existence.

    Mirrors execute._mint: the author's own key argument wins when they supplied one,
    otherwise the variable name; several resources suffix it. Kept in step with the
    visitor deliberately — this predicts what that code will do, and a prediction that
    drifts is worse than none.
    """
    kind = st.get("kind")
    spec = config.KINDS.get(kind) or {}
    creators = spec.get("creators") or {}
    chosen = (next((c for c in creators.values() if c.get("from")), None)
              if st.get("from") else None) or creators.get("create") or {}
    key = chosen.get("key") or spec.get("key")
    supplied = (st.get("args") or {}).get(key)
    base = (supplied if isinstance(supplied, str) and supplied.strip()
            and not refs.names(supplied) else st.get("var"))
    if not isinstance(base, str) or not base:
        return []
    n = st.get("amount", 1)
    if not isinstance(n, int) or n < 1:
        return [base]                      # a $parameter or a shortfall: predict the base
    return [base] if n == 1 else [f"{base}{i + 1}" for i in range(n)]


def _walk_stmts(body: Any) -> List[Dict[str, Any]]:
    """Every statement under `body`, nested blocks included.

    A shallow scan of a loop's direct children is not enough and rung 13 proved it: the
    inner `foreach` sat inside an `if` inside the body, slipped the nesting check, and ran
    23 calls. Anything asking "does this block CONTAIN X" has to descend.
    """
    out: List[Dict[str, Any]] = []
    for st in body or []:
        if not isinstance(st, dict):
            continue
        out.append(st)
        for field in ("do", "then", "else", "ifails"):
            kids = st.get(field)
            if isinstance(kids, list):
                out += _walk_stmts(kids)
    return out


def one_check(value: Any) -> Any:
    """The single predicate an arity-one combinator wraps — `NOT(x)`'s x.

    Accepts a ONE-ELEMENT LIST as well as a bare object, and the reason is that three
    parts of this system disagreed about which it was. The manifest says `not` takes one
    check; the SCHEMA offered `of` as an array for every non-value arity, so constrained
    decoding produced `[{...}]` exactly as instructed; the executor coerced a list and ran
    it fine; and only the validator refused. Rung 8 and rung 5 both died there, on
    programs that were correct in every other respect and that the runtime would have
    executed.

    Shared by the validator and the renderer rather than written twice, because they were
    already answering the same question differently — the renderer printed
    `<not a predicate: [...]>` for the shape the executor accepts. Fix the reader, not the
    model: the same argument `coerce_body` makes one level up.
    """
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]
    return value


def _dotted(value: Any, root: str) -> bool:
    """Does `value` reach into `root` with a dotted path — `$item.networks`?"""
    return isinstance(value, str) and f"{config.SIGIL}{root}." in value


def _at_most_one(sel: Any) -> bool:
    """Does this select match at most one member, whatever the world contains?

    True when it pins the kind's KEY to a literal — `name` for a vm, `net_name` for a
    network. A `$reference` does not count: it may resolve to a whole set.

    THE LOOP VARIABLE IS THE EXCEPTION, and it is not a special case so much as the
    definition of `foreach`: `$item` is ONE member of the set being walked, always. Rung 9
    wrote `ENSURE REACH(SELECT vm WHERE name = '$item') >= 2` inside a loop — asking
    whether one machine can reach two, which cannot hold in any world — and the check that
    already refuses exactly this shape for a literal name declined to look, because a
    reference "might be a set". It never can be here. The program aborted on its first
    iteration after a single call, and the rung was scored as a planning failure.
    """
    if not isinstance(sel, dict):
        return False
    key = (config.KINDS.get(sel.get("kind")) or {}).get("key")
    val = sel.get(key) if key else None
    if not isinstance(val, str) or not val:
        return False
    named = refs.names(val)
    if not named:
        return True                        # a literal name
    return named == [config.LOOP_VAR] and val == f"{config.SIGIL}{config.LOOP_VAR}"


def _opposite(a: Any, b: Any) -> bool:
    """Do these two checks test a thing and its negation?

    Deliberately NARROW. It answers only the two spellings the author actually produces —
    `NOT(p)` against `p`, and `IS(x) = true` against `IS(x) = false` — because this is used
    to make an objection MORE specific, and an objection that names the wrong statement is
    worse than one that names none. General predicate negation is not decidable here
    anyway: two selects can be complements without saying so.
    """
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return False
    for x, y in ((a, b), (b, a)):
        if x.get("shape") == "not" and one_check(x.get("of")) == y:
            return True
    if a.get("shape") == b.get("shape") == "is" and a.get("of") == b.get("of"):
        av, bv = a.get("eq"), b.get("eq")
        if isinstance(av, bool) and isinstance(bv, bool):
            return av is not bv
    return False


def _negated_sibling(st: Dict[str, Any], body: List[Any], i: int) -> Optional[str]:
    """"statement N", if another IF in this block tests the opposite AND does the work.

    The point is not to find a duplicate — it is to be able to say WHICH statement is the
    real decision, so the author is told its empty twin was never needed rather than told
    to fill something in. Only a sibling that ACTS counts: two empty ifs are not a
    decision written in the wrong place, they are two statements saying nothing.
    """
    for j, other in enumerate(body):
        if j == i or not isinstance(other, dict) or other.get("op") != "if":
            continue
        if other.get("then") and _opposite(st.get("cond"), other.get("cond")):
            return f"{j + 1}"
    return None


def _check_predicate(pred: Any, where: str, bound: Optional[set] = None,
                     elsewhere: Optional[set] = None,
                     sets: Optional[set] = None) -> List[str]:
    """A predicate names its `shape` and supplies that shape's operand."""
    if pred is None:
        return []
    if not isinstance(pred, dict):
        return [f"{where}: predicate must be an object"]
    shape = pred.get("shape")
    spec = config.PREDICATES.get(shape)
    if spec is None:
        return [f"{where}: predicate shape must be one of "
                f"{', '.join(config.PREDICATES)}, got {shape!r}"]
    out, operand = [], spec["operand"]
    value = pred.get(operand)
    if spec.get("arity") == "value":
        # IS($answer.reachable) = false — reads a grafted result, not the world.
        if not isinstance(value, str) or not value.startswith(config.SIGIL):
            return [f"{where}: {shape} reads a grafted value, e.g. "
                    f"{config.SIGIL}answer.reachable — got {value!r}"]
        if not (set(pred) & set(spec["comparators"])):
            return [f"{where}: {shape} needs "
                    f"{'/'.join(spec['comparators'])} to compare against"]
        # `IS` READS A CALL'S RESULT, and the loop member is not one. `$item` is the
        # member's NAME — a plain string — so `IS($item.name) = 'db'` reaches for a field
        # on a string, resolves to nothing, and is false for every member in every world.
        # Rung 8 wrote exactly that: `NOT(IS($item.name) = 'db')` was therefore true for
        # everything, db went onto `core` with the rest, six calls ran, no error was
        # raised and the program reported ok. It validated because `item` IS in scope —
        # which is the wrong question to ask about it.
        if refs.names(value) == [config.LOOP_VAR]:
            return [f"{where}: {shape} reads what a CALL returned, and "
                    f"{config.SIGIL}{config.LOOP_VAR} is the member's name, not a result "
                    f"— reading a field off it is always empty. To treat one member "
                    f"differently, filter the SET instead: `select` takes "
                    f"`name = '...'`, and a carve-out excludes one "
                    f"(EXCEPT name = '...')."]
        # And the name it reads has to BE in scope. Predicates were the one place a
        # reference went unchecked, which mattered the moment loops got block scoping:
        # a result grafted inside a loop is gone after it, so `ENSURE IS($answers.alive)`
        # following the loop reads nothing. It validated silently — the exact shape of
        # someone reaching for "collect every answer, then check them", which is a
        # feature the language does not have. Better to say so than to pass.
        if bound is not None:
            for ref in refs.names(value):
                if ref not in bound:
                    # Say WHICH mistake it is. Blaming loop scoping unconditionally was
                    # wrong for rung 13, where the call had no `graft` at all — the model
                    # simply never bound the name, and was told it had bound it in the
                    # wrong place. A diagnosis that names the wrong cause costs a repair
                    # round and teaches the wrong lesson.
                    hint = ("a result grafted inside a loop does not outlive it"
                            if ref in (elsewhere or ()) else
                            f"nothing binds it — add graft: {ref!r} to the call whose "
                            f"answer you mean")
                    return [f"{where}: {shape} reads {config.SIGIL}{ref}, which is not in "
                            f"scope here — {hint}"]
        return []
    if operand == "of":
        # A composite's operand is other predicates, checked recursively — so a malformed
        # child names itself rather than the parent looking wrong.
        if spec.get("arity") == "one":
            value = one_check(value)       # `[{...}]` is what the schema asks the model for
        kids = [value] if spec.get("arity") == "one" else value
        if spec.get("arity") == "one":
            if not isinstance(value, dict):
                return [f"{where}: {shape} takes one check under `of`, got {value!r}"]
        elif not isinstance(value, (list, tuple)) or len(value) < 2:
            return [f"{where}: {shape} takes two or more checks under `of`, got {value!r}"]
        for kid in kids:
            out += _check_predicate(kid, where, bound, elsewhere, sets)
        return out
    if operand == "select":
        if not isinstance(value, dict):
            out.append(f"{where}: {shape} needs `select` — the set to measure, "
                       f"e.g. {{'kind':'vm','tag':'prod'}}")
        else:
            out += _check_select(value, where, sets)
    elif operand == "sets":
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            out.append(f"{where}: {shape} needs `sets` — two or more, got {value!r}")
    # A floor above one over a set that can hold at most one member is unsatisfiable by
    # construction. Reported as a problem, not a warning: the whole contract of ENSURE is
    # that passing it means something.
    if operand == "select" and _at_most_one(value):
        key = (config.KINDS.get(value.get("kind")) or {}).get("key")
        for c, floor in (("min", 1), ("gte", 1), ("eq", 1)):
            n = pred.get(c)
            if isinstance(n, int) and n > floor:
                out.append(
                    f"{where}: {shape} over {key} = {value.get(key)!r} can never reach "
                    f"{n} — a {value.get('kind')} {key} names ONE resource. Select the "
                    f"whole set (e.g. a shared label), or drop the floor.")
                break

    if (spec["comparators"] and not spec.get("comparators_optional")
            and not (set(pred) & set(spec["comparators"]))):
        # `reach` opts out. Its own doc reads "the members can reach each other" and the
        # deriver has always defaulted (`min`, 2) — only this check ever demanded a
        # number, so REACH(SELECT vm WHERE label='fleet') meaning ALL of them was
        # intended everywhere except the one place that rejected it. An author asked for
        # "make sure they all ping each other" has no N to supply and had to invent one.
        out.append(f"{where}: {shape} needs one of "
                   f"{'/'.join(spec['comparators'])} to compare against")
    return out


def kinds_used(body: List[Any]) -> List[str]:
    """Every resource kind a program touches — what `imports` is derived from."""
    seen = []
    for st in body or []:
        if not isinstance(st, dict):
            continue
        for k in (st.get("kind"), (st.get("select") or {}).get("kind")
                  if isinstance(st.get("select"), dict) else None):
            if k and k not in seen:
                seen.append(k)
    return seen
