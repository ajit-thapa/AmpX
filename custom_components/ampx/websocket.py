"""WebSocket API for the sidebar panel."""

from __future__ import annotations

import base64
import binascii
from datetime import timedelta
from pathlib import Path
import re
import secrets
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    AP_MODES,
    CONF_AGENT,
    CONF_AI_PER_HOUR,
    CONF_AS_NOTES,
    CONF_AS_STYLE,
    AS_STYLES,
    CONF_AP_LLM,
    CONF_AP_PLANNER,
    CONF_AP_MODE,
    CONF_AUTO_EXPORT,
    CONF_AUTO_TOPUP,
    CONF_EXPORT_FLOOR,
    CONF_BATT_MAX_KW,
    CONF_EV_PRIORITY,
    CONF_EV_TRICKLE_KW,
    CONF_EXPORT_KW,
    CONF_HEALTH_IGNORE,
    CONF_MUTE_PUSH,
    PUSH_CATEGORIES,
    CONF_TOPUP_KW,
    DOMAIN,
)
from .const import *  # noqa: F403 - profile and setup option keys
from .memory import CATEGORIES
from .runtime import AmpX
from . import tariff


def _brain(hass: HomeAssistant) -> AmpX | None:
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, AmpX):
            return value
    return None


def _json_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    out = dict(snap)
    if "next_change" in out:
        out["next_change"] = out["next_change"].isoformat()
    return out


def async_register_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_overview)
    websocket_api.async_register_command(hass, ws_memory_add)
    websocket_api.async_register_command(hass, ws_memory_delete)
    websocket_api.async_register_command(hass, ws_hush)
    websocket_api.async_register_command(hass, ws_cancel)
    websocket_api.async_register_command(hass, ws_action)
    websocket_api.async_register_command(hass, ws_set_options)
    websocket_api.async_register_command(hass, ws_plans_save)
    websocket_api.async_register_command(hass, ws_upload)


def _profile(brain: AmpX) -> dict[str, Any]:
    """Everything the panel needs to know about this home: names, photos, entities, tariff."""
    o, p = brain.opts, brain.energy.plan()
    f = lambda k, d=0.0: float(o.get(k) or d)  # noqa: E731
    lst = lambda k: [x for x in (o.get(k) or []) if isinstance(x, str) and x]  # noqa: E731
    return {
        "names": {"battery": o.get(CONF_NAME_BATTERY) or "Home battery", "ev": o.get(CONF_NAME_EV) or "EV",
                  "charger": o.get(CONF_NAME_CHARGER) or "EV charger", "plan": o.get(CONF_PLAN_NAME) or "My plan"},
        "photos": {k: o.get(v) or "" for k, v in PHOTO_KINDS.items()},
        "battery": {"soc": o.get(CONF_SOC) or "", "power": o.get(CONF_ST_BATT) or "", "mode": o.get(CONF_MODE) or "",
                    "capacity": f(CONF_BATTERY_KWH, 10), "reserve": f(CONF_RESERVE), "efficiency": f(CONF_EFFICIENCY, 90)},
        "ev": {"soc": o.get(CONF_EV_SOC) or "", "plug": o.get(CONF_EV_PLUG) or "", "target": o.get(CONF_EV_TARGET) or "",
               "start": o.get(CONF_EV_START) or "", "capacity": f(CONF_EV_KWH, 60), "charger_kw": f(CONF_EV_CHARGER_KW, 7)},
        "charger": {"power": o.get(CONF_ST_EV) or "", "energy": o.get(CONF_EV_ENERGY) or ""},
        "solar": {"power": o.get(CONF_ST_PV) or "", "forecast_now": o.get(CONF_PV_NOW) or "",
                  "today": o.get(CONF_PV_TODAY) or "", "tomorrow": o.get(CONF_PV_TOMORROW) or ""},
        "grid": o.get(CONF_ST_GRID) or "",
        "load": o.get(CONF_ST_LOAD) or "",
        "day": {"pv": o.get(CONF_ST_DAY_PV) or "", "load": o.get(CONF_ST_DAY_LOAD) or "", "export": o.get(CONF_ST_DAY_EXPORT) or "",
                "import": o.get(CONF_ST_DAY_IMPORT) or "", "charge": o.get(CONF_ST_DAY_CHARGE) or "",
                "discharge": o.get(CONF_ST_DAY_DISCHARGE) or ""},
        "holidays": o.get(CONF_HOLIDAYS) or "", "notify": o.get(CONF_NOTIFY) or "",
        "summary": o.get(CONF_SUMMARY) or "", "best_time": o.get(CONF_BEST_TIME) or "", "weather": o.get(CONF_WEATHER) or "",
        "house": lst(CONF_HOUSE_SENSORS), "bills": lst(CONF_BILL_SENSORS), "automations": lst(CONF_AUTOMATIONS),
        "tariff": {
            "shoulder": p.shoulder, "off": p.off_peak, "hi": p.high_season_peak, "lo": p.low_season_peak,
            "fitE": p.fit_evening, "fitM": p.fit_morning, "fitO": p.fit_off_peak, "supply": p.supply_charge,
            "sw": list(p.shoulder_window), "pw": list(p.peak_window), "few": list(p.fit_evening_window),
            "fmw": list(p.fit_morning_window), "months": list(p.high_months), "peak_days": p.peak_days,
        },
    }


