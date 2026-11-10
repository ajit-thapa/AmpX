"""BYD Sealion 7 (DM-i plug-in hybrid) charging system. Pure Python, no Home Assistant imports.

Standalone from the home battery brain. Reads a snapshot of car + charger values and returns
a decision. The caller applies it (start/stop charging) and publishes the telemetry.

Rules, in priority order (first match wins):
  1. car unplugged                       -> none
  2. battery at or above target          -> stop (if charging)
  3. outside allowed grid windows        -> hold (wait, never charge in peak)
  4. charge needed inside window         -> start (if not charging)
  5. otherwise                           -> hold
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

ACTION_START = "start"
ACTION_STOP = "stop"
ACTION_HOLD = "hold"
ACTION_NONE = "none"

# Sealion 7 DM-i: usable battery ~ 40 kWh (LFP). Pure EV range roughly 6.5 km per % at full pack.
BATTERY_KWH = 40.0
# Single-phase wall connector set to 32 A at ~235 V gives ~7.2 kW ceiling; observed 6.6 kW / 30.2 A.
MAX_CHARGE_KW = 7.2
SLOW_RATIO = 0.8          # below 80% of expected power counts as slow
SLOW_MINUTES = 5          # sustained for this long before we report it


@dataclass(frozen=True)
class Window:
    start: int  # hour, inclusive
    end: int    # hour, exclusive; start > end wraps midnight

    def contains(self, hour: int) -> bool:
        if self.start <= self.end:
            return self.start <= hour < self.end
        return hour >= self.start or hour < self.end


@dataclass(frozen=True)
class Config:
    target_soc: float = 80.0
    min_soc: float = 20.0                      # below this, charge regardless of window (car safety)
    allowed: tuple[Window, ...] = (Window(10, 14),)   # grid-charge windows (AGL shoulder)
    peak: tuple[Window, ...] = (Window(14, 21),)      # never charge from grid here
    kwh: float = BATTERY_KWH
    max_kw: float = MAX_CHARGE_KW


@dataclass(frozen=True)
class CarState:
    soc: float | None
    plugged: bool
    charging: bool
    power_kw: float | None = None
    voltage: float | None = None
    current_a: float | None = None
    pure_range_km: float | None = None
    total_range_km: float | None = None
    fuel_pct: float | None = None
    car_schedule_on: bool = False             # car's own scheduled charging; conflicts with AmpX


@dataclass
class Decision:
    action: str
    target_soc: float
    reason: str
    warnings: list[str] = field(default_factory=list)


def in_peak(now: datetime, cfg: Config) -> bool:
    return any(w.contains(now.hour) for w in cfg.peak)


def in_allowed(now: datetime, cfg: Config) -> bool:
    return any(w.contains(now.hour) for w in cfg.allowed) and not in_peak(now, cfg)


def decide(car: CarState, now: datetime, cfg: Config = Config()) -> Decision:
    warnings: list[str] = []
    if car.car_schedule_on:
        warnings.append("Car's own scheduled charging is on. Turn it off or it fights AmpX.")

    if not car.plugged:
        return Decision(ACTION_NONE, cfg.target_soc, "unplugged", warnings)
    if car.soc is None:
        return Decision(ACTION_HOLD, cfg.target_soc, "no SOC reading, not touching charger", warnings)

    if car.soc < cfg.min_soc:
        act = ACTION_START if not car.charging else ACTION_HOLD
        return Decision(act, cfg.target_soc, f"below minimum {cfg.min_soc:.0f}%, charge now", warnings)

    if car.soc >= cfg.target_soc:
        act = ACTION_STOP if car.charging else ACTION_HOLD
        return Decision(act, cfg.target_soc, f"at target {cfg.target_soc:.0f}%", warnings)

    if in_peak(now, cfg):
        act = ACTION_STOP if car.charging else ACTION_HOLD
        return Decision(act, cfg.target_soc, "peak rate, grid charging paused", warnings)

    if in_allowed(now, cfg):
        act = ACTION_HOLD if car.charging else ACTION_START
        return Decision(act, cfg.target_soc, "cheap window, charging to target", warnings)

    act = ACTION_HOLD
    return Decision(act, cfg.target_soc, "outside cheap window, waiting", warnings)


def energy_needed_kwh(soc: float | None, cfg: Config = Config()) -> float | None:
    if soc is None:
        return None
    return round(max(cfg.target_soc - soc, 0.0) / 100.0 * cfg.kwh, 2)


def time_to_target_min(soc: float | None, cfg: Config = Config()) -> int | None:
    need = energy_needed_kwh(soc, cfg)
    if need is None:
        return None
    return round(need / cfg.max_kw * 60)


class SlowChargeWatch:
    """Reports when charging runs well below what the charger can give, for SLOW_MINUTES in a row."""

    def __init__(self) -> None:
        self._since: datetime | None = None

    def update(self, car: CarState, now: datetime, cfg: Config = Config()) -> str | None:
        if not (car.charging and car.power_kw is not None):
            self._since = None
            return None
        expected = min(cfg.max_kw, (car.voltage or 235.0) * (car.current_a or 32.0) / 1000.0)
        at_target = car.soc is not None and car.soc >= cfg.target_soc
        if car.power_kw >= SLOW_RATIO * expected or at_target:
            self._since = None
            return None
        if self._since is None:
            self._since = now
            return None
        if (now - self._since).total_seconds() < SLOW_MINUTES * 60:
            return None
        return (
            f"Charging {car.power_kw:.1f} kW, expected about {expected:.1f} kW. "
            "Check charger current limit, car charge limit, cable and battery temperature."
        )
