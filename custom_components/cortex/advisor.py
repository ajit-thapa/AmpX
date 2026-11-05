"""Instant, rule-based energy tips. Pure Python, no Home Assistant imports.

Works without any AI model: a handful of plain checks on the tariff, the live
power flows and the battery and EV. Each tip says what to do and why, in one line.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

ACT, WARN, INFO = "act", "warn", "info"
_RANK = {WARN: 0, ACT: 1, INFO: 2}


def _hm(when: Any) -> str:
    return when.strftime("%H:%M") if isinstance(when, datetime) else str(when or "")


def _mins_until(when: Any, now: datetime) -> float | None:
    return (when - now).total_seconds() / 60 if isinstance(when, datetime) else None


def tips(s: dict[str, Any], live: dict[str, float], now: datetime, *, mode: str = "off",
         reserve: float = 20.0, limit: int = 4) -> list[dict[str, str]]:
    """Return up to ``limit`` tips, most urgent first.

    ``s`` is the energy snapshot (rates in cents, energy in kWh); ``live`` holds kW
    flows: pv, grid (+ import), batt (+ charging), ev, load. ``mode`` is the
    battery control mode: off (manual), timers, shadow (advise) or auto.
    """
    out: list[dict[str, str]] = []
    add = lambda level, text, why="": out.append({"level": level, "text": text, "why": why})  # noqa: E731

    period, rate, fit = s.get("period"), s.get("import_rate") or 0.0, s.get("feed_in_rate") or 0.0
    soc, usable = s.get("battery_soc"), s.get("battery_usable")
    nxt, nxt_at = s.get("next_period"), s.get("next_change")
    to_next = _mins_until(nxt_at, now)
    pv, grid, batt, ev = (live.get(k, 0.0) or 0.0 for k in ("pv", "grid", "batt", "ev"))
    plugged, ev_room = bool(s.get("ev_plugged")), s.get("ev_room") or 0.0
    hands_off = mode == "off"

    # Where the EV's power comes from: only the grid share costs money now; solar is free and the
    # home battery is fine as long as it still covers the house until the cheap window and the supply charge.
    ev_grid = min(ev, max(grid, 0.0)) if ev > 0.5 else 0.0
    ev_batt = min(ev - ev_grid, max(-batt, 0.0)) if ev > 0.5 else 0.0
    ev_solar = min(max(ev - ev_grid - ev_batt, 0.0), max(pv, 0.0))
    ev_grid += max(ev - ev_grid - ev_batt - ev_solar, 0.0)  # anything unexplained is assumed to be grid
    mix = ", ".join(p for p in (f"{ev_solar:.1f} kW solar" if ev_solar >= 0.1 else "",
                                f"{ev_batt:.1f} kW battery" if ev_batt >= 0.1 else "",
                                f"{ev_grid:.1f} kW grid" if ev_grid >= 0.1 else "") if p)
    b = s.get("budget") or {}
    spare = b.get("spare")
    cheap = period == "shoulder"
    need_txt = (f"{b.get('house', 0):.0f} kWh for the house until {b.get('until', '10:00')}"
                + (f" and {b['supply']:.0f} kWh of export for the supply charge" if b.get("supply") else ""))
    drain = max(-batt, 0.0)
    eta = ""
    if drain > 0.3 and b.get("usable"):
        eta = (now + timedelta(hours=b["usable"] / drain)).strftime("%H:%M")

    pre_peak = nxt == "peak" and to_next is not None and 0 < to_next <= 90 and ev > 0.5 and (ev_grid > 0.5 or (spare is not None and spare < 0))
    if ev > 0.5 and not cheap and not pre_peak:
        if ev_grid > 0.5:
            add(ACT, f"EV is pulling {ev_grid:.1f} kW from the grid at {rate:.0f}c (of its {ev:.1f} kW: {mix}).",
                f"pause it until {b.get('until', '10:00')} or lower its charge rate so solar and the battery can cover it")
        elif ev_batt > 0.5 and spare is not None and spare < 0:
            add(ACT, f"EV is draining the home battery: {-spare:.0f} kWh short of {need_txt}.",
                f"pause the EV, or the house will buy {rate:.0f}c power later tonight"
                + (f" (battery reaches its reserve about {eta})" if eta else ""))
        elif ev_batt > 0.5:
            more = f", about {spare / ev_batt:.1f} h more at this rate" if spare is not None and ev_batt > 0 else ""
            add(INFO, f"EV charging at {ev:.1f} kW from {mix}, no grid power.",
                f"battery keeps {need_txt} with {spare:.0f} kWh spare{more}" if spare is not None else "nothing to do")
        else:
            add(INFO, f"EV charging at {ev:.1f} kW from solar.", "free energy: nothing to do")
    if pre_peak:
        add(ACT, f"Peak starts at {_hm(nxt_at)} and the EV is charging at {ev:.1f} kW ({mix}).",
            "it will need the grid in peak: let it finish before then or pause it" if ev_grid > 0.5 else
            f"the battery can't also cover {need_txt}: pause it before then")

    # Is the battery enough for tonight?
    if not cheap and spare is not None and spare < 0 and not (ev_batt > 0.5):
        if b.get("supply") and b.get("house", 0) <= b.get("usable", 0):
            add(WARN, f"Stop exporting soon: the battery has {b['usable']:.0f} kWh usable and needs {b['house']:.0f} kWh for the house until {b['until']}.",
                f"the rest of the supply charge (${s.get('supply_left', 0):.2f}) isn't worth buying {rate:.0f}c power for later")
        else:
            add(WARN, f"Battery is {-spare:.0f} kWh short of {need_txt}.",
                (f"it reaches its reserve about {eta}; " if eta else "") + "the grid will cover the rest")
    if period == "peak" and grid > 0.5 and grid - ev_grid > 0.5:
        house = grid - ev_grid
        add(WARN, f"House is buying {house:.1f} kW at the peak rate ({rate:.0f}c).",
            "the battery should be covering the house; check its mode and reserve" if (soc or 0) > reserve + 5 else "battery is at its reserve")
    if spare is None and nxt == "peak" and to_next is not None and 0 < to_next <= 90 and soc is not None and soc < 60:
        add(WARN, f"Battery is at {soc:.0f}% going into the {_hm(nxt_at)} peak.", "it may run out before the cheap window")

    # Cheap shoulder window
    if period == "shoulder":
        if plugged and ev_room > 5 and ev < 0.5:
            add(ACT, f"Cheapest power now ({rate:.0f}c). The EV is plugged in with {ev_room:.0f} kWh of room: start charging.")
        elif not plugged and ev_room > 10:
            add(INFO, f"Plug in the EV before {_hm(nxt_at) or '14:00'} to charge at {rate:.0f}c.", f"{ev_room:.0f} kWh of room")
        short = s.get("pv_shortfall")
        if hands_off and soc is not None and soc < 90 and short is not None and short > 1:
            add(ACT, f"Solar looks {short:.0f} kWh short today. Top up the battery now at {rate:.0f}c.",
                "Autopilot is off, so nothing will do it for you")

    # Solar spilling to the grid for little money
    if pv > 2 and grid < -1 and (soc or 0) >= 97 and fit <= 5:
        add(ACT, f"Battery is full and {-grid:.1f} kW is going to the grid for {fit:.0f}c. Run the dishwasher, laundry or EV now.",
            "that energy is almost free")

    # EV first: exporting only to cover the supply charge
    if s.get("ev_guard") and ev > 0.5:
        left = s.get("supply_left")
        add(INFO, s["ev_guard"], f"${left:.2f} of the supply charge left to earn" if left else "supply charge covered")

    # Evening feed-in window
    if s.get("fit_high", fit >= 20) and hands_off and grid > -0.5:
        room = spare if spare is not None else (usable or 0) - 5
        if room is not None and room > 2:
            add(INFO, f"Feed-in pays {fit:.0f}c now. The battery can spare {room:.0f} kWh after the house's needs: export up to that from the Battery tab.",
                "Autopilot and timers are off")

    # Tomorrow
    tom, low = s.get("pv_tomorrow"), s.get("low_solar")
    if now.hour >= 17 and tom is not None and low and tom < low:
        add(INFO, f"Tomorrow looks dull ({tom:.0f} kWh of solar). Plan a battery top-up in the {s.get('shoulder_window') or '10:00 to 14:00'} window.")

    if soc is not None and soc <= reserve + 3 and period != "shoulder":
        add(WARN, f"Battery is down to {soc:.0f}% (reserve {reserve:.0f}%).")

    if not out:
        add(INFO, "Nothing needs doing right now.", f"{(period or '').replace('_', ' ')} at {rate:.0f}c")
    out.sort(key=lambda t: _RANK.get(t["level"], 3))
    seen, uniq = set(), []
    for t in out:
        if t["text"] not in seen:
            seen.add(t["text"])
            uniq.append(t)
    return uniq[:limit]