@websocket_api.websocket_command({vol.Required("type"): "ampx/overview"})
@websocket_api.async_response
async def ws_overview(hass: HomeAssistant, connection, msg) -> None:
    brain = _brain(hass)
    if brain is None:
        connection.send_error(msg["id"], "not_loaded", "AmpX is not set up")
        return
    brain.refresh()
    now = dt_util.now()
    hushed = brain.gate.hushed_until
    connection.send_result(
        msg["id"],
        {
            "energy": _json_snapshot(brain.snapshot),
            "schedule": [
                {"hour": h, "import": i, "feed_in": f}
                for h, i, f in tariff.schedule(now.date(), brain.energy.plan(), brain.energy.is_holiday(now.date()))
            ],
            "hour": now.hour,
            "memories": [vars(m) for m in brain.book.items],
            "categories": list(CATEGORIES),
            "watches": brain.watches,
            "reminders": brain.reminders,
            "health": brain.health,
            "speech": list(brain.speaker.log),
            "pushes": list(brain.speaker.push_log),
            "mute_push": list(brain.opts.get(CONF_MUTE_PUSH) or []),
            "hushed": bool(hushed and hushed > now),
            "routines": list(brain.routines.items.values()),
            "motion_lights": list(brain.motion_lights.rules.values()),
            "heating": list(brain.heating.rules.values()),
            "suggestions": [x for x in brain.learning.suggestions if x["status"] == "new"],
            "visitors": {
                "log": brain.visitors.log[-15:][::-1],
                "parcels": brain.visitors.parcels_waiting,
                "today": brain.visitors.today_count(),
                "spots": brain.visitors.spots,
                "cameras": sorted(s.entity_id for s in hass.states.async_all("camera")),
            },
            "timeline": list(brain.timeline.items)[:30],
            "week": brain.timeline.week(),
            "security": brain.security.check(),
            "backups": await brain.backup.list(),
            "profile": _profile(brain),
            "studio": {
                "pv": brain.opts.get("studio_pv"),
                "grid": brain.opts.get("studio_grid"),
                "battery": brain.opts.get("studio_battery"),
                "ev": brain.opts.get("studio_ev"),
                "grid_invert": bool(brain.opts.get("studio_grid_invert")),
                "battery_invert": bool(brain.opts.get("studio_battery_invert")),
                "soc": brain.opts.get("battery_soc"),
                "ev_soc": brain.opts.get("ev_soc"),
                "day_pv": brain.opts.get("studio_day_pv"),
                "day_load": brain.opts.get("studio_day_load"),
                "day_export": brain.opts.get("studio_day_export"),
                "day_import": brain.opts.get("studio_day_import"),
            },
            "control": {
                "autopilot_mode": brain.autopilot.mode,
                "use_ai": bool(brain.opts.get(CONF_AP_LLM)),
                "use_planner": bool(brain.opts.get(CONF_AP_PLANNER)),
                "auto_topup": bool(brain.opts[CONF_AUTO_TOPUP]),
                "auto_export": bool(brain.opts[CONF_AUTO_EXPORT]),
                "topup_kw": float(brain.opts[CONF_TOPUP_KW]),
                "export_kw": float(brain.opts[CONF_EXPORT_KW]),
                "export_floor": float(brain.opts[CONF_EXPORT_FLOOR]),
                "mode_entity": brain.opts.get("dispatch_mode"),
                "ev_priority": bool(brain.opts.get(CONF_EV_PRIORITY)),
                "house_rule": bool(brain.opts.get(CONF_HOUSE_RULE)),
                "batt_max_kw": float(brain.opts.get(CONF_BATT_MAX_KW) or 10),
                "ev_trickle_kw": float(brain.opts.get(CONF_EV_TRICKLE_KW) or 0),
            },
            "autopilot": {
                "mode": brain.autopilot.mode,
                "active": brain.autopilot.active,
                "decisions": brain.autopilot.decisions[-6:][::-1],
            },
            "advice": brain.advice(),
            "plan": brain.energy.plan_result,
            "plans": brain.plans,
            "settings": {
                "agent": brain.opts.get(CONF_AGENT) or "",
                "ai_per_hour": int(brain.opts.get(CONF_AI_PER_HOUR) or 0),
                "style": brain.opts.get(CONF_AS_STYLE) or "brief",
                "notes": brain.opts.get(CONF_AS_NOTES) or "",
                "speakers": bool(brain.opts.get("speakers")),
                "ai_task": bool(brain.opts.get("ai_task")),
                "health_ignore": list(brain.opts.get(CONF_HEALTH_IGNORE) or []),
            },
            "automation": {
                "topup": brain.opts["auto_topup"],
                "export": brain.opts["auto_export"],
                "ev_gate": brain.opts["ev_gate"],
            },
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ampx/memory_add",
        vol.Required("text"): str,
        vol.Optional("category", default="fact"): str,
    }
)
@websocket_api.async_response
async def ws_memory_add(hass: HomeAssistant, connection, msg) -> None:
    brain = _brain(hass)
    if brain is None:
        connection.send_error(msg["id"], "not_loaded", "AmpX is not set up")
        return
    memory = brain.remember(msg["text"], msg["category"], "panel")
    connection.send_result(msg["id"], vars(memory))


