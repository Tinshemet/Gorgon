"""dialogbank.py — READ SOMEBODY ELSE'S GOLD ANNOTATIONS. DiAML-XML, parsed.

    PYTHONPATH=. python3 -m tests.bench.dialogbank <dir-or-file>     # what is in there
    PYTHONPATH=. python3 -m tests.bench.dialogbank <dir> --score     # us against them

# ⇒⇒ WHY THIS FILE EXISTS

Every number in this project is measured against a corpus one of us wrote — fourteen rungs, 48
controls, the door key, the stance key. **DialogBank is the first that is not.** Its dialogues
carry gold ISO 24617-2 annotations made by people who have never seen Gorgon, on conversations
that have nothing to do with a lab.

⇒ **AND THE PREDICTION WAS SEALED BEFORE THE DATA ARRIVED** — see `iso_probe.py`. Nothing named
  in it may be repaired before the run, or the corpus is spent without being used.

# ⇒ THE SHAPE OF A DiAML FILE, WHICH TAKES THREE HOPS TO GET FROM A LABEL TO ITS WORDS

    <dialogueAct dimension="task" communicativeFunction="instruct" target="#fsp1TSKCV0"/>
    <fs xml:id="fsp1TSKCV0"><f name="verbalComponent" fVal="#vesp1TSKCV0"/></fs>
    <spanGrp xml:id="vesp1TSKCV0"><span from="#wp11"/><span from="#wp12"/>…</spanGrp>
    <w xml:id="wp11">right</w>

A dialogue act names a FUNCTIONAL SEGMENT, the segment names a span group, the span group names
words. **The same segment may carry SEVERAL acts in several dimensions** — which is ISO's
multidimensionality, and the thing a single-label reading cannot express.

⇒ ⚠ **AND `_` IS A TOKEN IN THIS CORPUS**, standing for a non-verbal event — a cough, a pause.
  It is dropped: it is not a word anybody said, and leaving it in makes a segment look like it
  contains something it does not.
"""
import collections
import glob
import os
import re
from typing import Dict, List, NamedTuple, Optional, Tuple

_W = re.compile(r'<w xml:id="([^"]+)"[^>]*>([^<]*)</w>')
_SPANGRP = re.compile(r'<spanGrp xml:id="([^"]+)"[^>]*>(.*?)</spanGrp>', re.S)
_SPAN = re.compile(r'<span [^>]*from="#([^"]+)"')
_FS = re.compile(r'<fs xml:id="([^"]+)"[^>]*>(.*?)</fs>', re.S)
_FVAL = re.compile(r'fVal="#([^"]+)"')
_ACT = re.compile(r'<dialogueAct\b([^>]*)/?>')
_ATTR = re.compile(r'(\w+)="([^"]*)"')


class Gold(NamedTuple):
    """One annotated functional segment: the words, and every act laid on them."""
    dialogue: str
    text: str
    acts: Tuple[Tuple[str, str], ...]      # (dimension, communicativeFunction), in file order

    @property
    def dimensions(self) -> Tuple[str, ...]:
        return tuple(d for d, _ in self.acts)


def parse(path: str) -> List[Gold]:
    """Every functional segment in one DiAML file, with its gold acts."""
    raw = open(path, encoding="ISO-8859-1", errors="replace").read()
    words = {wid: text for wid, text in _W.findall(raw)}
    groups = {gid: _SPAN.findall(body) for gid, body in _SPANGRP.findall(raw)}
    segments: Dict[str, str] = {}
    for fid, body in _FS.findall(raw):
        got = _FVAL.search(body)
        if not got:
            continue
        # ⇒ `_` IS A NON-VERBAL EVENT, NOT A WORD. Dropped — see the module note.
        said = [words.get(w, "") for w in groups.get(got.group(1), ())]
        segments[fid] = " ".join(w for w in said if w and w != "_").strip()

    by_segment: Dict[str, List[Tuple[str, str]]] = collections.defaultdict(list)
    for attrs in _ACT.findall(raw):
        a = dict(_ATTR.findall(attrs))
        target = (a.get("target") or "").lstrip("#")
        if target:
            by_segment[target].append((a.get("dimension", ""),
                                       a.get("communicativeFunction", "")))

    name = os.path.basename(path)
    out = [Gold(name, segments[fid], tuple(acts))
           for fid, acts in by_segment.items() if segments.get(fid)]
    return out


