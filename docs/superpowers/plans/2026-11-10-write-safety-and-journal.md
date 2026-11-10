# Write Safety, Decision Ladder and Journal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the items `docs/REQUIREMENTS.md` marks *(planned)*: stale-sensor hand-back, an explicit first-match decision ladder with a journal, command dwell and deadband, the no-export cap and observe mode, and fix what the review of `main` (61b31c7) found.

**Architecture:** Two new pure modules hold the logic: `safety.py` (frozen-reading watch, command gate) and `ladder.py` (ordered rules returning rule, action, reason). `energy.py` keeps the Home Assistant I/O: `house_guard` collects facts, asks the ladder, journals the verdict and carries it out through the single write gate `_set`. A `Journal` feature stores verdicts.

**Tech Stack:** Python 3.13, Home Assistant 2026.2, pytest + pytest-homeassistant-custom-component, vanilla JS panel (`frontend/ampx-studio.js`).

## Global Constraints

- House never imports grid outside the cheap window. Only the EV may, and never in peak.
- Evening export only above the floor; the floor rises for overnight need.
- No hard-coded home values in `DEFAULTS`. `migrate.py` fills legacy installs only.
- Pure logic modules have no Home Assistant imports and are unit tested.
- Features follow load, start, stop, dump.
- Every panel write is validated in `websocket.CONTROL_OPTIONS`.
- Existing installs keep controlling the battery after upgrade. New installs start in observe mode.
- Branch `feat/write-safety-journal`. No merge to `main` without the owner's say.
- Run tests with: `python3 -m pytest -q -p no:cacheprovider`

## Review findings (main at 61b31c7)

| # | Finding | Fix in |
|---|---|---|
| R1 | Panel reads `control.decision_engine`, but the overview never sends it. Hermes mode never shows in the panel. | Task 6 |
| R2 | Sealion 7 charges from the grid in peak when below minimum. Breaks "never in peak". | Task 5 |
| R3 | Sealion 7 has its own hard-coded windows (`10-14`, `14-21`) and ignores peak days, so it pauses on weekends and holidays. | Task 5 |
| R4 | Sealion 7 control mode presses the car's buttons even when Hermes is the engine. | Task 5 |
| R5 | Power follow-up writes use a 0.1 kW deadband and no dwell. | Task 4 |
| R6 | EV-first guard exports at full power to "cover the supply charge" even when feed-in is 3c. | Task 4 |
| R7 | No guard stops a grid charge that is still running in peak. | Task 4 |
| R8 | Nothing reacts to a battery level that goes missing, or a grid reading that stops moving, while AmpX forces dispatch. | Task 4 |
| R9 | `tariff.py` peak 16–20 is only the dataclass default. The live window comes from options `peak_start`/`peak_end`. No code change. | none |

## File Structure

| File | Responsibility |
|---|---|
| `custom_components/ampx/safety.py` (new) | `FreezeWatch`, `CommandGate`. Pure. |
| `custom_components/ampx/ladder.py` (new) | `Inputs`, `Verdict`, `evaluate`. Pure. |
| `custom_components/ampx/journal.py` (new) | `Journal` feature: stores verdicts. |
| `custom_components/ampx/tariff.py` | `export_pays`. |
| `custom_components/ampx/energy.py` | Ladder facts, carrying out verdicts, write gate, dispatch source. |
| `custom_components/ampx/runtime.py` | `observe()`, journal feature, timer source. |
| `custom_components/ampx/autopilot.py` | Dispatch source, journal entries. |
| `custom_components/ampx/migrate.py`, `const.py`, `config_flow.py` | `observe_only` option, schema 3. |
| `custom_components/ampx/sealion7.py`, `sealion7_feature.py` | Peak hard rule, tariff windows, engine and observe gates. |
| `custom_components/ampx/websocket.py`, `sensor.py`, `strings.json`, `translations/en.json` | Overview payload, option validators, decision sensor. |
| `custom_components/ampx/frontend/ampx-studio.js` | Observe toggle, journal card, Sealion 7 placeholders. |

---

### Task 1: safety.py (freeze watch, command gate)

**Files:**
- Create: `custom_components/ampx/safety.py`
- Test: `tests/test_safety.py`

**Interfaces:**
- Produces: `STALE_AFTER_S = 600`, `DWELL_S = 300`, `DEADBAND_KW = 0.2`
- Produces: `FreezeWatch(after_s=STALE_AFTER_S)` with `update(key, value: float | None, now)`, `clear(key)`, `state(key, now, may_hold=False) -> "missing" | "stuck" | None`
- Produces: `CommandGate(dwell_s=DWELL_S, deadband_kw=DEADBAND_KW)` with `allow(current: float | None, want: float, now, reason: str, urgent=False) -> bool`, `sent(now, reason)`

- [ ] **Step 1: Write the failing test**

<!-- file: tests/test_safety.py -->
```python
"""Write safety: frozen-reading watch and command dwell. Pure logic."""

from datetime import datetime, timedelta

from custom_components.ampx.safety import DEADBAND_KW, DWELL_S, STALE_AFTER_S, CommandGate, FreezeWatch

T0 = datetime(2026, 11, 10, 18, 0)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


# ---- FreezeWatch ------------------------------------------------------------
def test_changing_reading_is_never_stale():
    w = FreezeWatch()
    for i in range(0, STALE_AFTER_S * 2, 60):
        w.update("grid", 1000.0 + i, at(i))
    assert w.state("grid", at(STALE_AFTER_S * 2)) is None


def test_reading_stuck_on_one_value_is_reported_after_the_limit():
    w = FreezeWatch()
    w.update("grid", -5000.0, at(0))
    w.update("grid", -5000.0, at(STALE_AFTER_S - 1))
    assert w.state("grid", at(STALE_AFTER_S - 1)) is None
    w.update("grid", -5000.0, at(STALE_AFTER_S))
    assert w.state("grid", at(STALE_AFTER_S)) == "stuck"


def test_missing_reading_is_reported_after_the_limit():
    w = FreezeWatch()
    w.update("soc", None, at(0))
    assert w.state("soc", at(STALE_AFTER_S - 1)) is None
    assert w.state("soc", at(STALE_AFTER_S)) == "missing"


def test_battery_level_may_hold_one_value_but_not_go_missing():
    w = FreezeWatch()
    w.update("soc", 100.0, at(0))
    assert w.state("soc", at(STALE_AFTER_S * 6), may_hold=True) is None
    w.update("soc", None, at(STALE_AFTER_S * 6))
    assert w.state("soc", at(STALE_AFTER_S * 7), may_hold=True) == "missing"


def test_a_new_value_restarts_the_clock_and_clear_forgets():
    w = FreezeWatch()
    w.update("grid", 1.0, at(0))
    w.update("grid", 2.0, at(STALE_AFTER_S - 10))
    assert w.state("grid", at(STALE_AFTER_S + 10)) is None
    w.clear("grid")
    assert w.state("grid", at(STALE_AFTER_S * 5)) is None
    assert w.state("never_seen", at(0)) is None


# ---- CommandGate ------------------------------------------------------------
def test_change_inside_the_deadband_is_not_sent():
    g = CommandGate()
    assert not g.allow(5.0, 5.0 + DEADBAND_KW - 0.05, at(0), "house_only")
    assert g.allow(8.0, 8.2, at(0), "house_only")  # exactly the deadband counts as a change


def test_first_change_is_sent_then_lowering_waits_for_the_dwell():
    g = CommandGate()
    assert g.allow(5.0, 3.0, at(0), "house_only")
    g.sent(at(0), "house_only")
    assert not g.allow(3.0, 2.0, at(DWELL_S - 1), "house_only")
    assert g.allow(3.0, 2.0, at(DWELL_S), "house_only")


def test_urgent_change_skips_the_dwell_but_not_the_deadband():
    g = CommandGate()
    g.sent(at(0), "house_only")
    assert g.allow(3.0, 4.0, at(10), "house_only", urgent=True)
    assert not g.allow(3.0, 3.1, at(10), "house_only", urgent=True)


def test_a_new_reason_is_a_new_situation_and_is_sent_at_once():
    g = CommandGate()
    g.sent(at(0), "ev_first:export")
    assert g.allow(10.0, 8.2, at(5), "ev_first:trickle")


def test_unknown_current_power_is_always_sent():
    g = CommandGate()
    g.sent(at(0), "house_only")
    assert g.allow(None, 1.2, at(5), "house_only")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_safety.py -q -p no:cacheprovider`
Expected: collection error, `ModuleNotFoundError: No module named 'custom_components.ampx.safety'`

- [ ] **Step 3: Write minimal implementation**

