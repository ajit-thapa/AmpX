"""Instant, rule-based energy tips. Pure Python, no Home Assistant imports.

Works without any AI model: a handful of plain checks on the tariff, the live
power flows and the battery and EV. Each tip says what to do and why, in one line.
"""

from __future__ import annotations

from datetime import datetime
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

    # Peak is about to start or running
    if nxt == "peak" and to_next is not None and 0 < to_next <= 90:
        if ev > 0.5:
            add(ACT, f"Peak starts at {_hm(nxt_at)}. The EV is charging at {ev:.1f} kW: let it finish before then or pause it.",
                "peak import costs about 4x the shoulder rate")
        if soc is not None and soc < 60:
            add(WARN, f"Battery is at {soc:.0f}% going into the {_hm(nxt_at)} peak.", "it may run out before the cheap window")
    if period == "peak":
        if grid > 0.5:
            add(WARN, f"Buying {grid:.1f} kW at the peak rate ({rate:.0f}c).",
                "the battery should be covering the house; check its mode and reserve" if (soc or 0) > reserve + 5 else "battery is at its reserve")
        if ev > 0.5:
            add(ACT, f"EV is charging in peak ({ev:.1f} kW at {rate:.0f}c). Pause it until 10:00 if you can.")

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

    # Evening feed-in window
    if fit >= 20 and hands_off and usable and usable > 5 and grid > -0.5:
        add(INFO, f"Feed-in pays {fit:.0f}c now and the battery has {usable:.0f} kWh usable. Export from the Battery tab if you want.",
            "Autopilot and timers are off")

    # Tomorrow
    tom, low = s.get("pv_tomorrow"), s.get("low_solar")
    if now.hour >= 17 and tom is not None and low and tom < low:
        add(INFO, f"Tomorrow looks dull ({tom:.0f} kWh of solar). Plan a battery top-up in the 10:00 to 14:00 window.")

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
