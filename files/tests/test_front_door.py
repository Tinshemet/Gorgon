"""THE FRONT DOOR — junk out ASAP, one layer down (the operator, 2026-08-19).

The v2 degradation run priced two cells and the operator ruled them ONE defect:
a leading filler killed 9/10 instructed acts (the imperative-shape test never fired),
and a typo'd CLOSED-SET marker un-recognized its construct so the debris became op
targets (`stop_vm(sorry)`). Both are junk surviving past the entrance. The fix is not
per-consumer — it is ONE pass before ANY construct reads, producing a working VIEW
plus an offset map back to the original bytes, so spans still score at the original
offsets and names are never rewritten.
"""
import pytest

from orchestrator.languages.english.seam import front_door as FD


def test_a_typoed_marker_is_DECLINED_and_its_candidates_carried():
    """⇒⇒ **OPERATOR CHARTER, 2026-09-19 — THIS TEST ASSERTED THE OPPOSITE UNTIL THEN.**

    *"The front door should only fix typos on obviously wrong / non-existent words, fix noise,
    add commas and spaces where obvious. If anything changes meaning it's not the door's job —
    if it CAN alter a meaning we move it to route to ask. I would rather not serve something
    than serve something the user didn't ask for."*

    ⇒ `no wait` REDIRECTS the request. Creating one from a typo is the door deciding that the
      operator retracted something, on the evidence of a single transposed character. The
      repair is still FOUND — the door says so and carries the candidate — it is simply not
      APPLIED, and ROUTE asks.

    ⇒ The content-word repair in the same sentence (`restrt` -> `restart`) is untouched: that
      is the charter's first clause, an obviously wrong word with no meaning of its own.
    """
    v = FD.read("restrt the web vm, no wati, the db one")
    assert "no wait" not in v.text                  # the phrase is NOT created
    assert "wati" in v.text                         # the token is left exactly as typed
    assert "restart" in v.text                      # …while a content-word typo still repairs
    ask = [n for n in v.notices if "could not apply" in n and "wati" in n]
    assert ask, f"the decline must be SPOKEN, not silent: {v.notices}"
    assert "no wait" in ask[0], f"the candidate must be carried for ROUTE: {ask[0]}"
    # ⇒⇒ **THE OPERATION VERB'S TYPO IS REPAIRED TOO, and this line used to assert the
    #   opposite** — *"the operation verb's own typo is NOT a closed-set word — never
    #   touched"*. That reason was never true: `launch` IS a closed-set word and
    #   `test_typo_words::test_a_verb_sure_hit` has asserted `launhc` -> `launch` since the
    #   same day. The two tests contradicted each other and both passed only because
    #   `restart` was ABSENT from `scan._operation_words` — there was no candidate to repair
    #   toward, so the outcome looked like a rule and was an accident.
    #   ⇒ SAME TWO COMMITS AS THE DOCSTRING FIXED ON 09-17, SEVEN HOURS APART: `0f22b30`
    #     (2026-08-19 14:44) wrote this assertion; `07d0301` (21:42) landed N2 with the
    #     operator's ruling *"very distinct common words like thrm = them, OR EVEN VERBS —
    #     the system should try to correct it."* N2 superseded it. This is the THIRD and last
    #     artifact of that 14:44 draft — the NEVER-TOUCHES list and its `restrt` example were
    #     the other two — and it survived 30 days because the word it named was missing.
    assert "restart the web vm" in v.text
    assert any("restrt" in n for n in v.notices)


def test_a_name_is_never_rewritten():
    """The name rule is unchanged; the MARKER line moved to the charter (2026-09-19).

    ⇒ `i meant` REDIRECTS the request — it says the previous target was wrong. The door finds
      the candidate and declines it; what this test still guards is that `alpah`, a typo'd
      NAME, is left alone either way. That was always the point of the case.
    """
    v = FD.read("stop alpah — sorry, i mesnt beta")
    assert "i meant" not in v.text      # the marker is FOUND but not applied — charter
    assert any("could not apply" in n and "i meant" in n for n in v.notices)
    assert "alpah" in v.text            # the name's typo is the name
    assert "beta" in v.text


def test_courtesy_with_a_typo_is_DECLINED_because_it_would_raise_authority():
    """⚠ THE SHARPEST CASE ON THE CHARTER, and the reason it is not a style preference.

    [[gorgon-courtesy-escalates-intent]] (2026-08-14, LIVE, 7/7 phrasings): *"when you get a
    chance"* is an ACHIEVE marker — **a pleasantry grants write authority**. So repairing one
    character in `wehn` used to escalate a read into a write. The door now declines and says
    which authority the phrase would have asked for.
    """
    v = FD.read("wehn you get a chance, stop the test vms")
    assert "when you get a chance" not in v.text
    ask = [n for n in v.notices if "could not apply" in n]
    assert ask and "authority" in ask[0], f"the decline must name the stake: {v.notices}"


def test_a_filled_pause_is_dropped_and_offsets_map_back():
    original = "uh stop the vms on the lab network"
    v = FD.read(original)
    assert v.text == "stop the vms on the lab network"
    # a span found in the VIEW maps back to its ORIGINAL offsets
    s = v.text.index("the vms")
    e = s + len("the vms on the lab network")
    assert original[v.back[s]:v.back[e]] == "the vms on the lab network"


def test_evidence_is_opaque():
    # ruled: evidence is opaque testimony — nothing inside quotes is ever edited
    v = FD.read("the log says 'no wati, retrying'")
    assert "no wati" in v.text


def test_clean_text_is_the_identity():
    req = "stop the web vm and launch the db one"
    v = FD.read(req)
    assert v.text == req
    assert v.notices == []
    assert all(v.back[i] == i for i in range(len(req) + 1))


def test_a_real_word_pair_below_the_length_floor_is_left_alone():
    # `no way` is ed-1 inside... it is not: 3 chars < the floor — never touched
    v = FD.read("there is no way the db vm survives")
    assert "no way" in v.text


def test_mid_sentence_pause_with_commas():
    v = FD.read("stop it, um, right away")
    assert v.text == "stop it, right away"


# ── N3: the missing clause break is restored (operator-approved, sim-check principle:
#      only where the closed-class grammar votes; no vote, no comma) ─────────────────

def test_the_missing_comma_is_restored():
    assert FD.read("if alpha is stopped launch it").text == \
        "if alpha is stopped, launch it"
    assert FD.read("when the backup finishes snapshot the db vm").text == \
        "when the backup finishes, snapshot the db vm"


def test_two_breaks_restore_two_commas():
    v = FD.read("the web vm after you have checked the others restart it")
    assert v.text == "the web vm, after you have checked the others, restart it"


def test_comma_restore_composes_with_the_pause_drop():
    v = FD.read("uh if alpha is stopped launch it")
    assert v.text == "if alpha is stopped, launch it"
    # and offsets still land on the ORIGINAL bytes
    s = v.text.index("launch it")
    assert v.original[v.back[s]:].startswith("launch it")


def test_no_vote_no_comma():
    assert FD.read("stop alpha beta and gamma").text == "stop alpha beta and gamma"
    assert FD.read("how many machines carry the 'fleet' label").text == \
        "how many machines carry the 'fleet' label"


def test_comma_text_is_the_identity_still():
    req = "if alpha is stopped, launch it"
    assert FD.read(req).text == req


def test_the_testimony_comma_is_restored():
    v = FD.read("vm2 is not working it boots to a blue screen")
    assert v.text == "vm2 is not working, it boots to a blue screen"
