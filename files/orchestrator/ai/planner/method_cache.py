"""
method_cache.py — a cache of parameterized decompositions (HTN "methods").

The weak local model decomposes compound goals INCONSISTENTLY (it split "create two
vms" one run, one-shot it the next). A method cache fixes that: for a goal that
matches a known method, we use the CACHED decomposition — deterministic, no model,
no variance. Only NOVEL goals reach the model, and a successful model decomposition
is LEARNED back into the cache (generalized to a template), so the system decomposes
less over time — Voyager/SOAR-style skill accumulation.

Methods are PARAMETERIZED (not exact-match): a method has a regex pattern with named
slots and step templates using those slots, so "create two vms named alpha and beta"
and "…named web and cache" hit the same method. Retrieval is deterministic
(first-match); the model is not involved on a hit.
"""
import re
from typing import Any, Dict, List, Optional


def _m(name: str, pattern: str, steps: List[str]) -> Dict:
    return {"name": name, "pattern": re.compile(pattern, re.I), "steps": steps}


# Seed library — the common compound shapes, most-specific first (first match wins).
SEED = [
    _m("create-two-and-launch",
       r"create two (?P<os>\w+) vms? (?:named|called) (?P<a>[\w-]+) and (?P<b>[\w-]+).*launch",
       ["create a {os} vm named {a}", "create a {os} vm named {b}",
        "launch the vm named {a}", "launch the vm named {b}"]),
    _m("create-two",
       r"create two (?P<os>\w+) vms? (?:named|called) (?P<a>[\w-]+) and (?P<b>[\w-]+)",
       ["create a {os} vm named {a}", "create a {os} vm named {b}"]),
    _m("create-and-launch",
       r"create (?:a |an )?(?P<os>\w+) vm (?:named|called) (?P<name>[\w-]+).*\blaunch\b",
       ["create a {os} vm named {name}", "launch the vm named {name}"]),
]

# Words that are never entity names when generalizing a learned method.
_STOP = {"create", "launch", "start", "stop", "delete", "make", "the", "a", "an",
         "vm", "vms", "and", "then", "named", "called", "two", "both", "it", "of",
         "to", "linux", "ubuntu", "windows", "with", "new", "up"}


