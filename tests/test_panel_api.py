"""What the panel reads and may change: engine, observe mode, journal, Sealion 7 windows, decision sensor."""

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx import ladder
from custom_components.ampx.const import DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY


async def _setup(hass: HomeAssistant, **opts):
    async_mock_service(hass, "notify", "send_message")
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press")):
        async_mock_service(hass, domain, svc)
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={}, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


async def test_overview_carries_engine_observe_and_journal(hass: HomeAssistant, hass_ws_client):
    brain = await _setup(hass, decision_engine="hermes")
    brain.journal.add(ladder.HOUSE_RULE, ladder.STOP_DISCHARGE, "the house needs it")
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/overview"})
    result = (await ws.receive_json())["result"]
    assert result["control"]["decision_engine"] == "hermes" and result["control"]["observe"] is False
    assert result["journal"][0]["rule"] == ladder.HOUSE_RULE and result["journal"][0]["reason"] == "the house needs it"


async def test_panel_may_switch_observe_mode_and_clear_sealion_windows(hass: HomeAssistant, hass_ws_client):
    await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/set_options", "options": {"observe_only": "yes"}})
    assert not (await ws.receive_json())["success"]
    await ws.send_json({"id": 2, "type": "ampx/set_options", "options": {"sl7_window": "ten to two"}})
    assert not (await ws.receive_json())["success"]
    await ws.send_json({"id": 3, "type": "ampx/set_options", "options": {"observe_only": True, "sl7_window": "", "sl7_peak": "14-21"}})
    assert (await ws.receive_json())["success"]
    await hass.async_block_till_done()
    options = hass.config_entries.async_entries(DOMAIN)[0].options
    assert options["observe_only"] is True and options["sl7_window"] == "" and options["sl7_peak"] == "14-21"


async def test_decision_sensor_shows_the_rule_and_reason(hass: HomeAssistant):
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(LEGACY["battery_soc"], "21")
    hass.states.async_set(LEGACY["dispatch_mode"], ladder.DISCHARGE)
    now = datetime(2026, 11, 10, 18, 0, tzinfo=dt_util.get_default_time_zone())
    assert await brain.energy.house_guard(now) == "export_stopped"
    await hass.async_block_till_done()
    state = hass.states.get("sensor.ampx_decision")
    assert state.state == ladder.RESERVE
    assert state.attributes["action"] == ladder.STOP_DISCHARGE and "reserve" in state.attributes["reason"]
