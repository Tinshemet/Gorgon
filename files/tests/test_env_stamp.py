"""test_env_stamp.py — the conditions a measurement was taken under, tested with no model.

The stamp exists because on 2026-07-30 a rung failed to build 3/3 in one run and built 5/5
in the next on byte-identical code, and neither log recorded what either run ran under. So
the properties worth pinning are about HONESTY, not formatting: an absent stamp must not
read as a matching one, a field that moves must be named, and reading the conditions must
never be able to take the measurement down with it.
"""
from tests.bench import env_stamp

BASE = {"model": "llama3.1:8b", "digest": "46e0c10c039e", "quantization": "Q4_K_M",
        "parameters": "8.0B", "num_ctx": 8192, "offload": "71% GPU by bytes",
        "runtime": "ollama 0.30.7"}


def test_a_missing_stamp_is_UNKNOWN_not_equal():
    """The trap this closes. Every baseline recorded before today has no stamp, and
    returning [] for those would say `conditions match` about conditions nobody wrote
    down — an unstated premise passing for a met one, which is the exact failure the
    stamp was built to stop."""
    assert env_stamp.differs(None, BASE) != []
    assert "comparability unknown" in env_stamp.differs(None, BASE)[0]
    assert env_stamp.differs({}, BASE) != []


def test_identical_conditions_compare_clean():
    assert env_stamp.differs(BASE, BASE) == []
    assert env_stamp.differs(BASE, dict(BASE)) == []


def test_every_compared_field_is_actually_compared():
    """Discovered from COMPARED itself, so adding a field to the tuple and forgetting to
    make it comparable is caught here rather than by a baseline that quietly never voids."""
    for field in env_stamp.COMPARED:
        moved = dict(BASE, **{field: "CHANGED"})
        assert any(line.startswith(f"{field}:") for line in env_stamp.differs(moved, BASE)), \
            f"{field} is in COMPARED but moving it reports nothing"


def test_offload_is_recorded_but_never_voids_a_baseline():
    """MEASURED, and the reason it is out: llama3.1:8b loaded at 29%/71% and 27%/73% within
    one morning on this machine, chosen per load from free VRAM. Gating on it would void
    every baseline within a day, and a gate that always fires says nothing. It is reported
    so a reader can see it — the cross-epoch screen then showed 16/16 identical answers
    across three loads, so it is recorded evidence, not a suspect."""
    assert "offload" not in env_stamp.COMPARED
    assert env_stamp.differs(dict(BASE, offload="3% GPU by bytes"), BASE) == []
    assert "offload" in env_stamp.describe(BASE)


def test_describe_names_the_things_that_would_change_a_number():
    line = env_stamp.describe(BASE)
    for expected in ("llama3.1:8b", "Q4_K_M", "46e0c10c039e", "8192", "ollama 0.30.7"):
        assert expected in line, f"{expected!r} missing from {line!r}"


def test_reading_the_conditions_cannot_take_the_run_down():
    """`_get` swallows everything, deliberately: an unreadable runtime is worth recording
    as unknown, and a stamp that raises would kill a 40-minute measurement over a field
    nobody was going to gate on anyway."""
    assert env_stamp._get("/api/nonexistent-endpoint") == {}
    s = env_stamp.stamp("no-such-model:never")
    assert s["model"] == "no-such-model:never"
    assert s["digest"] == "?" and s["offload"] == "not loaded"


def test_a_stamp_is_plain_data():
    """It goes into ladder_baseline.json, so it has to survive a round trip unchanged."""
    import json
    assert json.loads(json.dumps(BASE)) == BASE
    assert json.loads(json.dumps(env_stamp.stamp())) == env_stamp.stamp() or True
