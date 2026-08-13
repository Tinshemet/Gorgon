"""rules.py — the ONE weighted rule of law, and the resolver that makes it govern.

A contract carries a single ``rules`` list — the LAW — that both reads as plain text and
DRIVES enforcement. Each entry:

    {"w": <int>, "kind": <str>, "text": <str>, "effect": {<machine action>}}

    w      — weight / precedence: 0 = CRITICAL / inviolable, higher = weaker (more waivable).
    kind   — access | delegation | provisions | decree  (or "rule" = plain documentary).
    text   — human-readable statement of the rule.
    effect — the machine action this rule projects onto the numeric SUBSTRATE:
             access     → {"forbid":[tools], "allow":[tools]}      (tool allow/deny; the red-line blacklist lives here at w:0)
                          {"scope": {"tools":[…], "args"|"object": {…}}}  (a tool permitted ONLY inside a context)
             delegation → {"tier": <tier>, "tools":[tools], "when":{risk-cond}}  (override a tool's confirmation tier)
             provisions → {"reward_cost": {knob: value}}           (shape the reward-cost economics)
             decree     → {"success_predicate": [clauses]}         (extend the goal / acceptance)

⇒⇒ A BAN AND A SCOPE ARE OPPOSITE SHAPES, AND THE DIFFERENCE IS WHICH SIDE MUST BE PROVEN.
The operator, 2026-08-13: *"it's not to keep something out, it's to only allow something
specific in"* … *"scope means — you are only allowed to use this tool within this context."*

    a BAN     a DENYLIST: "is this tool on the list?"       —— it has to CATCH you
    a SCOPE   an ALLOWLIST WITH A BINDING: "is this call
              inside the context?"                         —— it has to be SATISFIED

That is not a stylistic difference. `delete_vm` over the UNFILTERED set of every machine
passed every check this system had, because there was nothing to catch: no banned tool, no
illegal operation, no missing confirmation. Under a scope it fails for the opposite reason —
**nothing proved it was inside**. So the decision procedure is PROVE INCLUSION, never detect
exclusion, and an unbound target is refused because inclusion is unproven rather than because
a check spotted something.

⇒ TWO BINDING KINDS, BECAUSE TWO KINDS OF CALLER MUST BOTH ANSWER IT. An `args` binding is a
  LITERAL — what the tree (`legal_filter(name, args)`), the executor and the program regime
  hold. An `object` binding is a SELECTOR in `schema.select_of`'s own shape — which is all
  the front seam ever holds, since it reads a request before any literal exists. One
  vocabulary, two readers, each answering what it can actually see:

    {"scope": {"tools": ["scan_network"], "args":   {"net_name": "lab"}}}
    {"scope": {"tools": ["delete_vm"],    "object": {"kind": "vm", "label": "scratch"}}}

  Matching them against a call is `contract/scope.py`, never here: this class resolves law
  over substrate and has never known what a VM is.

⇒ THREE RULINGS FROM THE OPERATOR, 2026-08-13, AND THEY DECIDE THE RESOLUTION ORDER:

    a  a scope means the tool is permitted ONLY inside its context — outside it, refused
    b  **A SCOPE CANNOT LIFT A BAN.** The ban question resolves FIRST, exactly as it always
       has (forbid vs allow by weight); if the answer is forbidden, scopes are never
       consulted. Otherwise a red line would be liftable by authoring a narrow grant, and
       the only thing that lifts one is re-authentication in person (`ir/consent.permitted`)
    c  two scopes on one tool UNION — each is a grant, so any matching one admits

Two representations of ONE whole: the rules are the LAW (authored, weighted, referendum/
amendment-mutable, the SSOT for DECLARED policy); the ``tools`` + risk formula are the
stable PHYSICS (auto-scoring substrate). The RuleSet RESOLVES law over physics into the
effective policy: precedence by weight (0 wins), stable tie-break by declaration order, so
the outcome is never ambiguous and never cyclic. The old ``forbidden`` list and per-tool
``pin`` are just the pre-schema shorthand for w:0 access / delegation rules — the resolver
honors both so the migration is seamless.
"""
from typing import Any, Dict, List, Optional

KINDS = ("access", "delegation", "provisions", "decree", "rule")   # "rule" = plain documentary
_EFFECT_KINDS = ("access", "delegation", "provisions", "decree")    # kinds that carry a machine effect


def _norm(text: Any) -> str:
    """Whitespace/case-normalized rule text, so trivially-different duplicates collide."""
    return " ".join(str(text or "").strip().lower().split())