<!-- file: custom_components/ampx/safety.py -->
```python
"""Write safety for battery control: frozen-reading watch and command dwell. Pure Python, no Home Assistant imports."""

from __future__ import annotations

from datetime import datetime

STALE_AFTER_S = 600  # a reading missing, or stuck on one value, this long is not trusted
DWELL_S = 300        # least time between automatic power changes made for the same reason
DEADBAND_KW = 0.2    # smaller power changes are not sent


class FreezeWatch:
    """Remembers when each reading last changed, and says when one is missing or stuck too long."""

    def __init__(self, after_s: int = STALE_AFTER_S) -> None:
        self.after_s = after_s
        self._seen: dict[str, tuple[float | None, datetime]] = {}

    def update(self, key: str, value: float | None, now: datetime) -> None:
        last = self._seen.get(key)
        if last is None or last[0] != value:
            self._seen[key] = (value, now)

    def clear(self, key: str) -> None:
        self._seen.pop(key, None)

    def state(self, key: str, now: datetime, may_hold: bool = False) -> str | None:
        """"missing", "stuck" or None. ``may_hold``: this reading may sit on one value (a battery level)."""
        last = self._seen.get(key)
        if last is None:
            return None
        value, since = last
        if (now - since).total_seconds() < self.after_s:
            return None
        if value is None:
            return "missing"
        return None if may_hold else "stuck"


class CommandGate:
    """Deadband and dwell for automatic power changes, so the battery is not written every cycle.

    A change smaller than the deadband is never sent. A bigger one is sent at once when it is
    urgent (it keeps the house off the grid), when the reason changed (a new situation), or when
    the current power is unknown. Otherwise it waits out the dwell since the last change."""

    def __init__(self, dwell_s: int = DWELL_S, deadband_kw: float = DEADBAND_KW) -> None:
        self.dwell_s = dwell_s
        self.deadband_kw = deadband_kw
        self._at: datetime | None = None
        self._reason: str | None = None

    def allow(self, current: float | None, want: float, now: datetime, reason: str, urgent: bool = False) -> bool:
        if current is None:
            return True
        if round(abs(want - current), 3) < self.deadband_kw:
            return False
        if urgent or self._at is None or reason != self._reason:
            return True
        return (now - self._at).total_seconds() >= self.dwell_s

    def sent(self, now: datetime, reason: str) -> None:
        self._at, self._reason = now, reason
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_safety.py -q -p no:cacheprovider`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add tests/test_safety.py custom_components/ampx/safety.py
git commit -m "Add freeze watch and command gate for battery write safety"
```

---

### Task 2: ladder.py (decision ladder) and tariff.export_pays

**Files:**
- Create: `custom_components/ampx/ladder.py`
- Modify: `custom_components/ampx/tariff.py` (add `export_pays` after `feed_in_rate`)
- Test: `tests/test_ladder.py`, `tests/test_tariff.py`

**Interfaces:**
- Consumes: `safety.DWELL_S`; `tariff.PEAK`, `tariff.SHOULDER`, `tariff.OFF_PEAK`
- Produces: rule names `STALE, PEAK_GUARD, EV_GRID, RESERVE, HOUSE_RULE, EXPORT_CAP, MANUAL, PLAN, AUTOPILOT, SELF`; tuple `RULES` in priority order
- Produces: action names `HAND_BACK, STOP_CHARGE, HOUSE_ONLY, RESUME, STOP_DISCHARGE, PAUSE_EV, TOPUP, EXPORT, HOLD, NONE`; `WRITES` (actions that change the inverter)
- Produces: mode names `NORMAL = "Normal"`, `CHARGE = "Force Charge"`, `DISCHARGE = "Force Discharge"`
- Produces: `Inputs` (frozen dataclass, fields below), `Verdict(rule, action, reason)`, `evaluate(Inputs) -> Verdict`
- Produces: `tariff.export_pays(now, plan) -> bool`

- [ ] **Step 1: Write the failing tests**

<!-- file: tests/test_ladder.py -->
```python
"""Battery decision ladder: first match wins, every verdict names its rule and reason."""

from dataclasses import replace

from custom_components.ampx import ladder as L
from custom_components.ampx.safety import DWELL_S
from custom_components.ampx.tariff import OFF_PEAK, PEAK, SHOULDER

# Off-peak evening, inverter in Normal, plenty in the battery, AmpX in charge of it.
BASE = L.Inputs(period=OFF_PEAK, mode=L.NORMAL, soc=80.0, reserve=20.0, house_rule=True,
                spare_kwh=10.0, ev_kw=0.0, acting=True, export_pays=False)


def v(**kw):
    return L.evaluate(replace(BASE, **kw))


def test_nothing_special_is_self_consumption():
    out = v()
    assert (out.rule, out.action) == (L.SELF, L.NONE) and out.reason


def test_stale_readings_hand_a_forced_dispatch_back_and_beat_every_other_rule():
    out = v(stale="battery level missing for 10 min", mode=L.DISCHARGE, period=PEAK, spare_kwh=0.0, ev_kw=7.0)
    assert (out.rule, out.action) == (L.STALE, L.HAND_BACK)
    assert "battery level missing" in out.reason
    assert v(stale="grid reading stuck for 10 min").action == L.NONE  # nothing forced: nothing to hand back


def test_peak_never_charges_the_battery_from_the_grid():
    out = v(period=PEAK, mode=L.CHARGE)
    assert (out.rule, out.action) == (L.PEAK_GUARD, L.STOP_CHARGE)
    assert v(period=SHOULDER, mode=L.CHARGE).action == L.TOPUP
    assert v(period=OFF_PEAK, mode=L.CHARGE).action == L.TOPUP  # the owner's own off-peak charge is left alone


def test_ev_on_the_grid_with_nothing_to_spare_puts_battery_on_house_only():
    out = v(ev_kw=7.0, spare_kwh=0.2)
    assert (out.rule, out.action) == (L.EV_GRID, L.HOUSE_ONLY)
    assert v(ev_kw=7.0, spare_kwh=5.0).action == L.NONE  # battery has spare: it may feed the car
    assert v(ev_kw=7.0, spare_kwh=0.2, acting=False).action == L.NONE  # AmpX is not running the battery
    assert v(ev_kw=7.0, spare_kwh=0.2, house_rule=False).action == L.NONE
    assert v(ev_kw=7.0, spare_kwh=0.2, period=SHOULDER).action == L.NONE


def test_house_only_holds_through_a_short_ev_dip_then_resumes():
    held = v(house_only=True, mode=L.DISCHARGE, ev_kw=0.0, spare_kwh=0.2, held_s=DWELL_S - 1)
    assert (held.rule, held.action) == (L.EV_GRID, L.HOUSE_ONLY)
    done = v(house_only=True, mode=L.DISCHARGE, ev_kw=0.0, spare_kwh=0.2, held_s=DWELL_S)
    assert (done.rule, done.action) == (L.SELF, L.RESUME)


def test_house_only_ends_at_once_when_the_window_or_control_changes():
    for change in (dict(period=SHOULDER), dict(period=PEAK), dict(acting=False), dict(house_rule=False), dict(spare_kwh=None)):
        out = v(house_only=True, mode=L.DISCHARGE, ev_kw=7.0, held_s=0.0, **change)
        assert out.action == L.RESUME, change


def test_forced_export_stops_at_the_house_share():
    out = v(mode=L.DISCHARGE, spare_kwh=0.5, export_pays=True)
    assert (out.rule, out.action) == (L.HOUSE_RULE, L.STOP_DISCHARGE)
    assert v(mode=L.DISCHARGE, spare_kwh=0.5, export_pays=True, house_rule=False, source=L.MANUAL).action == L.EXPORT


def test_forced_export_stops_at_the_reserve_even_without_the_house_rule():
    out = v(mode=L.DISCHARGE, soc=21.0, house_rule=False, export_pays=True)
    assert (out.rule, out.action) == (L.RESERVE, L.STOP_DISCHARGE) and "20%" in out.reason


def test_no_export_when_it_does_not_pay_unless_the_owner_started_it():
    out = v(mode=L.DISCHARGE, export_pays=False, source=L.AUTOPILOT)
    assert (out.rule, out.action) == (L.EXPORT_CAP, L.STOP_DISCHARGE)
    assert v(mode=L.DISCHARGE, export_pays=False, source=None).rule == L.EXPORT_CAP  # unknown starter is capped
    assert v(mode=L.DISCHARGE, export_pays=False, source=L.MANUAL).rule == L.MANUAL
    assert v(mode=L.DISCHARGE, export_pays=True, source=L.AUTOPILOT).rule == L.AUTOPILOT


def test_scheduled_stops_get_to_run_first_at_a_window_edge():
    """Timers and Autopilot stop their own dispatch seconds after a window ends: no guard, no alert, before that."""
    assert v(period=PEAK, mode=L.CHARGE, edge=True, source=L.AUTOPILOT).rule == L.AUTOPILOT
    assert v(mode=L.DISCHARGE, export_pays=False, edge=True, source=L.PLAN).rule == L.PLAN
    # the floors never wait
    assert v(mode=L.DISCHARGE, spare_kwh=0.2, export_pays=False, edge=True).rule == L.HOUSE_RULE
    assert v(mode=L.DISCHARGE, soc=20.0, export_pays=False, edge=True).rule == L.RESERVE


