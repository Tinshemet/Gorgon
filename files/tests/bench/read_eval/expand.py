"""expand.py — GROW THE SET: mechanical noise twins over the CERTIFIED release.

    PYTHONPATH=. python3 -m tests.bench.read_eval.expand              # build + validate
    PYTHONPATH=. python3 -m tests.bench.read_eval.expand --emit       # write v2-draft + verdicts
    PYTHONPATH=. python3 -m tests.bench.read_eval.expand --show typos # eyeball a noise type

# ⇒⇒ THE SPEC'S §4.3, MECHANICAL HALF — and why it starts from v1.jsonl, never seeds.py

Noised twins inherit their gold from a CLEAN TWIN THE OPERATOR ALREADY CERTIFIED — that is
the whole economy of the pairing (the review's fast path: "is the noise faithful?"). So the
source is the FROZEN release, byte-certified, and the 59 clean cases ride into the draft
unchanged: their verdicts are PRE-SEEDED into the draft's review file (same bytes, same
hashes, still valid), and the operator reviews only the twins.

# ⇒ EVERY NOISER IS DETERMINISTIC — seeded by the case id, so a re-emit is byte-stable and
#   a re-review is never caused by regeneration ([[gorgon-seed-dependence]] applied to data).

    terse     articles and courtesy dropped — "web vm restart now" is the operator's own
              likely register (spec: probably the DOMINANT real one)
    typos     keyboard-adjacent swaps/drops INSIDE words, spans included — a typo'd span is
              still the gold span, WITH its typo (spec §1)
    no-punct  lowercase, terminal punctuation gone, run-on
    voice     transcription-ish: lowercase, apostrophes and colons collapsed, small numbers
              spelled out, a leading filler
    list-form v3.1 — "stop: alpha, beta, gamma": one act, its members as a colon list
    shouting  v3.1 — ALL CAPS and three bangs; offsets untouched, casing is the noise
    (embedded-junk and code-switch are DEFERRED with the identifier work — ledger item 8)

# ⇒ THE OFFSET MAP IS THE WHOLE TRICK. Every edit records old->new index; spans, actions and
#   triggers are converted THROUGH the map and the schema validator then re-proves every
#   offset against the new surface. A twin that fails validation is DROPPED AND REPORTED —
#   never patched by hand, because hand-typed offsets are hand-typed bugs.

# ⇒ PROPORTIONS: 30 terse · 30 typos · 19 no-punct · 10 voice = 89 twins + 59 clean = 148,
#   which is the spec's ~150 first release at its own declared 40% clean / 60% noise
#   assumption. Selection round-robins the strata so every stratum gets noise.
"""
import hashlib
import json
import os
import random
import re
from typing import Dict, List, Optional, Tuple

from .schema import CLEAN, load, validate

CASES_DIR = os.path.join(os.path.dirname(__file__), "cases")
V1 = os.path.join(CASES_DIR, "v1.jsonl")
COUNTS = {"terse": 30, "typos": 30, "no-punct": 19, "voice": 10, "fused": 10}

_ARTICLES = {"a", "an", "the"}
_COURTESY = ("please ", "kindly ")
_NUMBERS = {"2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
            "7": "seven", "8": "eight", "9": "nine", "10": "ten"}
_NEIGHBOURS = {"a": "s", "e": "r", "i": "o", "o": "i", "n": "m", "t": "r", "s": "a",
               "r": "e", "l": "k", "d": "s", "c": "v", "m": "n", "p": "o", "v": "c"}


def _edit(sentence: str, edits: List[Tuple[int, int, str]]) -> Tuple[str, List[int]]:
    """Apply (start, end, replacement) edits; return the new text and an OLD->NEW index map
    of length len(sentence)+1 so span boundaries convert exactly."""
    edits = sorted(edits)
    out, mapping, at, new_at = [], [0] * (len(sentence) + 1), 0, 0
    for start, end, rep in edits:
        for i in range(at, start):
            mapping[i] = new_at
            new_at += 1
        out.append(sentence[at:start])
        for i in range(start, end):
            mapping[i] = new_at            # every replaced char points at the replacement
        out.append(rep)
        new_at += len(rep)
        at = end
    for i in range(at, len(sentence)):
        mapping[i] = new_at
        new_at += 1
    out.append(sentence[at:])
    mapping[len(sentence)] = new_at
    return "".join(out), mapping


