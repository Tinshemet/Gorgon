"""The structural difficulty axis — computed from the gold, nobody ranks it (08-22 split)."""
from tests.bench.read_eval.difficulty import FEATURES, structural


def _case(sentence, spans, actions, attachments, **extra):
    c = {"id": "t-0001", "stratum": "s", "noise": "clean", "pair_id": None, "source": "seed",
         "sentence": sentence,
         "gold": {"spans": spans, "actions": actions, "attachments": attachments}}
    c.update(extra)
    return c


def test_a_plain_order_counts_two():
    c = _case("stop alpha", [{"text": "alpha", "start": 5, "end": 10, "type": "object"}],
              [{"text": "stop", "start": 0, "end": 4}], [{"action": 0, "objects": [0]}])
    f = structural(c)
    assert f["structural"] == 2 and f["spans"] == 1 and f["acts"] == 1
    assert all(f[k] == 0 for k in FEATURES if k not in ("spans", "acts"))


def test_every_feature_is_counted_once():
    s = "stop it and launch them one at a time"
    c = _case(s,
              [{"text": "it", "start": 5, "end": 7, "type": "object"},
               {"text": "them", "start": 19, "end": 23, "type": "object"},
               {"text": "one at a time", "start": 24, "end": 37, "type": "evidence"}],
              [{"text": "stop", "start": 0, "end": 4},
               {"text": "launch", "start": 12, "end": 18,
                "manner": {"text": "one at a time", "start": 24, "end": 37}},
               {"text": "stop it and launch them one at a time", "start": 0, "end": 37,
                "kind": "rule"}],
              [{"action": 0, "objects": [{"span": 0, "role": "patient"}]},
               {"action": 1, "objects": [1, 2]}],
              context={"expecting": "yes-no"}, store=[{"word": "x"}, {"word": "y"}])
    c["gold"]["mood"] = [{"kind": "urgency", "text": "one at a time", "start": 24, "end": 37}]
    f = structural(c)
    assert f == {"spans": 3, "acts": 3, "asks": 1, "channels": 1, "roles": 1, "fan": 1,
                 "anaphora": 2, "nesting": 2, "moods": 1, "context": 1, "store": 2,
                 "empty": 0, "structural": 18}


def test_an_empty_reading_is_its_own_feature():
    c = _case("yeah", [], [], [], outcome="context-needed", context={"expecting": "yes-no"})
    f = structural(c)
    assert f["empty"] == 1 and f["context"] == 1 and f["structural"] == 2


def test_the_sum_is_unit_weight_and_declared():
    c = _case("stop the blue ones",
              [{"text": "the blue ones", "start": 5, "end": 18, "type": "object"}],
              [{"text": "stop", "start": 0, "end": 4}], [{"action": 0, "objects": [0]}])
    f = structural(c)
    assert f["anaphora"] == 1
    assert f["structural"] == sum(f[k] for k in FEATURES)
