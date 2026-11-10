"""Sealion 7 feature: tariff-following windows, observe by default, engine and observe gates."""

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx.const import CONF_SL7_PEAK, CONF_SL7_WINDOW, DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY, SCHEMA
from custom_components.ampx.sealion7 import Window

SOC, PLUG, START = LEGACY["ev_soc"], LEGACY["ev_plug"], LEGACY["ev_start_button"]


async def _setup(hass: HomeAssistant, data: dict | None = None, **opts):
    async_mock_service(hass, "notify", "send_message")
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={} if data is None else data, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def when(day: int, hour: int) -> datetime:
    return datetime(2026, 11, day, hour, 0, tzinfo=dt_util.get_default_time_zone())  # Nov 10 is a Tuesday, Nov 14 a Saturday


def plugged_in(hass: HomeAssistant, soc: str = "50") -> None:
    hass.states.async_set(SOC, soc)
    hass.states.async_set(PLUG, "on")


async def test_windows_follow_the_tariff_and_its_peak_days(hass: HomeAssistant):
    assert DEFAULTS[CONF_SL7_WINDOW] == "" and DEFAULTS[CONF_SL7_PEAK] == ""
    brain = await _setup(hass, shoulder_start="11:00:00", shoulder_end="15:00:00", peak_start="15:00:00", peak_end="21:00:00")
    cfg = brain.sealion7.config(when(10, 16))
    assert cfg.allowed == (Window(11, 15),) and cfg.peak == (Window(15, 21),)
    assert brain.sealion7.config(when(14, 16)).peak == ()  # Saturday: no peak, so no peak pause
    status = brain.sealion7.status()
    assert status["window"] == "" and status["window_now"] == "11-15"


async def test_an_explicit_window_overrides_the_tariff(hass: HomeAssistant):
    brain = await _setup(hass, sl7_window="9-13", sl7_peak="13-22")
    cfg = brain.sealion7.config(when(10, 16))
    assert cfg.allowed == (Window(9, 13),) and cfg.peak == (Window(13, 22),)


async def test_observe_by_default_then_control_presses_start(hass: HomeAssistant):
    presses = async_mock_service(hass, "button", "press")
    brain = await _setup(hass)
    plugged_in(hass)
    await brain.sealion7._tick(when(10, 11))  # Tuesday 11:00, cheap window
    assert brain.sealion7.decision.action == "start" and not presses
    brain.opts["sl7_enabled"] = True
    await brain.sealion7._tick(when(10, 11))
    assert [c.data["entity_id"] for c in presses] == [START]
    assert brain.sealion7.last_action["action"] == "start"


async def test_peak_pauses_the_car_even_below_minimum(hass: HomeAssistant):
    presses = async_mock_service(hass, "button", "press")
    brain = await _setup(hass, sl7_enabled=True)
    plugged_in(hass, soc="10")
    await brain.sealion7._tick(when(10, 17))  # Tuesday 17:00, peak
    assert brain.sealion7.decision.action == "hold" and "peak" in brain.sealion7.decision.reason and not presses
    await brain.sealion7._tick(when(14, 17))  # Saturday 17:00, off-peak: below minimum charges now
    assert brain.sealion7.decision.action == "start" and len(presses) == 1


async def test_hermes_or_observe_mode_blocks_the_car_buttons(hass: HomeAssistant):
    presses = async_mock_service(hass, "button", "press")
    brain = await _setup(hass, sl7_enabled=True, decision_engine="hermes")
    plugged_in(hass)
    await brain.sealion7._tick(when(10, 11))
    assert not presses and brain.sealion7.status()["blocked"] == "hermes"
    brain.opts["decision_engine"] = "ampx"
    brain.opts["observe_only"] = True
    await brain.sealion7._tick(when(10, 11))
    assert not presses and brain.sealion7.status()["blocked"] == "observe"
    brain.opts["observe_only"] = False
    await brain.sealion7._tick(when(10, 11))
    assert len(presses) == 1 and brain.sealion7.status()["blocked"] is None
