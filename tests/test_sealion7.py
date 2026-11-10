from datetime import datetime, timedelta

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "sealion7", Path(__file__).resolve().parent.parent / "custom_components/ampx/sealion7.py"
)
import sys

_mod = importlib.util.module_from_spec(_spec)
sys.modules["sealion7"] = _mod
_spec.loader.exec_module(_mod)
ACTION_HOLD, ACTION_NONE, ACTION_START, ACTION_STOP = (
    _mod.ACTION_HOLD, _mod.ACTION_NONE, _mod.ACTION_START, _mod.ACTION_STOP
)
CarState, SlowChargeWatch, decide = _mod.CarState, _mod.SlowChargeWatch, _mod.decide
energy_needed_kwh, time_to_target_min = _mod.energy_needed_kwh, _mod.time_to_target_min

def at(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute)

def car(**kw):
    base = dict(soc=50.0, plugged=True, charging=False)
    base.update(kw)
    return CarState(**base)

def test_unplugged_is_none():
    assert decide(car(plugged=False), at(11)).action == ACTION_NONE

def test_starts_in_cheap_window():
    d = decide(car(), at(11))
    assert d.action == ACTION_START

def test_never_starts_in_peak():
    assert decide(car(), at(15)).action == ACTION_HOLD
    assert decide(car(charging=True), at(15)).action == ACTION_STOP

def test_waits_outside_window_overnight():
    assert decide(car(soc=60), at(2)).action == ACTION_HOLD

def test_min_soc_overrides_window():
    d = decide(car(soc=10), at(15))
    assert d.action == ACTION_START  # car safety (min_soc) beats peak pause

def test_stops_at_target():
    assert decide(car(soc=80, charging=True), at(11)).action == ACTION_STOP
    assert decide(car(soc=80), at(11)).action == ACTION_HOLD

def test_no_soc_does_not_touch_charger():
    d = decide(car(soc=None), at(11))
    assert d.action == ACTION_HOLD

def test_car_schedule_warns():
    d = decide(car(car_schedule_on=True), at(11))
    assert any("scheduled" in w for w in d.warnings)

def test_energy_and_time():
    assert energy_needed_kwh(50.0) == 12.0      # 30% of 40 kWh
    assert energy_needed_kwh(None) is None
    assert time_to_target_min(50.0) == 100      # 12 kWh / 7.2 kW
    assert time_to_target_min(90.0) == 0

def test_slow_charge_reported_after_five_minutes():
    w = SlowChargeWatch()
    c = car(charging=True, power_kw=3.0, voltage=235.0, current_a=30.2)
    t0 = at(11)
    assert w.update(c, t0) is None
    assert w.update(c, t0 + timedelta(minutes=4)) is None
    assert "Charging 3.0 kW" in w.update(c, t0 + timedelta(minutes=5))

def test_normal_charge_clears_watch():
    w = SlowChargeWatch()
    slow = car(charging=True, power_kw=3.0, voltage=235.0, current_a=30.2)
    fast = car(charging=True, power_kw=6.6, voltage=235.0, current_a=30.2)
    t0 = at(11)
    w.update(slow, t0)
    assert w.update(fast, t0 + timedelta(minutes=10)) is None
    assert w.update(slow, t0 + timedelta(minutes=11)) is None  # timer restarted