class MethodCache:
    """Parameterized decomposition cache. `lookup` is deterministic (no model);
    `remember` generalizes a successful decomposition into a reusable method.

    A learned method is PROVISIONAL until `confirm` marks it proven. `remember` runs at
    PLAN time — before a single child has executed — so what it captures is a plan the
    model PROPOSED, not one that worked. That's tolerable inside a run (the worst case is
    reusing a mediocre decomposition for a few nodes) but it must never reach the durable
    store, where a bad generalization would be handed to every future run forever. So the
    engine confirms a method only when its composite actually closes `done`, and only
    proven methods are persisted — a method earns its place by WORKING, the same
    verified-completion rule the rest of the system runs on."""

    def __init__(self, methods: Optional[List[Dict]] = None):
        self._methods: List[Dict] = list(methods or [])
        self.hits = 0
        self.learned = 0

    def lookup(self, goal: str) -> Optional[List[str]]:
        """Return the instantiated steps for `goal` if a method matches, else None."""
        for meth in self._methods:
            mo = meth["pattern"].search(goal.strip())
            if mo:
                slots = {k: (v or "") for k, v in mo.groupdict().items()}
                steps = [s.format(**slots).strip() for s in meth["steps"]]
                if len(steps) >= 2:
                    self.hits += 1
                    return steps
        return None

    def remember(self, goal: str, steps: List[str]) -> Optional[str]:
        """Learn a method from a decomposition. Generalizes entity names (tokens shared
        between the goal and its steps) into slots. Returns the method's name, or None if
        nothing generalizable / already covered.

        A re-plan SUPERSEDES the unproven method learned from the same goal. Without that,
        a goal whose first plan failed keeps that plan: `lookup` matches the discarded
        method, so the corrective decomposition is never learned, and `confirm` then marks
        the FAILED one proven when the retry closes — durably teaching every future run a
        plan known not to work. Only UNPROVEN methods are superseded; one that already
        earned its place is never overwritten by a fresh guess."""
        g = (goal or "").strip()
        prior = next((m for m in self._methods
                      if m.get("learned") and m.get("source") == g), None)
        if prior is not None and not prior.get("proven"):
            meth = _generalize(g, steps)
            if not meth:
                return None
            self._methods[self._methods.index(prior)] = meth   # the newer plan is the one under test
            return meth["name"]
        if self.lookup(goal):
            return None
        meth = _generalize(goal, steps)
        if not meth:
            return None
        self._methods.insert(0, meth)   # learned methods take precedence over seeds
        self.learned += 1
        return meth["name"]

    def confirm(self, goal: str) -> bool:
        """Mark the method LEARNED FROM `goal` as proven — its decomposition closed done.
        Only proven methods are durable (see `proven`). Returns whether one was marked."""
        for meth in self._methods:
            if meth.get("source") == (goal or "").strip():
                if meth.get("proven"):
                    return False
                meth["proven"] = True
                return True
        return False

    def names(self) -> List[str]:
        return [m["name"] for m in self._methods]

    def proven(self) -> List[Dict[str, Any]]:
        """The proven LEARNED methods, as plain JSON records for the store. Seeds are
        never included: they live in code, which is their SSOT — persisting them would
        fossilize a copy that silently outranks the edited seed library."""
        return [{"name": m["name"], "pattern": m["pattern"].pattern,
                 "steps": list(m["steps"]), "source": m.get("source", "")}
                for m in self._methods if m.get("proven") and m.get("learned")]

    @staticmethod
    def from_records(records: List[Dict[str, Any]], seeds: bool = True) -> "MethodCache":
        """Rebuild a cache from stored records (most-precedent first), over the seeds.
        A record with an uncompilable pattern is DROPPED, not raised on: a corrupt or
        hand-edited store must degrade to "no learned methods", never brick a run."""
        methods = []
        for r in records or []:
            try:
                methods.append({"name": r["name"], "pattern": re.compile(r["pattern"], re.I),
                                "steps": list(r["steps"]), "source": r.get("source", ""),
                                "learned": True, "proven": True})
            except Exception:
                continue
        return MethodCache(methods + (list(SEED) if seeds else []))


def _generalize(goal: str, steps: List[str]) -> Optional[Dict]:
    """Turn a concrete (goal, steps) into a parameterized method by slotting the
    entity tokens that appear in BOTH the goal and its steps."""
    g = goal.strip()
    low = g.lower()
    toks, seen = [], set()
    for t in re.findall(r"[\w-]+", low):
        if t in _STOP or t.isdigit() or len(t) < 2 or t in seen:
            continue
        if any(re.search(rf"\b{re.escape(t)}\b", s, re.I) for s in steps):
            toks.append(t)
            seen.add(t)
    if not toks:
        return None
    toks.sort(key=len, reverse=True)                 # longer first, avoid substring clobber
    pat = re.escape(g)
    tsteps = list(steps)
    for i, e in enumerate(toks):
        slot = f"s{i}"
        # Only the FIRST occurrence becomes the capturing group; a token repeated in the
        # goal (e.g. "all … all") would otherwise redefine the group name and crash the
        # regex compile. Later occurrences stay literal — still matches, just less general.
        pat = pat.replace(re.escape(e), f"(?P<{slot}>[\\w-]+)", 1)   # literal insert, first only
        tsteps = [re.sub(rf"\b{re.escape(e)}\b", "{" + slot + "}", s, flags=re.I) for s in tsteps]
    return {"name": f"learned:{low[:32]}", "pattern": re.compile(pat, re.I), "steps": tsteps,
            "source": g, "learned": True, "proven": False}


def seeded() -> MethodCache:
    """A fresh cache preloaded with the seed library."""
    return MethodCache(list(SEED))