def test_peak_ev_the_battery_cannot_carry_is_flagged_after_battery_actions():
    out = v(period=PEAK, ev_kw=7.0, spare_kwh=1.0)
    assert (out.rule, out.action) == (L.PEAK_GUARD, L.PAUSE_EV)
    assert v(period=PEAK, ev_kw=7.0, spare_kwh=20.0).action == L.NONE
    # a forced export with nothing to spare is stopped first
    assert v(period=PEAK, ev_kw=7.0, spare_kwh=0.2, mode=L.DISCHARGE, export_pays=True).action == L.STOP_DISCHARGE


def test_running_dispatch_names_who_started_it():
    assert v(mode=L.DISCHARGE, export_pays=True, source=L.PLAN).rule == L.PLAN
    assert v(mode=L.CHARGE, period=SHOULDER, source=L.PLAN).action == L.TOPUP
    assert v(mode=L.DISCHARGE, export_pays=True, source=L.AUTOPILOT).action == L.EXPORT
    assert v(mode=L.CHARGE, period=SHOULDER, source=None).rule == L.MANUAL


def test_every_rule_is_listed_in_priority_order():
    assert L.RULES[:5] == (L.STALE, L.PEAK_GUARD, L.EV_GRID, L.RESERVE, L.HOUSE_RULE)
    assert L.RULES[-1] == L.SELF and len(set(L.RULES)) == len(L.RULES)
    assert L.WRITES == {L.HAND_BACK, L.STOP_CHARGE, L.HOUSE_ONLY, L.RESUME, L.STOP_DISCHARGE}
```

Append to `tests/test_tariff.py`:

<!-- append: tests/test_tariff.py -->
```python


def test_export_pays_only_at_the_best_feed_in_rate():
    assert t.export_pays(at(3, 18), PLAN)  # 28c from 17:00 to 21:00
    assert not t.export_pays(at(3, 12), PLAN)  # 3c
    flat = t.Plan(fit_evening=5.0, fit_morning=5.0, fit_off_peak=5.0)
    assert t.export_pays(at(3, 12), flat)  # a flat feed-in never blocks an export
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ladder.py tests/test_tariff.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: ...ampx.ladder` and `AttributeError: module ... has no attribute 'export_pays'`

- [ ] **Step 3: Write minimal implementation**

Add to `custom_components/ampx/tariff.py` after `feed_in_rate`:

```python
def export_pays(now: datetime, plan: Plan) -> bool:
    """True while the feed-in rate is at the plan's best. A flat feed-in always pays."""
    return feed_in_rate(now, plan) >= max(plan.fit_evening, plan.fit_morning, plan.fit_off_peak)
```

<!-- file: custom_components/ampx/ladder.py -->
```python
"""Battery decision ladder. Pure Python, no Home Assistant imports.

One call answers: which rule applies right now, what it does and why. The first rule that
matches wins, in the order of ``RULES``. The caller carries the action out and logs the verdict.

 1. stale        readings missing or stuck: hand the battery back to the inverter
 2. peak_guard   peak rate: never charge the battery from the grid
 3. ev_grid      EV charging from the grid: the battery covers only the house
 4. reserve      battery at its reserve: stop discharging
    house_rule   battery holds only the house's share until the cheap window: stop exporting
    export_cap   feed-in is low: no forced export (the owner's own export is left alone)
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

    # 1. readings can't be trusted
    if i.stale:
        action = HAND_BACK if forced or i.house_only else NONE
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
        if not i.export_pays and i.source != MANUAL and not i.edge:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_ladder.py tests/test_tariff.py -q -p no:cacheprovider`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_ladder.py tests/test_tariff.py custom_components/ampx/ladder.py custom_components/ampx/tariff.py
git commit -m "Add battery decision ladder and export_pays"
```

---

### Task 3: Observe mode, journal, schema 3 migration

**Files:**
- Create: `custom_components/ampx/journal.py`
- Modify: `const.py` (add `CONF_OBSERVE = "observe_only"`, `DEFAULTS[CONF_OBSERVE] = True`), `migrate.py` (`SCHEMA = 3`), `config_flow.py` (new entries use `migrate.SCHEMA`; option in the `autopilot` section), `strings.json` + `translations/en.json` (label), `runtime.py` (`observe()`, `self.journal`), `energy.py` (`_set` gate, result strings)
- Test: `tests/test_observe_journal.py`

**Interfaces:**
- Consumes: `ladder.Verdict`
- Produces: `AmpX.observe() -> bool`; `AmpX.journal: Journal`
- Produces: `Journal.add(rule, action, reason, now=None, *, soc=None, mode=None, observe=False) -> dict`; `Journal.note(verdict, now=None, *, soc=None, mode=None, observe=False) -> bool`; `Journal.last`; `Journal.items` (newest first, 100 kept)
- Produces: `EnergyBrain._set` returns False and sends nothing in observe mode; `start_topup`, `start_export`, `stop` return `"observe only: nothing sent"` then
- Produces: `migrate.upgrade` sets `observe_only` False for entries below schema 3; LEGACY fill only below schema 2

- [ ] **Step 1: Write the failing test**

<!-- file: tests/test_observe_journal.py -->
```python
"""Observe mode, the decision journal, and the upgrade that keeps older installs in control."""

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx import ladder
from custom_components.ampx.const import CONF_OBSERVE, DEFAULTS, DOMAIN
from custom_components.ampx.journal import KEEP
from custom_components.ampx.migrate import LEGACY, SCHEMA, upgrade


def _record(hass: HomeAssistant) -> list:
    sent: list = []
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press")):
        async def rec(call, d=domain, s=svc):
            sent.append((d, s, dict(call.data)))
            if d == "select":
                hass.states.async_set(call.data["entity_id"], call.data["option"])
        hass.services.async_register(domain, svc, rec)
    return sent


async def _setup(hass: HomeAssistant, data: dict | None = None, **opts):
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={} if data is None else data, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def test_upgrade_keeps_older_installs_in_control():
    assert DEFAULTS[CONF_OBSERVE] is True
    from_v2 = upgrade({"battery_soc": "sensor.mine"}, {"schema": 2})
    assert from_v2[CONF_OBSERVE] is False and "ev_name" not in from_v2  # no legacy fill for a 0.21+ install
    from_v1 = upgrade({"battery_soc": "sensor.mine", CONF_OBSERVE: True}, {})
    assert from_v1[CONF_OBSERVE] is False and from_v1["ev_name"] == LEGACY["ev_name"]
    assert upgrade({}, {"schema": SCHEMA}) is None


async def test_new_install_starts_in_observe_mode(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "AmpX"})
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.data["schema"] == SCHEMA and entry.options[CONF_OBSERVE] is True
    assert hass.data[DOMAIN][entry.entry_id].observe()


async def test_older_install_keeps_writing_after_upgrade(hass: HomeAssistant):
    brain = await _setup(hass)
    assert not brain.observe() and brain.entry.data["schema"] == SCHEMA


async def test_observe_mode_sends_nothing_and_says_so(hass: HomeAssistant):
    async_mock_service(hass, "notify", "send_message")
    sent = _record(hass)
    brain = await _setup(hass, data={"schema": SCHEMA}, observe_only=True)
    hass.states.async_set(LEGACY["battery_soc"], "80")
    assert (await brain.energy.start_export(True, 5.0, 40)).startswith("observe only")
    assert (await brain.energy.start_topup(True, 5.0, 90)).startswith("observe only")
    assert (await brain.energy.stop()).startswith("observe only")
    await hass.async_block_till_done()
    assert sent == []


async def test_journal_logs_a_verdict_once_until_it_changes(hass: HomeAssistant):
    brain = await _setup(hass)
    j = brain.journal
    t0 = datetime(2026, 11, 10, 18, 0, tzinfo=dt_util.get_default_time_zone())
    idle = ladder.Verdict(ladder.SELF, ladder.NONE, "self-consumption")
    stop = ladder.Verdict(ladder.HOUSE_RULE, ladder.STOP_DISCHARGE, "the house needs it")
    assert j.note(idle, t0, soc=80.0, mode="Normal")
    assert not j.note(idle, t0 + timedelta(minutes=1))
    assert j.note(stop, t0 + timedelta(minutes=2), soc=40.0, mode="Force Discharge", observe=True)
    assert j.note(idle, t0 + timedelta(minutes=3))
    assert [e["rule"] for e in j.items] == [ladder.SELF, ladder.HOUSE_RULE, ladder.SELF]
    newest_stop = j.items[1]
    assert newest_stop["action"] == ladder.STOP_DISCHARGE and newest_stop["reason"] == "the house needs it"
    assert newest_stop["soc"] == 40.0 and newest_stop["mode"] == "Force Discharge" and newest_stop["observe"] is True
    assert j.last["time"].startswith("2026-11-10T18:03")


async def test_journal_does_not_repeat_what_autopilot_just_logged(hass: HomeAssistant):
    brain = await _setup(hass)
    j = brain.journal
    t0 = datetime(2026, 11, 10, 17, 0, 45, tzinfo=dt_util.get_default_time_zone())
    j.add(ladder.AUTOPILOT, ladder.EXPORT, "Evening export 7 kW down to 45%", t0)
    assert not j.note(ladder.Verdict(ladder.AUTOPILOT, ladder.EXPORT, "started by Autopilot"), t0 + timedelta(seconds=20))
    assert len(j.items) == 1 and "45%" in j.last["reason"]


async def test_journal_keeps_its_entries_across_a_restart_and_caps_them(hass: HomeAssistant):
    brain = await _setup(hass)
    j = brain.journal
    t0 = datetime(2026, 11, 10, 18, 0, tzinfo=dt_util.get_default_time_zone())
    for n in range(KEEP + 20):
        j.add(ladder.MANUAL, ladder.EXPORT, f"entry {n}", t0 + timedelta(minutes=n))
    assert len(j.items) == KEEP and j.last["reason"] == f"entry {KEEP + 19}"
    saved = j.dump()
    j.load(saved)
    assert len(j.items) == KEEP and j.last["reason"] == f"entry {KEEP + 19}"
    # after a restart the same verdict is not logged again
    assert not j.note(ladder.Verdict(ladder.MANUAL, ladder.EXPORT, "started by hand"), t0 + timedelta(days=1))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_observe_journal.py -q -p no:cacheprovider`
Expected: `ImportError: cannot import name 'CONF_OBSERVE'`

- [ ] **Step 3: Write minimal implementation**

<!-- file: custom_components/ampx/journal.py -->
```python
"""Decision journal: which rule drove the battery, what it did and why."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .feature import Feature
from .ladder import Verdict