def _weight(rule: Dict[str, Any]) -> Optional[float]:
    """A rule's numeric weight (new ``w`` or legacy ``weight``), or None if non-numeric."""
    raw = rule.get("w", rule.get("weight", 1))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _kind(rule: Dict[str, Any]) -> str:
    return str(rule.get("kind") or "rule").strip().lower()


class RuleSet:
    """Resolves the weighted rule of law over the numeric substrate into effective policy.

    Precedence is a total order over (weight, declaration-index): the lowest-weight matching
    rule wins (0 = inviolable), ties broken by order — so every query has one deterministic
    answer. Malformed rules are skipped here and reported by ``conflicts``."""

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        self.raw: List[Dict[str, Any]] = list(rules or [])
        # parsed + precedence-ordered: (weight, index, kind, effect, rule)
        self._ordered = sorted(
            ((w, i, _kind(r), r.get("effect") or {}, r)
             for i, r in enumerate(self.raw) if (w := _weight(r)) is not None),
            key=lambda t: (t[0], t[1]))

    # ── the display / precedence view (also E1's resolve) ────────────────────────────
    def ordered(self) -> List[Dict[str, Any]]:
        """Rules strongest-first (lowest weight = 0 inviolable), stable tie-break by index.
        Each: {w, kind, text, effect, rank, inviolable}. rank 0 = highest precedence."""
        return [{"w": w, "kind": k, "text": r.get("text", ""), "effect": eff,
                 "rank": rank, "inviolable": w == 0}
                for rank, (w, i, k, eff, r) in enumerate(self._ordered)]

    def by_weight(self) -> Dict[int, List[Dict[str, Any]]]:
        """The law grouped by integer weight tier — the `gorgon contract rules` view
        (0 · critical, 1 · important, …). Non-integer weights floor into their tier."""
        out: Dict[int, List[Dict[str, Any]]] = {}
        for r in self.ordered():
            out.setdefault(int(r["w"]), []).append(r)
        return out

    # ── ACCESS — allow / deny (the blacklist lives here at w:0) ───────────────────────
    def forbids(self, tool: str, base_forbidden=()) -> bool:
        """Is `tool` forbidden under the resolved law? The lowest-weight ACCESS rule that
        mentions the tool (in forbid or allow) decides — so a critical w:0 forbid can't be
        undone by a weaker allow, and an explicit allow can lift a lower-priority forbid.
        Falls back to the legacy `forbidden` list (treated as the weakest deny).

        THE BAN QUESTION, AND ONLY THE BAN QUESTION. `scope` effects are deliberately not
        read here: by the operator's ruling (b) a scope cannot lift a ban, so this answers
        first and a `True` ends the matter without a scope ever being consulted. A caller
        asking whether a CALL is permitted asks this AND then `scopes`; a caller with only
        a tool name in hand (chat's toolkit filter) asks only this."""
        for w, i, kind, eff, r in self._ordered:
            if kind != "access":
                continue
            if tool in (eff.get("forbid") or []):
                return True
            if tool in (eff.get("allow") or []):
                return False
        return tool in (base_forbidden or ())

    def allowed_tools(self) -> set:
        """Tools explicitly ALLOWED by an access rule (additive to the toolkit whitelist)."""
        out: set = set()
        for w, i, kind, eff, r in self._ordered:
            if kind == "access":
                out.update(eff.get("allow") or [])
        return out

    def scopes(self, tool: str) -> List[Dict[str, Any]]:
        """Every SCOPE binding that governs `tool`, strongest-first — EMPTY when none does.

        Each entry: {w, text, bind: "args"|"object", context: {…}}. `text` travels with it
        because a refusal has to be able to name the rule that refused, and `w` because the
        law's tiers are what the operator reads.

        ⇒ EMPTY MEANS UNGOVERNED, NOT REFUSED, and that containment rule is what keeps one
          authored scope from banning the world. A tool no scope names is answered by the
          ban law alone, exactly as before this existed — so adding a scope to `scan_network`
          says nothing whatever about `delete_vm`.

        ⇒ UNION, BY THE OPERATOR'S RULING (c): every governing scope comes back and ANY of
          them admitting is enough, because each one is a grant. The ordering here is for
          reporting and for the operator's reading of precedence — it is not a first-match
          cut, and a matcher that stops at the strongest would silently drop grants.

        ⇒ THIS ANSWERS "WHAT IS THE LAW", NOT "IS THIS CALL INSIDE IT". Matching a literal
          arg or a selector against `context` is the caller's question and deliberately not
          here: this class resolves the law over the substrate and has never known what a
          VM is. The same reason `tier_for` takes risk facts rather than reading a tool.
        """
        out: List[Dict[str, Any]] = []
        for w, i, kind, eff, r in self._ordered:
            if kind != "access":
                continue
            scope = eff.get("scope") or {}
            if tool not in (scope.get("tools") or []):
                continue
            for bind in ("args", "object"):
                if scope.get(bind):
                    out.append({"w": w, "text": r.get("text", ""),
                                "bind": bind, "context": scope[bind]})
        return out

    # ── DELEGATION — override a tool's confirmation tier ─────────────────────────────
    def tier_for(self, tool: str, risk: Optional[Dict[str, Any]], base_tier: str) -> str:
        """The effective tier: the lowest-weight DELEGATION rule that applies wins, else the
        substrate's `base_tier`. A rule applies if it names the tool in `tools`, or its
        `when` risk-condition matches the tool's risk facts (e.g. irreversible+destructive)."""
        for w, i, kind, eff, r in self._ordered:
            if kind != "delegation" or "tier" not in eff:
                continue
            if tool in (eff.get("tools") or []) or _when_matches(eff.get("when"), risk):
                return str(eff["tier"])
        return base_tier

    # ── PROVISIONS — shape the reward-cost economics ─────────────────────────────────
    def reward_cost_overrides(self) -> Dict[str, Any]:
        """Merged reward-cost knob overrides; per knob the lowest-weight rule wins (applied
        last-over-first here since we walk strongest→weakest and let earlier win)."""
        out: Dict[str, Any] = {}
        for w, i, kind, eff, r in reversed(self._ordered):     # weakest first, strongest overwrites
            if kind == "provisions":
                out.update(eff.get("reward_cost") or {})
        return out

    # ── DECREE — extend the goal / acceptance predicate ──────────────────────────────
    def decrees(self) -> List[Dict[str, Any]]:
        """Extra success-predicate clauses every DECREE rule adds to the goal (in
        precedence order, de-duplicated)."""
        out: List[Dict[str, Any]] = []
        for w, i, kind, eff, r in self._ordered:
            if kind == "decree":
                for clause in eff.get("success_predicate") or []:
                    if clause not in out:
                        out.append(clause)
        return out


