"""48-hour planner (pure)."""

from datetime import date, datetime

from custom_components.cortex import autopilot_rules as rules
from custom_components.cortex.planner import BatterySpec, Plan, best_plan, simulate
from custom_components.cortex.tariff import FixedTOU, Plan as Tariff, battery_budget

LOAD = [0.6] * 6 + [1.0] * 4 + [0.8] * 6 + [1.6] * 5 + [1.0] * 3


def test_tariff_interface_slots_and_holidays():
    tar = FixedTOU(Tariff(), lambda d: d == date(2026, 11, 6))
    slots = tar.slots(datetime(2026, 11, 5, 15, 40), 48, 30)
    assert len(slots) == 96 and slots[0][0] == datetime(2026, 11, 5, 15, 30)
    assert tar.rate(datetime(2026, 11, 5, 17, 0)) == (41.91, 28.0, "peak")
    assert tar.rate(datetime(2026, 11, 6, 17, 0))[2] == "off_peak"  # public holiday: no peak
    assert tar.rate(datetime(2026, 11, 5, 12, 0))[1] == 3.0  # midday feed-in is 3c, not 28c


def test_plan_beats_doing_nothing_and_respects_reserve():
    r = best_plan(datetime(2026, 11, 5, 16, 30), FixedTOU(Tariff()), 90, BatterySpec(), LOAD, 1, 45)
    assert r["saving"] >= 0 and r["min_soc"] >= 19.5 and r["candidates"] > 100
    assert len(r["rows"]) == 96 and r["floor"] in (0,) + tuple(range(30, 91, 10))
    # a dull day tomorrow, battery low at night: it should top up in the cheap window
    r = best_plan(datetime(2026, 11, 5, 22, 0), FixedTOU(Tariff()), 30, BatterySpec(), LOAD, 0, 5)
    assert r["topup"] >= 60


def test_exporting_is_never_free():
    """Exporting at 28c and buying back at 32c overnight must lose to keeping the energy."""
    spec = BatterySpec(cycle_cost_c=3.0)
    tar = FixedTOU(Tariff())
    slots = tar.slots(datetime(2026, 11, 5, 17, 0), 48, 30)
    load = [LOAD[t.hour] * 0.5 for t, *_ in slots]
    pv = [0.0] * len(slots)  # no solar at all
    keep = simulate(Plan(0, 0, 17), slots, load, pv, 60, spec)
    dump = simulate(Plan(0, 30, 17), slots, load, pv, 60, spec)
    assert keep.cost < dump.cost


def test_budget_uses_the_hourly_profile():
    prof = [0.5] * 24
    prof[18] = 3.0
    b = battery_budget(datetime(2026, 11, 5, 18, 0), 70.0, 50.0, 20.0, Tariff(), 24.0, 0.0, prof)
    assert b["house"] == 3.0 + 15 * 0.5  # one big evening hour, then quieter ones until 10:00


def test_from_plan_keeps_the_night_floor():
    ctx = {"soc": 80.0, "battery_kwh": 50.0, "export_floor": 30.0, "avg_daily_load": 40.0, "night_share": 0.5,
           "topup_kw": 10.0, "export_kw": 7.0}
    d = rules.from_plan(rules.EXPORT, {"floor": 30, "saving": 1.2}, ctx)
    assert d["do"] and d["floor_soc"] == 50  # 20 kWh of night use + 10% margin beats the plan's 30%
    d = rules.from_plan(rules.TOPUP, {"topup": 90, "saving": 0.5}, ctx)
    assert d["do"] and d["target_soc"] == 90
    assert not rules.from_plan(rules.TOPUP, {"topup": 0}, ctx)["do"]
