"""The decision ladder wired to the battery: stale hand-back, peak guard, floors, export cap, dwell."""

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx import ladder
from custom_components.ampx.const import DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY, SCHEMA

MODE, POWER, SOC = LEGACY["dispatch_mode"], LEGACY["dispatch_power"], LEGACY["battery_soc"]
GRID, EV, PV, BATT = LEGACY["studio_grid"], LEGACY["studio_ev"], LEGACY["studio_pv"], LEGACY["studio_battery"]


def _record(hass: HomeAssistant) -> list:
    """Stand in for the inverter: remember every write, and let mode and power take effect."""
    sent: list = []
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press")):
        async def rec(call, d=domain, s=svc):
            sent.append((d, s, dict(call.data)))
            if d == "select":
                hass.states.async_set(call.data["entity_id"], call.data["option"])
            if d == "number" and call.data["entity_id"] == POWER:
                hass.states.async_set(POWER, str(call.data["value"]))
        hass.services.async_register(domain, svc, rec)
    return sent


async def _setup(hass: HomeAssistant, data: dict | None = None, **opts):
    async_mock_service(hass, "notify", "send_message")
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={} if data is None else data, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def when(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 10, hour, minute, tzinfo=dt_util.get_default_time_zone())  # a Tuesday


def flows(hass: HomeAssistant, grid_kw: float, ev_kw: float, batt_discharge_kw: float, pv_kw: float = 0.0) -> None:
    hass.states.async_set(GRID, str(grid_kw), {"unit_of_measurement": "kW"})
    hass.states.async_set(EV, str(ev_kw), {"unit_of_measurement": "kW"})
    hass.states.async_set(PV, str(pv_kw), {"unit_of_measurement": "kW"})
    hass.states.async_set(BATT, str(batt_discharge_kw), {"unit_of_measurement": "kW"})  # this sensor reads + for discharge


async def test_missing_battery_level_hands_the_battery_back(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    hass.states.async_set(SOC, "unavailable")
    assert await brain.energy.house_guard(when(18, 0)) is None  # not yet: a blip is not a fault
    assert await brain.energy.house_guard(when(18, 5)) is None
    assert await brain.energy.house_guard(when(18, 10)) == "handed_back"
    assert hass.states.get(MODE).state == ladder.NORMAL
    assert any(d == "button" for d, _, _ in sent)
    last = brain.journal.last
    assert last["rule"] == ladder.STALE and last["action"] == ladder.HAND_BACK and "battery level missing" in last["reason"]


async def test_grid_reading_stuck_during_a_forced_dispatch_hands_back(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "80")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    flows(hass, grid_kw=-5.0, ev_kw=0.0, batt_discharge_kw=6.0)
    for minute in (0, 5):
        assert await brain.energy.house_guard(when(18, minute)) is None
    assert await brain.energy.house_guard(when(18, 10)) == "handed_back"
    assert "grid reading stuck" in brain.journal.last["reason"]


async def test_a_steady_grid_reading_is_not_stale_while_the_battery_reading_moves(hass: HomeAssistant):
    """A rounded grid reading can sit still under an export limit. A frozen meter link freezes both readings."""
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "80")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    for minute, batt in ((0, 6.0), (5, 6.1), (10, 6.2), (15, 6.1)):
        flows(hass, grid_kw=-5.0, ev_kw=0.0, batt_discharge_kw=batt)
        assert await brain.energy.house_guard(when(18, minute)) is None
    assert hass.states.get(MODE).state == ladder.DISCHARGE


async def test_a_quiet_grid_reading_is_fine_when_nothing_is_forced(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "80")
    hass.states.async_set(MODE, ladder.NORMAL)
    flows(hass, grid_kw=0.0, ev_kw=0.0, batt_discharge_kw=1.0)
    for minute in (0, 10, 20, 30):
        assert await brain.energy.house_guard(when(22, minute)) is None
    assert sent == [] and brain.journal.last["rule"] == ladder.SELF


async def test_peak_stops_a_running_grid_charge(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "50")
    hass.states.async_set(MODE, ladder.CHARGE)
    flows(hass, grid_kw=5.0, ev_kw=0.0, batt_discharge_kw=-4.0)
    assert await brain.energy.house_guard(when(11, 0)) is None  # cheap window: charging is the plan
    assert hass.states.get(MODE).state == ladder.CHARGE
    flows(hass, grid_kw=5.2, ev_kw=0.0, batt_discharge_kw=-4.0)
    assert await brain.energy.house_guard(when(17, 30)) == "charge_stopped"  # peak is 16:00 to 20:00 by default
    assert hass.states.get(MODE).state == ladder.NORMAL
    assert brain.journal.last["rule"] == ladder.PEAK_GUARD


