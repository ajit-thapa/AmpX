"""Time-of-use tariff engine (cheap window, peak, off-peak, two feed-in windows). Pure Python, no Home Assistant imports.

Rates are in cents per kWh. All windows are configurable through ``Plan``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

PEAK = "peak"
SHOULDER = "shoulder"
OFF_PEAK = "off_peak"


@dataclass(frozen=True)
class Plan:
    """Tariff rates and windows."""

    high_season_peak: float = 41.91
    low_season_peak: float = 42.416
    shoulder: float = 11.11
    off_peak: float = 32.12
    supply_charge: float = 166.617  # cents per day
    fit_evening: float = 28.0
    fit_morning: float = 3.0
    fit_off_peak: float = 3.0
    high_months: tuple[int, ...] = (11, 12, 1, 2, 3)
    shoulder_window: tuple[int, int] = (10, 14)
    peak_window: tuple[int, int] = (16, 20)
    fit_evening_window: tuple[int, int] = (17, 21)
    fit_morning_window: tuple[int, int] = (7, 8)
    peak_days: str = "business"  # business (weekdays, not holidays) | weekdays | everyday


def _in(hour: int, window: tuple[int, int]) -> bool:
    start, end = window
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def is_business_day(day: date, is_holiday: bool = False) -> bool:
    """Peak only applies Monday to Friday, excluding public holidays."""
    return day.weekday() < 5 and not is_holiday


def peak_day(day: date, plan: Plan, is_holiday: bool = False) -> bool:
    if plan.peak_days == "everyday":
        return True
    if plan.peak_days == "weekdays":
        return day.weekday() < 5
    return is_business_day(day, is_holiday)


def is_high_season(day: date, plan: Plan) -> bool:
    return day.month in plan.high_months


def period(now: datetime, plan: Plan, is_holiday: bool = False) -> str:
    """Return the import period active at ``now``."""
    hour = now.hour
    if _in(hour, plan.shoulder_window):
        return SHOULDER
    if _in(hour, plan.peak_window) and peak_day(now.date(), plan, is_holiday):
        return PEAK
    return OFF_PEAK


def import_rate(now: datetime, plan: Plan, is_holiday: bool = False) -> float:
    current = period(now, plan, is_holiday)
    if current == SHOULDER:
        return plan.shoulder
    if current == PEAK:
        return plan.high_season_peak if is_high_season(now.date(), plan) else plan.low_season_peak
    return plan.off_peak


def feed_in_rate(now: datetime, plan: Plan) -> float:
    if _in(now.hour, plan.fit_evening_window):
        return plan.fit_evening
    if _in(now.hour, plan.fit_morning_window):
        return plan.fit_morning
    return plan.fit_off_peak


def export_pays(now: datetime, plan: Plan) -> bool:
    """True while the feed-in rate is at the plan's best. A flat feed-in always pays."""
    return feed_in_rate(now, plan) >= max(plan.fit_evening, plan.fit_morning, plan.fit_off_peak)


def next_change(
    now: datetime,
    plan: Plan,
    holiday: Callable[[date], bool] | None = None,
) -> tuple[datetime, str]:
    """Return when the import period next changes, and what it changes to.

    ``holiday`` answers whether a given date is a public holiday; unknown future
    dates should return False.
    """
    holiday = holiday or (lambda _d: False)
    current = period(now, plan, holiday(now.date()))
    probe = now.replace(minute=0, second=0, microsecond=0)
    for _ in range(24 * 8):
        probe += timedelta(hours=1)
        found = period(probe, plan, holiday(probe.date()))
        if found != current:
            return probe, found
    return probe, current


def schedule(
    day: date, plan: Plan, is_holiday: bool = False
) -> list[tuple[int, float, float]]:
    """24 rows of (hour, import c/kWh, feed-in c/kWh) for charting."""
    rows = []
    for hour in range(24):
        stamp = datetime(day.year, day.month, day.day, hour)
        rows.append(
            (hour, import_rate(stamp, plan, is_holiday), feed_in_rate(stamp, plan))
        )
    return rows


def export_kwh_to_cover(plan: Plan) -> float:
    """kWh to export at the evening FiT to cover the daily supply charge."""
    if plan.fit_evening <= 0:
        return 0.0
    return round(plan.supply_charge / plan.fit_evening, 2)