KEEP = 100
REPEAT_S = 120  # a ladder verdict that repeats an entry this fresh is not logged twice


class Journal(Feature):
    name = "journal"

    def __init__(self, brain) -> None:
        super().__init__(brain)
        self.items: deque[dict[str, Any]] = deque(maxlen=KEEP)  # newest first
        self._state: tuple[str, str] | None = None  # the last ladder verdict seen

    def load(self, data) -> None:
        self.items = deque((data or {}).get("items", []), maxlen=KEEP)
        self._state = (self.items[0]["rule"], self.items[0]["action"]) if self.items else None

    def dump(self) -> dict[str, Any]:
        return {"items": list(self.items)}

    @property
    def last(self) -> dict[str, Any] | None:
        return self.items[0] if self.items else None

    def add(self, rule: str, action: str, reason: str, now: datetime | None = None, *,
            soc: float | None = None, mode: str | None = None, observe: bool = False) -> dict[str, Any]:
        """Log one decision. ``observe``: it was not carried out (observe mode or advice only)."""
        entry = {
            "time": (now or dt_util.now()).isoformat(timespec="seconds"),
            "rule": rule, "action": action, "reason": reason[:240],
            "soc": soc, "mode": mode, "observe": observe,
        }
        self.items.appendleft(entry)
        self.brain.save()
        return entry

    def note(self, verdict: Verdict, now: datetime | None = None, *, soc: float | None = None,
             mode: str | None = None, observe: bool = False) -> bool:
        """Log a ladder verdict when it differs from the last one. True when an entry was added."""
        now = now or dt_util.now()
        key = (verdict.rule, verdict.action)
        if key == self._state:
            return False
        self._state = key
        last = self.last
        if last and (last["rule"], last["action"]) == key:
            made = dt_util.parse_datetime(last["time"])
            if made and abs((now - made).total_seconds()) < REPEAT_S:
                return False
        self.add(verdict.rule, verdict.action, verdict.reason, now, soc=soc, mode=mode, observe=observe)
        return True
```

`const.py`: next to `CONF_ENGINE`

```python
CONF_OBSERVE = "observe_only"  # AmpX decides and logs, but sends nothing to the battery or EV
```

and in `DEFAULTS` next to `CONF_ENGINE: ENGINE_AMPX,`

```python
    CONF_OBSERVE: True,
```

`migrate.py`: `SCHEMA = 3`, import `CONF_OBSERVE`, and

```python
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
```

`config_flow.py`: `from .migrate import SCHEMA`; `data={"schema": SCHEMA}`; add `CONF_OBSERVE: sel.BooleanSelector(),` as the first key of `SECTIONS["autopilot"]`. `strings.json` and `translations/en.json`, options step `autopilot` data: `"observe_only": "Observe only (AmpX decides and logs, but sends nothing to the battery or EV)"`.

`runtime.py`: import `CONF_OBSERVE` and `Journal`; `self.journal = Journal(self)` after the timeline; add it to `features` after `self.timeline`; and

```python
    def observe(self) -> bool:
        """True when AmpX only watches: it decides and logs, but writes nothing."""
        return bool(self.opts.get(CONF_OBSERVE))
```

`energy.py`: in `_set`, after the Hermes check

```python
        if self.brain.observe():
            _LOGGER.debug("Observe mode: not writing %s.%s", domain, service)
            return False
```

`start_topup` and `start_export` end with

```python
        if ok:
            return "started"
        return OBSERVED if self.brain.observe() else "failed"
```

`stop` ends with

```python
        await self._set("button", "press", CONF_STOP)
        await self._set("select", "select_option", CONF_MODE, option="Normal")
        return OBSERVED if self.brain.observe() else "stopped"
```

with module constant `OBSERVED = "observe only: nothing sent"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_observe_journal.py tests/test_public.py tests/test_integration.py -q -p no:cacheprovider`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add -A tests custom_components
git commit -m "Add observe mode, decision journal and schema 3 upgrade"
```

---

### Task 4: Ladder drives the battery guards

**Files:**
- Modify: `custom_components/ampx/energy.py` (`__init__`, new `stale_reason`, `ladder_inputs`, `_carry_out`, `_run_house_only`; rewrite `house_guard`; `ev_guard` gate and `export_pays`; `source` on `start_topup`/`start_export`), `runtime.py` (timers pass `source=ladder.PLAN`), `autopilot.py` (`_act` source, journal entry in `decide`)
- Test: `tests/test_guard.py`; modify `tests/test_features.py::test_house_rule_guard` (house-only now holds 5 min after the EV stops)

**Interfaces:**
- Consumes: `ladder.evaluate`, `ladder.Inputs`, `safety.FreezeWatch`, `safety.CommandGate`, `tariff.export_pays`, `Journal.note`, `Journal.add`, `AmpX.observe`
- Produces: `EnergyBrain.house_guard(now) -> str | None` with results `"handed_back"`, `"charge_stopped"`, `"house_only"`, `"ended"`, `"export_stopped"`, `"export_capped"`, `"pause_ev"`, `"failed"`, `"observed"`, `None`
- Produces: `EnergyBrain.dispatch_source: str | None`, `EnergyBrain.verdict: ladder.Verdict | None`
- Produces: `start_topup(force=False, kw=None, target=None, source=ladder.MANUAL)`, `start_export(force=False, kw=None, floor=None, source=ladder.MANUAL)`

- [ ] **Step 1: Write the failing tests**

