"""multiwoz_manifest.py — A SECOND WORLD, WRITTEN AS A CONFIG AND NOTHING ELSE.

    PYTHONPATH=. python3 -m tests.bench.multiwoz_manifest        # what the scanner reads
    PYTHONPATH=. python3 -m tests.bench.multiwoz_manifest --score <dir>

# ⇒⇒ WRITING THIS FILE **IS** THE EXPERIMENT

The operator, 2026-08-16: *"a good reader works no matter what it reads, the reader just needs
to be able to extract information and label it correctly, thats it."*

The WRITER's portability is proven — 1932/2000 across two unrelated domains. The READER's has
only ever been claimed. **If the scanner reads MultiWOZ with nothing but this config, D6 is
answered and the reader is portable. If it needs a line of code changed, that is the answer
too, and a more useful one than any percentage.**

⇒ **AND THE CHICKEN-AND-EGG IS REAL AND IS NOT AN EXCUSE.** The operator again: *"we cant
  create a corpus this large for gorgon until we have it."* No corpus of typed lab requests
  exists because the product that would generate one is what we are building. MultiWOZ is the
  nearest thing with the right SHAPE — 3,842 typed user turns per file, span-annotated against
  a declared inventory of attributes, which is exactly what a manifest is.

# ⇒ WHAT MULTIWOZ ANNOTATES, AND WHY IT IS THE HALF THAT MATTERS

    the ACT     3 user-side kinds — Inform · Request · general-*.  SHALLOWER THAN OURS,
                and useful only as a floor: can we tell an instruction from a question
    the SLOTS   15 types, span-marked, with values.  `departure = norwich` ·
                `arriveby = 18:00` · `bookpeople = 4`
                ⇒ **THIS IS `scan.conditions_from`'s EXACT JOB.** `{arriveby: 18:00}` and
                  `{status: running}` are the same operation over a different manifest

# ⇒ THE SHAPE OF A KIND, AND WHAT IS DELIBERATELY LEFT OUT

A manifest row carries what the WRITER needs — creators, setters, acts, delete — and what the
READER needs: `nouns`, `attrs`, `aliases`, `attr_values`, `key`. **Only the reader's half is
filled here.** Nothing plans against this world; asking for `create` rows would be inventing
capability MultiWOZ never describes, and a manifest that claims tools it does not have is the
thing `gorgon-built-and-never-called` is about.

⇒ ⚠ **AND THE ALIASES ARE THE INTERESTING COLUMN.** `leaving from` -> departure,
  `arrive by` -> arriveby, `price range` -> pricerange. Those are the operator's words for the
  slot, which is exactly what `vm.aliases` holds for `ram` -> memory_mb. If the reader needs
  MORE than aliases to read this domain, the aliases are not carrying what we thought.
"""
from typing import Dict

