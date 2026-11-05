"""48-hour battery planner. Pure Python, no Home Assistant imports.

It simulates the house in 30-minute slots for a small set of candidate plans and
picks the cheapest one that respects the hard limits. A plan is three numbers:

* ``topup``  - charge from the grid in the cheap (shoulder) window up to this SOC (0 = no top-up)
* ``floor``  - in the evening feed-in window, force-export down to this SOC (0 = no export)
* ``start``  - hour the evening export starts

Score = import cost - export revenue + battery wear - value of energy left at the end.
Energy left at the end is worth the cheapest future import rate (after losses), so the
planner never empties the battery just because the horizon ends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any, Protocol

SLOT_H = 0.5


class Tariff(Protocol):
    deterministic: bool

    def slots(self, start: datetime, hours: int = 48, minutes: int = 30) -> list[tuple[datetime, float, float, str]]: ...


@dataclass(frozen=True)
class BatterySpec:
    capacity_kwh: float = 50.0
    efficiency: float = 0.90  # round trip; applied half on charge, half on discharge
    reserve_pct: float = 20.0
    max_kw: float = 10.0
    topup_kw: float = 10.0
    export_kw: float = 7.0
    min_export_floor: float = 30.0
    cycle_cost_c: float = 3.0  # cents per kWh discharged (wear)
    house_rule: bool = True  # plans that make the house buy grid power outside the cheap window are a last resort


@dataclass
class Plan:
    topup: int
    floor: int
    start: int
    cost: float = 0.0  # cents, the score
    imported: float = 0.0
    exported: float = 0.0
    import_c: float = 0.0
    export_c: float = 0.0
    wear_c: float = 0.0
    end_value_c: float = 0.0
    min_soc: float = 100.0
    house_grid: float = 0.0  # kWh the house buys outside the cheap window
    rows: list[dict[str, Any]] = field(default_factory=list)

    def describe(self) -> str:
        parts = []
        parts.append(f"top up to {self.topup}% in the shoulder window" if self.topup else "no grid top-up")
        parts.append(f"export from {self.start}:00 down to {self.floor}%" if self.floor else "no forced export")
        return ", ".join(parts)


def solar_shape(day_kwh: float, hours: list[float]) -> list[float]:
    """Spread a day's solar over daylight (06:00-18:00, sine shaped). ``hours`` are slot start
    hours (fractional); returns kWh per 30-min slot."""
    weights = [max(math.sin((h + 0.25 - 6) / 12 * math.pi), 0.0) if 6 <= h < 18 else 0.0 for h in hours]
    total = sum(max(math.sin((h + 0.25 - 6) / 12 * math.pi), 0.0) for h in [6 + i * 0.5 for i in range(24)])
    return [day_kwh * w / total for w in weights]


def simulate(p: Plan, slots: list, load: list[float], pv: list[float], soc0: float, spec: BatterySpec,
             keep_rows: bool = False) -> Plan:
    cap, half = spec.capacity_kwh, math.sqrt(spec.efficiency)
    stored = soc0 / 100 * cap
    floor_res = spec.reserve_pct / 100 * cap
    lim = spec.max_kw * SLOT_H
    imp = exp = cost_imp = rev = wear = house_grid = 0.0
    low = soc0
    rows = []
    fit_hi = max((s[2] for s in slots), default=0.0) - 0.01  # forced export only in the best feed-in hours
    for i, (t, rate, fit, period) in enumerate(slots):
        h = t.hour + t.minute / 60
        net = load[i] - pv[i]  # + needs energy, - surplus
        g_in = g_out = 0.0
        action = "self-use"
        # forced evening export (house is served first, the rest goes to the grid)
        if p.floor and fit >= fit_hi and h >= p.start and stored > p.floor / 100 * cap:
            room = stored - p.floor / 100 * cap
            out = min(spec.export_kw * SLOT_H + max(net, 0.0), lim, room * half)
            drawn = out / half
            stored -= drawn
            wear += out * spec.cycle_cost_c
            g_out = out - max(net, 0.0) + max(-net, 0.0)
            if g_out < 0:
                g_in, g_out = -g_out, 0.0
            action = "export"
        # shoulder top-up from the grid (solar surplus goes in first)
        elif p.topup and period == "shoulder" and stored < p.topup / 100 * cap:
            want = min(p.topup / 100 * cap - stored, lim * half)
            from_pv = min(max(-net, 0.0) * half, want)
            from_grid = min(spec.topup_kw * SLOT_H * half, want - from_pv)
            stored += from_pv + from_grid
            g_in = max(net, 0.0) + from_grid / half
            g_out = max(max(-net, 0.0) - from_pv / half, 0.0)
            action = "top-up"
        else:
            if net > 0:  # battery covers the house above reserve
                give = min(net, lim, max(stored - floor_res, 0.0) * half)
                stored -= give / half
                wear += give * spec.cycle_cost_c
                g_in = net - give
            else:  # surplus fills the battery, the rest is exported
                take = min(-net, lim, max(cap - stored, 0.0) / half)
                stored += take * half
                g_out = -net - take
        imp += g_in
        if period != "shoulder":
            house_grid += g_in
        exp += g_out
        cost_imp += g_in * rate
        rev += g_out * fit
        soc = stored / cap * 100
        low = min(low, soc)
        if keep_rows:
            rows.append({"t": t.isoformat(timespec="minutes"), "rate": rate, "fit": fit, "period": period,
                         "load": round(load[i], 2), "pv": round(pv[i], 2), "action": action,
                         "grid": round(g_in - g_out, 2), "soc": round(soc, 1)})
    cheapest = min(s[1] for s in slots) / spec.efficiency
    p.end_value_c = max(stored - floor_res, 0.0) * cheapest
    p.imported, p.exported = round(imp, 2), round(exp, 2)
    p.import_c, p.export_c, p.wear_c = round(cost_imp, 1), round(rev, 1), round(wear, 1)
    p.cost = round(cost_imp - rev + wear - p.end_value_c, 1)
    p.min_soc = round(low, 1)
    p.house_grid = round(house_grid, 2)
    p.rows = rows
    return p


def best_plan(now: datetime, tariff: Tariff, soc0: float, spec: BatterySpec, load_by_hour: list[float],
              pv_today_left: float, pv_tomorrow: float) -> dict[str, Any]:
    """Search candidate plans over 48 h. ``load_by_hour`` is house kWh per hour of day (24 values,
    EV excluded); ``pv_today_left`` is solar still to come today."""
    slots = tariff.slots(now, 48, 30)
    load = [load_by_hour[t.hour] * SLOT_H for t, *_ in slots]
    day0 = slots[0][0].date()
    hours0 = [t.hour + t.minute / 60 for t, *_ in slots if t.date() == day0]
    # today's remaining solar spread over the remaining daylight slots, tomorrow's over the whole day
    shape0 = solar_shape(1.0, hours0)
    s0 = sum(shape0) or 1.0
    pv = []
    for t, *_ in slots:
        h = t.hour + t.minute / 60
        if t.date() == day0:
            pv.append(pv_today_left * solar_shape(1.0, [h])[0] / s0)
        else:
            pv.append(solar_shape(pv_tomorrow, [h])[0])
    f0, f1 = getattr(getattr(tariff, "plan", None), "fit_evening_window", (17, 21))
    starts = [(f0 + i) % 24 for i in range(max(min((f1 - f0) % 24, 4), 1))]
    floors = [0] + list(range(int(max(spec.min_export_floor, spec.reserve_pct + 5)), 91, 10))
    plans = [simulate(Plan(t, f, s), slots, load, pv, soc0, spec)
             for t in [0, 40, 50, 60, 70, 80, 90, 100]
             for f in floors for s in (starts if f else starts[:1])]
    base = next(p for p in plans if not p.topup and not p.floor)
    ok = [p for p in plans if p.min_soc >= spec.reserve_pct - 0.5] or plans
    if spec.house_rule:
        clean = [p for p in ok if p.house_grid <= 0.2]
        # no plan keeps the house off the grid: buy as little as possible outside the cheap window
        ok = clean or [p for p in ok if p.house_grid <= min(x.house_grid for x in ok) + 0.2]
    best = min(ok, key=lambda p: (p.cost, p.topup, -p.floor))
    simulate(best, slots, load, pv, soc0, spec, keep_rows=True)
    simulate(base, slots, load, pv, soc0, spec, keep_rows=False)
    return {
        "made": now.isoformat(timespec="seconds"),
        "topup": best.topup, "floor": best.floor, "start": best.start,
        "summary": best.describe().capitalize(),
        "cost": round(best.cost / 100, 2), "baseline": round(base.cost / 100, 2),
        "saving": round((base.cost - best.cost) / 100, 2),
        "imported": best.imported, "exported": best.exported, "min_soc": best.min_soc,
        "house_grid": best.house_grid, "house_rule": spec.house_rule,
        "candidates": len(plans), "rows": best.rows,
    }