@websocket_api.websocket_command(
    {vol.Required("type"): "ampx/memory_delete", vol.Required("target"): str}
)
@websocket_api.async_response
async def ws_memory_delete(hass: HomeAssistant, connection, msg) -> None:
    brain = _brain(hass)
    gone = brain.forget(msg["target"]) if brain else None
    connection.send_result(msg["id"], {"deleted": bool(gone)})


@websocket_api.websocket_command(
    {vol.Required("type"): "ampx/hush", vol.Required("minutes"): vol.All(int, vol.Range(min=0))}
)
@websocket_api.async_response
async def ws_hush(hass: HomeAssistant, connection, msg) -> None:
    brain = _brain(hass)
    if brain:
        minutes = msg["minutes"]
        brain.gate.hush(dt_util.now() + timedelta(minutes=minutes) if minutes else None)
        brain.notify_update()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {vol.Required("type"): "ampx/cancel", vol.Required("kind"): vol.In(["reminder", "watch"]), vol.Required("target"): str}
)
@websocket_api.async_response
async def ws_cancel(hass: HomeAssistant, connection, msg) -> None:
    brain = _brain(hass)
    ok = False
    if brain:
        ok = brain.cancel_reminder(msg["target"]) if msg["kind"] == "reminder" else brain.remove_watch(msg["target"])
    connection.send_result(msg["id"], {"ok": ok})