# ⇒ THE FIVE DOMAINS MULTIWOZ'S USER TURNS TALK ABOUT. `police` and `hospital` are dropped —
#   they carry no slots on the user side in the files fetched.
KINDS: Dict[str, dict] = {
    "train": {
        "package": "multiwoz",
        "key": "trainid",
        "nouns": ["train", "trains", "rail", "service"],
        "attrs": ["trainid", "departure", "destination", "day", "arriveby", "leaveat",
                  "bookpeople"],
        "aliases": {
            "from": "departure", "leaving": "departure", "depart": "departure",
            "to": "destination", "arriving": "destination", "arrive": "arriveby",
            "arriveby": "arriveby", "by": "arriveby", "leave": "leaveat",
            "leaveat": "leaveat", "people": "bookpeople", "tickets": "bookpeople",
            "passengers": "bookpeople",
        },
        "attr_values": {"day": ["monday", "tuesday", "wednesday", "thursday", "friday",
                                "saturday", "sunday"]},
    },
    "restaurant": {
        "package": "multiwoz",
        "key": "name",
        "nouns": ["restaurant", "restaurants", "place to eat", "eatery"],
        "attrs": ["name", "area", "food", "pricerange", "bookday", "booktime", "bookpeople"],
        "aliases": {
            "cuisine": "food", "type of food": "food", "serving": "food",
            "price": "pricerange", "pricerange": "pricerange", "cost": "pricerange",
            "part of town": "area", "side": "area", "location": "area",
            "people": "bookpeople", "table for": "bookpeople",
            "day": "bookday", "time": "booktime",
        },
        "attr_values": {
            "pricerange": ["cheap", "moderate", "expensive"],
            "area": ["centre", "north", "south", "east", "west"],
            "bookday": ["monday", "tuesday", "wednesday", "thursday", "friday",
                        "saturday", "sunday"],
        },
    },
    "hotel": {
        "package": "multiwoz",
        "key": "name",
        "nouns": ["hotel", "hotels", "guesthouse", "guest house", "lodging", "place to stay"],
        "attrs": ["name", "area", "pricerange", "stars", "type", "parking", "internet",
                  "bookday", "bookstay", "bookpeople"],
        "aliases": {
            "price": "pricerange", "pricerange": "pricerange",
            "part of town": "area", "side": "area", "location": "area",
            "star": "stars", "rating": "stars",
            "nights": "bookstay", "people": "bookpeople", "day": "bookday",
            "wifi": "internet", "wi-fi": "internet",
        },
        "attr_values": {
            "pricerange": ["cheap", "moderate", "expensive"],
            "area": ["centre", "north", "south", "east", "west"],
            "type": ["hotel", "guesthouse"],
            "parking": ["yes", "no"], "internet": ["yes", "no"],
        },
    },
    "attraction": {
        "package": "multiwoz",
        "key": "name",
        "nouns": ["attraction", "attractions", "museum", "college", "park", "cinema",
                  "theatre", "gallery"],
        "attrs": ["name", "area", "type"],
        "aliases": {"part of town": "area", "side": "area", "location": "area",
                    "kind": "type", "sort": "type"},
        "attr_values": {"area": ["centre", "north", "south", "east", "west"]},
    },
    "taxi": {
        "package": "multiwoz",
        "key": "taxiid",
        "nouns": ["taxi", "taxis", "cab", "car"],
        "attrs": ["taxiid", "departure", "destination", "arriveby", "leaveat"],
        "aliases": {"from": "departure", "to": "destination",
                    "arrive": "arriveby", "leave": "leaveat", "pick": "departure"},
        "attr_values": {},
    },
}


def read_with(text: str):
    """What the scanner extracts from one MultiWOZ turn, against THIS manifest.

    ⇒ **NOTHING IS PASSED BUT THE CONFIG.** `use_kinds` swaps the module-level manifest and
      `Board()` picks it up; `anchors_in`, `scan` and `conditions_from` are called exactly as
      they are for the lab. If this function needs a special case, the reader is not portable.
    """
    from planner.formula.legal import Board
    from planner.ir import config as _config
    from orchestrator.languages.english.seam import scan as SC

    with _config.use_kinds(KINDS):
        board = Board()
        out = []
        for anchor in SC.anchors_in(text, board):
            got = SC.scan(anchor, text, board)
            if not got:
                continue
            where = SC.conditions_from(got.modifiers, got.kind, board, span=got.span)
            out.append((anchor, got.kind, got.count, where, got.span))
        return out


def gold_turns(where: str):
    """Every USER turn that INTRODUCES a slot value, with the values it introduced.

    ⇒ ⚠ **THE STATE IS CUMULATIVE AND MUST BE DIFFED.** MultiWOZ carries the whole dialogue
      state on every turn, so turn 9 still lists the departure named in turn 1. Scoring against
      the raw state asks a reader to extract from one sentence everything said in nine, which
      is not a reading task at all — it credits nothing and punishes everything. The DELTA is
      what this turn said.
    """
    import glob
    import json
    import os

    rows = []
    files = ([where] if os.path.isfile(where)
             else sorted(glob.glob(os.path.join(where, "dialogues_*.json"))))
    for path in files:
        for dialogue in json.load(open(path)):
            seen = {}
            for turn in dialogue.get("turns") or []:
                state = {}
                for frame in turn.get("frames") or []:
                    for slot, vals in ((frame.get("state") or {})
                                       .get("slot_values") or {}).items():
                        if vals:
                            state[slot] = str(vals[0]).lower()
                if turn.get("speaker") != "USER":
                    continue
                new = {k: v for k, v in state.items() if seen.get(k) != v}
                seen.update(state)
                if new:
                    rows.append((turn.get("utterance") or "", new))
    return rows