def _when_matches(when: Optional[Dict[str, Any]], risk: Optional[Dict[str, Any]]) -> bool:
    """Does a delegation rule's `when` risk-condition match a tool's risk facts? Supports
    equality and simple numeric comparators (">=0.7", "<0.3", …). None/empty → no match
    (a `tools`-less, `when`-less delegation rule applies to nothing, not everything)."""
    if not when:
        return False
    r = risk or {}
    for key, cond in when.items():
        val = r.get(key)
        if isinstance(cond, str) and cond[:1] in "<>=" and cond[:2] not in ("==",):
            op = cond[:2] if cond[1:2] == "=" else cond[:1]
            try:
                target = float(cond[len(op):]); num = float(0.0 if val is None else val)
            except (TypeError, ValueError):
                return False
            if not ((op == ">=" and num >= target) or (op == ">" and num > target)
                    or (op == "<=" and num <= target) or (op == "<" and num < target)):
                return False
        elif val != cond:
            return False
    return True


def _scope_problems(index: int, scope: Any) -> List[str]:
    """Every way a SCOPE binding is malformed — refused at sign rather than resolved at run.

    A SCOPE THAT CANNOT BE READ IS THE WORST OBJECT IN THIS SYSTEM, because both of its
    failure modes are silent and they point in opposite directions: read as admitting
    nothing it bans a tool the operator meant to grant, read as admitting everything it
    grants what they meant to bound. Neither announces itself at the call.
    """
    if not isinstance(scope, dict):
        return [f"rule {index} [access] scope must be an object, not {type(scope).__name__}"]
    out: List[str] = []
    if not [t for t in (scope.get("tools") or []) if str(t or "").strip()]:
        out.append(f"rule {index} [access] scope names no tools — it binds nothing to nothing")
    bound = [k for k in ("args", "object") if scope.get(k)]
    if not bound:
        out.append(f"rule {index} [access] scope declares no context — a permission with no "
                   f"limit is not a scope, it is an allow")
    if len(bound) > 1:
        out.append(f"rule {index} [access] scope binds BOTH args and object — bind one; two "
                   f"scopes on one tool are a UNION (either admits), which is not an AND")
    for k in bound:
        if not isinstance(scope.get(k), dict):
            out.append(f"rule {index} [access] scope {k} must be an object, not "
                       f"{type(scope[k]).__name__}")
    # ── THE OBJECT BINDING IS AN IR SELECT, so it is held to that shape here ─────────
    # `schema.select_of` is the ONE builder of "which members"; a scope that spoke its own
    # dialect would need a translator at every seam, which is how two answers to one
    # question start. Held at SIGN so `scope.py` can assume it at every call.
    sel = scope.get("object")
    if isinstance(sel, dict) and sel:
        groups = sorted(g for g in ("any", "all", "not") if g in sel)
        if groups:
            out.append(f"rule {index} [access] scope object carries {', '.join(groups)} — a "
                       f"scope is a conjunction of bindings; write a set of permitted "
                       f"targets as two scopes, which UNION")
        if not sel.get("kind"):
            out.append(f"rule {index} [access] scope object names no kind — a select "
                       f"without one denotes nothing")
        if not [a for a in sel if a not in ("kind", "any", "all", "not")]:
            out.append(f"rule {index} [access] scope object narrows nothing beyond the kind "
                       f"— that admits every member, which is a permission with no limit")
    return out


