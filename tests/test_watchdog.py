"""Health checks for the inverter-schedule setup: the battery must follow its own
schedule, and AmpX's own energy sensors must be reporting."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx.const import DEFAULTS, DOMAIN, ENGINE_INVERTER
from custom_components.ampx.migrate import LEGACY


async def _setup(hass: HomeAssistant, **opts):
    async_mock_service(hass, "notify", "send_message")
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={}, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def _backdate(brain, eid, minutes):
    brain._watch_since[eid] = dt_util.utcnow() - timedelta(minutes=minutes)


async def test_battery_off_its_schedule_is_a_health_issue(hass: HomeAssistant):
    brain = await _setup(hass, decision_engine=ENGINE_INVERTER)
    mode = brain.opts["dispatch_mode"]
    hass.states.async_set(mode, "Force Discharge")
    await brain.run_health()
    assert not [i for i in brain.health if "schedule" in i]  # just switched: give it time
    _backdate(brain, mode, 20)
    issues = await brain.run_health()
    assert any("Force Discharge" in i and "own schedule" in i for i in issues)
    hass.states.async_set(mode, "Normal (Auto)")
    assert not [i for i in await brain.run_health() if "schedule" in i]


async def test_schedule_watchdog_only_runs_for_the_inverter_engine(hass: HomeAssistant):
    brain = await _setup(hass, decision_engine="ampx")
    mode = brain.opts["dispatch_mode"]
    hass.states.async_set(mode, "Force Discharge")
    _backdate(brain, mode, 60)
    assert not [i for i in await brain.run_health() if "schedule" in i]


async def test_dead_energy_sensor_is_a_health_issue(hass: HomeAssistant):
    brain = await _setup(hass, decision_engine=ENGINE_INVERTER)
    pv = brain.opts["studio_pv"]
    hass.states.async_set(pv, "unavailable")
    await brain.run_health()
    assert not [i for i in brain.health if "sensor" in i]
    _backdate(brain, pv, 15)
    issues = await brain.run_health()
    assert any(pv in i and "not reporting" in i for i in issues)
    hass.states.async_set(pv, "2.5", {"unit_of_measurement": "kW"})
    assert not [i for i in await brain.run_health() if "not reporting" in i]


async def test_runtime_is_in_the_energy_snapshot(hass: HomeAssistant):
    brain = await _setup(hass, decision_engine=ENGINE_INVERTER)
    hass.states.async_set(brain.opts["battery_soc"], "60", {"unit_of_measurement": "%"})
    data = brain.energy.snapshot()
    assert data["battery_runtime"]["hours"] > 0
