"""Run READ over a Serpent conversation and SHOW what it produces — the unfiltered look. Gold-free:
we flag STRUCTURAL breakage, not correctness. Generate a scenario, read each user turn, print the
decomposition + flags. (Standalone per turn for now; cross-turn context is the next enhancement.)"""
import sys, signal
from tests.bench.read_eval import runner
from tests.bench.read_eval.marathon import serpent

signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError()))

# a rough verb set (Gorgon's surface) to spot an imperative that lost its target
_VERBS = {"create", "make", "spin", "stop", "kill", "restart", "launch", "snapshot", "delete",
          "nuke", "put", "add", "give", "set", "label", "tag", "call", "name", "list", "check",
          "clear", "move", "back", "start", "boot", "provision", "wipe", "reboot"}
# words that should NEVER be buried inside a content span — a prep/pronoun/adverb glued in means
# READ failed to split (a PP, a reference, a repetition adverb).
_PREP = {"on", "in", "to", "at", "of", "with", "from", "onto", "into", "for"}
_PRO = {"it", "that", "them", "those", "they", "this", "these"}
_ADV = {"again", "instead", "anyway"}
# discourse / filler words — never content; a content role on one is breakage.
_FILLER = {"wait", "actually", "no", "please", "ok", "okay", "well", "hmm", "yeah", "yep",
           "anyway", "just", "again", "instead", "too", "also", "then", "still", "right",
           "sure", "thanks", "gimme", "hey", "oh", "lol", "each", "scratch", "nah"}
_SANCTIONED_DUAL = ({"selector", "evidence"}, {"patient", "ownership"})   # the legit multi-roles
_CONTENT = ("patient", "reference", "value", "selector")


_FUNC = {"the", "a", "an", "of", "to", "is", "are", "on", "in", "for", "and", "or", "with"}


def flags(sent, r):
    f = []
    rows = [p for p in r.get("rows", []) if p.get("start") is not None]
    subs = [(p["start"], p["end"]) for p in rows if p.get("sub")]

    def decomposed(p):   # does any tighter sub-span live inside this fat span?
        return any(p["start"] <= ss and se <= p["end"] and (ss, se) != (p["start"], p["end"])
                   for ss, se in subs)
    if not rows and not r.get("operations") and not r.get("queries"):
        f.append("EMPTY")
    first = sent.strip().lower().split()[0].strip(",.") if sent.strip() else ""
    if first in _VERBS and not (any(p.get("role") in ("patient", "reference") for p in rows)
                                or r.get("queries")):
        f.append("NO-TARGET")           # a command whose acted-on thing READ never found
    for p in rows:
        if p.get("sub"):
            continue
        role = p.get("role"); span = p.get("span") or ""; toks = span.lower().split()
        if role in _CONTENT:
            buried = []
            for i, w in enumerate(toks):
                if w in _PREP or w in _ADV:
                    buried.append(w)                              # a PP / adverb never belongs in a span
                elif w in _PRO and not (i + 1 < len(toks) and toks[i + 1] in ("one", "ones")):
                    if i > 0 or (i + 1 < len(toks) and toks[i + 1] not in ("one", "ones")):
                        buried.append(w)                          # pronoun+real-noun or mid-span (NOT `that one`)
            if len(toks) >= 2 and buried:
                f.append(f"GLOB[{role}]:{span!r}<-{buried}")     # swallowed a PP / reference / adverb
            if toks and toks[0].strip(",.") in _VERBS:
                f.append(f"VERB-GLOB[{role}]:{span!r}")           # a verb glued into a content span
            if toks and toks[0] in ("is", "are", "was", "were", "be", "been"):
                f.append(f"COPULA[{role}]:{span!r}")              # a predicate read as content
            fillers = [w for w in toks if w in _FILLER]
            if fillers and len(toks) <= 3:
                f.append(f"FILLER[{role}]:{span!r}<-{fillers}")   # a discourse word given content
    # a span carrying 2+ roles that aren't a sanctioned dual (or a filler faking the diagnosis dual)
    from collections import defaultdict
    byoff = defaultdict(set)
    for p in rows:
        if p.get("role"):
            byoff[(p.get("start"), p.get("end"), p.get("span"))].add(p.get("role"))
    for (s, e, sp), roles in byoff.items():
        if len(roles) >= 2:
            if roles not in _SANCTIONED_DUAL:
                f.append(f"MULTIROLE:{sp!r}={sorted(roles)}")
            elif roles == {"selector", "evidence"} and (sp or "").lower() in _FILLER:
                f.append(f"BAD-DUAL:{sp!r}(not a diagnosis)")
    return f or ["ok"]


def read_turn(sent):
    signal.alarm(40)
    try:
        r = runner.read_case(sent); runner.annotate_roles(r)
        return r, None
    except TimeoutError:
        return None, "TIMEOUT"
    except Exception as e:
        return None, f"CRASH {e!r}"
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    turns, _ = serpent.serpent_turns(serpent.SCENARIOS[n])
    print(f"=== SCENARIO {n} — {len(turns)} turns ===\n")
    tally = {}
    for i, t in enumerate(turns, 1):
        r, err = read_turn(t)
        if err:
            print(f"{i:2}. {t!r}\n     !! {err}"); tally[err.split()[0]] = tally.get(err.split()[0], 0) + 1
            continue
        spans = [f"{p.get('span')!r}:{p.get('role')}" for p in r["rows"]
                 if p.get("start") is not None and p.get("role")]
        fl = flags(t, r)
        for x in fl:
            k = x.split("(")[0]; tally[k] = tally.get(k, 0) + 1
        print(f"{i:2}. {t!r}")
        print(f"     roles: {spans}")
        print(f"     flags: {fl}\n")
    print("TALLY:", tally)