def score(rows) -> dict:
    """Us against MultiWOZ's gold slots — recall, precision, and WHERE THE MISSES LIVE.

    ⇒ **THE THREE-WAY SPLIT IS THE POINT, NOT THE PERCENTAGE.** A miss is one of three
      different bugs and they are fixed in different files: no anchor was found at all
      (`anchors_in`), the value sat inside a span we DID scan but was not converted
      (`conditions_from`), or the value fell outside the span we drew (`scan`). One number
      over all three says only that something is wrong.
    """
    hit = miss_noanchor = miss_inspan = miss_outspan = miss_absent = 0
    spurious = emitted = 0
    by_slot: Dict[str, int] = {}
    for text, gold in rows:
        got = read_with(text)
        # ⇒ **THE SPANS WE ACTUALLY DREW, NOT THE SENTENCE.** A first cut tested `value in
        #   text` here and so reported ZERO out-of-span misses — every value present anywhere
        #   counted as in-span, which made the one bucket that measures `scan`'s BOUNDARIES
        #   permanently empty. A classifier that cannot report a category is not measuring it.
        spans = [str(g[4] or "").lower() for g in got]
        ours = set()
        for _anchor, kind, _count, where, _span in got:
            for attr, val in (where or {}).items():
                ours.add((str(kind), str(attr), str(val).lower()))
        emitted += len(ours)
        low = text.lower()
        for slot, value in gold.items():
            domain, _, attr = slot.partition("-")
            attr = attr.replace(" ", "")
            if (domain, attr, value) in ours:
                hit += 1
                continue
            by_slot[attr] = by_slot.get(attr, 0) + 1
            if value not in low:
                miss_absent += 1
            elif not spans:
                miss_noanchor += 1
            elif any(value in s for s in spans):
                miss_inspan += 1
            else:
                miss_outspan += 1
    n = sum(len(g) for _t, g in rows) or 1
    spurious = max(0, emitted - hit)
    return {"turns": len(rows), "gold": n, "hit": hit, "emitted": emitted,
            "recall": 100.0 * hit / n,
            "precision": 100.0 * hit / (emitted or 1),
            "no_anchor": miss_noanchor, "in_span": miss_inspan,
            "out_span": miss_outspan, "absent": miss_absent,
            "spurious": spurious, "by_slot": by_slot}


def main(argv=None) -> int:                                       # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--score" in argv:
        at = argv.index("--score")
        where = argv[at + 1] if at + 1 < len(argv) else "."
        rows = gold_turns(where)
        got = score(rows)
        print(f"\n  {got['turns']} user turns that introduce a slot · "
              f"{got['gold']} gold slot-values")
        print(f"    RECALL      {got['hit']:5} / {got['gold']}   {got['recall']:.0f}%")
        print(f"    PRECISION   {got['hit']:5} / {got['emitted']}   {got['precision']:.0f}%")
        print("\n  WHERE THE MISSES LIVE")
        for label, key in (("no anchor found", "no_anchor"), ("in a scanned span", "in_span"),
                           ("outside the span", "out_span"),
                           ("not literally present", "absent")):
            print(f"    {got[key]:5}  {label}")
        print("\n  MISSES BY SLOT")
        for slot, count in sorted(got["by_slot"].items(), key=lambda kv: -kv[1])[:12]:
            print(f"    {count:5}  {slot}")
        return 0
    samples = [
        "I need train reservations from norwich to cambridge",
        "I'd like to leave on Monday and arrive by 18:00.",
        "Can you book me a table for 11:00 on Friday?",
        "I am looking for a cheap restaurant in the centre",
        "I want a 4 star hotel with free wifi in the north",
        "book it for 3 people and 2 nights",
        "I need a taxi from the hotel to the restaurant",
    ]
    print("\n  THE SCANNER, POINTED AT A MANIFEST IT HAS NEVER SEEN\n")
    for t in samples:
        print(f"  {t!r}")
        got = read_with(t)
        if not got:
            print("       — nothing read")
        for anchor, kind, count, where, _span in got:
            print(f"       {anchor:14} kind={str(kind):11} count={str(count):5} {where or '{}'}")
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