def _tokens(sentence: str):
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[\w:']+", sentence)]


def _noise_edits(noise: str, sentence: str, rng: random.Random):
    edits = []
    if noise == "terse":
        for word, s0, e0 in _tokens(sentence):
            if word.lower() in _ARTICLES:
                gap = 1 if e0 < len(sentence) and sentence[e0] == " " else 0
                edits.append((s0, e0 + gap, ""))
        for c in _COURTESY:
            at = sentence.lower().find(c)
            if at >= 0:
                edits.append((at, at + len(c), ""))
    elif noise == "typos":
        words = [t for t in _tokens(sentence) if len(t[0]) >= 4 and t[0].isalpha()]
        rng.shuffle(words)
        for word, s0, e0 in words[:max(2, len(words) // 3)]:
            k = rng.randrange(3)
            i = rng.randrange(1, len(word) - 1)
            if k == 0:                        # swap two inner letters
                rep = word[:i] + word[i + 1] + word[i] + word[i + 2:]
            elif k == 1:                      # drop one letter
                rep = word[:i] + word[i + 1:]
            else:                             # keyboard-adjacent substitution
                rep = word[:i] + _NEIGHBOURS.get(word[i], word[i]) + word[i + 1:]
            edits.append((s0, e0, rep))
    elif noise == "no-punct":
        for m in re.finditer(r"[,.?!;—–]", sentence):
            gap = (m.end() < len(sentence) and sentence[m.end()] == " "
                   and m.start() > 0 and sentence[m.start() - 1] == " ")
            edits.append((m.start(), m.end(), ""))
    elif noise == "fused":
        # ⇒ a missing SPACE is a typo class of its own — ledger #9, the operator
        #   (08-19): "does the typo also cover two words or more as one string?".
        #   Fuse one or two adjacent word pairs; never across punctuation. The gold
        #   inherits through the offset map exactly like every other class.
        toks = _tokens(sentence)
        pairs = []
        for i in range(len(toks) - 1):
            w1, s0, e0 = toks[i]
            w2, s1, e1 = toks[i + 1]
            if sentence[e0:s1] == " " and w1.isalpha() and w2.isalpha():
                pairs.append((i, e0, s1))
        rng.shuffle(pairs)
        seen: set = set()
        for i, e0, s1 in pairs:
            if i in seen or i + 1 in seen:
                continue
            seen |= {i, i + 1}
            edits.append((e0, s1, ""))
            if len(edits) == 2:
                break
    elif noise == "voice":
        for m in re.finditer(r"[,.?!;—–':]", sentence):
            edits.append((m.start(), m.end(), ""))
        for word, s0, e0 in _tokens(sentence):
            if word in _NUMBERS:
                edits.append((s0, e0, _NUMBERS[word]))
    return edits


def _convert(item: dict, mapping: List[int], new_sentence: str) -> Optional[dict]:
    start, end = mapping[item["start"]], mapping[item["end"]]
    text = new_sentence[start:end].strip()
    s2 = start + (len(new_sentence[start:end]) - len(new_sentence[start:end].lstrip()))
    out = dict(item)
    out["start"], out["end"], out["text"] = s2, s2 + len(text), text
    if not text:
        return None
    return out


def twin(case: dict, noise: str, trial: int = 1) -> Optional[dict]:
    # ⇒ RANDOMIZED TRIALS (the operator, 08-18): the rng seed carries a TRIAL index, so the
    #   noise is randomized in character yet byte-stable per trial — trial 1 always yields
    #   the same twin, trial 2 a genuinely different randomization of the same case. A new
    #   release can draw a fresh trial without ever changing a frozen one, and a dropped
    #   (case, noise) pair gets retried on later trials before giving up.
    rng = random.Random(int(hashlib.sha256(f"{case['id']}:{noise}:{trial}".encode())
                            .hexdigest()[:8], 16))
    sentence = case["sentence"]
    if noise == "list-form":
        # ⇒ v3.1 SURFACE class (structure_map: BULLET LIST) — "stop: alpha, beta, gamma".
        #   Needs the GOLD, not just the text: one act, two or more objects after it. The
        #   space after the act becomes ": " (the act's end offset stays before the colon)
        #   and every " and " between members becomes ", ". Any other shape: no twin.
        acts, spans = case["gold"]["actions"], case["gold"]["spans"]
        if len(acts) != 1 or any("trigger" in a or "manner" in a for a in acts):
            return None
        a_end = acts[0]["end"]
        members = sorted((sp for sp in spans if sp["start"] > a_end and sp["type"] == "object"),
                         key=lambda sp: sp["start"])
        tagged = any(isinstance(o, dict) for at in case["gold"]["attachments"]
                     for o in at["objects"])
        if len(members) < 2 or tagged or a_end >= len(sentence) or sentence[a_end] != " ":
            return None
        # members must be COORDINATED — nothing but ", " / " and " / ", and " between them;
        # "give the web vm the ip 10.0.0.7" has two spans and is not a list
        joins = [sentence[p["end"]:q["start"]] for p, q in zip(members, members[1:])]
        if any(j not in (", ", " and ", ", and ") for j in joins) or members[0]["start"] != a_end + 1:
            return None
        edits = [(a_end, a_end + 1, ": ")]
        for p, q in zip(members, members[1:]):
            if sentence[p["end"]:q["start"]] != ", ":
                edits.append((p["end"], q["start"], ", "))
    else:
        edits = _noise_edits(noise, sentence, rng)
    new_sentence, mapping = _edit(sentence, edits)
    if noise in ("no-punct", "voice"):
        new_sentence = new_sentence.lower()
    if noise == "voice":
        new_sentence = "uh " + new_sentence
        mapping = [m + 3 for m in mapping]
    if noise == "shouting":
        # ⇒ v3.1 SURFACE class — ALL CAPS plus bangs. Per-character upper so no length
        #   changes (ß -> SS would break the map); the bangs go after every offset.
        new_sentence = "".join(c.upper() if len(c.upper()) == 1 else c
                               for c in new_sentence) + "!!!"
    if new_sentence.strip() == sentence.strip():
        return None                            # the noise changed nothing — no twin
    gold = {"spans": [], "actions": [], "attachments": case["gold"]["attachments"]}
    if "hint" in case["gold"]:          # v2.3: kind + gloss, no offsets — inherited verbatim
        gold["hint"] = dict(case["gold"]["hint"])
    if "mood" in case["gold"]:          # v2.4: a mood is a SPAN — it converts like any other
        gold["mood"] = []
        for m in case["gold"]["mood"]:
            conv = _convert(m, mapping, new_sentence)
            if conv is None:
                return None
            gold["mood"].append(conv)
    for s in case["gold"]["spans"]:
        got = _convert(s, mapping, new_sentence)
        if got is None:
            return None
        gold["spans"].append(got)
    for a in case["gold"]["actions"]:
        got = _convert(a, mapping, new_sentence)
        if got is None:
            return None
        for channel in ("trigger", "manner"):      # v2.0: manner rides like trigger
            if channel in a:
                conv = _convert(a[channel], mapping, new_sentence)
                if conv is None:
                    return None
                got[channel] = conv
        gold["actions"].append(got)
    suffix = f"-{noise[0]}{noise[-1]}" + (f".t{trial}" if trial > 1 else "")
    out = {"id": f"{case['id']}{suffix}", "stratum": case["stratum"],
           "noise": noise, "pair_id": case["id"], "source": "seed-expansion",
           "sentence": new_sentence, "gold": gold}
    for carried in ("store", "outcome"):         # v2.0 / v2.2: inherited verbatim
        if carried in case:
            out[carried] = case[carried]
    return out


def build(trial: int = 1) -> Tuple[List[dict], List[str]]:
    clean = load(V1)
    by_stratum: Dict[str, List[dict]] = {}
    for c in clean:
        by_stratum.setdefault(c["stratum"], []).append(c)
    order = []                                  # stratum round-robin, id-stable
    strata = sorted(by_stratum)
    pools = {s: sorted(by_stratum[s], key=lambda c: c["id"]) for s in strata}
    while any(pools.values()):
        for s in strata:
            if pools[s]:
                order.append(pools[s].pop(0))
    twins, dropped, used = [], [], set()
    for noise, want in COUNTS.items():
        made = 0
        for case in order:
            if made >= want:
                break
            if (case["id"], noise) in used:
                continue
            used.add((case["id"], noise))
            got = None
            for t in range(trial, trial + 3):      # retry a dud on the next trials
                got = twin(case, noise, t)
                if got is not None:
                    break
            if got is None:
                dropped.append(f"{case['id']}:{noise} — no trial produced a valid twin")
                continue
            faults = validate(clean + twins + [got])
            if faults:
                dropped.append(f"{got['id']} — {faults[0]}")
                continue
            twins.append(got)
            made += 1
    return clean + twins, dropped


def build_v21(trial: int = 1):
    """v2.1 = the frozen v2 (148, certified) + the FUSED twins of its clean cases."""
    v2_path = os.path.join(CASES_DIR, "v2.jsonl")
    cases = [json.loads(l) for l in open(v2_path, encoding="utf-8")]
    clean = [c for c in cases if c["noise"] == CLEAN]
    by_stratum: dict = {}
    for c in clean:
        by_stratum.setdefault(c["stratum"], []).append(c)
    order = []
    pools = {st: sorted(by_stratum[st], key=lambda c: c["id"]) for st in sorted(by_stratum)}
    while any(pools.values()):
        for st in sorted(pools):
            if pools[st]:
                order.append(pools[st].pop(0))
    twins, dropped, made = [], [], 0
    for case in order:
        if made >= COUNTS["fused"]:
            break
        got = None
        for t in range(trial, trial + 3):
            got = twin(case, "fused", t)
            if got is not None:
                break
        if got is None:
            dropped.append(f"{case['id']}:fused — no trial produced a valid twin")
            continue
        faults = validate(cases + twins + [got])
        if faults:
            dropped.append(f"{got['id']} — {faults[0]}")
            continue
        twins.append(got)
        made += 1
    return cases + twins, dropped


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    trial = int(argv[argv.index("--trial") + 1]) if "--trial" in argv else 1
    cases, dropped = build(trial)
    twins = [c for c in cases if c["noise"] != CLEAN]
    print(f"  {len(cases)} cases: {len(cases) - len(twins)} certified clean + "
          f"{len(twins)} twins")
    for n in COUNTS:
        print(f"    {n:9} {sum(1 for t in twins if t['noise'] == n)}")
    if dropped:
        print(f"  dropped ({len(dropped)}):")
        for d in dropped[:10]:
            print(f"    {d}")
    if "--show" in argv:
        kind = argv[argv.index("--show") + 1]
        for t in twins:
            if t["noise"] == kind:
                print(f"    {t['pair_id']:14} {t['sentence']!r}")
        return 0
    if "--emit-v21" in argv:
        cases21, dropped21 = build_v21(trial)
        for d in dropped21:
            print(f"    dropped: {d}")
        path = os.path.join(CASES_DIR, "v21-draft.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for c in cases21:
                fh.write(json.dumps(c) + "\n")
        import shutil
        shutil.copyfile(os.path.join(CASES_DIR, "v2.review.json"),
                        os.path.join(CASES_DIR, "v21-draft.review.json"))
        fused = [c for c in cases21 if c["noise"] == "fused"]
        print(f"  {len(cases21)} cases -> {path}")
        print(f"  148 verdicts pre-seeded — the operator reviews ONLY the {len(fused)} fused twins:")
        for t in fused:
            print(f"    {t['pair_id']:14} {t['sentence']!r}")
        return 0
    if "--emit" in argv:
        path = os.path.join(CASES_DIR, "v2-draft.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for c in cases:
                fh.write(json.dumps(c) + "\n")
        # pre-seed the verdicts: the 59 clean cases are byte-identical to the certified
        # release, so their accepted verdicts remain TRUE of these bytes
        import shutil
        src = os.path.join(CASES_DIR, "v1.review.json")
        dst = os.path.join(CASES_DIR, "v2-draft.review.json")
        shutil.copyfile(src, dst)
        print(f"  -> {path}")
        print(f"  -> {dst}  (59 clean verdicts pre-seeded — the operator reviews ONLY twins)")
        return 0
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
