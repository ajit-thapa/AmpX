"""Face mode: an external engine (EMHASS) is the brain, AmpX only shows.

AmpX writes nothing to the battery or the car, plans nothing, judges nothing,
and the panel and options can no longer change energy-control settings."""

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx import config_flow as cf
from custom_components.ampx.const import (
    CONF_AUTO_EXPORT,
    CONF_ENGINE,
    CONF_EXPORT_KW,
    CONF_MODE,
    CONF_SOC,
    DEFAULTS,
    DOMAIN,
    ENGINE_EMHASS,
)
from custom_components.ampx.migrate import LEGACY


async def _setup(hass: HomeAssistant, **opts):
    async_mock_service(hass, "notify", "send_message")
    sent: list = []
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press"), ("switch", "turn_on")):
        async def rec(call, d=domain, s=svc):
            sent.append((d, s, dict(call.data)))
        hass.services.async_register(domain, svc, rec)
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={}, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id], sent


async def test_emhass_engine_is_face_mode(hass: HomeAssistant):
    brain, sent = await _setup(hass, decision_engine=ENGINE_EMHASS, autopilot_mode="auto", sl7_enabled=True)
    assert brain.face() and brain.hermes()  # every existing write gate keys on hermes()
    assert brain.autopilot.mode == "off"  # no planning and no AI calls of its own
    assert await brain.energy._set("number", "set_value", "dispatch_power", value=5.0) is False
    assert brain.sealion7.blocked() == "external"
    await hass.async_block_till_done()
    assert not sent


async def test_face_mode_does_not_judge_the_external_plan(hass: HomeAssistant):
    """EMHASS may buy grid power on purpose; AmpX raises no house-rule breach."""
    brain, sent = await _setup(hass, decision_engine=ENGINE_EMHASS, house_off_grid=True)
    o = brain.opts
    hass.states.async_set(o["studio_grid"], "3.0", {"unit_of_measurement": "kW"})
    hass.states.async_set(o["studio_ev"], "0", {"unit_of_measurement": "kW"})
    peak = dt_util.now().replace(hour=18, minute=0)
    assert await brain.energy.house_guard(peak) is None
    await hass.async_block_till_done()
    assert not sent


async def test_face_mode_refuses_energy_actions_and_control_options(hass: HomeAssistant, hass_ws_client):
    await _setup(hass, decision_engine=ENGINE_EMHASS)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/action", "action": "manual_export", "kw": 5})
    r = await ws.receive_json()
    assert not r["success"] and r["error"]["code"] == "external_engine"
    await ws.send_json({"id": 2, "type": "ampx/set_options", "options": {"export_kw": 4}})
    r = await ws.receive_json()
    assert not r["success"] and r["error"]["code"] == "external_engine"
    # display and house options still change, and the engine can be handed back
    await ws.send_json({"id": 3, "type": "ampx/set_options", "options": {"mute_push": ["health"]}})
    assert (await ws.receive_json())["success"]
    await hass.async_block_till_done()
    await ws.send_json({"id": 4, "type": "ampx/set_options", "options": {"decision_engine": "ampx"}})
    assert (await ws.receive_json())["success"]


async def test_overview_flags_face_mode_and_carries_the_external_plan(hass: HomeAssistant, hass_ws_client):
    await _setup(hass, decision_engine=ENGINE_EMHASS)
    hass.states.async_set("sensor.optim_status", "Optimal")
    hass.states.async_set("sensor.p_batt_forecast", "5000", {"battery_scheduled_power": [
        {"date": "2026-11-20 17:00:00+11:00", "p_batt_forecast": "5000.0"},
        {"date": "2026-11-20 17:30:00+11:00", "p_batt_forecast": "-1200.5"}]})
    hass.states.async_set("sensor.soc_batt_forecast", "90", {"battery_scheduled_soc": [
        {"date": "2026-11-20 17:00:00+11:00", "soc_batt_forecast": "90.0"},
        {"date": "2026-11-20 17:30:00+11:00", "soc_batt_forecast": "92.5"}]})
    hass.states.async_set("sensor.p_grid_forecast", "-4800", {"forecasts": [
        {"date": "2026-11-20 17:00:00+11:00", "p_grid_forecast": "-4800.0"},
        {"date": "2026-11-20 17:30:00+11:00", "p_grid_forecast": "300"}]})
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/overview"})
    result = (await ws.receive_json())["result"]
    assert result["control"]["face"] is True
    horizon = result["optimiser"]["horizon"]
    assert horizon == [
        {"t": "2026-11-20 17:00:00+11:00", "batt": 5000.0, "soc": 90.0, "grid": -4800.0},
        {"t": "2026-11-20 17:30:00+11:00", "batt": -1200.5, "soc": 92.5, "grid": 300.0},
    ]


def test_options_flow_hides_control_settings_in_face_mode():
    face = {CONF_ENGINE: ENGINE_EMHASS}
    keys = {str(k) for k in cf.section_schema("energy", face).schema}
    assert CONF_SOC in keys and CONF_ENGINE in keys  # what AmpX shows, and the way back
    assert CONF_MODE not in keys and CONF_EXPORT_KW not in keys and CONF_AUTO_EXPORT not in keys
    assert CONF_EXPORT_KW in {str(k) for k in cf.section_schema("energy", {}).schema}
    assert "autopilot" not in cf.menu(face) and "autopilot" in cf.menu({})


def test_engine_validator_accepts_emhass():
    from custom_components.ampx.websocket import CONTROL_OPTIONS
    check = CONTROL_OPTIONS[CONF_ENGINE]
    assert check("emhass") == "emhass"
    with pytest.raises(vol.Invalid):
        check("both")


async def test_energy_actions_say_who_drives(hass: HomeAssistant):
    """The assistant's tools reach energy.start_* directly; they must explain, not just fail."""
    brain, sent = await _setup(hass, decision_engine=ENGINE_EMHASS)
    for result in (await brain.energy.start_export(True), await brain.energy.start_topup(True), await brain.energy.stop()):
        assert result == "skipped: EMHASS drives the battery"
    await hass.async_block_till_done()
    assert not sent


async def test_inverter_schedule_engine_is_face_mode(hass: HomeAssistant):
    """The inverter's own schedule (Neovolt app/settings) drives the battery: AmpX only shows it."""
    from custom_components.ampx.const import ENGINE_INVERTER

    brain, sent = await _setup(hass, decision_engine=ENGINE_INVERTER, autopilot_mode="auto")
    assert brain.face() and brain.autopilot.mode == "off"
    assert await brain.energy._set("number", "set_value", "dispatch_power", value=5.0) is False
    assert await brain.energy.start_export(True) == "skipped: the inverter's own schedule drives the battery"
    await hass.async_block_till_done()
    assert not sent


def test_engine_validator_accepts_inverter():
    from custom_components.ampx.websocket import CONTROL_OPTIONS

    assert CONTROL_OPTIONS[CONF_ENGINE]("inverter") == "inverter"
