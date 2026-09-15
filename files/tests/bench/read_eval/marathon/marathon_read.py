"""MARATHON PHASE 2 — READ the frozen ruler through Gorgon and evaluate, gold-free. For each
frozen {said}: Gorgon reads it, we score atom-recovery (GORGON/SERPENT-DROP) + structural flags.
Checkpointed to results.jsonl and RESUMABLE (skip done). Then summarize -> the two lists.
Usage: python3 marathon_read.py [--summary]."""
import sys, json, os, signal
from collections import Counter
from tests.bench.read_eval import runner
from tests.bench.read_eval.marathon import broken_telephone as BT
from tests.bench.read_eval.marathon import read_marathon as RM

signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError()))
FROZEN = os.path.join(os.path.dirname(__file__), "frozen.jsonl")
RESULTS = os.path.join(os.path.dirname(__file__), "results.jsonl")


def done_ids():
    if not os.path.exists(RESULTS):
        return set()
    return {json.loads(l)["id"] for l in open(RESULTS) if l.strip()}


def run(limit=None):
    have = done_ids()
    rows = [json.loads(l) for l in open(FROZEN) if l.strip()]
    todo = [r for r in rows if r["id"] not in have and r.get("said")]
    if limit:
        todo = todo[:limit]                   # bounded validation batch (e.g. 300) before the full run
    with open(RESULTS, "a") as f:
        for i, row in enumerate(todo):
            said = row["said"]; intent = {"atoms": [tuple(a) for a in row["atoms"]], "clean": row["clean"]}
            BT.cool_down()                       # throttle: keep the GPU cool before each read
            signal.alarm(40)
            try:
                r = runner.read_case(said); runner.annotate_roles(r)
                rec = BT.recover(intent, said, r)
                sflags = [x for x in RM.flags(said, r) if x != "ok"]
                res = {"id": row["id"], "clean": row["clean"], "said": said,
                       "persona": row.get("persona"), "oow": row.get("oow", []),
                       "atoms": [[w, k, v] for w, k, v in rec], "struct": sflags,
                       "spans": [(p.get("span"), p.get("role")) for p in r["rows"]
                                 if p.get("start") is not None and p.get("role")]}
            except TimeoutError:
                res = {"id": row["id"], "said": said, "persona": row.get("persona"), "err": "read-timeout"}
            except Exception as e:
                res = {"id": row["id"], "said": said, "persona": row.get("persona"), "err": repr(e)[:100]}
            finally:
                signal.alarm(0)
            f.write(json.dumps(res) + "\n"); f.flush()
            if (i + 1) % 25 == 0:
                print(f"  read {i + 1}/{len(todo)}", flush=True)


def summarize():
    ok = gdrop = sdrop = crashes = clean_turns = 0
    struct = Counter(); gdrop_ex = []; struct_ex = {}
    rows = [json.loads(l) for l in open(RESULTS) if l.strip()]
    for res in rows:
        if res.get("err"):
            crashes += 1; continue
        turn_flagged = bool(res.get("struct")) or any(v == "GORGON-DROP" for _, _, v in res.get("atoms", []))
        clean_turns += not turn_flagged
        for w, k, v in res.get("atoms", []):
            ok += v == "ok"; sdrop += v == "SERPENT-DROP"
            if v == "GORGON-DROP":
                gdrop += 1
                if len(gdrop_ex) < 8:
                    gdrop_ex.append(f"{res['said']!r} lost {w}({k})")
        for s in res.get("struct", []):
            key = s.split("[")[0].split(":")[0]
            struct[key] += 1
            struct_ex.setdefault(key, s)
    n = len(rows)
    print(f"\n=== MARATHON SUMMARY over {n} turns ===")
    print(f"  clean turns (no flag): {clean_turns}/{n} = {100*clean_turns//max(n,1)}%")
    print(f"  atoms: ok {ok} · GORGON-DROP {gdrop} (content lost) · SERPENT-DROP {sdrop} (serpent noise) · crashes {crashes}")
    print(f"\n  CAN'T-COVER — structural breakage taxonomy (count):")
    for k, c in struct.most_common():
        print(f"    {k:12} {c:4}   e.g. {struct_ex[k]}")
    print(f"\n  GORGON-DROP examples (content Serpent kept but READ lost):")
    for e in gdrop_ex:
        print(f"    {e}")


if __name__ == "__main__":
    if "--summary" in sys.argv:
        summarize()
    else:
        lim = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)
        run(lim); summarize()