def load(where: str) -> List[Gold]:
    """Every `.diaml` under a path — a file or a directory."""
    files = [where] if os.path.isfile(where) else sorted(glob.glob(os.path.join(where, "*.diaml")))
    out: List[Gold] = []
    for f in files:
        out.extend(parse(f))
    return out


# ⇒⇒ THEIR NAMES AND OURS. `iso.py` holds the dimension strings in the standard's own prose
#   form; the files use lowerCamelCase. One table, here, because this is the only place the two
#   spellings meet — and `contactManagement` has NO counterpart of ours, which is a fact about
#   our coverage rather than a parsing problem.
THEIRS = {
    "task": "Task",
    "autoFeedback": "Auto-Feedback",
    "alloFeedback": "Allo-Feedback",
    "turnManagement": "Turn Management",
    "timeManagement": "Time Management",
    "discourseStructuring": "Discourse Structuring",
    "ownCommunicationManagement": "Own Communication Management",
    "partnerCommunicationManagement": "Partner Communication Management",
    "socialObligationManagement": "Social Obligations Management",
    "contactManagement": "Contact Management",      # ⚠ a tenth dimension we never named
}


def score(rows: List[Gold]) -> Dict[str, object]:
    """Us against them, on DIMENSION and on FUNCTION, scored apart.

    ⇒ **A SEGMENT COUNTS AS A DIMENSION HIT IF ANY ACT WE EMIT MATCHES ANY GOLD ACT**, which is
      the generous reading and is the right one: ISO is multidimensional, and a segment may
      legitimately carry Task AND Auto-Feedback. Scoring it strictly would punish us for a
      structure the standard requires.
    ⇒ **AND THE TWO AXES ARE APART BECAUSE THEY FAIL DIFFERENTLY.** A wrong dimension means we
      did not know what the utterance was ABOUT; a wrong function means we knew and mislabelled
      it. One number over both would hide which.
    """
    from orchestrator.seam import iso

    dim_hit = fn_hit = 0
    confusion: Dict[Tuple[str, str], int] = collections.Counter()
    gold_dims: Dict[str, int] = collections.Counter()
    for row in rows:
        want_d = {THEIRS.get(d, d) for d, _ in row.acts}
        want_f = {f.lower() for _, f in row.acts}
        for d in want_d:
            gold_dims[d] += 1
        got = iso.annotate(row.text)
        ours_d = {a.dimension for a in got}
        ours_f = {a.function.lower().replace(" ", "") for a in got}
        if ours_d & want_d:
            dim_hit += 1
        else:
            for d in sorted(want_d):
                confusion[(d, sorted(ours_d)[0] if ours_d else "—")] += 1
        if ours_f & want_f:
            fn_hit += 1
    return {"n": len(rows), "dimension": dim_hit, "function": fn_hit,
            "confusion": confusion, "gold_dims": gold_dims}


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    where = next((a for a in argv if not a.startswith("--")), None)
    if not where:
        print("usage: python3 -m tests.bench.dialogbank <dir-or-file> [--score]")
        return 2
    rows = load(where)
    print(f"\n  {len(rows)} annotated functional segments from "
          f"{len({r.dialogue for r in rows})} dialogue(s)")

    dims = collections.Counter(d for r in rows for d in r.dimensions)
    print("\n  THEIR GOLD, BY DIMENSION")
    for d, n in dims.most_common():
        print(f"    {n:4}  {d}")

    if "--score" not in argv:
        for r in rows[:8]:
            print(f"\n    {r.text[:70]!r}")
            print(f"      gold {list(r.acts)}")
        return 0

    got = score(rows)
    n = got["n"] or 1
    print(f"\n{'─' * 96}")
    print(f"  US AGAINST THEM, on {got['n']} segments")
    print(f"    DIMENSION  {got['dimension']:4} / {got['n']}   {100 * got['dimension'] / n:.0f}%")
    print(f"    FUNCTION   {got['function']:4} / {got['n']}   {100 * got['function'] / n:.0f}%")
    print("\n  WHERE THE DIMENSION WENT WRONG — their gold -> what we said")
    for (want, ours), count in sorted(got["confusion"].items(), key=lambda kv: -kv[1])[:10]:
        print(f"    {count:4}  {want:32} -> {ours}")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
