"""Battery decision ladder. Pure Python, no Home Assistant imports.

One call answers: which rule applies right now, what it does and why. The first rule that
matches wins, in the order of ``RULES``. The caller carries the action out and logs the verdict.

 1. stale        readings missing or stuck: hand the battery back to the inverter (AmpX's own
                 dispatch, or any dispatch while AmpX runs the battery)
 2. peak_guard   peak rate: never charge the battery from the grid
 3. ev_grid      EV charging from the grid: the battery covers only the house
 4. reserve      battery at its reserve: stop discharging
    house_rule   battery holds only the house's share until the cheap window: stop exporting
    export_cap   feed-in is low: no forced export (same scope as stale; an export the owner
                 started from AmpX is left alone)
 5. manual, plan a dispatch someone started: the owner, or the day plan and its timers
 6. autopilot    a dispatch Autopilot's rules started
 7. self_consumption  nothing above applies: the inverter runs the battery
"""

from __future__ import annotations

from dataclasses import dataclass

from .safety import DWELL_S
from .tariff import OFF_PEAK, PEAK, SHOULDER

# rules, in priority order
STALE = "stale"
PEAK_GUARD = "peak_guard"
EV_GRID = "ev_grid"
RESERVE = "reserve"
HOUSE_RULE = "house_rule"
EXPORT_CAP = "export_cap"
MANUAL = "manual"
PLAN = "plan"
AUTOPILOT = "autopilot"
SELF = "self_consumption"
RULES = (STALE, PEAK_GUARD, EV_GRID, RESERVE, HOUSE_RULE, EXPORT_CAP, MANUAL, PLAN, AUTOPILOT, SELF)

# actions
HAND_BACK = "hand_back"            # stop any forced dispatch; the inverter runs itself
STOP_CHARGE = "stop_charge"
HOUSE_ONLY = "house_only"          # discharge at the house's load so the grid feeds only the EV
RESUME = "resume"                  # leave house-only, back to normal
STOP_DISCHARGE = "stop_discharge"
PAUSE_EV = "pause_ev"              # advice only: AmpX cannot switch every charger
TOPUP = "topup"
EXPORT = "export"
HOLD = "hold"
NONE = "none"
WRITES = frozenset({HAND_BACK, STOP_CHARGE, HOUSE_ONLY, RESUME, STOP_DISCHARGE})

# inverter dispatch modes
NORMAL = "Normal"
CHARGE = "Force Charge"
DISCHARGE = "Force Discharge"

EV_ON_KW = 0.5       # the EV counts as charging above this
EV_OFF_KW = 0.3      # and as finished below this
SPARE_KWH = 0.5      # battery energy beyond the house's need that counts as "nothing to spare"
RESERVE_MARGIN = 1.0  # % above the reserve where a forced discharge is stopped


@dataclass(frozen=True)
class Inputs:
    stale: str | None = None        # why readings can't be trusted, or None
    period: str = OFF_PEAK          # tariff period now
    mode: str | None = None         # inverter dispatch mode
    soc: float | None = None        # battery level, %
    reserve: float = 20.0           # battery reserve, %
    house_rule: bool = True         # the house never buys grid power outside the cheap window
    spare_kwh: float | None = None  # battery energy above what the house needs until the cheap window
    ev_kw: float = 0.0              # EV charger draw
    acting: bool = False            # AmpX runs the battery (timers or Autopilot), not just advising
    house_only: bool = False        # AmpX already runs the battery at house load
    held_s: float = float("inf")    # seconds since house-only began
    export_pays: bool = False       # feed-in is at the plan's best rate
    source: str | None = None       # who started the running dispatch: MANUAL, PLAN, AUTOPILOT or unknown
    edge: bool = False              # a tariff window changed in the last two minutes: scheduled stops run first


@dataclass(frozen=True)
class Verdict:
    rule: str
    action: str
    reason: str


def evaluate(i: Inputs) -> Verdict:
    forced = i.mode in (CHARGE, DISCHARGE)
    # AmpX polices its own dispatch always, and any dispatch while it runs the battery. In Manual
    # or Advise someone else's dispatch only meets the hard limits: peak, reserve, the house's share.
    ours = i.acting or i.house_only or i.source in (PLAN, AUTOPILOT)

    # 1. readings can't be trusted
    if i.stale:
        action = HAND_BACK if (forced or i.house_only) and ours else NONE
        return Verdict(STALE, action, f"{i.stale}: the inverter runs the battery until readings return")

    # 2. peak: never charge the battery from the grid
    if i.period == PEAK and i.mode == CHARGE and not i.edge:
        return Verdict(PEAK_GUARD, STOP_CHARGE, "peak rate: no grid charging")

    guard = i.house_rule and i.period != SHOULDER and i.spare_kwh is not None

    # 3. EV on the grid: the battery covers only the house
    if i.house_only:
        if guard and i.period != PEAK and i.acting and (i.ev_kw >= EV_OFF_KW or i.held_s < DWELL_S):
            return Verdict(EV_GRID, HOUSE_ONLY, "EV charges from the grid: the battery covers only the house")
        return Verdict(SELF, RESUME, "EV finished or the window changed: battery back to normal")
    if (guard and i.ev_kw >= EV_ON_KW and i.period != PEAK and i.spare_kwh <= SPARE_KWH
            and i.acting and i.mode in (None, NORMAL)):
        return Verdict(EV_GRID, HOUSE_ONLY, "EV charges from the grid and the battery has nothing to spare: it covers only the house")

    # 4. floors on a forced discharge
    if i.mode == DISCHARGE:
        if i.soc is not None and i.soc <= i.reserve + RESERVE_MARGIN:
            return Verdict(RESERVE, STOP_DISCHARGE, f"battery at the {i.reserve:.0f}% reserve")
        if guard and i.spare_kwh <= SPARE_KWH:
            return Verdict(HOUSE_RULE, STOP_DISCHARGE, "the battery holds only what the house needs until the cheap window")
        if not i.export_pays and ours and i.source != MANUAL and not i.edge:
            return Verdict(EXPORT_CAP, STOP_DISCHARGE, "feed-in is low: the battery covers the house, nothing is exported")

    # peak, second part: an EV the battery can't carry. Advice, so it comes after the battery actions.
    if guard and i.ev_kw >= EV_ON_KW and i.period == PEAK and i.spare_kwh - i.ev_kw * 0.5 < 0:
        return Verdict(PEAK_GUARD, PAUSE_EV, "peak: the battery can't carry the EV and the house; pause the EV")

    # 5-6. a dispatch someone started
    if forced:
        action = TOPUP if i.mode == CHARGE else EXPORT
        if i.source == PLAN:
            return Verdict(PLAN, action, "following the day plan")
        if i.source == AUTOPILOT:
            return Verdict(AUTOPILOT, action, "started by Autopilot")
        return Verdict(MANUAL, action, "started by hand or by another automation")

    # 7. nothing to do
    return Verdict(SELF, NONE, "self-consumption: solar first, then the battery, then the grid")
