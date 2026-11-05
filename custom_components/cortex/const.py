"""Constants and option defaults for Cortex."""

from __future__ import annotations

DOMAIN = "cortex"
STORAGE_VERSION = 1
SIGNAL_UPDATE = f"{DOMAIN}_update"
EVENT_SPOKEN = f"{DOMAIN}_spoken"

# --- general ---------------------------------------------------------------
CONF_SPEAKERS = "speakers"
CONF_TTS_ENGINE = "tts_engine"
CONF_NOTIFY = "notify"
CONF_MOTION = "motion_sensors"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_BANNED = "banned_words"
CONF_DEDUPE = "dedupe_minutes"
CONF_AGENT = "conversation_agent"

# --- briefing, reports, AI -------------------------------------------------
CONF_BRIEF_MORNING = "briefing_morning"
CONF_BRIEF_EVENING = "briefing_evening"
CONF_BRIEF_SECTIONS = "briefing_sections"
CONF_BRIEF_AI = "briefing_ai"
CONF_WEATHER = "weather_entity"
CONF_WEEKLY_TIME = "weekly_time"
CONF_AUTO_BACKUP = "auto_backup"
CONF_AI_TASK = "ai_task"
CONF_AI_PER_HOUR = "ai_per_hour"
CONF_AS_STYLE = "assistant_style"  # brief | normal | detailed
CONF_MUTE_PUSH = "mute_push"  # notification categories that are not pushed to the phone
PUSH_CATEGORIES = ("health", "autopilot", "energy", "routines", "suggestions", "speech")
CONF_AS_NOTES = "assistant_notes"  # the household's own standing instructions for the assistant
AS_STYLES = ("brief", "normal", "detailed")

# --- security, visitors, learning ------------------------------------------
CONF_NIGHT_WATCH = "night_watch"
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"
CONF_DOORBELL = "doorbell_entities"
CONF_DOORBELL_CAMERA = "doorbell_camera"
CONF_LEARN = "learn_entities"
CONF_HEALTH_IGNORE = "health_ignore"  # entities house health never reports

# Autopilot: local-AI energy decisions inside hard guardrails
CONF_AP_MODE = "autopilot_mode"  # off | shadow | auto
CONF_AP_LLM = "autopilot_use_ai"
CONF_AP_PLANNER = "autopilot_planner"  # Autopilot follows the 48-hour plan instead of the simple rules
CONF_CYCLE_COST = "cycle_cost_c"  # battery wear, cents per kWh discharged
CONF_EV_ENERGY = "ev_energy"  # wall connector energy counter, used to take EV charging out of house history
CONF_AP_NIGHT = "autopilot_night_share"
CONF_AP_TIMEOUT = "autopilot_timeout"
AP_MODES = ["off", "shadow", "auto"]

# Energy Studio panel: live power sources and daily energy totals
CONF_ST_PV = "studio_pv"
CONF_ST_GRID = "studio_grid"
CONF_ST_BATT = "studio_battery"
CONF_ST_EV = "studio_ev"
CONF_ST_GRID_INVERT = "studio_grid_invert"
CONF_ST_BATT_INVERT = "studio_battery_invert"
CONF_ST_DAY_PV = "studio_day_pv"
CONF_ST_DAY_LOAD = "studio_day_load"
CONF_ST_DAY_EXPORT = "studio_day_export"
CONF_ST_DAY_IMPORT = "studio_day_import"

BRIEF_SECTIONS = ["energy", "weather", "reminders", "health", "security", "parcels"]

# --- energy entities -------------------------------------------------------
CONF_SOC = "battery_soc"
CONF_MODE = "dispatch_mode"
CONF_POWER = "dispatch_power"
CONF_DURATION = "dispatch_duration"
CONF_CHARGE_TARGET = "charge_target"
CONF_DISCHARGE_TARGET = "discharge_target"
CONF_STOP = "stop_button"
CONF_PV_TODAY = "pv_forecast_today"
CONF_PV_TOMORROW = "pv_forecast_tomorrow"
CONF_EV_SOC = "ev_soc"
CONF_EV_PLUG = "ev_plug"
CONF_EV_TARGET = "ev_target_soc"
CONF_EV_START = "ev_start_button"
CONF_HOLIDAYS = "holiday_calendar"

