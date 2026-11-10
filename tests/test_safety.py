"""Write safety: frozen-reading watch and command dwell. Pure logic."""

from datetime import datetime, timedelta

from custom_components.ampx.safety import DEADBAND_KW, DWELL_S, STALE_AFTER_S, CommandGate, FreezeWatch

T0 = datetime(2026, 11, 10, 18, 0)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


# ---- FreezeWatch ------------------------------------------------------------
def test_changing_reading_is_never_stale():
    w = FreezeWatch()
    for i in range(0, STALE_AFTER_S * 2, 60):
        w.update("grid", 1000.0 + i, at(i))
    assert w.state("grid", at(STALE_AFTER_S * 2)) is None


def test_reading_stuck_on_one_value_is_reported_after_the_limit():
    w = FreezeWatch()
    w.update("grid", -5000.0, at(0))
    w.update("grid", -5000.0, at(STALE_AFTER_S - 1))
    assert w.state("grid", at(STALE_AFTER_S - 1)) is None
    w.update("grid", -5000.0, at(STALE_AFTER_S))
    assert w.state("grid", at(STALE_AFTER_S)) == "stuck"


def test_missing_reading_is_reported_after_the_limit():
    w = FreezeWatch()
    w.update("soc", None, at(0))
    assert w.state("soc", at(STALE_AFTER_S - 1)) is None
    assert w.state("soc", at(STALE_AFTER_S)) == "missing"


def test_battery_level_may_hold_one_value_but_not_go_missing():
    w = FreezeWatch()
    w.update("soc", 100.0, at(0))
    assert w.state("soc", at(STALE_AFTER_S * 6), may_hold=True) is None
    w.update("soc", None, at(STALE_AFTER_S * 6))
    assert w.state("soc", at(STALE_AFTER_S * 7), may_hold=True) == "missing"


def test_a_new_value_restarts_the_clock_and_clear_forgets():
    w = FreezeWatch()
    w.update("grid", 1.0, at(0))
    w.update("grid", 2.0, at(STALE_AFTER_S - 10))
    assert w.state("grid", at(STALE_AFTER_S + 10)) is None
    w.clear("grid")
    assert w.state("grid", at(STALE_AFTER_S * 5)) is None
    assert w.state("never_seen", at(0)) is None


# ---- CommandGate ------------------------------------------------------------
def test_change_inside_the_deadband_is_not_sent():
    g = CommandGate()
    assert not g.allow(5.0, 5.0 + DEADBAND_KW - 0.05, at(0), "house_only")
    assert g.allow(8.0, 8.2, at(0), "house_only")  # exactly the deadband counts as a change


def test_first_change_is_sent_then_lowering_waits_for_the_dwell():
    g = CommandGate()
    assert g.allow(5.0, 3.0, at(0), "house_only")
    g.sent(at(0), "house_only")
    assert not g.allow(3.0, 2.0, at(DWELL_S - 1), "house_only")
    assert g.allow(3.0, 2.0, at(DWELL_S), "house_only")


def test_urgent_change_skips_the_dwell_but_not_the_deadband():
    g = CommandGate()
    g.sent(at(0), "house_only")
    assert g.allow(3.0, 4.0, at(10), "house_only", urgent=True)
    assert not g.allow(3.0, 3.1, at(10), "house_only", urgent=True)


def test_a_new_reason_is_a_new_situation_and_is_sent_at_once():
    g = CommandGate()
    g.sent(at(0), "ev_first:export")
    assert g.allow(10.0, 8.2, at(5), "ev_first:trickle")


def test_unknown_current_power_is_always_sent():
    g = CommandGate()
    g.sent(at(0), "house_only")
    assert g.allow(None, 1.2, at(5), "house_only")
