"""Public-release setup: blank defaults, upgrade of older installs, profile, photos, tariff windows."""

import base64
from datetime import datetime
import os

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cortex import tariff
from custom_components.cortex.const import DEFAULTS, DOMAIN
from custom_components.cortex.migrate import LEGACY, SCHEMA, upgrade

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_defaults_name_no_one_s_home():
    for key, value in DEFAULTS.items():
        if isinstance(value, str):
            assert not any(w in value.lower() for w in ("neovolt", "byd", "tesla", "sungrow", "iphone", "nsw", "ingleburn")), key


def test_upgrade_fills_only_missing_and_only_once():
    old = {"battery_soc": "sensor.mine", "battery_kwh": 13.0}
    out = upgrade(old, {})
    assert out["battery_soc"] == "sensor.mine" and out["battery_kwh"] == 13.0
    assert out["ev_name"] == LEGACY["ev_name"] and out["photo_ev"] == LEGACY["photo_ev"]
    assert upgrade(old, {"schema": SCHEMA}) is None


def test_peak_days():
    sat = datetime(2026, 11, 7, 17)
    assert tariff.period(sat, tariff.Plan()) == tariff.OFF_PEAK
    assert tariff.period(sat, tariff.Plan(peak_days="everyday")) == tariff.PEAK
    mon = datetime(2026, 11, 9, 17)
    assert tariff.period(mon, tariff.Plan(peak_days="weekdays"), is_holiday=True) == tariff.PEAK
    assert tariff.period(mon, tariff.Plan(), is_holiday=True) == tariff.OFF_PEAK


async def test_new_install_profile_windows_and_photo(hass: HomeAssistant, hass_ws_client, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN, title="Cortex", data={"schema": SCHEMA},
                            options={**DEFAULTS, "shoulder_start": "11:00:00", "shoulder_end": "15:00:00", "peak_days": "everyday"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    brain = hass.data[DOMAIN][entry.entry_id]
    plan = brain.energy.plan()
    assert plan.shoulder_window == (11, 15) and plan.peak_days == "everyday"
    assert "ev_name" not in entry.data and entry.options["battery_soc"] == ""  # no upgrade for new installs

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "cortex/overview"})
    prof = (await ws.receive_json())["result"]["profile"]
    assert prof["names"]["battery"] == "Home battery" and prof["tariff"]["sw"] == [11, 15] and prof["battery"]["soc"] == ""

    await ws.send_json({"id": 2, "type": "cortex/set_options", "options": {"peak_end": 24, "high_months": [12, "1"], "ev_name": " Model Y ", "photo_ev": "javascript:x"}})
    assert not (await ws.receive_json())["success"]  # bad photo address rejected, nothing saved
    await ws.send_json({"id": 3, "type": "cortex/set_options", "options": {"peak_end": 24, "high_months": [12, "1"], "ev_name": " Model Y "}})
    assert (await ws.receive_json())["success"]
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.options["peak_end"] == "00:00:00" and entry.options["high_months"] == ["1", "12"] and entry.options["ev_name"] == "Model Y"

    await ws.send_json({"id": 4, "type": "cortex/upload", "kind": "ev", "data": "data:image/gif;base64," + base64.b64encode(b"not an image").decode()})
    assert not (await ws.receive_json())["success"]
    await ws.send_json({"id": 5, "type": "cortex/upload", "kind": "ev", "data": "data:image/png;base64," + base64.b64encode(PNG).decode()})
    url = (await ws.receive_json())["result"]["url"]
    await hass.async_block_till_done()
    path = os.path.join(str(tmp_path), DOMAIN, url.rsplit("/", 1)[1])
    assert url.startswith("/cortex_files/ev-") and url.endswith(".png") and os.path.exists(path)
    assert hass.config_entries.async_entries(DOMAIN)[0].options["photo_ev"] == url
    await ws.send_json({"id": 6, "type": "cortex/upload", "kind": "ev"})
    assert (await ws.receive_json())["result"]["url"] == ""
    await hass.async_block_till_done()
    assert not os.path.exists(path) and hass.config_entries.async_entries(DOMAIN)[0].options["photo_ev"] == ""


async def test_older_install_keeps_its_setup(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, title="Cortex", data={}, options={"battery_soc": "sensor.neovolt_online_soc"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data["schema"] == SCHEMA
    assert entry.options["ev_name"] == "BYD Sealion 7" and entry.options["rate_shoulder"] == 11.11