<!-- file: tests/test_guard.py -->
```python
"""The decision ladder wired to the battery: stale hand-back, peak guard, floors, export cap, dwell."""

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx import ladder
from custom_components.ampx.const import DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY, SCHEMA

MODE, POWER, SOC = LEGACY["dispatch_mode"], LEGACY["dispatch_power"], LEGACY["battery_soc"]
GRID, EV, PV, BATT = LEGACY["studio_grid"], LEGACY["studio_ev"], LEGACY["studio_pv"], LEGACY["studio_battery"]


def _record(hass: HomeAssistant) -> list:
    """Stand in for the inverter: remember every write, and let mode and power take effect."""
    sent: list = []
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press")):
        async def rec(call, d=domain, s=svc):
            sent.append((d, s, dict(call.data)))
            if d == "select":
                hass.states.async_set(call.data["entity_id"], call.data["option"])
            if d == "number" and call.data["entity_id"] == POWER:
                hass.states.async_set(POWER, str(call.data["value"]))
        hass.services.async_register(domain, svc, rec)
    return sent


async def _setup(hass: HomeAssistant, data: dict | None = None, **opts):
    async_mock_service(hass, "notify", "send_message")
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={} if data is None else data, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def when(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 10, hour, minute, tzinfo=dt_util.get_default_time_zone())  # a Tuesday


def flows(hass: HomeAssistant, grid_kw: float, ev_kw: float, batt_discharge_kw: float, pv_kw: float = 0.0) -> None:
    hass.states.async_set(GRID, str(grid_kw), {"unit_of_measurement": "kW"})
    hass.states.async_set(EV, str(ev_kw), {"unit_of_measurement": "kW"})
    hass.states.async_set(PV, str(pv_kw), {"unit_of_measurement": "kW"})
    hass.states.async_set(BATT, str(batt_discharge_kw), {"unit_of_measurement": "kW"})  # this sensor reads + for discharge


async def test_missing_battery_level_hands_the_battery_back(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    hass.states.async_set(SOC, "unavailable")
    assert await brain.energy.house_guard(when(18, 0)) is None  # not yet: a blip is not a fault
    assert await brain.energy.house_guard(when(18, 5)) is None
    assert await brain.energy.house_guard(when(18, 10)) == "handed_back"
    assert hass.states.get(MODE).state == ladder.NORMAL
    assert any(d == "button" for d, _, _ in sent)
    last = brain.journal.last
    assert last["rule"] == ladder.STALE and last["action"] == ladder.HAND_BACK and "battery level missing" in last["reason"]


async def test_grid_reading_stuck_during_a_forced_dispatch_hands_back(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "80")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    flows(hass, grid_kw=-5.0, ev_kw=0.0, batt_discharge_kw=6.0)
    for minute in (0, 5):
        assert await brain.energy.house_guard(when(18, minute)) is None
    assert await brain.energy.house_guard(when(18, 10)) == "handed_back"
    assert "grid reading stuck" in brain.journal.last["reason"]


async def test_a_steady_grid_reading_is_not_stale_while_the_battery_reading_moves(hass: HomeAssistant):
    """A rounded grid reading can sit still under an export limit. A frozen meter link freezes both readings."""
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "80")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    for minute, batt in ((0, 6.0), (5, 6.1), (10, 6.2), (15, 6.1)):
        flows(hass, grid_kw=-5.0, ev_kw=0.0, batt_discharge_kw=batt)
        assert await brain.energy.house_guard(when(18, minute)) is None
    assert hass.states.get(MODE).state == ladder.DISCHARGE


async def test_a_quiet_grid_reading_is_fine_when_nothing_is_forced(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "80")
    hass.states.async_set(MODE, ladder.NORMAL)
    flows(hass, grid_kw=0.0, ev_kw=0.0, batt_discharge_kw=1.0)
    for minute in (0, 10, 20, 30):
        assert await brain.energy.house_guard(when(22, minute)) is None
    assert sent == [] and brain.journal.last["rule"] == ladder.SELF


async def test_peak_stops_a_running_grid_charge(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "50")
    hass.states.async_set(MODE, ladder.CHARGE)
    flows(hass, grid_kw=5.0, ev_kw=0.0, batt_discharge_kw=-4.0)
    assert await brain.energy.house_guard(when(11, 0)) is None  # cheap window: charging is the plan
    assert hass.states.get(MODE).state == ladder.CHARGE
    flows(hass, grid_kw=5.2, ev_kw=0.0, batt_discharge_kw=-4.0)
    assert await brain.energy.house_guard(when(17, 30)) == "charge_stopped"  # peak is 16:00 to 20:00 by default
    assert hass.states.get(MODE).state == ladder.NORMAL
    assert brain.journal.last["rule"] == ladder.PEAK_GUARD


async def test_export_outside_the_paying_window_is_capped_unless_the_owner_started_it(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    hass.states.async_set(MODE, ladder.DISCHARGE)  # started by something AmpX did not see
    assert await brain.energy.house_guard(when(22, 0)) == "export_capped"
    assert hass.states.get(MODE).state == ladder.NORMAL and brain.journal.last["rule"] == ladder.EXPORT_CAP
    # the owner's own export from the panel is left alone
    assert await brain.energy.start_export(True, 5.0, 40) == "started"
    assert brain.energy.dispatch_source == ladder.MANUAL
    assert await brain.energy.house_guard(when(22, 1)) is None
    assert hass.states.get(MODE).state == ladder.DISCHARGE and brain.journal.last["rule"] == ladder.MANUAL


async def test_no_guard_alert_in_the_two_minutes_after_a_window_ends(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    assert await brain.energy.start_export(True, 5.0, 40, source=ladder.AUTOPILOT) == "started"
    assert await brain.energy.house_guard(when(21, 0)) is None  # the evening feed-in ended this minute
    assert hass.states.get(MODE).state == ladder.DISCHARGE
    assert await brain.energy.house_guard(when(21, 3)) == "export_capped"  # nothing stopped it: the cap does


async def test_reserve_stops_a_forced_export_even_without_the_house_rule(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto", house_off_grid=False)
    hass.states.async_set(SOC, "21")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    assert await brain.energy.house_guard(when(18, 0)) == "export_stopped"
    assert hass.states.get(MODE).state == ladder.NORMAL and brain.journal.last["rule"] == ladder.RESERVE


async def test_house_only_power_follows_the_house_with_deadband_and_dwell(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    brain.energy.profile = [1.0] * 24
    hass.states.async_set(SOC, "40")  # 10 kWh usable, the house needs 12 kWh until 10:00
    hass.states.async_set(MODE, ladder.NORMAL)
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=1.0)  # house 1.0 kW
    assert await brain.energy.house_guard(when(22, 0)) == "house_only"
    assert hass.states.get(POWER).state == "1.2"  # 1.0 kW house + 200 W
    power_writes = lambda: [x["value"] for d, _, x in sent if d == "number" and x["entity_id"] == POWER]  # noqa: E731
    assert power_writes() == [1.2]
    # 100 W less: inside the deadband, nothing is sent
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=0.9)
    assert await brain.energy.house_guard(when(22, 1)) == "house_only"
    assert power_writes() == [1.2]
    # 500 W less: a real change, but lowering waits out the dwell
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=0.5)
    assert await brain.energy.house_guard(when(22, 2)) == "house_only"
    assert power_writes() == [1.2]
    assert await brain.energy.house_guard(when(22, 5)) == "house_only"
    assert power_writes() == [1.2, 0.7]
    # the house draws more: raised at once so the house stays off the grid
    flows(hass, grid_kw=7.0, ev_kw=7.0, batt_discharge_kw=2.0)
    assert await brain.energy.house_guard(when(22, 6)) == "house_only"
    assert power_writes() == [1.2, 0.7, 2.2]


async def test_observe_mode_journals_the_verdict_and_touches_nothing(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, data={"schema": SCHEMA}, autopilot_mode="auto", observe_only=True)
    brain.energy.profile = [1.0] * 24
    hass.states.async_set(SOC, "40")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    assert await brain.energy.house_guard(when(22, 0)) == "observed"
    await hass.async_block_till_done()
    assert sent == [] and hass.states.get(MODE).state == ladder.DISCHARGE
    assert not brain.speaker.push_log  # nothing was done, so nothing is announced
    last = brain.journal.last
    assert last["rule"] == ladder.HOUSE_RULE and last["observe"] is True
    assert await brain.energy.ev_guard(when(22, 0)) is None


async def test_dispatch_remembers_who_started_it(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    assert await brain.energy.start_export(True, 5.0, 40, source=ladder.PLAN) == "started"
    assert brain.energy.dispatch_source == ladder.PLAN
    assert await brain.energy.stop() == "stopped" and brain.energy.dispatch_source is None
    decision = {"window": "export", "kw": 5.0, "floor_soc": 40, "time": "2026-11-10T17:00:45", "soc": 90, "source": "llm"}
    assert await brain.autopilot._act(decision) == "started" and brain.energy.dispatch_source == ladder.AUTOPILOT
    await brain.energy.stop()
    assert await brain.autopilot._act({**decision, "source": "plan"}) == "started" and brain.energy.dispatch_source == ladder.PLAN


async def test_autopilot_decisions_reach_the_journal(hass: HomeAssistant):
    _record(hass)
    brain = await _setup(hass, autopilot_mode="shadow", autopilot_use_ai=False)
    hass.states.async_set(SOC, "31")
    decision = await brain.autopilot.decide("export")
    last = brain.journal.last
    assert not decision["do"] and last["rule"] == ladder.AUTOPILOT and last["action"] == ladder.HOLD
    assert last["reason"].startswith("No evening export")


async def test_ev_first_exports_only_a_trickle_when_feed_in_is_low(hass: HomeAssistant):
    sent = _record(hass)
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(SOC, "90")
    hass.states.async_set(MODE, ladder.DISCHARGE)
    hass.states.async_set(POWER, "7")
    flows(hass, grid_kw=-1.0, ev_kw=7.2, batt_discharge_kw=9.0)  # load 8.0 kW: EV 7.2 + house 0.8
    assert brain.energy.supply_left() > 1  # supply charge not covered, but 3c feed-in is not worth chasing
    assert await brain.energy.ev_guard(when(23, 0)) == "trickle"
    assert ("number", "set_value", {"entity_id": POWER, "value": 8.2}) in sent  # 7.2 + 0.8 + 0.2, not + 7 kW export
    assert "feed-in is low" in brain.energy.ev_guard_note
```

Change the end of `tests/test_features.py::test_house_rule_guard`:

```python
    # EV done: the battery holds house-only through a short dip, then goes back to normal
    hass.states.async_set(LEGACY["studio_ev"], "0", {"unit_of_measurement": "kW"})
    assert await brain.energy.house_guard(now) == "house_only"
    later = now + timedelta(minutes=6)
    assert await brain.energy.house_guard(later) == "ended" and hass.states.get(mode).state == "Normal"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_guard.py tests/test_features.py::test_house_rule_guard -q -p no:cacheprovider`
Expected: failures such as `assert None == 'handed_back'`, `AttributeError: 'EnergyBrain' object has no attribute 'dispatch_source'`, `assert 'ended' == 'house_only'`

