"""SPLIT RECOGNITION — the fused-word cover (ledger #9), built AGAINST its measurement.

The v2.1 price (results/9d59f14-*): 4 spans, 3 acts, +3 halluc across 10 pairs, and the
damage sits exactly where a fusion hides a CLOSED word. The cover is the same family as
every front-door fix: an UNKNOWN token that splits into two known words is read apart —
but only where the grammar votes, the operator's sim-check principle:

  both halves closed          -> the strongest evidence, split (`isnot`, `onthe`)
  verb + tail, segment-initial-> `stopalpha.` · `then launchbeta`
  opener + tail, noun in reach-> `thedb vm`
  tail is a noun, opener near -> `the testvms`
  condition head, seg-initial -> `ifalpha is stopped`
Exactly one fitting split wins, with a notice; ambiguity or no vote changes NOTHING —
`cancel` never becomes `can cel`, `notice` never `not ice`.
"""
from orchestrator.seam import front_door as FD


# ── the measured damage this must heal ───────────────────────────────────────────────

def test_a_fused_verb_splits_at_segment_start():
    assert FD.read("stopalpha. then launchbeta.").text == "stop alpha. then launch beta."


def test_a_fused_testimony_frame_splits():
    v = FD.read("vm2 isnot working, it boots to a bluescreen")
    assert "is not working" in v.text


def test_a_fused_boundary_word_splits():
    assert "vm and" in FD.read("restart the web vmand thedb vm").text
    assert "vm except" in FD.read("stop every vmexcept thedb vm").text


def test_a_fused_courtesy_word_splits():
    assert "a chance" in FD.read("when you get achance, stop the testvms").text


def test_a_fused_opener_with_a_noun_in_reach():
    assert "the db vm" in FD.read("restart thedb vm").text


def test_a_fused_noun_with_an_opener_before():
    assert "test vms" in FD.read("stop the testvms").text


def test_a_fused_condition_head():
    assert FD.read("ifalpha is stopped, launch it").text == \
        "if alpha is stopped, launch it"


# ── what must NEVER split ────────────────────────────────────────────────────────────

def test_real_words_never_split():
    for w in ("cancel the vm", "notice the label", "the database is up",
              "free memory on the vm"):
        assert FD.read(w).text == w


def test_an_unvoted_fusion_stays():
    # `bluescreen` — neither half is a closed word; evidence-adjacent, untouched
    assert "bluescreen" in FD.read("it boots to a bluescreen").text


def test_quotes_stay_opaque_to_splits():
    assert "stopalpha" in FD.read("the log says 'stopalpha failed'").text


def test_offsets_map_back_through_the_split():
    original = "stopalpha. then launchbeta."
    v = FD.read(original)
    s = v.text.index("then")
    assert original[v.back[s]:].startswith("then")
