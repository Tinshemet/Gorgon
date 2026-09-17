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
from orchestrator.languages.english.seam import front_door as FD

# ⇒⇒ **THE SPEC ABOVE HAS A PRECONDITION IT NEVER STATED: THE NAMES MUST BE DECLARED.** Three of
#   its five rules split a fusion whose second half is a NAME — `thedb vm`, `stopalpha`,
#   `ifalpha is stopped` — and until 2026-09-17 the pass was never told which names exist, so it
#   licensed the free half from a NEIGHBOUR instead. In `stop the X vm` the next token is `vm`, a
#   noun, and that alone tore every word opening with `an`/`no`/`all`/`me`: `antiseptic` ->
#   `an tiseptic`, 188 of 6000 sampled dictionary words, 3.13%.
#   ⇒ EVERY ASSERTION BELOW IS UNCHANGED and every one still passes; what changed is that the
#     lab is now DECLARED, which is what production does too since `pipeline.run` began handing
#     the door `world.names()`. A call with no lab is a different question — *may the door guess
#     at a name nobody told it about* — and the answer to that one is no.
LAB = ("alpha", "beta", "web", "db", "test", "vm2", "core", "lab", "dmz")


# ── the measured damage this must heal ───────────────────────────────────────────────

def test_a_fused_verb_splits_at_segment_start():
    assert FD.read("stopalpha. then launchbeta.", known=LAB).text == "stop alpha. then launch beta."


def test_a_fused_testimony_frame_splits():
    v = FD.read("vm2 isnot working, it boots to a bluescreen", known=LAB)
    assert "is not working" in v.text


def test_a_fused_boundary_word_splits():
    assert "vm and" in FD.read("restart the web vmand thedb vm", known=LAB).text
    assert "vm except" in FD.read("stop every vmexcept thedb vm", known=LAB).text


def test_a_fused_courtesy_word_splits():
    assert "a chance" in FD.read("when you get achance, stop the testvms", known=LAB).text


def test_a_fused_opener_with_a_noun_in_reach():
    assert "the db vm" in FD.read("restart thedb vm", known=LAB).text


def test_a_fused_noun_with_an_opener_before():
    assert "test vms" in FD.read("stop the testvms", known=LAB).text


def test_a_fused_condition_head():
    assert FD.read("ifalpha is stopped, launch it", known=LAB).text == \
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


# ── a flag is a code shape: an obvious leading-dash token is left whole (2026-09-14) ──────
#    A `-`/`--` + letter run is shell option syntax; recognising it is syntactic, so the front
#    door leaves it BYTE-IDENTICAL and names it — the decision (real option? which vms?) is
#    READ/ROUTE's, the layer with the world. Extends the 2026-09-07 "detect code shapes" ruling.

def test_a_flag_is_not_split_even_when_it_holds_a_function_word():
    # `the` inside `--all-the-vms` used to make the separator pass read it as a fused sentence
    assert FD.read("stop --all-the-vms").text == "stop --all-the-vms"
    assert FD.read("get --no-color output").text == "get --no-color output"
    assert FD.defused("stop --all-the-vms") == "stop --all-the-vms"


def test_a_flag_is_named_as_a_code_shape():
    v = FD.read("stop --all-the-vms")
    assert any("--all-the-vms" in n and "flag" in n for n in v.notices)


def test_a_real_fused_sentence_still_opens_without_a_leading_dash():
    assert FD.read("do-not-stop beta").text == "do not stop beta"
    assert "which vms r stopped" in FD.read("which-vms-r-stopped").text


def test_obvious_enough_a_dash_before_a_digit_is_not_a_flag():
    # `-5gb` is dash+digit, a value shape — recognition stays conservative, nothing is named
    v = FD.read("resize the db to -5gb")
    assert not any("flag" in n for n in v.notices)