- [ ] **Step 3: Write the implementation**

`energy.py` imports: `from . import ladder, planner, safety, tariff`; add `CONF_ST_GRID` and `CONF_ST_BATT` to the const import. In `__init__`:

```python
        self.watch = safety.FreezeWatch()
        self.gate = safety.CommandGate()
        self.verdict: ladder.Verdict | None = None
        self.dispatch_source: str | None = None  # who started the running dispatch
        self._source_at: datetime | None = None
        self._house_only_at: datetime | None = None
```

New methods (replace the body of `house_guard`, keep `_watch_house`, `_tell_once`):

```python
    def stale_reason(self, now: datetime, forced: bool) -> str | None:
        """Why the readings can't be trusted right now, or None.

        The battery level may sit on one value for hours, so only its absence counts. The grid
        reading moves while a dispatch is forced, so there a stuck value counts too. A rounded
        grid reading can sit still under an export limit, though, while a frozen meter link
        freezes every reading: so when battery power is known, it must be stuck as well."""
        o = self.brain.opts
        mins = self.watch.after_s // 60
        if o.get(CONF_SOC):
            self.watch.update("soc", self._num(CONF_SOC), now)
            if self.watch.state("soc", now, may_hold=True):
                return f"battery level missing for {mins} min"
        if not (forced and o.get(CONF_ST_GRID)):
            self.watch.clear("grid")
            self.watch.clear("batt")
            return None
        self.watch.update("grid", self._num(CONF_ST_GRID), now)
        grid = self.watch.state("grid", now)
        if o.get(CONF_ST_BATT):
            self.watch.update("batt", self._num(CONF_ST_BATT), now)
            if grid == "stuck" and self.watch.state("batt", now) is None:
                return None
        return f"grid reading {grid} for {mins} min" if grid else None

    def ladder_inputs(self, now: datetime) -> tuple[ladder.Inputs, dict[str, Any]]:
        """Facts for the decision ladder, plus the numbers its actions need."""
        o, plan = self.brain.opts, self.plan()
        mode_id = o.get(CONF_MODE)
        state = self.hass.states.get(mode_id) if mode_id else None
        mode = state.state if state else None
        forced = mode in (ladder.CHARGE, ladder.DISCHARGE)
        if not forced and self._source_at and (now - self._source_at).total_seconds() > SOURCE_GRACE_S:
            self.dispatch_source = None  # the dispatch ended on its own
        soc = self._num(CONF_SOC)
        cap, res = float(o[CONF_BATTERY_KWH]), float(o[CONF_RESERVE])
        need = self.house_needs(now)["until_cheap"] or 0.0
        usable = None if soc is None else max(soc - res, 0.0) / 100 * cap
        live = self.brain.live_flows()
        held = (now - self._house_only_at).total_seconds() if self._house_only_at else float("inf")
        period, pays = tariff.period(now, plan, self.is_holiday(now.date())), tariff.export_pays(now, plan)
        before = now - timedelta(seconds=EDGE_S)
        edge = (period != tariff.period(before, plan, self.is_holiday(before.date()))
                or pays != tariff.export_pays(before, plan))
        inputs = ladder.Inputs(
            stale=self.stale_reason(now, forced or self.house_only),
            period=period,
            mode=mode, soc=soc, reserve=res, house_rule=bool(o.get(CONF_HOUSE_RULE)),
            spare_kwh=None if usable is None else usable - need,
            ev_kw=live["ev"], acting=self.brain.control_mode() in ("auto", "timers"),
            house_only=self.house_only, held_s=held,
            export_pays=pays, source=self.dispatch_source, edge=edge,
        )
        return inputs, {"plan": plan, "need": need, "res": res, "ev": live["ev"], "home": max(live["load"] - live["ev"], 0.0)}

    async def house_guard(self, now: datetime | None = None) -> str | None:
        """Run the decision ladder once and carry out its verdict (see ladder.py for the rules).

        Every verdict goes to the journal when it changes. Under Hermes AmpX only watches the
        house rule. In observe mode the verdict is logged and nothing is sent."""
        now = now or dt_util.now()
        if self.brain.hermes():
            return await self._watch_house(now)
        inputs, ctx = self.ladder_inputs(now)
        verdict = self.verdict = ladder.evaluate(inputs)
        observe = self.brain.observe()
        self.brain.journal.note(verdict, now, soc=inputs.soc, mode=inputs.mode, observe=observe and verdict.action in ladder.WRITES)
        self.house_note = None
        if observe:
            return "observed" if verdict.action in ladder.WRITES else None
        return await self._carry_out(verdict, ctx, now)

    async def _carry_out(self, v: ladder.Verdict, ctx: dict[str, Any], now: datetime) -> str | None:
        cheap = f"{ctx['plan'].shoulder_window[0]:02d}:00"
        if v.action == ladder.HAND_BACK:
            self.house_only, self._house_only_at, self.ev_guard_note = False, None, None
            await self.stop()
            await self._tell_once("stale", f"Battery handed back to the inverter: {v.reason}.")
            return "handed_back"
        if v.action == ladder.STOP_CHARGE:
            await self.stop(only_mode=ladder.CHARGE)
            await self._tell_once("peak_charge", "Grid charging stopped: it is peak rate.")
            return "charge_stopped"
        if v.action == ladder.HOUSE_ONLY:
            return await self._run_house_only(now, ctx)
        if v.action == ladder.RESUME:
            return await self._end_house_only()
        if v.action == ladder.STOP_DISCHARGE:
            await self.stop(only_mode=ladder.DISCHARGE)
            self.ev_guard_note = None
            if v.rule == ladder.EXPORT_CAP:
                await self._tell_once("export_cap", "Export stopped: feed-in is low now, so the battery only covers the house.")
                return "export_capped"
            if v.rule == ladder.RESERVE:
                await self._tell_once("reserve", f"Export stopped: battery at the {ctx['res']:.0f}% reserve.")
            else:
                await self._tell_once("export", f"Export stopped: the battery keeps {ctx['need']:.0f} kWh for the house until "
                                                f"{cheap}, so the house won't buy grid power.")
            return "export_stopped"
        if v.action == ladder.PAUSE_EV:
            self.house_note = f"Peak: the battery can't carry the EV ({ctx['ev']:.1f} kW) and the house until {cheap}. Pause the EV."
            await self._tell_once("peak_ev", self.house_note)
            return "pause_ev"
        return None

    async def _run_house_only(self, now: datetime, ctx: dict[str, Any]) -> str:
        """Battery at the house's load, so the grid feeds only the EV."""
        o = self.brain.opts
        home, ev = ctx["home"], ctx["ev"]
        want = round(min(float(o.get(CONF_BATT_MAX_KW) or 10.0), home + float(o.get(CONF_EV_TRICKLE_KW) or 0.0)), 1)
        if not self.house_only:
            await self._set("number", "set_value", CONF_DURATION, value=240)
            await self._set("number", "set_value", CONF_DISCHARGE_TARGET, value=ctx["res"])
            await self._set("number", "set_value", CONF_POWER, value=want)
            if not await self._set("select", "select_option", CONF_MODE, option=ladder.DISCHARGE):
                return "failed"
            self.house_only, self._house_only_at = True, now
            self.gate.sent(now, "house_only")
            self.brain.log("energy", f"house rule: battery covers the house ({want:.1f} kW), grid charges the EV")
        else:
            current = self._num(CONF_POWER)
            # raising keeps the house off the grid, so it never waits; lowering does
            if self.gate.allow(current, want, now, "house_only", urgent=current is None or want > current):
                if await self._set("number", "set_value", CONF_POWER, value=want):
                    self.gate.sent(now, "house_only")
        self.house_note = (f"House rule: the battery covers only the house ({home:.1f} kW); the EV ({ev:.1f} kW) "
                           f"charges from the off-peak grid so the battery keeps {ctx['need']:.0f} kWh for the house.")
        return "house_only"
```

with module constants `SOURCE_GRACE_S = 180` and `EDGE_S = 120`. `_end_house_only` also sets `self._house_only_at = None`.

`ev_guard`: return None first when `self.brain.hermes() or self.brain.observe()`. Replace from `covered = ...` to the end:

```python
        covered = self.supply_left() <= 0.004 or short
        pays = tariff.export_pays(now, self.plan())
        trickle = covered or not pays  # nothing worth exporting: just cover the EV and the house
        extra = float(o.get(CONF_EV_TRICKLE_KW) or 0.0) if trickle else float(o[CONF_EXPORT_KW])
        want = round(min(float(o.get(CONF_BATT_MAX_KW) or 10.0), ev + home + extra), 1)
        if covered and not short and self.earned.get("covered") != self.earned["day"]:
            (unchanged: announce "Supply charge covered")
        if short:
            (unchanged note)
        elif not covered:
            self.ev_guard_note = (
                f"EV first: battery {want:.1f} kW covers the EV ({ev:.1f} kW) and house, "
                f"exporting the rest until ${self.supply_left():.2f} supply is covered." if pays else
                f"EV first: feed-in is low now. Battery {want:.1f} kW covers the EV ({ev:.1f} kW) and house, "
                f"exporting about {extra * 1000:.0f} W.")
        else:
            (unchanged "supply charge covered" note)
        power = self._num(CONF_POWER)
        reason = "ev_first:trickle" if trickle else "ev_first:export"
        if self.gate.allow(power, want, now, reason, urgent=power is None or want > power):
            if await self._set("number", "set_value", CONF_POWER, value=want):
                self.gate.sent(now, reason)
            return "trickle" if trickle else "adjusted"
        return "ok"
```

