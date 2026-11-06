"""Energy brain: tariff-aware snapshot and battery/EV actions."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import planner, tariff
from .const import (
    CONF_ENGINE,
    ENGINE_CORTEX,
    CONF_AP_PLANNER,
    CONF_BATT_MAX_KW,
    CONF_CYCLE_COST,
    CONF_EV_ENERGY,
    CONF_ST_DAY_LOAD,
    CONF_ST_DAY_PV,
    CONF_BATTERY_KWH,
    CONF_EV_PRIORITY,
    CONF_EV_TRICKLE_KW,
    CONF_ST_DAY_EXPORT,
    CONF_CHARGE_TARGET,
    CONF_DISCHARGE_TARGET,
    CONF_DURATION,
    CONF_EV_KWH,
    CONF_EV_PLUG,
    CONF_EV_SOC,
    CONF_EV_START,
    CONF_EV_TARGET,
    CONF_EXPORT_FLOOR,
    CONF_EXPORT_KW,
    CONF_EXPORT_MIN_SOC,
    CONF_FIT_EVENING,
    CONF_FIT_MORNING,
    CONF_FIT_OTHER,
    CONF_HOLIDAYS,
    CONF_LOW_SOLAR,
    CONF_MODE,
    CONF_POWER,
    CONF_PV_TODAY,
    CONF_PV_TOMORROW,
    CONF_RATE_HIGH_PEAK,
    CONF_RATE_LOW_PEAK,
    CONF_RATE_OFF_PEAK,
    CONF_RATE_SHOULDER,
    CONF_RESERVE,
    CONF_SOC,
    CONF_STOP,
    CONF_SUPPLY,
    CONF_TOPUP_KW,
    CONF_EFFICIENCY,
    CONF_HOUSE_RULE,
    CONF_FIT_EVENING_END,
    CONF_FIT_EVENING_START,
    CONF_FIT_MORNING_END,
    CONF_FIT_MORNING_START,
    CONF_HIGH_MONTHS,
    CONF_PEAK_DAYS,
    CONF_PEAK_END,
    CONF_PEAK_START,
    CONF_SHOULDER_END,
    CONF_SHOULDER_START,
)

if TYPE_CHECKING:
    from .runtime import Cortex

_LOGGER = logging.getLogger(__name__)
UNKNOWN = ("unknown", "unavailable", "none", "")


def hour(value: Any) -> int:
    """Hour of a "HH:MM[:SS]" option (or a plain number of hours)."""
    if isinstance(value, (int, float)):
        return int(value) % 24
    try:
        return int(str(value).split(":")[0]) % 24
    except ValueError:
        return 0


def months(value: Any) -> tuple[int, ...]:
    out = []
    for m in value or []:
        try:
            if 1 <= int(m) <= 12:
                out.append(int(m))
        except (TypeError, ValueError):
            continue
    return tuple(out)


class EnergyBrain:
    """Reads the house, applies the tariff, and (optionally) drives the battery."""

    def __init__(self, hass: HomeAssistant, brain: Cortex) -> None:
        self.hass = hass
        self.brain = brain
        # Today's export earnings, built minute by minute from the export counter at the rate of the moment.
        self.earned: dict[str, Any] = {"day": None, "cents": 0.0, "last": None}
        self.ev_guard_note: str | None = None
        self.house_only = False  # Cortex is running the battery at house load so the grid charges the EV
        self.house_note: str | None = None
        self._rule_told: dict[str, str] = {}
        self.house_kwh_day = 22.0  # average daily use, refreshed hourly from history
        self.profile: list[float] | None = None  # house kWh per hour of day, EV charging removed
        self.holidays: set[date] = set()  # public holidays for the next year, from the calendar
        self.plan_result: dict[str, Any] | None = None

    # ---- inputs ---------------------------------------------------------
    def plan(self) -> tariff.Plan:
        o = self.brain.opts
        return tariff.Plan(
            high_season_peak=float(o[CONF_RATE_HIGH_PEAK]),
            low_season_peak=float(o[CONF_RATE_LOW_PEAK]),
            shoulder=float(o[CONF_RATE_SHOULDER]),
            off_peak=float(o[CONF_RATE_OFF_PEAK]),
            supply_charge=float(o[CONF_SUPPLY]),
            fit_evening=float(o[CONF_FIT_EVENING]),
            fit_morning=float(o[CONF_FIT_MORNING]),
            fit_off_peak=float(o[CONF_FIT_OTHER]),
            high_months=months(o.get(CONF_HIGH_MONTHS)),
            shoulder_window=(hour(o[CONF_SHOULDER_START]), hour(o[CONF_SHOULDER_END])),
            peak_window=(hour(o[CONF_PEAK_START]), hour(o[CONF_PEAK_END])),
            fit_evening_window=(hour(o[CONF_FIT_EVENING_START]), hour(o[CONF_FIT_EVENING_END])),
            fit_morning_window=(hour(o[CONF_FIT_MORNING_START]), hour(o[CONF_FIT_MORNING_END])),
            peak_days=str(o.get(CONF_PEAK_DAYS) or "business"),
        )

    def _num(self, key: str) -> float | None:
        entity_id = self.brain.opts.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in UNKNOWN:
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    def _is_on(self, key: str) -> bool:
        entity_id = self.brain.opts.get(key)
        state = self.hass.states.get(entity_id) if entity_id else None
        return state is not None and state.state == "on"

    def is_holiday(self, day: date) -> bool:
        """Public holiday? Uses the cached year of calendar events, and today's calendar state."""
        if day in self.holidays:
            return True
        entity_id = self.brain.opts.get(CONF_HOLIDAYS)
        if not entity_id or day != dt_util.now().date():
            return False
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == "on"

    @staticmethod
    def _tomorrow_estimate(state: Any) -> float | None:
        """Prefer the central (P50) estimate when the sensor offers one."""
        if state is None or state.state in UNKNOWN:
            return None
        estimate = state.attributes.get("estimate")
        try:
            return float(estimate if estimate is not None else state.state)
        except (TypeError, ValueError):
            return None

    # ---- snapshot -------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        o = self.brain.opts
        plan = self.plan()
        now = dt_util.now()
        holiday = self.is_holiday(now.date())
        cur = tariff.period(now, plan, holiday)
        change_at, change_to = tariff.next_change(now, plan, self.is_holiday)
        bat_kwh = float(o[CONF_BATTERY_KWH])
        ev_kwh = float(o[CONF_EV_KWH])
        reserve = float(o[CONF_RESERVE])
        soc = self._num(CONF_SOC)
        ev_soc = self._num(CONF_EV_SOC)
        ev_target = self._num(CONF_EV_TARGET)
        pv = self._num(CONF_PV_TODAY)
        pv_state = self.hass.states.get(o.get(CONF_PV_TOMORROW) or "")
        tomorrow = self._tomorrow_estimate(pv_state)
        plugged = self._is_on(CONF_EV_PLUG)
        shortfall = (
            tariff.pv_shortfall(pv, soc, bat_kwh, plugged, ev_soc, ev_target, ev_kwh)
            if pv is not None and soc is not None
            else None
        )
        export_cover = tariff.export_kwh_to_cover(plan)
        data: dict[str, Any] = {
            "period": cur,
            "import_rate": tariff.import_rate(now, plan, holiday),
            "feed_in_rate": tariff.feed_in_rate(now, plan),
            "fit_high": tariff.feed_in_rate(now, plan) >= plan.fit_evening > max(plan.fit_morning, plan.fit_off_peak),
            "shoulder_window": f"{plan.shoulder_window[0]:02d}:00 to {plan.shoulder_window[1]:02d}:00",
            "next_period": change_to,
            "next_change": change_at,
            "business_day": tariff.is_business_day(now.date(), holiday),
            "high_season": tariff.is_high_season(now.date(), plan),
            "export_to_cover": export_cover,
            "daily_charge": round(plan.supply_charge / 100, 2),
            "pv_today": pv,
            "pv_tomorrow": tomorrow,
            "solar_day": tariff.solar_day(pv, float(o[CONF_LOW_SOLAR])),
            "pv_shortfall": shortfall,
            "battery_soc": soc,
            "battery_stored": tariff.stored_kwh(soc, bat_kwh) if soc is not None else None,
            "battery_usable": tariff.usable_kwh(soc, bat_kwh, reserve) if soc is not None else None,
            "battery_room": tariff.room_kwh(soc, bat_kwh) if soc is not None else None,
            "ev_soc": ev_soc,
            "ev_stored": tariff.stored_kwh(ev_soc, ev_kwh) if ev_soc is not None else None,
            "ev_room": tariff.room_kwh(ev_soc, ev_kwh) if ev_soc is not None else None,
            "ev_plugged": plugged,
            "low_solar": float(o[CONF_LOW_SOLAR]),
        }
        data["export_earned"] = round(self.earned["cents"] / 100, 2)
        data["supply_left"] = round(self.supply_left(), 2)
        data["budget"] = tariff.battery_budget(now, soc, bat_kwh, reserve, plan, self.house_kwh_day, self.supply_left(), self.profile)
        data["ev_guard"] = self.ev_guard_note
        data["house_rule"] = bool(o.get(CONF_HOUSE_RULE))
        data["decision_engine"] = o.get(CONF_ENGINE) or ENGINE_CORTEX
        data["house_note"] = self.house_note
        data["storage_summary"] = self._storage_summary(data, bat_kwh, ev_kwh)
        data["summary"] = self._summary(data)
        return data

    @staticmethod
    def _storage_summary(d: dict[str, Any], bat_kwh: float, ev_kwh: float) -> str:
        parts = []
        if d["battery_soc"] is not None:
            parts.append(
                f"Battery {d['battery_stored']}/{bat_kwh:g} kWh "
                f"({d['battery_soc']:.0f}%, room {d['battery_room']} kWh)"
            )
        if d["ev_soc"] is not None:
            parts.append(
                f"EV {d['ev_stored']}/{ev_kwh:g} kWh "
                f"({d['ev_soc']:.0f}%, room {d['ev_room']} kWh)"
            )
        return " | ".join(parts)[:255]

    @staticmethod
    def _summary(d: dict[str, Any]) -> str:
        name = d["period"].replace("_", " ")
        parts = [
            f"{name.capitalize()} {d['import_rate']:g}c",
            f"next {d['next_period'].replace('_', ' ')} {d['next_change'].astimezone().strftime('%H:%M')}",
        ]
        if d.get("fit_high"):
            parts.insert(0, f"Export {d['feed_in_rate']:g}c now")
        if d["pv_today"] is not None:
            parts.append(f"solar {d['pv_today']:.0f} kWh ({d['solar_day']})")
        if d["battery_soc"] is not None:
            parts.append(f"battery {d['battery_soc']:.0f}%")
        parts.append(f"daily charge ${d['daily_charge']:.2f}")
        return " | ".join(parts)[:255]

    # ---- planner inputs and the 48-hour plan -----------------------------
    async def refresh_holidays(self) -> None:
        """Cache a year of public holidays so the tariff knows future no-peak days."""
        entity_id = self.brain.opts.get(CONF_HOLIDAYS)
        if not entity_id or self.hass.states.get(entity_id) is None:
            return
        now = dt_util.now()
        try:
            res = await self.hass.services.async_call(
                "calendar", "get_events",
                {"entity_id": entity_id, "start_date_time": now.isoformat(), "end_date_time": (now + timedelta(days=366)).isoformat()},
                blocking=True, return_response=True,
            )
        except Exception as err:  # noqa: BLE001 - holidays are a nicety
            _LOGGER.debug("Holidays not loaded: %s", err)
            return
        days: set[date] = set()
        for ev in ((res or {}).get(entity_id) or {}).get("events", []):
            try:
                days.add(date.fromisoformat(str(ev.get("start", ""))[:10]))
            except ValueError:
                continue
        self.holidays = days

    async def refresh_profile(self, days: int = 14) -> None:
        """House use per hour of day over the last two weeks, with EV charging taken out."""
        o = self.brain.opts
        load_id, ev_id = o.get(CONF_ST_DAY_LOAD), o.get(CONF_EV_ENERGY)
        if not load_id:
            return
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period

            ids = {load_id} | ({ev_id} if ev_id else set())
            start = dt_util.utcnow() - timedelta(days=days)
            stats = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period, self.hass, start, None, ids, "hour", None, {"state"}
            )
        except Exception as err:  # noqa: BLE001 - history is a nicety, never a blocker
            _LOGGER.debug("No load history: %s", err)
            return
        self.profile_from_stats(stats.get(load_id, []), stats.get(ev_id, []) if ev_id else [])

    def profile_from_stats(self, load_rows: list[dict], ev_rows: list[dict]) -> None:
        def deltas(rows: list[dict], lifetime: bool) -> dict[datetime, float]:
            out: dict[datetime, float] = {}
            prev = None
            for r in sorted(rows, key=lambda r: r["start"]):
                v = r.get("state")
                if v is None:
                    continue
                t = r["start"] if isinstance(r["start"], datetime) else dt_util.utc_from_timestamp(r["start"])
                lt = dt_util.as_local(t)
                if prev is None or (not lifetime and lt.hour == 0):
                    d = v if not lifetime and prev is not None else 0.0
                else:
                    d = v - prev
                if d < 0:
                    d = 0.0 if lifetime else v
                prev = v
                if 0 <= d < 30:
                    out[lt] = d
            return out
        load, ev = deltas(load_rows, False), deltas(ev_rows, True)
        sums, counts = [0.0] * 24, [0] * 24
        for t, kwh in load.items():
            house = max(kwh - ev.get(t, 0.0), 0.0)
            sums[t.hour] += house
            counts[t.hour] += 1
        if sum(counts) < 24 * 3:  # under three days of data: not enough to trust
            return
        flat = sum(sums) / max(sum(counts), 1)
        self.profile = [round(sums[h] / counts[h], 3) if counts[h] else flat for h in range(24)]
        self.house_kwh_day = round(sum(self.profile), 1)

    def house_needs(self, now: datetime | None = None) -> dict[str, float | None]:
        """What the house alone needs from the battery (kWh), for the house rule.

        ``until_cheap``: from now until the next cheap window opens. ``night``: from the end of
        today's cheap window until the next one, and ``pv_after``: forecast solar after it ends."""
        now = now or dt_util.now()
        o, plan = self.brain.opts, self.plan()
        cap, res = float(o[CONF_BATTERY_KWH]), float(o[CONF_RESERVE])
        b = tariff.battery_budget(now, 100.0, cap, res, plan, self.house_kwh_day, 0.0, self.profile)
        end = now.replace(hour=plan.shoulder_window[1] % 24, minute=0, second=0, microsecond=0)
        at = end if end > now else now
        n = tariff.battery_budget(at, 100.0, cap, res, plan, self.house_kwh_day, 0.0, self.profile)
        pv = self._num(CONF_PV_TODAY)
        hours = [h / 2 for h in range(48)]
        shape = planner.solar_shape(1.0, hours)
        frac = sum(v for h, v in zip(hours, shape) if h >= at.hour + at.minute / 60) / (sum(shape) or 1.0)
        return {"until_cheap": b["house"] if b else None, "night": n["house"] if n else None,
                "pv_after": round(pv * frac, 1) if pv is not None and at.date() == now.date() else 0.0}

    def spec(self) -> planner.BatterySpec:
        o = self.brain.opts
        return planner.BatterySpec(
            capacity_kwh=float(o[CONF_BATTERY_KWH]), reserve_pct=float(o[CONF_RESERVE]),
            max_kw=float(o.get(CONF_BATT_MAX_KW) or 10), topup_kw=float(o[CONF_TOPUP_KW]),
            export_kw=float(o[CONF_EXPORT_KW]), min_export_floor=float(o[CONF_EXPORT_FLOOR]),
            cycle_cost_c=float(o.get(CONF_CYCLE_COST) or 0),
            efficiency=min(max(float(o.get(CONF_EFFICIENCY) or 90) / 100, 0.5), 1.0),
            house_rule=bool(o.get(CONF_HOUSE_RULE)),
        )

    def run_planner(self, now: datetime | None = None) -> dict[str, Any] | None:
        """Search the next 48 hours for the cheapest battery plan."""
        now = now or dt_util.now()
        soc = self._num(CONF_SOC)
        if soc is None:
            return self.plan_result
        o = self.brain.opts
        made = self._num(CONF_ST_DAY_PV)
        fc_today = self._num(CONF_PV_TODAY)
        left = max((fc_today or 0.0) - (made or 0.0), 0.0)
        tomorrow = self._tomorrow_estimate(self.hass.states.get(o.get(CONF_PV_TOMORROW) or ""))
        profile = self.profile or [self.house_kwh_day / 24] * 24
        tar = tariff.FixedTOU(self.plan(), self.is_holiday)
        result = planner.best_plan(now, tar, soc, self.spec(), profile, left, tomorrow if tomorrow is not None else (fc_today or 0.0))
        result["follow"] = bool(o.get(CONF_AP_PLANNER))
        result["profile_source"] = "history, EV removed" if self.profile else "average daily use"
        self.plan_result = result
        return result

    # ---- export earnings and the EV-first guard --------------------------
    def track_export(self, now: datetime | None = None) -> float:
        """Add the kWh exported since the last call at the current feed-in rate. Returns cents earned today."""
        now = now or dt_util.now()
        day = now.date().isoformat()
        kwh = self._num(CONF_ST_DAY_EXPORT)
        e = self.earned
        if e["day"] != day:
            e.update(day=day, cents=0.0, last=None)
            self.ev_guard_note = None
        if kwh is not None:
            last = e["last"]
            if last is not None and 0 <= kwh - last < 5:
                e["cents"] += (kwh - last) * tariff.feed_in_rate(now, self.plan())
            e["last"] = kwh
        return e["cents"]

    def supply_left(self) -> float:
        """Dollars of today's supply charge not yet covered by exports."""
        return max(self.plan().supply_charge - self.earned["cents"], 0.0) / 100

    async def ev_guard(self, now: datetime | None = None) -> str | None:
        """While the EV charges during a forced export, keep the battery feeding the car first.
        Export at the set power until the day's supply charge is covered, then only a trickle
        (default 200 W) so the inverter's own use never comes from the grid."""
        now = now or dt_util.now()
        o = self.brain.opts
        if self.brain.hermes():
            return None
        if not o.get(CONF_EV_PRIORITY):
            return None
        mode_id = o.get(CONF_MODE)
        state = self.hass.states.get(mode_id) if mode_id else None
        if state is None or state.state != "Force Discharge" or self.house_only:
            return None
        live = self.brain.live_flows()
        ev = live["ev"]
        if ev < 0.5:
            return None
        home = max(live["load"] - ev, 0.0)
        budget = tariff.battery_budget(now, self._num(CONF_SOC), float(o[CONF_BATTERY_KWH]), float(o[CONF_RESERVE]),
                                       self.plan(), self.house_kwh_day, self.supply_left(), self.profile)
        short = budget is not None and budget["house"] > budget["usable"]  # the house alone needs all that's left
        covered = self.supply_left() <= 0.004 or short
        extra = float(o.get(CONF_EV_TRICKLE_KW) or 0.0) if covered else float(o[CONF_EXPORT_KW])
        want = round(min(float(o.get(CONF_BATT_MAX_KW) or 10.0), ev + home + extra), 1)
        if covered and not short and self.earned.get("covered") != self.earned["day"]:
            self.earned["covered"] = self.earned["day"]
            msg = (f"Supply charge covered (${self.plan().supply_charge / 100:.2f} earned). "
                   f"Battery now powers the EV, exporting just {extra * 1000:.0f} W.")
            self.brain.log("energy", msg)
            await self.brain.speaker.push(msg, title="Cortex energy")
        if short:
            self.ev_guard_note = (f"EV first: battery needed for the house until {budget['until']} "
                                  f"({budget['house']:.0f} kWh, {budget['usable']:.0f} kWh usable), so exporting only {extra * 1000:.0f} W.")
        else:
            self.ev_guard_note = (
                f"EV first: supply charge covered. Battery {want:.1f} kW covers the EV ({ev:.1f} kW) and house, "
                f"exporting about {extra * 1000:.0f} W." if covered else
                f"EV first: battery {want:.1f} kW covers the EV ({ev:.1f} kW) and house, "
                f"exporting the rest until ${self.supply_left():.2f} supply is covered.")
        power = self._num(CONF_POWER)
        if power is None or abs(power - want) >= 0.1:
            await self._set("number", "set_value", CONF_POWER, value=want)
            return "trickle" if covered else "adjusted"
        return "ok"

    async def _tell_once(self, key: str, msg: str) -> None:
        day = dt_util.now().date().isoformat()
        if self._rule_told.get(key) == day:
            return
        self._rule_told[key] = day
        self.brain.log("energy", msg)
        await self.brain.speaker.push(msg, title="Cortex energy")

    async def _watch_house(self, now: datetime) -> str | None:
        """Hermes decides: Cortex only checks the house rule and tells the owner on a breach."""
        if not self.brain.opts.get(CONF_HOUSE_RULE):
            return None
        plan = self.plan()
        per = tariff.period(now, plan, self.is_holiday(now.date()))
        if per == tariff.SHOULDER:
            return None
        live = self.brain.live_flows()
        house_import = live["grid"] - (live["ev"] if per == tariff.OFF_PEAK else 0.0)
        if house_import > 0.5:
            await self._tell_once("hermes_breach", f"House rule: {house_import:.1f} kW from the grid outside "
                                                   f"{plan.shoulder_window[0]:02d}:00 to {plan.shoulder_window[1]:02d}:00. "
                                                   "Hermes is in control; check its decisions.")
            return "breach"
        return "ok"

    async def house_guard(self, now: datetime | None = None) -> str | None:
        """The house rule: outside the cheap window the house never buys grid power.

        * A forced export stops once the battery holds only what the house needs until the
          next cheap window (any mode, manual included).
        * While the EV charges off-peak and the battery has nothing to spare, Cortex runs the
          battery at the house's load so the grid charges the car and the house stays on the
          battery (only when Cortex controls the battery: timers or Autopilot).
        * In peak the EV may not use the grid either: Cortex asks to pause it if the battery
          can't cover both.
        """
        now = now or dt_util.now()
        o = self.brain.opts
        if self.brain.hermes():
            return await self._watch_house(now)
        if not o.get(CONF_HOUSE_RULE):
            self.house_note = None
            return await self._end_house_only() if self.house_only else None
        plan = self.plan()
        mode_id = o.get(CONF_MODE)
        state = self.hass.states.get(mode_id) if mode_id else None
        mode = state.state if state else None
        cheap = tariff._in(now.hour, plan.shoulder_window)
        per = tariff.period(now, plan, self.is_holiday(now.date()))
        need = self.house_needs(now)["until_cheap"] or 0.0
        soc = self._num(CONF_SOC)
        cap, res = float(o[CONF_BATTERY_KWH]), float(o[CONF_RESERVE])
        usable = None if soc is None else max(soc - res, 0.0) / 100 * cap
        spare = None if usable is None else usable - need
        live = self.brain.live_flows()
        ev, home = live["ev"], max(live["load"] - live["ev"], 0.0)
        self.house_note = None
        if cheap or spare is None:
            return await self._end_house_only() if self.house_only else None

        # 1. a forced export must leave the house's share in the battery
        if mode == "Force Discharge" and not self.house_only and spare <= 0.5:
            await self.stop(only_mode="Force Discharge")
            self.ev_guard_note = None
            await self._tell_once("export", f"Export stopped: the battery keeps {need:.0f} kWh for the house until "
                                            f"{plan.shoulder_window[0]:02d}:00, so the house won't buy grid power.")
            return "export_stopped"

        acting = self.brain.control_mode() in ("auto", "timers")
        # 2. EV charging off-peak with nothing to spare: battery for the house, grid for the car
        if self.house_only or (ev >= 0.5 and per != tariff.PEAK and spare <= 0.5 and acting and mode in (None, "Normal")):
            if ev < 0.3 or per == tariff.PEAK or not acting:
                return await self._end_house_only()
            want = round(min(float(o.get(CONF_BATT_MAX_KW) or 10.0), home + float(o.get(CONF_EV_TRICKLE_KW) or 0.0)), 1)
            if not self.house_only:
                await self._set("number", "set_value", CONF_DURATION, value=240)
                await self._set("number", "set_value", CONF_DISCHARGE_TARGET, value=res)
                await self._set("number", "set_value", CONF_POWER, value=want)
                if not await self._set("select", "select_option", CONF_MODE, option="Force Discharge"):
                    return "failed"
                self.house_only = True
                self.brain.log("energy", f"house rule: battery covers the house ({want:.1f} kW), grid charges the EV")
            elif abs((self._num(CONF_POWER) or 0.0) - want) >= 0.1:
                await self._set("number", "set_value", CONF_POWER, value=want)
            self.house_note = (f"House rule: the battery covers only the house ({home:.1f} kW); the EV ({ev:.1f} kW) "
                               f"charges from the off-peak grid so the battery keeps {need:.0f} kWh for the house.")
            return "house_only"

        # 3. peak: no grid for the EV either
        if ev >= 0.5 and per == tariff.PEAK and spare - ev * 0.5 < 0:
            self.house_note = f"Peak: the battery can't carry the EV ({ev:.1f} kW) and the house until {plan.shoulder_window[0]:02d}:00. Pause the EV."
            await self._tell_once("peak_ev", self.house_note)
            return "pause_ev"
        return None

    async def _end_house_only(self) -> str:
        self.house_only = False
        self.house_note = None
        await self.stop(only_mode="Force Discharge")
        self.brain.log("energy", "house rule: battery back to normal")
        return "ended"

    # ---- actions --------------------------------------------------------
    async def _set(self, domain: str, service: str, key: str, **data: Any) -> bool:
        if self.brain.hermes():  # Hermes decides and writes; Cortex only shows and suggests
            _LOGGER.debug("Decision engine is Hermes: not writing %s.%s", domain, service)
            return False
        entity_id = self.brain.opts.get(key)
        if not entity_id:
            return False
        try:
            await self.hass.services.async_call(
                domain, service, {"entity_id": entity_id, **data}, blocking=True
            )
        except HomeAssistantError as err:
            _LOGGER.warning("%s.%s on %s failed: %s", domain, service, entity_id, err)
            return False
        return True

    async def start_topup(
        self, force: bool = False, kw: float | None = None, target: float | None = None
    ) -> str:
        """Charge the battery from the grid during the cheap shoulder window."""
        snap = self.snapshot()
        short = snap["pv_shortfall"]
        if not force and (short is None or short <= 0):
            return "skipped: forecast solar covers the battery and EV"
        o = self.brain.opts
        plan_hours = 4
        await self._set("number", "set_value", CONF_POWER, value=float(kw or o[CONF_TOPUP_KW]))
        await self._set("number", "set_value", CONF_DURATION, value=plan_hours * 60)
        await self._set("number", "set_value", CONF_CHARGE_TARGET, value=float(target or 100))
        ok = await self._set(
            "select", "select_option", CONF_MODE, option="Force Charge"
        )
        if ok:
            await self.brain.speaker.push(
                f"Grid top-up started: solar short by {short} kWh."
                if short is not None
                else "Grid top-up started.",
                title="Cortex energy",
            )
        if ok:
            self.brain.record("energy_actions")
            self.brain.log("energy", "battery action started")
        return "started" if ok else "failed"

    async def start_export(
        self, force: bool = False, kw: float | None = None, floor: float | None = None
    ) -> str:
        """Discharge to the grid during the evening feed-in window."""
        o = self.brain.opts
        soc = self._num(CONF_SOC)
        if not force and (soc is None or soc <= float(o[CONF_EXPORT_MIN_SOC])):
            return "skipped: battery too low to export"
        plan = self.plan()
        if o.get(CONF_HOUSE_RULE):
            # never export what the house needs before the next cheap window
            cap, res = float(o[CONF_BATTERY_KWH]), float(o[CONF_RESERVE])
            keep = res + (self.house_needs()["until_cheap"] or 0.0) / cap * 100 + 2
            floor = max(float(floor or o[CONF_EXPORT_FLOOR]), min(round(keep), 100))
            if soc is not None and soc <= floor + 1:
                return f"skipped: the house needs the battery down to {floor:.0f}% until the cheap window"
        await self._set("number", "set_value", CONF_POWER, value=float(kw or o[CONF_EXPORT_KW]))
        await self._set("number", "set_value", CONF_DURATION, value=240)
        await self._set(
            "number", "set_value", CONF_DISCHARGE_TARGET, value=float(floor or o[CONF_EXPORT_FLOOR])
        )
        ok = await self._set(
            "select", "select_option", CONF_MODE, option="Force Discharge"
        )
        if ok:
            await self.brain.speaker.push(
                f"Evening export started at {plan.fit_evening:g}c/kWh.", title="Cortex energy"
            )
        if ok:
            self.brain.record("energy_actions")
            self.brain.log("energy", "battery action started")
        return "started" if ok else "failed"

    async def stop(self, only_mode: str | None = None) -> str:
        """Stop forced dispatch (optionally only when currently in ``only_mode``)."""
        mode_id = self.brain.opts.get(CONF_MODE)
        state = self.hass.states.get(mode_id) if mode_id else None
        if only_mode and (state is None or state.state != only_mode):
            return "skipped: not in that mode"
        await self._set("button", "press", CONF_STOP)
        await self._set("select", "select_option", CONF_MODE, option="Normal")
        return "stopped"

    async def ev_plugged_in(self, window: tuple[int, int]) -> str:
        """Gate EV charging to the cheap window."""
        now = dt_util.now()
        o = self.brain.opts
        soc, target = self._num(CONF_EV_SOC), self._num(CONF_EV_TARGET)
        start, end = window
        in_window = start <= now.hour < end and now < now.replace(
            hour=end, minute=0, second=0, microsecond=0
        ) - timedelta(minutes=15)
        if in_window and (soc is None or target is None or soc < target):
            if o.get(CONF_EV_START):
                await self._set("button", "press", CONF_EV_START)
            return "charging"
        await self.brain.speaker.say(
            f"The car is plugged in outside the {start}:00 to {end}:00 cheap window. "
            "Charging will wait.",
        )
        return "held"
