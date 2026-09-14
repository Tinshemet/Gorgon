"""MARATHON PHASE 1 — FREEZE the ruler. For N turns: rotate a PERSONA, Serpent selects an intent
(known atoms), and messifies it through the PRE-FIRE FAITHFULNESS GATE (messify_faithful — it must
not drop a value atom it selected, or the case would measure Serpent's sloppiness, not Gorgon).

The `said` text is Serpent's FROZEN noise — the fixed ruler that a baseline and a re-run both read,
so a code change is measured against IDENTICAL input (adding turns invalidates the comparison). Each
row carries {id, clean, atoms, said, persona, oow} — oow = the atoms Serpent still dropped despite
the gate. Checkpointed to frozen.jsonl and RESUMABLE: a hang-kill just re-runs and skips done ids.

THERMAL: cool_down() runs before every model call and now guards the CPU package as well as the GPU
(the 09-02 halt was the CPU). The launcher (start_marathon.sh) adds the hard backstop.

Usage:  cd files && PYTHONPATH=. python3 -m tests.bench.read_eval.marathon.marathon_freeze <N> [seed]
"""
import sys, os, json, signal, random
from tests.bench.read_eval.marathon import broken_telephone as BT

signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError()))
OUT = os.path.join(os.path.dirname(__file__), "frozen.jsonl")


def done_ids():
    if not os.path.exists(OUT):
        return set()
    return {json.loads(l)["id"] for l in open(OUT) if l.strip()}


def _missing(atoms, said):
    """The value atoms Serpent dropped from `said` despite the gate (oow — out of words)."""
    toks = BT._tok(said or "")
    return [[w, k] for w, k in atoms
            if not (w.lower() in toks if k == "reference" else BT._near(w, toks))]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260829
    random.seed(seed)
    have = done_ids()
    prior = []
    personas = BT.PERSONA_LIST
    with open(OUT, "a") as f:
        for i in range(n):
            cid = f"m{seed}-{i:05d}"
            persona = personas[i % len(personas)]          # rotate the 13 personas deterministically
            intent = BT.make_intent(prior)                 # advance the intent stream even when skipping (deterministic resume)
            prior += intent["new"]
            if len(prior) > 12:
                prior = prior[-12:]
            if cid in have:
                continue
            BT.cool_down()                                 # THERMAL throttle (CPU + GPU) before the model call
            signal.alarm(90)
            try:
                said, faithful, tries = BT.messify_faithful(
                    intent["clean"], intent["atoms"],
                    noise=random.choice(["light", "light", "medium", "heavy"]), persona=persona)
                row = {"id": cid, "clean": intent["clean"], "atoms": intent["atoms"],
                       "said": said, "persona": persona, "faithful": faithful,
                       "oow": _missing(intent["atoms"], said)}
            except TimeoutError:
                row = {"id": cid, "clean": intent["clean"], "atoms": intent["atoms"],
                       "said": None, "persona": persona, "err": "messify-timeout"}
            except Exception as e:
                row = {"id": cid, "clean": intent["clean"], "atoms": intent["atoms"],
                       "said": None, "persona": persona, "err": repr(e)[:80]}
            finally:
                signal.alarm(0)
            f.write(json.dumps(row) + "\n"); f.flush()
            if (i + 1) % 25 == 0:
                print(f"  frozen {i + 1}/{n}", flush=True)
    total = sum(1 for _ in open(OUT))
    ok = sum(1 for l in open(OUT) if json.loads(l).get("said"))
    print(f"DONE frozen.jsonl: {total} rows, {ok} with said-text")


if __name__ == "__main__":
    main()