`start_topup` and `start_export` take `source: str = ladder.MANUAL` and on `ok` set `self.dispatch_source, self._source_at = source, dt_util.now()`. `stop` clears `self.dispatch_source` and `self._source_at` when the mode write succeeded.

`runtime.py` timers: `start_topup(source=ladder.PLAN)`, `start_export(source=ladder.PLAN)`.

`autopilot.py` `_act`:

```python
        source = ladder.PLAN if d.get("source") == "plan" else ladder.AUTOPILOT
        if d["window"] == rules.TOPUP:
            result = await energy.start_topup(True, d["kw"], d["target_soc"], source=source)
        else:
            result = await energy.start_export(True, d["kw"], d["floor_soc"], source=source)
```

and in `decide`, after `text = rules.describe(decision)`:

```python
        rule = ladder.PLAN if decision.get("source") == "plan" else ladder.AUTOPILOT
        action = (ladder.TOPUP if window == rules.TOPUP else ladder.EXPORT) if decision["do"] else ladder.HOLD
        brain.journal.add(rule, action, text, soc=ctx.get("soc"), observe=decision["do"] and decision["result"] != "started")
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m pytest -q -p no:cacheprovider`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add -A tests custom_components
git commit -m "Drive battery guards from the decision ladder with write safety"
```

---

### Task 5: Sealion 7 review fixes (R2, R3, R4)

**Files:**
- Modify: `custom_components/ampx/sealion7.py` (`decide` order), `sealion7_feature.py` (`config(now)`, `blocked()`, status), `const.py` (`CONF_SL7_WINDOW`, `CONF_SL7_PEAK` default `""`), `websocket.py` (validators accept `""`)
- Test: `tests/test_sealion7.py`, `tests/test_sealion7_feature.py`

**Interfaces:**
- Consumes: `EnergyBrain.plan()`, `EnergyBrain.is_holiday`, `tariff.peak_day`, `AmpX.hermes()`, `AmpX.observe()`
- Produces: `sealion7.decide` order: unplugged, no reading, at target, peak pause, below minimum, cheap window, wait
- Produces: `Sealion7Feature.config(now) -> Config` (windows from the tariff unless overridden; no peak window on non-peak days), `Sealion7Feature.blocked() -> "hermes" | "observe" | None`
- Produces: status keys `window`, `peak` (the overrides, may be `""`), `window_now`, `peak_now` (in effect, e.g. `"10-14"`, `""` when today has no peak), `blocked`

- [ ] **Step 1: Write the failing tests**

In `tests/test_sealion7.py` add `Config, Window = _mod.Config, _mod.Window` and replace `test_min_soc_overrides_window` with:

```python
def test_below_minimum_charges_off_peak_but_never_in_peak():
    assert decide(car(soc=10), at(2)).action == ACTION_START
    d = decide(car(soc=10), at(15))
    assert d.action == ACTION_HOLD and "peak" in d.reason
    assert decide(car(soc=10, charging=True), at(15)).action == ACTION_STOP


def test_a_day_without_peak_has_no_peak_pause():
    weekend = Config(peak=())
    assert decide(car(), at(15), weekend).reason == "outside cheap window, waiting"
    assert decide(car(soc=10), at(15), weekend).action == ACTION_START
```

<!-- file: tests/test_sealion7_feature.py -->
```python
"""Sealion 7 feature: tariff-following windows, observe by default, engine and observe gates."""

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx.const import CONF_SL7_PEAK, CONF_SL7_WINDOW, DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY, SCHEMA
from custom_components.ampx.sealion7 import Window

SOC, PLUG, START = LEGACY["ev_soc"], LEGACY["ev_plug"], LEGACY["ev_start_button"]


async def _setup(hass: HomeAssistant, data: dict | None = None, **opts):
    async_mock_service(hass, "notify", "send_message")
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={} if data is None else data, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def when(day: int, hour: int) -> datetime:
    return datetime(2026, 11, day, hour, 0, tzinfo=dt_util.get_default_time_zone())  # Nov 10 is a Tuesday, Nov 14 a Saturday


def plugged_in(hass: HomeAssistant, soc: str = "50") -> None:
    hass.states.async_set(SOC, soc)
    hass.states.async_set(PLUG, "on")


async def test_windows_follow_the_tariff_and_its_peak_days(hass: HomeAssistant):
    assert DEFAULTS[CONF_SL7_WINDOW] == "" and DEFAULTS[CONF_SL7_PEAK] == ""
    brain = await _setup(hass, shoulder_start="11:00:00", shoulder_end="15:00:00", peak_start="15:00:00", peak_end="21:00:00")
    cfg = brain.sealion7.config(when(10, 16))
    assert cfg.allowed == (Window(11, 15),) and cfg.peak == (Window(15, 21),)
    assert brain.sealion7.config(when(14, 16)).peak == ()  # Saturday: no peak, so no peak pause
    status = brain.sealion7.status()
    assert status["window"] == "" and status["window_now"] == "11-15"


async def test_an_explicit_window_overrides_the_tariff(hass: HomeAssistant):
    brain = await _setup(hass, sl7_window="9-13", sl7_peak="13-22")
    cfg = brain.sealion7.config(when(10, 16))
    assert cfg.allowed == (Window(9, 13),) and cfg.peak == (Window(13, 22),)


async def test_observe_by_default_then_control_presses_start(hass: HomeAssistant):
    presses = async_mock_service(hass, "button", "press")
    brain = await _setup(hass)
    plugged_in(hass)
    await brain.sealion7._tick(when(10, 11))  # Tuesday 11:00, cheap window
    assert brain.sealion7.decision.action == "start" and not presses
    brain.opts["sl7_enabled"] = True
    await brain.sealion7._tick(when(10, 11))
    assert [c.data["entity_id"] for c in presses] == [START]
    assert brain.sealion7.last_action["action"] == "start"


async def test_peak_pauses_the_car_even_below_minimum(hass: HomeAssistant):
    presses = async_mock_service(hass, "button", "press")
    brain = await _setup(hass, sl7_enabled=True)
    plugged_in(hass, soc="10")
    await brain.sealion7._tick(when(10, 17))  # Tuesday 17:00, peak
    assert brain.sealion7.decision.action == "hold" and "peak" in brain.sealion7.decision.reason and not presses
    await brain.sealion7._tick(when(14, 17))  # Saturday 17:00, off-peak: below minimum charges now
    assert brain.sealion7.decision.action == "start" and len(presses) == 1


