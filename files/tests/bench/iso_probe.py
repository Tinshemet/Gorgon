"""iso_probe.py — WHAT THE ISO EMITTER SAYS ABOUT THE CORPUS WE HAVE, AND WHAT IT CANNOT SAY.

    PYTHONPATH=. python3 -m tests.bench.iso_probe            # the rungs, in ISO's vocabulary
    PYTHONPATH=. python3 -m tests.bench.iso_probe --arms     # and every mutation arm

# ⇒⇒ WHAT PHASE 5 WAS FOR, AND WHY THIS FILE IS NOT IT YET — SAID FIRST

The plan was to measure READ against **DialogBank**, the collection of dialogues carrying gold
ISO 24617-2 annotations. That would be the first number in this project not measured against a
corpus one of us wrote, which is the standing ceiling on every figure here.

⇒ ⚠ **THE CORPUS IS PUBLISHED AND ITS ANNOTATIONS ARE NOT MACHINE-FETCHABLE FROM HERE.** The
  site (Saarland, formerly Tilburg) offers DiAML-XML, DiAML-MultiTab and DiAML-TabSW, and
  serves the annotations themselves as PAGE IMAGES beside downloadable CONVERTER TOOLS. So the
  gold labels cannot be pulled and compared automatically without somebody fetching the corpus
  first.
  ⇒ **WHAT IS NEEDED IS ONE DOWNLOAD**, not a design: the DiAML-XML files for any one
    collection — Map Task, Switchboard, TRAINS or DBOX. `score()` below takes gold in exactly
    that shape and is written to be pointed at them.

⇒ **SO THIS MEASURES WHAT IT HONESTLY CAN**: the corpus we do have, in ISO's terms. That is not
  the external measurement and it is not nothing — it is the first time the rungs have been
  read in a vocabulary somebody else defined.

# ⇒⇒ AND THE ARMS MAKE IT A REAL MEASUREMENT RATHER THAN A PRINTOUT

`mutate.py` defines four arms over the fourteen rungs, and the arms are the gold:

    literal   the rung as written                    every one an Instruct
    filler    the same goal wrapped in politeness    **MUST ANNOTATE IDENTICALLY** — a courtesy
                                                     changes stance, never the act
    asked     a wh-frame around the goal             Instruct -> Set Question
    framed    greeting + meta-control + the frame    Greeting · Pausing · Set Question

⇒ **THE `filler` ROW IS THE ONE THAT CARRIES INFORMATION.** N2 measured that a courtesy cost 12
  SERVE / 2 ASK -> 0 SERVE at the PROGRAM level. At the ACT level it should cost nothing at
  all, because being polite does not change what you asked for — and an annotator that says
  otherwise is reading stance as illocution, which is the mistake the whole taxonomy exists to
  stop.
# ⇒⇒⇒ THE SEALED PREDICTION — WRITTEN 2026-08-16, BEFORE ANY DIALOGBANK DATA WAS IN HAND
#
# Rule V5: a measurement gets its expected answer written down BEFORE it runs. It matters more
# here than anywhere else in this project, because this is the FIRST measurement not made
# against a corpus one of us wrote — and therefore the one most tempting to rationalise
# afterwards. The operator, the same day: *"i do want you to not rig the test"* · *"if it fails
# it fails."*
#
# ⇒ **THE HEADLINE: I EXPECT THIS TO GO BADLY, AND FOR A REASON THAT IS NOT A DEFECT.** Every
#   rule in `speech_act` was built against lab-administration English — fourteen rungs about
#   virtual machines. DialogBank is human-human conversation about maps, trains and telephone
#   small talk. **A reader that transfers well would be the surprise.**
#
#   DIMENSION   40-60%.  `Task` is the plurality of segments in any task-oriented dialogue and
#               we emit it by default, so this number is inflated by a coin landing our way.
#   FUNCTION    25-40%.  Lower, and the honest one: we emit SIX functions and ISO has ~30.
#
# ⇒⇒ **AND THE BIGGEST SINGLE MISS WILL BE FEEDBACK, WHICH IS A WRONG ANSWER RATHER THAN A
#   GAP.** Real dialogue is full of *"okay"*, *"mm-hm"*, *"right"*, *"yeah"* — Auto- and
#   Allo-Positive, and by some counts a fifth of all segments. We emit NEITHER, and worse, the
#   producer test will reach EXPRESSIVE for them and we will confidently answer **Social
#   Obligations Management / Greeting**. A systematic wrong label, not a decline.
#
# ⇒ THREE MORE, NAMED SO THEY CANNOT BE CLAIMED AS INSIGHTS AFTERWARDS:
#     1  TURN MANAGEMENT will be ~0. There is no floor to contest in a CLI and we never built it
#     2  Our `Set Question` will over-fire, because every wh-question we can read is one and ISO
#        splits Set / Check / Choice
#     3  The QUALIFIERS will be near-empty — three of four are read and `sentiment` is declined,
#        and conversational data carries far more sentiment than a lab request does
#
# ⚠ **AND WHAT WOULD MAKE THIS MEASUREMENT WORTHLESS IS FIXING ANY OF THE ABOVE FIRST.** Nothing
#   named in this prediction may be repaired before the run. A rule may change for a reason
#   found elsewhere; it may not change because it is listed here.
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

from orchestrator.seam import iso
from tests.bench.mutate import apply
from tests.bench.rungs import RUNGS


class Row(NamedTuple):
    n: int
    arm: str
    text: str
    acts: Tuple[str, ...]          # "dimension/function" per segment, in order
    qualifiers: Tuple[str, ...]


def _lab():
    """The real lab, so a bare NAME is a member rather than a word nobody owns.

    ⇒ ⚠ **THE FIRST RUN FORGOT IT, AND CORRECTING THAT DID NOT FIX WHAT I BLAMED ON IT.** Rung
      3's literal comes back `Task/Instruct + Social Obligations Management/GREETING` because
      *"put web on lab"* names no manifest kind, and the REAL LAB DOES NOT HOLD `web` EITHER —
      so `names_something` is false with a world or without one and the producer test reaches
      EXPRESSIVE. That is the documented no-member degradation, not a probe defect and not a
      reader defect: **a bare name is a member or it is nothing, and only the lab decides.**
      Passing the world is still right; it simply was not the cause.
    """
    try:
        from tests.bench.twopass.metrics import Lab
        return Lab()
    except Exception:                                             # pragma: no cover
        return None


def read_arm(n: int, text: str, arm: str, world=None) -> Row:
    got = iso.annotate(text, world=world)
    return Row(n, arm, text,
               tuple(f"{a.dimension}/{a.function or '—'}" for a in got),
               tuple(sorted({f"{k}={v}" for a in got for k, v in a.qualifiers.items()})))


def over_rungs(arms: Optional[List[str]] = None) -> List[Row]:
    out: List[Row] = []
    world = _lab()
    for r in RUNGS:
        out.append(read_arm(r.n, r.goal, "literal", world))
        for arm in (arms or ()):
            out.append(read_arm(r.n, apply(r.goal, arm), arm, world))
    return out


def over_rungs_bare(arms: Optional[List[str]] = None) -> List[Row]:
    """The same reading with NO LAB — the honest floor, printed beside the other."""
    out: List[Row] = []
    for r in RUNGS:
        out.append(read_arm(r.n, r.goal, "literal", None))
        for arm in (arms or ()):
            out.append(read_arm(r.n, apply(r.goal, arm), arm, None))
    return out


def score(gold: List[Tuple[str, str, str]]) -> Dict[str, object]:
    """Compare the emitter against EXTERNAL gold — (text, dimension, function) per segment.

    ⇒⇒ **THIS IS THE FUNCTION PHASE 5 EXISTS FOR AND IT HAS NO DATA YET.** It takes gold in the
      shape DiAML-XML yields — one row per functional segment, with its dimension and its
      communicative function — so pointing it at a downloaded DialogBank collection is a
      parsing job and not a design one.

    ⇒ **AND IT SCORES THE TWO AXES APART, because they fail differently.** Getting the
      DIMENSION wrong means we did not know what the utterance was ABOUT; getting the FUNCTION
      wrong means we knew and mislabelled it. One number over both would hide which.
    """
    dim_hit = fn_hit = 0
    misses: List[str] = []
    for text, want_dim, want_fn in gold:
        got = iso.annotate(text)
        first = got[0] if got else None
        d = first.dimension if first else ""
        f = first.function if first else ""
        dim_hit += 1 if d == want_dim else 0
        fn_hit += 1 if f == want_fn else 0
        if (d, f) != (want_dim, want_fn):
            misses.append(f"{text!r}  want {want_dim}/{want_fn}  got {d}/{f or '—'}")
    return {"n": len(gold), "dimension": dim_hit, "function": fn_hit, "misses": misses}


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    arms = ["filler", "asked", "framed"] if "--arms" in argv else []

    # ⇒⇒ ⚠ **BOTH CONDITIONS, ALWAYS, AND THE REASON IS A CORRECTION.** The first run of this
    #   probe had no lab; rung 3 came back with a GREETING segment; I added a lab and wrote
    #   that the probe had been wrong. **IT HAD NOT BEEN** — the result is identical either
    #   way, because the real lab does not hold `web` either. The instrument was changed in
    #   response to a reading I did not like, on a reason that was false.
    #   ⇒ The operator, 2026-08-16: *"i do want you to not rig the test"* · *"if it fails it
    #     fails."* So neither condition is chosen: both are run and both are printed, and the
    #     difference between them is a finding rather than a setting.
    rows = over_rungs(arms)
    bare = {(r.n, r.arm): r for r in over_rungs_bare(arms)}
    by_rung: Dict[int, Dict[str, Row]] = {}
    for r in rows:
        by_rung.setdefault(r.n, {})[r.arm] = r

    print(f"\n  THE FOURTEEN RUNGS, IN ISO 24617-2's VOCABULARY"
          f"{'  ·  and every arm' if arms else ''}")
    for n in sorted(by_rung):
        lit = by_rung[n]["literal"]
        print(f"\n  rung {n:2}  {lit.text[:66]}")
        print(f"          {' + '.join(lit.acts)}"
              + (f"   [{' · '.join(lit.qualifiers)}]" if lit.qualifiers else ""))
        for arm in arms:
            row = by_rung[n].get(arm)
            if not row:
                continue
            same = "  same" if row.acts == lit.acts else "  MOVED"
            print(f"      {arm:8}{same}  {' + '.join(row.acts)}"
                  + (f"   [{' · '.join(row.qualifiers)}]" if row.qualifiers else ""))

    print(f"\n{'─' * 96}")
    lits = [by_rung[n]["literal"] for n in sorted(by_rung)]
    shapes: Dict[str, int] = {}
    for r in lits:
        shapes[" + ".join(r.acts)] = shapes.get(" + ".join(r.acts), 0) + 1
    print("  THE LITERAL ARM, BY SHAPE   (with the real lab)")
    for shape, count in sorted(shapes.items(), key=lambda kv: -kv[1]):
        print(f"    {count:2}  {shape}")
    differ = [n for n in sorted(by_rung)
              if bare[(n, "literal")].acts != by_rung[n]["literal"].acts]
    print(f"  and WITH NO LAB, {len(differ)} of {len(lits)} rungs read differently"
          + (f": {differ}" if differ else " — the lab changes nothing here, which is itself"
             " the answer to whether passing one was a thumb on the scale"))

    if arms:
        print("\n  THE ARMS, AGAINST THE LITERAL — and `filler` is the one that carries news")
        for arm in arms:
            moved = [n for n in sorted(by_rung)
                     if arm in by_rung[n] and by_rung[n][arm].acts != by_rung[n]["literal"].acts]
            note = ""
            if arm == "filler":
                note = ("   ⚠ A COURTESY MUST NOT MOVE THE ACT — it changes stance, never "
                        "illocution" if moved else "   ⇒ a courtesy costs NOTHING at the act "
                        "level, which is what the taxonomy predicts")
            print(f"    {arm:8} {len(moved):2} of {len(lits)} rungs moved{note}")
            for n in moved[:6]:
                print(f"        rung {n:2}  {' + '.join(by_rung[n]['literal'].acts)}"
                      f"   ->   {' + '.join(by_rung[n][arm].acts)}")

    print(f"\n  ⚠ AND THIS IS NOT THE EXTERNAL MEASUREMENT. `score()` is written and has no "
          f"data:\n    DialogBank publishes its gold annotations as page images beside "
          f"converter tools,\n    so the comparison needs the DiAML-XML for one collection "
          f"downloaded first.")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