# --- energy numbers / switches --------------------------------------------
CONF_BATTERY_KWH = "battery_kwh"
CONF_EV_KWH = "ev_kwh"
CONF_RESERVE = "battery_reserve_pct"
CONF_LOW_SOLAR = "low_solar_kwh"
CONF_TOPUP_KW = "topup_kw"
CONF_EXPORT_KW = "export_kw"
CONF_EXPORT_MIN_SOC = "export_min_soc"
CONF_EV_PRIORITY = "ev_priority"  # while the EV charges, export only enough to cover the supply charge
CONF_BATT_MAX_KW = "battery_max_kw"  # most the battery can deliver at once
CONF_EV_TRICKLE_KW = "ev_trickle_kw"  # small export kept once the supply charge is covered (inverter overhead)
CONF_EXPORT_FLOOR = "export_floor_soc"
CONF_AUTO_TOPUP = "auto_topup"
CONF_AUTO_EXPORT = "auto_export"
CONF_EV_GATE = "ev_gate"
CONF_EV_WINDOW = "ev_window"

# --- your home: names, photos and extra sensors the panel shows --------------
CONF_NAME_BATTERY = "battery_name"
CONF_NAME_EV = "ev_name"
CONF_NAME_CHARGER = "charger_name"
CONF_PLAN_NAME = "plan_name"
CONF_PHOTO_EV = "photo_ev"
CONF_PHOTO_BATTERY = "photo_battery"
CONF_PHOTO_BG = "photo_background"
PHOTO_KINDS = {"ev": CONF_PHOTO_EV, "battery": CONF_PHOTO_BATTERY, "background": CONF_PHOTO_BG}
CONF_EV_CHARGER_KW = "ev_charger_kw"
CONF_EFFICIENCY = "battery_efficiency"
CONF_ST_DAY_CHARGE = "studio_day_charge"
CONF_ST_DAY_DISCHARGE = "studio_day_discharge"
CONF_ST_LOAD = "studio_load"  # house load power, optional (peak power history)
CONF_PV_NOW = "pv_forecast_now"  # forecast solar power right now, optional (solar vs forecast chart)
CONF_SUMMARY = "summary_sensor"
CONF_BEST_TIME = "best_time_sensor"
CONF_HOUSE_SENSORS = "house_sensors"
CONF_BILL_SENSORS = "bill_sensors"
CONF_AUTOMATIONS = "related_automations"

# --- tariff ---------------------------------------------------------------
CONF_SHOULDER_START = "shoulder_start"
CONF_SHOULDER_END = "shoulder_end"
CONF_PEAK_START = "peak_start"
CONF_PEAK_END = "peak_end"
CONF_PEAK_DAYS = "peak_days"  # business | weekdays | everyday
PEAK_DAYS = ["business", "weekdays", "everyday"]
CONF_HIGH_MONTHS = "high_months"
CONF_FIT_EVENING_START = "fit_evening_start"
CONF_FIT_EVENING_END = "fit_evening_end"
CONF_FIT_MORNING_START = "fit_morning_start"
CONF_FIT_MORNING_END = "fit_morning_end"
WINDOW_KEYS = (CONF_SHOULDER_START, CONF_SHOULDER_END, CONF_PEAK_START, CONF_PEAK_END,
               CONF_FIT_EVENING_START, CONF_FIT_EVENING_END, CONF_FIT_MORNING_START, CONF_FIT_MORNING_END)
CONF_RATE_HIGH_PEAK = "rate_high_peak"
CONF_RATE_LOW_PEAK = "rate_low_peak"
CONF_RATE_SHOULDER = "rate_shoulder"
CONF_RATE_OFF_PEAK = "rate_off_peak"
CONF_SUPPLY = "supply_charge"
CONF_FIT_EVENING = "fit_evening"
CONF_FIT_MORNING = "fit_morning"
CONF_FIT_OTHER = "fit_other"