ACTIONS = (
    "autopilot_topup", "autopilot_export",
    "accept_suggestion", "dismiss_suggestion", "run_routine", "delete_routine",
    "set_spot", "parcels_collected", "security_check", "backup", "weekly_report",
    "manual_export", "manual_topup", "manual_stop",
)

# Options the panel may change. Anything else is rejected.
CONTROL_OPTIONS = {
    CONF_AP_MODE: vol.In(AP_MODES),
    CONF_AP_LLM: bool,
    CONF_AP_PLANNER: bool,
    CONF_AUTO_TOPUP: bool,
    CONF_AUTO_EXPORT: bool,
    CONF_TOPUP_KW: vol.All(vol.Coerce(float), vol.Range(min=0.5, max=15)),
    CONF_EXPORT_KW: vol.All(vol.Coerce(float), vol.Range(min=0.5, max=15)),
    CONF_EXPORT_FLOOR: vol.All(vol.Coerce(float), vol.Range(min=5, max=90)),
    CONF_HEALTH_IGNORE: vol.All([str], vol.Length(max=500)),
    CONF_MUTE_PUSH: [vol.In(PUSH_CATEGORIES)],
    CONF_AGENT: vol.Any(None, "", str),
    CONF_AI_PER_HOUR: vol.All(vol.Coerce(int), vol.Range(min=0, max=120)),
    CONF_AS_STYLE: vol.In(AS_STYLES),
    CONF_EV_PRIORITY: bool,
    CONF_HOUSE_RULE: bool,
    CONF_ENGINE: vol.In((ENGINE_AMPX, ENGINE_HERMES)),
    CONF_EV_TRICKLE_KW: vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
    CONF_BATT_MAX_KW: vol.All(vol.Coerce(float), vol.Range(min=1, max=50)),
    CONF_AS_NOTES: vol.All(str, vol.Length(max=600)),
}


def _hour_opt(value: Any) -> str:
    """0-24 or "HH:MM[:SS]" -> "HH:00:00" (24 means midnight)."""
    if isinstance(value, str) and ":" in value:
        value = value.split(":")[0]
    h = int(vol.Coerce(int)(value))
    if not 0 <= h <= 24:
        raise vol.Invalid("hour must be 0 to 24")
    return f"{h % 24:02d}:00:00"


def _months_opt(value: Any) -> list[str]:
    out = sorted({int(vol.Coerce(int)(m)) for m in value})
    if any(not 1 <= m <= 12 for m in out):
        raise vol.Invalid("months are 1 to 12")
    return [str(m) for m in out]


def _photo_opt(value: Any) -> str:
    value = str(value or "").strip()
    if value and not re.match(r"^(/|https?://)", value):
        raise vol.Invalid("photo must be a path or http(s) address")
    return value[:400]


_NAME = vol.All(str, vol.Strip, vol.Length(min=1, max=40))
_RATE = vol.All(vol.Coerce(float), vol.Range(min=-200, max=500))
CONTROL_OPTIONS.update({
    CONF_NAME_BATTERY: _NAME, CONF_NAME_EV: _NAME, CONF_NAME_CHARGER: _NAME, CONF_PLAN_NAME: _NAME,
    **{key: _photo_opt for key in PHOTO_KINDS.values()},
    CONF_BATTERY_KWH: vol.All(vol.Coerce(float), vol.Range(min=1, max=500)),
    CONF_EV_KWH: vol.All(vol.Coerce(float), vol.Range(min=1, max=300)),
    CONF_EV_CHARGER_KW: vol.All(vol.Coerce(float), vol.Range(min=1, max=50)),
    CONF_RESERVE: vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    CONF_EFFICIENCY: vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
    CONF_RATE_SHOULDER: _RATE, CONF_RATE_OFF_PEAK: _RATE, CONF_RATE_HIGH_PEAK: _RATE, CONF_RATE_LOW_PEAK: _RATE,
    CONF_FIT_EVENING: _RATE, CONF_FIT_MORNING: _RATE, CONF_FIT_OTHER: _RATE,
    CONF_SUPPLY: vol.All(vol.Coerce(float), vol.Range(min=0, max=2000)),
    **{key: _hour_opt for key in WINDOW_KEYS},
    CONF_PEAK_DAYS: vol.In(PEAK_DAYS),
    CONF_HIGH_MONTHS: _months_opt,
})