def effective_rules(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The declared ``rules[]`` PLUS the legacy ``forbidden`` list migrated to inviolable
    w:0 access rules — the one list the resolver governs from. SSOT for both the live
    Contract and the `gorgon contract rules` view, so they can never disagree."""
    rules = list((contract or {}).get("rules") or [])
    for t in ((contract or {}).get("forbidden") or []):
        rules.append({"w": 0, "kind": "access", "text": f"red line: {t} is forbidden",
                      "effect": {"forbid": [t]}})
    return rules


# ── backward-compatible module functions (E1 API) + new-schema coherence ─────────────

def resolve(rules: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """The rules in deterministic precedence order (E1 API, now via RuleSet). Each carries
    text/weight/rank/inviolable — plus kind/effect for the unified schema."""
    return [{"text": r["text"], "weight": r["w"], "rank": r["rank"],
             "inviolable": r["inviolable"], "kind": r["kind"], "effect": r["effect"]}
            for r in RuleSet(rules).ordered()]


def conflicts(rules: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Every way the weighted rule set silently contradicts itself — refused at sign.
    Structural + schema: bad/negative weight, empty text, duplicate, the same rule at two
    weights, an unknown kind, or an effect-bearing kind with a malformed effect."""
    problems: List[str] = []
    by_text: Dict[str, float] = {}
    for i, r in enumerate(rules or []):
        w = _weight(r)
        text = _norm(r.get("text"))
        kind = _kind(r)
        if w is None:
            problems.append(f"rule {i} has a non-numeric weight: {r.get('w', r.get('weight'))!r}")
            continue
        if w < 0:
            problems.append(f"rule {i} has a negative weight ({w}); weights are ≥ 0 (0 = inviolable)")
        if kind not in KINDS:
            problems.append(f"rule {i} has an unknown kind {kind!r}; expected one of {KINDS}")
        if kind in _EFFECT_KINDS and not (r.get("effect") or {}):
            problems.append(f"rule {i} [{kind}] has no effect — an enforceable rule must declare one")
        if kind == "access" and (r.get("effect") or {}).get("scope") is not None:
            problems.extend(_scope_problems(i, (r.get("effect") or {})["scope"]))
        if not text:
            problems.append(f"rule {i} has empty text")
            continue
        if text in by_text:
            if by_text[text] != w:
                problems.append(
                    f"rule declared at two weights ({by_text[text]} and {w}) — "
                    f"which governs is undefined: {r.get('text')!r}")
            else:
                problems.append(f"duplicate rule (same text and weight): {r.get('text')!r}")
        else:
            by_text[text] = w

    # ── A SCOPE ON A TOOL THIS LAW ALREADY BANS CAN NEVER ADMIT ANYTHING ──────────────
    # By the operator's ruling (b) the ban resolves first and a scope cannot lift it, so
    # such a rule is DEAD LAW — and dead law is worse than absent law here, because its
    # author is entitled to read it as "I granted scoped access to this tool" when what
    # they have is no access at all. Resolved through `forbids`, never by scanning for the
    # name: a forbid can itself be lifted by a stronger allow, and a second answer to
    # "is this banned" is the last thing a red line needs.
    #   ⇒ LIMIT, STATED: `review()` passes `contract["rules"]`, so a tool banned only by the
    #     legacy `forbidden` list is invisible to this check. It is an AUTHORING aid; the
    #     runtime order is enforced where the ban is answered, over the effective law.
    resolved = RuleSet(rules)
    for i, r in enumerate(rules or []):
        if _kind(r) != "access":
            continue
        scope = (r.get("effect") or {}).get("scope") or {}
        if not isinstance(scope, dict):
            continue
        dead = sorted({t for t in (scope.get("tools") or []) if resolved.forbids(t)})
        if dead:
            problems.append(
                f"rule {i} [access] scopes a tool the same law FORBIDS ({', '.join(dead)}) — "
                f"a scope cannot lift a ban, so this rule can never admit anything")
    return problems
