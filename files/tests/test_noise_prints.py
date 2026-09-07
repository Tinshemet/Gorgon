"""The noise print catalogue: what it explains, what it refuses, and the trichotomy it computes.

The point of the catalogue is NOT similarity. `betamax` is two edits from `beta` and must still be
refused; `templ` is three from `template` and must be accepted. What licenses a repair is whether
every edit is a DECLARED corruption — so these tests are written as two lists, explained and
refused, and the refusals matter more than the acceptances.
"""
from orchestrator.languages.english import noise_prints as NP


# ── the prints, each against the evidence it was mined from ──────────────────────────────
def test_each_print_explains_its_own_evidence():
    cases = {
        ("running", "runnin"):     "truncate",
        ("stopped", "stpped"):     "drop-vowel",
        ("which", "whch"):         "drop-vowel",
        ("snapshot", "snaphot"):   "drop-consonant",
        ("snapshot", "snapshott"): "double",
        ("snapshot", "snaphsot"):  "transpose",
        ("grubnash", "grbunash"):  "transpose",
        ("gamma", "gamna"):        "key-adjacent",
        ("running", "rynning"):    "key-adjacent",
        ("restart", "restaert"):   "stray-key",
        ("clone", "clon"):         "truncate",
    }
    for (clean, obs), expected in cases.items():
        prints = NP.explain(clean, obs)
        assert prints is not None, f"{obs!r} should be explained as a corruption of {clean!r}"
        assert expected in prints, f"{clean!r} <- {obs!r} gave {prints}, expected {expected!r}"


def test_leet_is_a_closed_table_and_a_symbol_may_stand_for_two_letters():
    assert NP.explain("create", "cr34te") == ("leet", "leet")
    assert "i" in NP.LEET["1"] and "l" in NP.LEET["1"]      # a dict of single letters lost one


def test_a_composition_of_declared_prints_is_itself_declared():
    """27% of mined corruptions carried more than one print — the largest single family."""
    assert NP.explain("template", "templ") == ("drop-vowel", "truncate")


def test_a_truncation_is_one_act_not_one_per_letter():
    """Counting each cut letter made `templ` breach the bound and go unexplained."""
    assert NP.explain("status", "stat") == ("truncate",)


# ── the refusals: this is where the catalogue earns its keep ─────────────────────────────
def test_a_different_word_is_never_explained():
    """Enough declared prints compose into any word from any other. `walking` came back as four
    substitutions before the bound existed."""
    assert NP.explain("running", "walking") is None


def test_a_longer_word_that_merely_contains_the_short_one_is_refused():
    """`betamax` is a real product and `webserver` a plausible hostname — treating the extra
    letters as repeats would rewrite a name."""
    for clean, obs in (("beta", "betamax"), ("web", "webserver"),
                       ("db", "database"), ("alpha", "alphabetical")):
        assert NP.explain(clean, obs) is None, f"{clean!r} <- {obs!r} must not be explained"


def test_an_undeclared_symbol_is_refused():
    assert NP.explain("stop", "st%p") is None
    assert NP.explain("gamma", "gamma-ray") is None


def test_noise_further_than_a_third_of_the_word_is_a_different_word():
    assert NP.explain("running", "qzxwv") is None


# ── the trichotomy the caller acts on ────────────────────────────────────────────────────
def test_one_reading_is_a_repair_with_evidence():
    got = NP.explain_all("runnin", ["running", "stopped", "snapshot"])
    assert got == [("running", ("truncate",))]


def test_two_readings_are_an_ask_that_can_name_both():
    """Ambiguity is REPORTED, never resolved — the module ranks, the caller refuses to choose."""
    got = NP.explain_all("stpped", ["stopped", "stepped", "shipped"])
    assert [c for c, _ in got][:2] == ["stepped", "stopped"]
    assert len(got) > 1


def test_no_reading_is_an_ask_that_can_say_what_was_unreadable():
    assert NP.explain_all("qzxwv", ["running", "stopped", "snapshot"]) == []


def test_explaining_a_name_is_the_catalogue_s_job_refusing_it_is_the_caller_s():
    """`alpah` IS a transposition and the catalogue says so. The operator's ruling that a typo'd
    name is the name lives at the call site, not here — the two concerns stay separate."""
    assert NP.explain("alpha", "alpah") == ("transpose",)


def test_an_identical_word_carries_no_prints():
    assert NP.explain("running", "running") == ()
    assert NP.explain("running", "RUNNING") == ()          # case never blocks recognition


def test_two_letter_swaps_turn_a_word_into_a_different_word():
    """`restart` -> `restore` is two substitutions. Admitting it rewrote `restart` across eleven
    sealed corpus cases. The mechanical prints leave a wreck; substitution lands on real words."""
    assert NP.explain("restore", "restart") is None
    assert NP.explain("restart", "restore") is None


def test_one_letter_swap_is_still_a_print():
    assert NP.explain("down", "dawn") == ("substitute",)
    assert NP.explain("gamma", "gamna") == ("key-adjacent",)


def test_leet_is_exempt_from_the_swap_cap():
    """A digit standing for a letter cannot produce a real word, so two are still explained."""
    assert NP.explain("create", "cr34te") == ("leet", "leet")
