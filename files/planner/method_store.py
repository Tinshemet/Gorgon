"""
method_store.py — durable, per-agent persistence for LEARNED decomposition methods.

The method cache turns a goal shape into a deterministic decomposition, and learns new
methods from the model as it goes ([[method_cache]]). Without a store that learning died
at process exit: every run rebuilt a fresh seeded cache and re-asked the model the same
questions, so the system could not actually "un-reason over time" — the whole point of
the cache. This file is that store, one JSON per agent at
``~/.gorgon/_agents/<agent>/methods.json``, holding records of
``{name, pattern, steps, source}``.

Scope is per-agent, like claims and toolstats: a doorman run's learned shortcuts have no
business steering a barenboim run, whose tools and law differ.

Only PROVEN methods reach this file — ones whose decomposition actually closed `done`.
The cache learns at plan time, before anything has executed, so an unproven method is
just a plan the model proposed; persisting that would hand a bad generalization to every
future run. See MethodCache.confirm / .proven.

The store is CAPPED (`MAX_METHODS`, newest first). A cache that grows without bound
would slow every lookup and quietly accumulate junk from one-off goals; the cap keeps
recent learning and drops the tail. Dropping the tail is safe — a lost method costs one
model call to re-learn, it doesn't lose state.
"""
import json
import os
import re
from typing import Any, Dict, List, Optional

from shared.bundle import Bundle

MAX_METHODS = 200


def _safe(agent: Optional[str]) -> str:
    """A filesystem-safe agent key (never traverses out of the bundle root)."""
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", agent or "default") or "default"


def store_path(agent: Optional[str]) -> str:
    """The agent's method store (~/.gorgon/_agents/<agent>/methods.json)."""
    return Bundle(_safe(agent)).methods_path


def load(agent: Optional[str]) -> List[Dict[str, Any]]:
    """The stored method records ([] if none / unreadable — never raises)."""
    try:
        with open(store_path(agent)) as f:
            data = json.load(f)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [r for r in data
            if isinstance(r, dict) and r.get("name") and r.get("pattern") and r.get("steps")]


def save(agent: Optional[str], records: List[Dict[str, Any]]) -> None:
    """Atomically replace the agent's store (write-temp-then-rename, so a crash
    mid-write can't corrupt the file)."""
    path = store_path(agent)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(records[:MAX_METHODS], f, indent=2)
    os.replace(tmp, path)


def merge_into(agent: Optional[str], records: List[Dict[str, Any]]) -> int:
    """Fold this run's proven methods into the agent's store, newest FIRST (so recent
    learning outranks old on a lookup, matching the in-run precedence where a learned
    method is inserted ahead of the seeds). De-duplicated by pattern — re-learning a
    shape the store already has refreshes its position, it doesn't add a twin. Returns
    the number of genuinely new records."""
    if not records:
        return 0
    existing = load(agent)
    seen = {r.get("pattern") for r in records}
    merged = list(records) + [r for r in existing if r.get("pattern") not in seen]
    new = len([r for r in records if r.get("pattern") not in {e.get("pattern") for e in existing}])
    save(agent, merged)
    return new


def clear(agent: Optional[str]) -> bool:
    """Forget everything this agent has learned. Returns whether a store existed."""
    try:
        os.remove(store_path(agent))
        return True
    except Exception:
        return False


# ── the NEGATIVE twin: plans that did NOT work ────────────────────────────────
# The system remembered what worked and forgot what didn't. Within a run, the `failed`
# post-mortems are what make revision corrective — the model is told "✗ attach b (no
# network lab)" and re-plans against it. At process exit that memory was thrown away, so
# the next run re-derived the same broken plan and re-discovered it was broken, paying
# full price each time. This is that memory, made durable.
#
# Stored per agent at ~/.gorgon/_agents/<agent>/plan_failures.json as
# {pattern, source, steps, why, n}, where `pattern` is the SAME generalization the method
# cache uses — so a failure learned on one goal warns about the next goal of that shape.
# It is advisory only: it becomes planning CONTEXT ("this was tried and failed"), never a
# block. A plan that failed for a transient reason must stay retryable.

MAX_FAILURES = 100


def failures_path(agent: Optional[str]) -> str:
    """The agent's failed-plan memory (~/.gorgon/_agents/<agent>/plan_failures.json)."""
    return Bundle(_safe(agent)).plan_failures_path


def load_failures(agent: Optional[str]) -> List[Dict[str, Any]]:
    """The stored failure records ([] if none / unreadable — never raises)."""
    try:
        with open(failures_path(agent)) as f:
            data = json.load(f)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict) and r.get("pattern") and r.get("why")]


def save_failures(agent: Optional[str], records: List[Dict[str, Any]]) -> None:
    """Atomically replace the agent's failure memory."""
    path = failures_path(agent)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(records[:MAX_FAILURES], f, indent=2)
    os.replace(tmp, path)


def record_failures(agent: Optional[str], records: List[Dict[str, Any]]) -> int:
    """Fold this run's failures in, newest first. A repeat of a failure already on file
    bumps its count rather than adding a twin — so "this keeps failing" is visible, and
    one flaky run doesn't look like ten. Returns the number of genuinely new records."""
    if not records:
        return 0
    existing = load_failures(agent)
    by_key = {(r.get("pattern"), r.get("why")): dict(r) for r in existing}
    new = 0
    fresh: List[Dict[str, Any]] = []
    for r in records:
        key = (r.get("pattern"), r.get("why"))
        if key in by_key:
            by_key[key]["n"] = int(by_key[key].get("n", 1)) + 1
        else:
            rec = dict(r)
            rec["n"] = 1
            fresh.append(rec)
            new += 1
    merged = fresh + [by_key[k] for k in by_key]
    save_failures(agent, merged)
    return new


def warnings_for(records: List[Dict[str, Any]], goal: str) -> List[Dict[str, Any]]:
    """The stored failures whose pattern matches `goal` — what to warn the planner about
    before it re-derives them. A record with an uncompilable pattern is skipped."""
    out = []
    for r in records or []:
        try:
            if re.search(r["pattern"], (goal or "").strip(), re.I):
                out.append(r)
        except Exception:
            continue
    return out


def clear_failures(agent: Optional[str]) -> bool:
    """Forget this agent's failed-plan memory. Returns whether a store existed."""
    try:
        os.remove(failures_path(agent))
        return True
    except Exception:
        return False
