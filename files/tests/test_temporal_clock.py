"""THE CLOCK TAIL — the last trigger slot (qual-0005, held open by design until now).

`clock_in` has classified time phrases since 08-14 but carried no OFFSETS, so the eval
scored "at 21:30" as a missed trigger — deliberately, keeping the hole visible. This is
the offset-bearing reader: the phrase itself, locatable, closed shapes only.
"""
from orchestrator.seam import temporal as T


def test_the_measured_case():
    assert T.clock_tail("snapshot every vm at 21:30") == "at 21:30"


def test_the_am_pm_shape():
    assert T.clock_tail("stop every vm at 9pm") == "at 9pm"
    assert T.clock_tail("stop every vm at 9 pm") == "at 9 pm"


def test_noon_and_midnight():
    assert T.clock_tail("restart the db vm at midnight") == "at midnight"
    assert T.clock_tail("check the lab at noon") == "at noon"


def test_no_clock_no_tail():
    assert T.clock_tail("stop the vms at the door") is None
    assert T.clock_tail("launch every vm that is stopped") is None


def test_at_a_place_is_not_a_time():
    assert T.clock_tail("put the vm at the lab network") is None