_BAND = vol.Schema({
    vol.Required("from"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
    vol.Required("to"): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
    vol.Required("rate"): vol.All(vol.Coerce(float), vol.Range(min=-200, max=500)),
    vol.Optional("days", default="all"): vol.In(["all", "weekday", "weekend"]),
})
PLAN_SCHEMA = vol.Schema({
    vol.Required("id"): vol.All(str, vol.Length(min=1, max=40)),
    vol.Required("name"): vol.All(str, vol.Length(min=1, max=40)),
    vol.Required("supply"): vol.All(vol.Coerce(float), vol.Range(min=0, max=1000)),
    vol.Required("import_default"): vol.All(vol.Coerce(float), vol.Range(min=-200, max=500)),
    vol.Optional("import", default=[]): vol.All([_BAND], vol.Length(max=12)),
    vol.Required("fit_default"): vol.All(vol.Coerce(float), vol.Range(min=-200, max=500)),
    vol.Optional("fit", default=[]): vol.All([_BAND], vol.Length(max=12)),
}, extra=vol.REMOVE_EXTRA)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ampx/action",
        vol.Required("action"): vol.In(ACTIONS),
        # "id" is reserved by the websocket protocol for the message number, so the object goes in "target"
        vol.Optional("target"): str,
        vol.Optional("camera"): str,
        vol.Optional("spot"): str,
        vol.Optional("kw"): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=15)),
        vol.Optional("soc"): vol.All(vol.Coerce(float), vol.Range(min=5, max=100)),
    }
)
@websocket_api.async_response
async def ws_action(hass: HomeAssistant, connection, msg) -> None:
    brain = _brain(hass)
    if brain is None:
        connection.send_error(msg["id"], "not_loaded", "AmpX is not set up")
        return
    action, ident = msg["action"], msg.get("target", "")
    try:
        if action == "accept_suggestion":
            result: Any = brain.learning.accept(ident)
        elif action == "dismiss_suggestion":
            result = brain.learning.dismiss(ident)
        elif action == "run_routine":
            result = await brain.routines.run(ident)
        elif action == "delete_routine":
            result = brain.routines.delete(ident)
        elif action == "set_spot":
            brain.visitors.set_spot(msg.get("camera", ""), msg.get("spot", ""))
            result = True
        elif action == "parcels_collected":
            brain.visitors.collected()
            result = True
        elif action == "security_check":
            result = brain.security.check()
        elif action in ("autopilot_topup", "autopilot_export"):
            result = await brain.autopilot.decide(action.split("_", 1)[1], False)
        elif action == "manual_export":
            result = await brain.energy.start_export(True, msg.get("kw"), msg.get("soc"))
        elif action == "manual_topup":
            result = await brain.energy.start_topup(True, msg.get("kw"), msg.get("soc"))
        elif action == "manual_stop":
            brain.autopilot.active = None  # a manual stop ends whatever Autopilot started too
            result = await brain.energy.stop()
        elif action == "backup":
            result = await brain.backup.create()
        else:
            result = await brain.briefing.weekly_report()
    except Exception as err:  # noqa: BLE001 - report to the panel instead of a stack trace
        connection.send_error(msg["id"], "failed", str(err))
        return
    connection.send_result(msg["id"], {"result": result})