DEFAULTS: dict[str, object] = {
    # Every entity id is blank: pick yours under Configure. Rates and windows are an example
    # time-of-use plan (cheap midday window, weekday evening peak); set your own.
    CONF_SPEAKERS: [],
    CONF_MOTION: [],
    CONF_BRIEF_MORNING: "07:30:00",
    CONF_BRIEF_EVENING: None,
    CONF_BRIEF_SECTIONS: ["energy", "weather", "reminders", "health", "security", "parcels"],
    CONF_BRIEF_AI: False,
    CONF_WEATHER: None,
    CONF_WEEKLY_TIME: "18:00:00",
    CONF_AUTO_BACKUP: True,
    CONF_AI_TASK: None,
    CONF_AI_PER_HOUR: 12,
    CONF_AS_STYLE: "brief",
    CONF_AS_NOTES: "",
    CONF_MUTE_PUSH: [],
    CONF_NIGHT_WATCH: True,
    CONF_NIGHT_START: "23:00:00",
    CONF_NIGHT_END: "06:00:00",
    CONF_DOORBELL: [],
    CONF_DOORBELL_CAMERA: None,
    CONF_LEARN: [],
    CONF_HEALTH_IGNORE: [],
    CONF_AP_MODE: "shadow",
    CONF_AP_LLM: True,
    CONF_AP_PLANNER: False,
    CONF_CYCLE_COST: 3.0,
    CONF_EV_ENERGY: "",
    CONF_AP_NIGHT: 0.35,
    CONF_AP_TIMEOUT: 150,
    CONF_ST_PV: "",
    CONF_ST_GRID: "",
    CONF_ST_BATT: "",
    CONF_ST_EV: "",
    CONF_ST_GRID_INVERT: False,
    CONF_ST_BATT_INVERT: False,
    CONF_ST_DAY_PV: "",
    CONF_ST_DAY_LOAD: "",
    CONF_ST_DAY_EXPORT: "",
    CONF_ST_DAY_IMPORT: "",
    CONF_ST_DAY_CHARGE: "",
    CONF_ST_DAY_DISCHARGE: "",
    CONF_ST_LOAD: "",
    CONF_PV_NOW: "",
    CONF_QUIET_START: "22:00:00",
    CONF_QUIET_END: "07:00:00",
    CONF_BANNED: "",
    CONF_DEDUPE: 30,
    CONF_NOTIFY: "",
    CONF_SOC: "",
    CONF_MODE: "",
    CONF_POWER: "",
    CONF_DURATION: "",
    CONF_CHARGE_TARGET: "",
    CONF_DISCHARGE_TARGET: "",
    CONF_STOP: "",
    CONF_PV_TODAY: "",
    CONF_PV_TOMORROW: "",
    CONF_EV_SOC: "",
    CONF_EV_PLUG: "",
    CONF_EV_TARGET: "",
    CONF_EV_START: "",
    CONF_HOLIDAYS: "",
    CONF_BATTERY_KWH: 13.5,
    CONF_EV_KWH: 60.0,
    CONF_EV_CHARGER_KW: 7.0,
    CONF_EFFICIENCY: 90.0,
    CONF_RESERVE: 20.0,
    CONF_LOW_SOLAR: 20.0,
    CONF_TOPUP_KW: 5.0,
    CONF_EXPORT_KW: 5.0,
    CONF_EXPORT_MIN_SOC: 35.0,
    CONF_EV_PRIORITY: True,
    CONF_BATT_MAX_KW: 5.0,
    CONF_EV_TRICKLE_KW: 0.2,
    CONF_EXPORT_FLOOR: 30.0,
    CONF_AUTO_TOPUP: False,
    CONF_AUTO_EXPORT: False,
    CONF_EV_GATE: False,
    CONF_NAME_BATTERY: "Home battery",
    CONF_NAME_EV: "EV",
    CONF_NAME_CHARGER: "EV charger",
    CONF_PLAN_NAME: "My plan",
    CONF_PHOTO_EV: "",
    CONF_PHOTO_BATTERY: "",
    CONF_PHOTO_BG: "",
    CONF_SUMMARY: "",
    CONF_BEST_TIME: "",
    CONF_HOUSE_SENSORS: [],
    CONF_BILL_SENSORS: [],
    CONF_AUTOMATIONS: [],
    CONF_RATE_HIGH_PEAK: 45.0,
    CONF_RATE_LOW_PEAK: 45.0,
    CONF_RATE_SHOULDER: 15.0,
    CONF_RATE_OFF_PEAK: 30.0,
    CONF_SUPPLY: 110.0,
    CONF_FIT_EVENING: 10.0,
    CONF_FIT_MORNING: 5.0,
    CONF_FIT_OTHER: 5.0,
    CONF_SHOULDER_START: "10:00:00",
    CONF_SHOULDER_END: "14:00:00",
    CONF_PEAK_START: "16:00:00",
    CONF_PEAK_END: "20:00:00",
    CONF_PEAK_DAYS: "business",
    CONF_HIGH_MONTHS: ["11", "12", "1", "2", "3"],
    CONF_FIT_EVENING_START: "17:00:00",
    CONF_FIT_EVENING_END: "21:00:00",
    CONF_FIT_MORNING_START: "07:00:00",
    CONF_FIT_MORNING_END: "08:00:00",
}

SAFETY_CLASSES = {
    "smoke": "has detected smoke",
    "carbon_monoxide": "has detected carbon monoxide",
    "gas": "has detected gas",
    "moisture": "has detected water",
    "tamper": "has been tampered with",
    "safety": "has raised a safety alert",
}
