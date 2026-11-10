"""Keep installs made before 0.21 working after the defaults went blank.

Versions up to 0.20 shipped with one home's entity ids, names and rates as defaults, and
the panel read a few of that home's sensors directly. Those values are copied into the
entry's options once, only where the entry has no value of its own, so nothing changes
for that install. New installs start blank.

From 0.24 new installs also start in observe mode (AmpX decides and logs but sends nothing).
An install from before that keeps controlling its battery: observe mode is switched off for it once.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_OBSERVE

SCHEMA = 3  # entry.data["schema"]: 2 = blank defaults (0.21), 3 = observe mode (0.24)

_N = "sensor.neovolt_online_"
LEGACY: dict[str, Any] = {
    "ev_energy": "sensor.tesla_wall_connector_energy",
    "studio_pv": "sensor.sungrow_pv",
    "studio_grid": "sensor.neovolt_online_grid",
    "studio_battery": _N + "battery_power",
    "studio_ev": "sensor.tesla_wall_connector_total_power",
    "studio_battery_invert": True,
    "studio_day_pv": _N + "pv_generated_today",
    "studio_day_load": _N + "consumed_today",
    "studio_day_export": _N + "feed_in_today",
    "studio_day_import": _N + "grid_import_today",
    "studio_day_charge": _N + "battery_charged_today",
    "studio_day_discharge": _N + "battery_discharged_today",
    "studio_load": "sensor.neovolt_neovoltlocal_combined_house_load",
    "pv_forecast_now": "sensor.pv_forecast_power_now",
    "notify": "notify.iphone_2",
    "battery_soc": _N + "soc",
    "dispatch_mode": "select.neovolt_neovoltlocal_dispatch_mode",
    "dispatch_power": "number.neovolt_neovoltlocal_dispatch_power",
    "dispatch_duration": "number.neovolt_neovoltlocal_dispatch_duration",
    "charge_target": "number.neovolt_neovoltlocal_dispatch_charge_target_soc",
    "discharge_target": "number.neovolt_neovoltlocal_dispatch_discharge_target_soc",
    "stop_button": "button.neovolt_neovoltlocal_stop_force_charge_discharge",
    "pv_forecast_today": "sensor.pv_forecast_ingleburn",
    "pv_forecast_tomorrow": "sensor.pv_forecast_forecast",
    "ev_soc": "sensor.byd_sealion_7_battery_level",
    "ev_plug": "binary_sensor.byd_sealion_7_plug",
    "ev_target_soc": "input_number.byd_target_soc",
    "ev_start_button": "button.byd_sealion_7_start_charging",
    "holiday_calendar": "calendar.australia_nsw",
    "battery_kwh": 50.0,
    "ev_kwh": 82.5,
    "ev_charger_kw": 7.4,
    "low_solar_kwh": 30.0,
    "export_kw": 7.0,
    "battery_max_kw": 10.0,
    "rate_high_peak": 41.91,
    "rate_low_peak": 42.416,
    "rate_shoulder": 11.11,
    "rate_off_peak": 32.12,
    "supply_charge": 166.617,
    "fit_evening": 28.0,
    "fit_morning": 3.0,
    "fit_other": 3.0,
    "battery_name": "Home ESS",
    "ev_name": "BYD Sealion 7",
    "charger_name": "Tesla Wall Connector",
    "plan_name": "AGL",
    "photo_ev": "/api/image/serve/3215d9a31830fbbdda209ef2fddeae4b/original",
    "photo_battery": "/local/cortex/neovolt-ess.png",
    "summary_sensor": "sensor.daily_summary",
    "best_time_sensor": "sensor.best_time_to_run_appliances",
    "house_sensors": ["sensor.fast_com_download", "input_number.solar_exported_at_battery_full"],
    "bill_sensors": [
        "sensor.agl_solar_sold_this_period", "sensor.agl_supply_charge", "sensor.globird_energy_balance",
        "sensor.globird_energy_latest_invoice", "sensor.agl_solar_feed_in_credit", "sensor.agl_consumption_this_period",
    ],
    "related_automations": [
        "automation.agl_plan_shoulder_grid_top_up_battery", "automation.agl_plan_evening_export_17_00_21_00_28c_fit",
        "automation.agl_plan_ev_charge_in_shoulder_window", "automation.agl_plan_ev_plug_in_gate_10_00_14_00_only",
        "automation.agl_plan_peak_guard_ev_and_battery",
    ],
}
# Keys that existed blank in older options but were filled in by the old panel itself.
_FILL_IF_BLANK = {"weather_entity": "weather.forecast_ingleburn"}


def upgrade(options: dict[str, Any], data: dict[str, Any]) -> dict[str, Any] | None:
    """New options for an entry from before ``SCHEMA``, or None when nothing is needed."""
    have = data.get("schema", 1)
    if have >= SCHEMA:
        return None
    out = dict(options)
    if have < 2:
        for key, value in LEGACY.items():
            if key not in out:
                out[key] = value
        if out.get("studio_ev") == "sensor.tesla_wall_connector_ev_charger":
            out["studio_ev"] = "sensor.tesla_wall_connector_total_power"
        for key, value in _FILL_IF_BLANK.items():
            if not out.get(key):
                out[key] = value
    if have < 3:
        out[CONF_OBSERVE] = False  # an install from before observe mode keeps controlling the battery
    return out


def async_migrate(hass: HomeAssistant, entry: ConfigEntry) -> None:
    options = upgrade(dict(entry.options), dict(entry.data))
    if options is None:
        return
    hass.config_entries.async_update_entry(entry, data={**entry.data, "schema": SCHEMA}, options=options)