@websocket_api.websocket_command(
    {vol.Required("type"): "ampx/set_options", vol.Required("options"): dict}
)
@websocket_api.async_response
async def ws_set_options(hass: HomeAssistant, connection, msg) -> None:
    """Change battery control settings (automatic or manual) from the panel."""
    brain = _brain(hass)
    if brain is None:
        connection.send_error(msg["id"], "not_loaded", "AmpX is not set up")
        return
    changes: dict[str, Any] = {}
    try:
        for key, value in msg["options"].items():
            if key not in CONTROL_OPTIONS:
                raise vol.Invalid(f"{key} cannot be changed here")
            changes[key] = CONTROL_OPTIONS[key](value)
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    entry = brain.entry
    hass.config_entries.async_update_entry(entry, options={**entry.options, **changes})  # reloads AmpX
    connection.send_result(msg["id"], {"saved": changes})


@websocket_api.websocket_command(
    {vol.Required("type"): "ampx/plans_save", vol.Required("plans"): vol.All(list, vol.Length(max=8))}
)
@websocket_api.async_response
async def ws_plans_save(hass: HomeAssistant, connection, msg) -> None:
    """Store the tariffs the panel compares the current plan against."""
    brain = _brain(hass)
    if brain is None:
        connection.send_error(msg["id"], "not_loaded", "AmpX is not set up")
        return
    try:
        plans = [PLAN_SCHEMA(p) for p in msg["plans"]]
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    brain.plans = plans
    brain.save()
    connection.send_result(msg["id"], {"plans": plans})


# ---- photos ------------------------------------------------------------------
MAX_PHOTO = 4 * 1024 * 1024
_MAGIC = ((b"\x89PNG", "png"), (b"\xff\xd8\xff", "jpg"), (b"GIF8", "gif"), (b"RIFF", "webp"))


def _photo_ext(raw: bytes) -> str | None:
    for magic, ext in _MAGIC:
        if raw.startswith(magic) and (ext != "webp" or raw[8:12] == b"WEBP"):
            return ext
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ampx/upload",
        vol.Required("kind"): vol.In(list(PHOTO_KINDS)),
        vol.Optional("data"): vol.Any(None, str),  # base64 or a data: URL; leave out to remove the photo
    }
)
@websocket_api.async_response
async def ws_upload(hass: HomeAssistant, connection, msg) -> None:
    """Save a photo (car, battery or background) under <config>/ampx and point the option at it."""
    brain = _brain(hass)
    if brain is None:
        connection.send_error(msg["id"], "not_loaded", "AmpX is not set up")
        return
    key, url = PHOTO_KINDS[msg["kind"]], ""
    folder = Path(hass.config.path(DOMAIN))
    old = str(brain.opts.get(key) or "")
    data = msg.get("data")
    if data:
        try:
            raw = base64.b64decode(data.split(",", 1)[1] if data.startswith("data:") else data, validate=True)
        except (binascii.Error, ValueError, IndexError):
            connection.send_error(msg["id"], "invalid", "Not a valid image")
            return
        ext = _photo_ext(raw)
        if not ext or len(raw) > MAX_PHOTO:
            connection.send_error(msg["id"], "invalid", "Use a PNG, JPEG, WebP or GIF under 4 MB")
            return
        name = f"{msg['kind']}-{secrets.token_hex(6)}.{ext}"

        def write() -> None:
            folder.mkdir(exist_ok=True)
            (folder / name).write_bytes(raw)

        await hass.async_add_executor_job(write)
        url = f"/{DOMAIN}_files/{name}"
    prefix = f"/{DOMAIN}_files/"
    if old.startswith(prefix):  # remove the photo this one replaces
        stale = folder / Path(old[len(prefix):]).name
        await hass.async_add_executor_job(lambda: stale.unlink(missing_ok=True))
    entry = brain.entry
    hass.config_entries.async_update_entry(entry, options={**entry.options, key: url})
    connection.send_result(msg["id"], {"url": url})
