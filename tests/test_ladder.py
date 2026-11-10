"""Battery decision ladder: first match wins, every verdict names its rule and reason."""

from dataclasses import replace

from custom_components.ampx import ladder as L
from custom_components.ampx.safety import DWELL_S
from custom_components.ampx.tariff import OFF_PEAK, PEAK, SHOULDER

# Off-peak evening, inverter in Normal, plenty in the battery, AmpX in charge of it.
BASE = L.Inputs(period=OFF_PEAK, mode=L.NORMAL, soc=80.0, reserve=20.0, house_rule=True,
                spare_kwh=10.0, ev_kw=0.0, acting=True, export_pays=False)


def v(**kw):
    return L.evaluate(replace(BASE, **kw))


def test_nothing_special_is_self_consumption():
    out = v()
    assert (out.rule, out.action) == (L.SELF, L.NONE) and out.reason


def test_stale_readings_hand_a_forced_dispatch_back_and_beat_every_other_rule():
    out = v(stale="battery level missing for 10 min", mode=L.DISCHARGE, period=PEAK, spare_kwh=0.0, ev_kw=7.0)
    assert (out.rule, out.action) == (L.STALE, L.HAND_BACK)
    assert "battery level missing" in out.reason
    assert v(stale="grid reading stuck for 10 min").action == L.NONE  # nothing forced: nothing to hand back


def test_peak_never_charges_the_battery_from_the_grid():
    out = v(period=PEAK, mode=L.CHARGE)
    assert (out.rule, out.action) == (L.PEAK_GUARD, L.STOP_CHARGE)
    assert v(period=SHOULDER, mode=L.CHARGE).action == L.TOPUP
    assert v(period=OFF_PEAK, mode=L.CHARGE).action == L.TOPUP  # the owner's own off-peak charge is left alone


def test_ev_on_the_grid_with_nothing_to_spare_puts_battery_on_house_only():
    out = v(ev_kw=7.0, spare_kwh=0.2)
    assert (out.rule, out.action) == (L.EV_GRID, L.HOUSE_ONLY)
    assert v(ev_kw=7.0, spare_kwh=5.0).action == L.NONE  # battery has spare: it may feed the car
    assert v(ev_kw=7.0, spare_kwh=0.2, acting=False).action == L.NONE  # AmpX is not running the battery
    assert v(ev_kw=7.0, spare_kwh=0.2, house_rule=False).action == L.NONE
    assert v(ev_kw=7.0, spare_kwh=0.2, period=SHOULDER).action == L.NONE


def test_house_only_holds_through_a_short_ev_dip_then_resumes():
    held = v(house_only=True, mode=L.DISCHARGE, ev_kw=0.0, spare_kwh=0.2, held_s=DWELL_S - 1)
    assert (held.rule, held.action) == (L.EV_GRID, L.HOUSE_ONLY)
    done = v(house_only=True, mode=L.DISCHARGE, ev_kw=0.0, spare_kwh=0.2, held_s=DWELL_S)
    assert (done.rule, done.action) == (L.SELF, L.RESUME)


def test_house_only_ends_at_once_when_the_window_or_control_changes():
    for change in (dict(period=SHOULDER), dict(period=PEAK), dict(acting=False), dict(house_rule=False), dict(spare_kwh=None)):
        out = v(house_only=True, mode=L.DISCHARGE, ev_kw=7.0, held_s=0.0, **change)
        assert out.action == L.RESUME, change


def test_forced_export_stops_at_the_house_share():
    out = v(mode=L.DISCHARGE, spare_kwh=0.5, export_pays=True)
    assert (out.rule, out.action) == (L.HOUSE_RULE, L.STOP_DISCHARGE)
    assert v(mode=L.DISCHARGE, spare_kwh=0.5, export_pays=True, house_rule=False, source=L.MANUAL).action == L.EXPORT


def test_forced_export_stops_at_the_reserve_even_without_the_house_rule():
    out = v(mode=L.DISCHARGE, soc=21.0, house_rule=False, export_pays=True)
    assert (out.rule, out.action) == (L.RESERVE, L.STOP_DISCHARGE) and "20%" in out.reason


def test_no_export_when_it_does_not_pay_unless_the_owner_started_it():
    out = v(mode=L.DISCHARGE, export_pays=False, source=L.AUTOPILOT)
    assert (out.rule, out.action) == (L.EXPORT_CAP, L.STOP_DISCHARGE)
    assert v(mode=L.DISCHARGE, export_pays=False, source=None).rule == L.EXPORT_CAP  # unknown starter is capped
    assert v(mode=L.DISCHARGE, export_pays=False, source=L.MANUAL).rule == L.MANUAL
    assert v(mode=L.DISCHARGE, export_pays=True, source=L.AUTOPILOT).rule == L.AUTOPILOT


def test_peak_ev_the_battery_cannot_carry_is_flagged_after_battery_actions():
    out = v(period=PEAK, ev_kw=7.0, spare_kwh=1.0)
    assert (out.rule, out.action) == (L.PEAK_GUARD, L.PAUSE_EV)
    assert v(period=PEAK, ev_kw=7.0, spare_kwh=20.0).action == L.NONE
    # a forced export with nothing to spare is stopped first
    assert v(period=PEAK, ev_kw=7.0, spare_kwh=0.2, mode=L.DISCHARGE, export_pays=True).action == L.STOP_DISCHARGE


def test_running_dispatch_names_who_started_it():
    assert v(mode=L.DISCHARGE, export_pays=True, source=L.PLAN).rule == L.PLAN
    assert v(mode=L.CHARGE, period=SHOULDER, source=L.PLAN).action == L.TOPUP
    assert v(mode=L.DISCHARGE, export_pays=True, source=L.AUTOPILOT).action == L.EXPORT
    assert v(mode=L.CHARGE, period=SHOULDER, source=None).rule == L.MANUAL


def test_every_rule_is_listed_in_priority_order():
    assert L.RULES[:5] == (L.STALE, L.PEAK_GUARD, L.EV_GRID, L.RESERVE, L.HOUSE_RULE)
    assert L.RULES[-1] == L.SELF and len(set(L.RULES)) == len(L.RULES)
    assert L.WRITES == {L.HAND_BACK, L.STOP_CHARGE, L.HOUSE_ONLY, L.RESUME, L.STOP_DISCHARGE}