async def test_hermes_or_observe_mode_blocks_the_car_buttons(hass: HomeAssistant):
    presses = async_mock_service(hass, "button", "press")
    brain = await _setup(hass, sl7_enabled=True, decision_engine="hermes")
    plugged_in(hass)
    await brain.sealion7._tick(when(10, 11))
    assert not presses and brain.sealion7.status()["blocked"] == "hermes"
    brain.opts["decision_engine"] = "ampx"
    brain.opts["observe_only"] = True
    await brain.sealion7._tick(when(10, 11))
    assert not presses and brain.sealion7.status()["blocked"] == "observe"
    brain.opts["observe_only"] = False
    await brain.sealion7._tick(when(10, 11))
    assert len(presses) == 1 and brain.sealion7.status()["blocked"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_sealion7.py tests/test_sealion7_feature.py -q -p no:cacheprovider`
Expected: `assert 'start' == 'hold'` (peak), `assert '10-14' == ''` (defaults), `TypeError: config() takes 1 positional argument`

- [ ] **Step 3: Write the implementation**

`sealion7.py` `decide`, after the no-reading check:

```python
    if car.soc >= cfg.target_soc:
        act = ACTION_STOP if car.charging else ACTION_HOLD
        return Decision(act, cfg.target_soc, f"at target {cfg.target_soc:.0f}%", warnings)

    if in_peak(now, cfg):  # hard rule: never from the grid in peak, even below minimum (the car has fuel)
        act = ACTION_STOP if car.charging else ACTION_HOLD
        return Decision(act, cfg.target_soc, "peak rate, grid charging paused", warnings)

    if car.soc < cfg.min_soc:
        act = ACTION_START if not car.charging else ACTION_HOLD
        return Decision(act, cfg.target_soc, f"below minimum {cfg.min_soc:.0f}%, charge now", warnings)
```

Update the module docstring's rule list to that order. `const.py`: both window defaults become `""`. `websocket.py`: `vol.Any("", vol.Match(...))` for both.

`sealion7_feature.py`:

```python
    def config(self, now: datetime | None = None) -> Config:
        """Charging limits. Windows follow the tariff unless set here; a day without peak has no peak window."""
        now = now or dt_util.now()
        o, energy = self.opts, self.brain.energy
        plan = energy.plan()
        (unchanged target, minimum, kwh parsing)
        peak = parse_window(o.get(CONF_SL7_PEAK), Window(*plan.peak_window))
        peak_today = tariff.peak_day(now.date(), plan, energy.is_holiday(now.date()))
        return Config(
            target_soc=target, min_soc=minimum,
            allowed=(parse_window(o.get(CONF_SL7_WINDOW), Window(*plan.shoulder_window)),),
            peak=(peak,) if peak_today else (), kwh=kwh,
        )

    def blocked(self) -> str | None:
        """Why AmpX may not press the car's buttons even in control mode."""
        if self.brain.hermes():
            return "hermes"
        return "observe" if self.brain.observe() else None
```

`_tick`: `cfg = self.config(now)`; act only when `self.enabled() and not self.blocked()`. `status()`: `cfg = self.config()`; `"window": o.get(CONF_SL7_WINDOW) or ""`, `"peak": o.get(CONF_SL7_PEAK) or ""`, `"window_now": f"{a.start}-{a.end}"`, `"peak_now"` likewise or `""`, `"blocked": self.blocked()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_sealion7.py tests/test_sealion7_feature.py -q -p no:cacheprovider`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add -A tests custom_components
git commit -m "Sealion 7: never charge in peak, follow the tariff, respect engine and observe mode"
```

---

### Task 6: Websocket, decision sensor, panel (R1)

**Files:**
- Modify: `websocket.py` (overview `control.decision_engine`, `control.observe`, `journal`; `CONTROL_OPTIONS[CONF_OBSERVE] = bool`), `sensor.py` (`decision` sensor), `strings.json`, `translations/en.json`, `frontend/ampx-studio.js` (observe toggle, journal card, Sealion 7 placeholders and blocked note), `__init__.py` (`FRONTEND_VERSION`), `manifest.json` (version `0.24.0`)
- Test: `tests/test_panel_api.py`; browser render check with Playwright against a real overview payload

**Interfaces:**
- Consumes: `Journal.items`, `Journal.last`, `AmpX.observe`, `AmpX.engine`, `ladder.RULES`
- Produces: overview `journal` (30 newest entries), `control.observe`, `control.decision_engine`
- Produces: `sensor.ampx_decision` with the rule as state and `action`, `reason`, `time`, `observe`, `recent` attributes

- [ ] **Step 1: Write the failing test**

<!-- file: tests/test_panel_api.py -->
```python
"""What the panel reads and may change: engine, observe mode, journal, Sealion 7 windows, decision sensor."""

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx import ladder
from custom_components.ampx.const import DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY


async def _setup(hass: HomeAssistant, **opts):
    async_mock_service(hass, "notify", "send_message")
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press")):
        async_mock_service(hass, domain, svc)
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={}, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


async def test_overview_carries_engine_observe_and_journal(hass: HomeAssistant, hass_ws_client):
    brain = await _setup(hass, decision_engine="hermes")
    brain.journal.add(ladder.HOUSE_RULE, ladder.STOP_DISCHARGE, "the house needs it")
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/overview"})
    result = (await ws.receive_json())["result"]
    assert result["control"]["decision_engine"] == "hermes" and result["control"]["observe"] is False
    assert result["journal"][0]["rule"] == ladder.HOUSE_RULE and result["journal"][0]["reason"] == "the house needs it"


async def test_panel_may_switch_observe_mode_and_clear_sealion_windows(hass: HomeAssistant, hass_ws_client):
    await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/set_options", "options": {"observe_only": "yes"}})
    assert not (await ws.receive_json())["success"]
    await ws.send_json({"id": 2, "type": "ampx/set_options", "options": {"sl7_window": "ten to two"}})
    assert not (await ws.receive_json())["success"]
    await ws.send_json({"id": 3, "type": "ampx/set_options", "options": {"observe_only": True, "sl7_window": "", "sl7_peak": "14-21"}})
    assert (await ws.receive_json())["success"]
    await hass.async_block_till_done()
    options = hass.config_entries.async_entries(DOMAIN)[0].options
    assert options["observe_only"] is True and options["sl7_window"] == "" and options["sl7_peak"] == "14-21"


async def test_decision_sensor_shows_the_rule_and_reason(hass: HomeAssistant):
    brain = await _setup(hass, autopilot_mode="auto")
    hass.states.async_set(LEGACY["battery_soc"], "21")
    hass.states.async_set(LEGACY["dispatch_mode"], ladder.DISCHARGE)
    now = datetime(2026, 11, 10, 18, 0, tzinfo=dt_util.get_default_time_zone())
    assert await brain.energy.house_guard(now) == "export_stopped"
    await hass.async_block_till_done()
    state = hass.states.get("sensor.ampx_decision")
    assert state.state == ladder.RESERVE
    assert state.attributes["action"] == ladder.STOP_DISCHARGE and "reserve" in state.attributes["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_panel_api.py -q -p no:cacheprovider`
Expected: `KeyError: 'decision_engine'`, `observe_only cannot be changed here`, `AttributeError: 'NoneType' object has no attribute 'state'`

- [ ] **Step 3: Write the implementation**

`websocket.py` overview:

```python
            "journal": list(brain.journal.items)[:30],
```

and in `control`:

```python
                "decision_engine": brain.engine(),
                "observe": brain.observe(),
```

`CONTROL_OPTIONS`: `CONF_OBSERVE: bool,`.

`sensor.py`, before `last_event`:

```python
    AmpXSensorDescription(
        key="decision", translation_key="decision", icon="mdi:source-branch",
        device_class=SensorDeviceClass.ENUM, options=list(ladder.RULES),
        value=lambda b: (b.journal.last or {}).get("rule"),
        attrs=lambda b: {**{k: (b.journal.last or {}).get(k) for k in ("action", "reason", "time", "observe")},
                         "recent": list(b.journal.items)[:10]},
    ),
```

`strings.json` and `translations/en.json`, `entity.sensor`: `"decision": {"name": "Decision"}`.

`ampx-studio.js`:
- `_ctlCards`: an "Observe only" row above "Decision engine" (`data-optobs`, saves `{observe_only: checked}`), with a note while it is on.
- `_journalCard()`: newest 12 entries as rows (rule label, reason, time; "would" tag when `observe`), rendered after the control card in the battery view.
- Sealion 7 control card: window and peak inputs show the override as value and `tariff: 10-14` as placeholder; a note when `blocked`.

Bump `FRONTEND_VERSION` and `manifest.json` version to `0.24.0`.

- [ ] **Step 4: Run tests, then render the panel**

Run: `python3 -m pytest -q -p no:cacheprovider`
Expected: all pass

Render check: dump a real `ampx/overview` payload from a test run, load `ampx-studio.js` in headless Chromium with a stub `hass`, open Devices → Battery and Devices → Sealion 7, assert no page errors and that the journal card, the observe toggle and the Sealion 7 card are in the DOM. Screenshot both.

- [ ] **Step 5: Commit**

```bash
git add -A tests custom_components
git commit -m "Panel and sensor: decision journal, observe toggle, engine shown"
```

---

### Task 7: Docs and final verification

**Files:**
- Create: `docs/REQUIREMENTS.md`
- Modify: `docs/BACKLOG.md`, `README.md` (house rule row, observe mode, journal)

- [ ] **Step 1:** Write `docs/REQUIREMENTS.md` from the owner's requirements, with every *(planned)* item marked built and the review findings listed.
- [ ] **Step 2:** Backlog: add `replan-after-stale` (re-decide the running window when readings return) and `deploy-0.24` (owner copies the integration to Home Assistant, maps Sealion 7 sensors, adds the AI provider).
- [ ] **Step 3:** Run `python3 -m pytest -q -p no:cacheprovider` and `node --input-type=module --check < custom_components/ampx/frontend/ampx-studio.js`. Expected: all pass, no syntax error.
- [ ] **Step 4:** Commit and push `feat/write-safety-journal`. Do not merge.

## Self-Review

- Spec coverage: §5 rule 1 (Task 4, R8), rule 2 (Task 4, R7), rule 3 and 4 (Task 2, 4), rules 5 to 7 (Task 2, 4 source tracking), rule name and reason logged (Task 3, 6). Write safety: dwell and deadband (Task 1, 4), discharge capped to house need (Task 2 `export_cap`, Task 4 EV-first trickle), observe default for new installs (Task 3). §3 "never in peak" for the EV (Task 5). §4 no hard-coded home values (Task 5 defaults). §9 panel (Task 6). §12 tariff peak question answered in R9.
- Not in this plan: deploying to the owner's Home Assistant, the AI provider key, dispatch power confirmation, the old AGL automations. They need the owner.
- Names checked across tasks: `ladder.WRITES`, `ladder.HOLD`, `Journal.note/add`, `EnergyBrain.dispatch_source`, `house_guard` result strings, `Sealion7Feature.config(now)`.