async def test_export_outside_the_paying_window_is_capped_unless_the_owner_started_it(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    hass.states.async_set(MODE, ladder.DISCHARGE)  # started by something AmpX did not see
    assert await brain.energy.house_guard(when(22, 0)) == "export_capped"
    assert hass.states.get(MODE).state == ladder.NORMAL and brain.journal.last["rule"] == ladder.EXPORT_CAP
    # the owner's own export from the panel is left alone
    assert await brain.energy.start_export(True, 5.0, 40) == "started"
    assert brain.energy.dispatch_source == ladder.MANUAL
    assert await brain.energy.house_guard(when(22, 1)) is None
    assert hass.states.get(MODE).state == ladder.DISCHARGE and brain.journal.last["rule"] == ladder.MANUAL


async def test_no_guard_alert_in_the_two_minutes_after_a_window_ends(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    assert await brain.energy.start_export(True, 5.0, 40, source=ladder.AUTOPILOT) == "started"
    assert await brain.energy.house_guard(when(21, 0)) is None  # the evening feed-in ended this minute
    assert hass.states.get(MODE).state == ladder.DISCHARGE
    assert await brain.energy.house_guard(when(21, 3)) == "export_capped"  # nothing stopped it: the cap does


async def test_reserve_stops_a_forced_export_even_without_the_house_rule(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto", house_off_grid=False)
    hass.states.async_set(SOC, "21")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    assert await brain.energy.house_guard(when(18, 0)) == "export_stopped"
    assert hass.states.get(MODE).state == ladder.NORMAL and brain.journal.last["rule"] == ladder.RESERVE


async def test_house_only_power_follows_the_house_with_deadband_and_dwell(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    brain.energy.profile = [1.0] * 24
    hass.states.async_set(SOC, "40")  # 10 kWh usable, the house needs 12 kWh until 10:00
    hass.states.async_set(MODE, ladder.NORMAL)
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=1.0)  # house 1.0 kW
    assert await brain.energy.house_guard(when(22, 0)) == "house_only"
    assert hass.states.get(POWER).state == "1.2"  # 1.0 kW house + 200 W
    power_writes = lambda: [x["value"] for d, _, x in sent if d == "number" and x["entity_id"] == POWER]  # noqa: E731
    assert power_writes() == [1.2]
    # 100 W less: inside the deadband, nothing is sent
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=0.9)
    assert await brain.energy.house_guard(when(22, 1)) == "house_only"
    assert power_writes() == [1.2]
    # 500 W less: a real change, but lowering waits out the dwell
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=0.5)
    assert await brain.energy.house_guard(when(22, 2)) == "house_only"
    assert power_writes() == [1.2]
    assert await brain.energy.house_guard(when(22, 5)) == "house_only"
    assert power_writes() == [1.2, 0.7]
    # the house draws more: raised at once so the house stays off the grid
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=2.0)
    assert await brain.energy.house_guard(when(22, 6)) == "house_only"
    assert power_writes() == [1.2, 0.7, 2.2]


async def test_observe_mode_journals_the_verdict_and_touches_nothing(hass: HomeAssistant):
    sent = _record(hass)
    pushes = async_mock_service(hass, "notify", "send_message")
    brain = await _setup(hass, data={"schema": SCHEMA}, autopilot_mode="auto", observe_only=True)
    brain.energy.profile = [1.0] * 24
    hass.states.async_set(SOC, "40")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    assert await brain.energy.house_guard(when(22, 0)) == "observed"
    await hass.async_block_till_done()
    assert sent == [] and hass.states.get(MODE).state == ladder.DISCHARGE and not pushes
    last = brain.journal.last
    assert last["rule"] == ladder.HOUSE_RULE and last["observe"] is True
    assert await brain.energy.ev_guard(when(22, 0)) is None


async def test_dispatch_remembers_who_started_it(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    assert await brain.energy.start_export(True, 5.0, 40, source=ladder.PLAN) == "started"
    assert brain.energy.dispatch_source == ladder.PLAN
    assert await brain.energy.stop() == "stopped" and brain.energy.dispatch_source is None
    decision = {"window": "export", "kw": 5.0, "floor_soc": 40, "time": "2026-11-10T17:00:45", "soc": 90, "source": "llm"}
    assert await brain.autopilot._act(decision) == "started" and brain.energy.dispatch_source == ladder.AUTOPILOT
    await brain.energy.stop()
    assert await brain.autopilot._act({**decision, "source": "plan"}) == "started" and brain.energy.dispatch_source == ladder.PLAN


async def test_autopilot_decisions_reach_the_journal(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="shadow", autopilot_use_ai=False)
    hass.states.async_set(SOC, "31")
    decision = await brain.autopilot.decide("export")
    last = brain.journal.last
    assert not decision["do"] and last["rule"] == ladder.AUTOPILOT and last["action"] == ladder.HOLD
    assert last["reason"].startswith("No evening export")


async def test_ev_first_exports_only_a_trickle_when_feed_in_is_low(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    hass.states.async_set(POWER, "7")
    flows(hass, grid_kw=-1.0, ev_kw=7.2, batt_discharge_kw=9.0)  # load 8.0 kW: EV 7.2 + house 0.8
    assert brain.energy.supply_left() > 1  # supply charge not covered, but 3c feed-in is not worth chasing
    assert await brain.energy.ev_guard(when(23, 0)) == "trickle"
    assert ("number", "set_value", {"entity_id": POWER, "value": 8.2}) in sent  # 7.2 + 0.8 + 0.2, not + 7 kW export
    assert "feed-in is low" in brain.energy.ev_guard_note