def solar_day(forecast_kwh: float | None, threshold_kwh: float) -> str:
    if forecast_kwh is None:
        return "unknown"
    return "low" if forecast_kwh < threshold_kwh else "ok"


def pv_shortfall(
    forecast_kwh: float,
    battery_soc: float,
    battery_capacity_kwh: float,
    ev_plugged: bool = False,
    ev_soc: float | None = None,
    ev_target: float | None = None,
    ev_capacity_kwh: float = 0.0,
) -> float:
    """kWh the sun is not forecast to cover (battery room plus EV need)."""
    need = max(0.0, 100 - battery_soc) / 100 * battery_capacity_kwh
    if ev_plugged and ev_soc is not None and ev_target is not None:
        need += max(0.0, ev_target - ev_soc) / 100 * ev_capacity_kwh
    return round(need - forecast_kwh, 1)


def stored_kwh(soc: float, capacity_kwh: float) -> float:
    return round(max(0.0, min(100.0, soc)) / 100 * capacity_kwh, 1)


def usable_kwh(soc: float, capacity_kwh: float, reserve_pct: float = 20.0) -> float:
    return round(max(0.0, soc - reserve_pct) / 100 * capacity_kwh, 1)


def room_kwh(soc: float, capacity_kwh: float) -> float:
    return round(capacity_kwh - stored_kwh(soc, capacity_kwh), 1)


def battery_budget(
    now: datetime,
    soc: float | None,
    capacity_kwh: float,
    reserve_pct: float,
    plan: Plan,
    house_kwh_per_day: float,
    supply_left_dollars: float,
    profile: list[float] | None = None,
) -> dict | None:
    """What the home battery has to cover until the next cheap (shoulder) window.

    Needs, in order: the house until the shoulder window opens, then enough evening
    export to cover what is left of the daily supply charge. Whatever remains is
    spare: safe to put into the EV or to export. Inside the shoulder window the grid
    is cheap, so nothing needs covering.
    """
    if soc is None:
        return None
    usable = max(soc - reserve_pct, 0.0) / 100 * capacity_kwh
    start, end = plan.shoulder_window
    if _in(now.hour, plan.shoulder_window):
        hours = 0.0
    else:
        nxt = now.replace(hour=start, minute=0, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        hours = (nxt - now).total_seconds() / 3600
    if profile and len(profile) == 24 and hours:
        # walk the hour-of-day profile (kWh per hour) from now to the window
        house, t, left = 0.0, now, hours
        while left > 1e-6:
            step = min(left, 1 - t.minute / 60) or 1.0
            house += profile[t.hour] * step
            t = t.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            left -= step
    else:
        house = house_kwh_per_day / 24 * hours
    fit_end = plan.fit_evening_window[1]
    supply = 0.0
    if plan.fit_evening > 0 and now.hour < fit_end and supply_left_dollars > 0:
        supply = supply_left_dollars / (plan.fit_evening / 100)
    spare = usable - house - supply
    return {
        "usable": round(usable, 1),
        "house": round(house, 1),
        "hours": round(hours, 1),
        "until": f"{start:02d}:00",
        "supply": round(supply, 1),
        "spare": round(spare, 1),
        "ok": spare >= 0,
    }


class FixedTOU:
    """Tariff interface used by the planner.

    Any tariff (a dynamic one such as Amber later) only needs ``rate`` and ``slots``
    and the ``deterministic`` flag; the planner never looks inside the tariff.
    """

    deterministic = True

    def __init__(self, plan: Plan, holiday: Callable[[date], bool] | None = None) -> None:
        self.plan = plan
        self.holiday = holiday or (lambda _d: False)

    def rate(self, ts: datetime) -> tuple[float, float, str]:
        """(import c/kWh, feed-in c/kWh, period) at ``ts``."""
        hol = self.holiday(ts.date())
        return import_rate(ts, self.plan, hol), feed_in_rate(ts, self.plan), period(ts, self.plan, hol)

    def slots(self, start: datetime, hours: int = 48, minutes: int = 30) -> list[tuple[datetime, float, float, str]]:
        first = start.replace(minute=(start.minute // minutes) * minutes, second=0, microsecond=0)
        n = hours * 60 // minutes
        return [(t, *self.rate(t)) for t in (first + timedelta(minutes=minutes * i) for i in range(n))]
