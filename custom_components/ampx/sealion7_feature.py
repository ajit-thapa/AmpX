"""BYD Sealion 7 feature: reads the car and charger, runs sealion7.decide, optionally starts or stops charging.

Observe mode (the default) only computes and shows decisions. Control mode also presses the
start/stop entities. Logic lives in sealion7.py; this file only does Home Assistant I/O.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EV_PLUG,
    CONF_EV_SOC,
    CONF_EV_START,
    CONF_SL7_CHARGING,
    CONF_SL7_CURRENT,
    CONF_SL7_ENABLED,
    CONF_SL7_FUEL,
    CONF_SL7_KWH,
    CONF_SL7_MIN,
    CONF_SL7_PEAK,
    CONF_SL7_POWER,
    CONF_SL7_PURE_RANGE,
    CONF_SL7_SCHEDULE,
    CONF_SL7_STOP,
    CONF_SL7_TARGET,
    CONF_SL7_TOTAL_RANGE,
    CONF_SL7_VOLTAGE,
    CONF_SL7_WINDOW,
)
from .feature import Feature
from .sealion7 import (
    ACTION_START,
    ACTION_STOP,
    CarState,
    Config,
    Decision,
    SlowChargeWatch,
    Window,
    decide,
    energy_needed_kwh,
    time_to_target_min,
)

# Entity settings the panel edits, in the order it shows them.
ENTITY_KEYS = (
    CONF_EV_SOC, CONF_EV_PLUG, CONF_SL7_POWER, CONF_SL7_VOLTAGE, CONF_SL7_CURRENT, CONF_SL7_CHARGING,
    CONF_SL7_PURE_RANGE, CONF_SL7_TOTAL_RANGE, CONF_SL7_FUEL, CONF_SL7_SCHEDULE, CONF_EV_START, CONF_SL7_STOP,
)
COOLDOWN = timedelta(minutes=5)  # after a start/stop, leave the car alone this long
ON_STATES = {"on", "home", "true", "connected", "charging"}
RANGE = re.compile(r"^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$")


def parse_window(text: str, default: Window) -> Window:
    """"10-14" -> Window(10, 14). Anything else falls back to the default."""
    m = RANGE.match(str(text or ""))
    if not m:
        return default
    a, b = int(m.group(1)), int(m.group(2))
    if not (0 <= a <= 24 and 0 <= b <= 24):
        return default
    return Window(a % 24, b % 24)


class Sealion7Feature(Feature):
    name = "sealion7"

    def __init__(self, brain) -> None:
        super().__init__(brain)
        self.watch = SlowChargeWatch()
        self.decision: Decision | None = None
        self.car: CarState | None = None
        self.slow_alert: str | None = None
        self.last_action: dict[str, Any] | None = None
        self._cool_until: datetime | None = None

    # persistence -----------------------------------------------------------
    def load(self, data) -> None:
        data = data or {}
        self.last_action = data.get("last_action")

    def dump(self) -> dict[str, Any]:
        return {"last_action": self.last_action}

    # lifecycle -------------------------------------------------------------
    async def start(self) -> None:
        self._unsubs.append(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=60))
        )

    # config and reads ------------------------------------------------------
    @property
    def opts(self) -> dict[str, Any]:
        return self.brain.opts

    def enabled(self) -> bool:
        return bool(self.opts.get(CONF_SL7_ENABLED))

    def config(self) -> Config:
        o = self.opts
        try:
            target = float(o.get(CONF_SL7_TARGET) or 80)
            minimum = float(o.get(CONF_SL7_MIN) or 20)
            kwh = float(o.get(CONF_SL7_KWH) or 40)
        except (TypeError, ValueError):
            target, minimum, kwh = 80.0, 20.0, 40.0
        return Config(
            target_soc=target,
            min_soc=minimum,
            allowed=(parse_window(o.get(CONF_SL7_WINDOW), Window(10, 14)),),
            peak=(parse_window(o.get(CONF_SL7_PEAK), Window(14, 21)),),
            kwh=kwh,
        )

    def _st(self, entity: str | None):
        if not entity:
            return None
        return self.hass.states.get(entity)

    def _num(self, entity: str | None) -> float | None:
        st = self._st(entity)
        if st is None:
            return None
        try:
            return float(st.state)
        except (TypeError, ValueError):
            return None

    def _kw(self, entity: str | None) -> float | None:
        st = self._st(entity)
        value = self._num(entity)
        if value is None:
            return None
        unit = str(st.attributes.get("unit_of_measurement") or "").lower()
        return value / 1000 if unit == "w" else value

    def _on(self, entity: str | None) -> bool:
        st = self._st(entity)
        return bool(st) and st.state.lower() in ON_STATES

    def read_car(self) -> CarState:
        o = self.opts
        power = self._kw(o.get(CONF_SL7_POWER))
        charging = self._on(o.get(CONF_SL7_CHARGING)) if o.get(CONF_SL7_CHARGING) else bool(power and power > 0.1)
        return CarState(
            soc=self._num(o.get(CONF_EV_SOC)),
            plugged=self._on(o.get(CONF_EV_PLUG)),
            charging=charging,
            power_kw=power,
            voltage=self._num(o.get(CONF_SL7_VOLTAGE)),
            current_a=self._num(o.get(CONF_SL7_CURRENT)),
            pure_range_km=self._num(o.get(CONF_SL7_PURE_RANGE)),
            total_range_km=self._num(o.get(CONF_SL7_TOTAL_RANGE)),
            fuel_pct=self._num(o.get(CONF_SL7_FUEL)),
            car_schedule_on=self._on(o.get(CONF_SL7_SCHEDULE)),
        )

    def missing(self) -> list[str]:
        """Names of the core entities still unset."""
        o = self.opts
        need = {"battery level": CONF_EV_SOC, "plug": CONF_EV_PLUG, "charging power": CONF_SL7_POWER,
                "start": CONF_EV_START, "stop": CONF_SL7_STOP}
        return [label for label, key in need.items() if not o.get(key)]

    # tick ------------------------------------------------------------------
    async def _tick(self, now: datetime) -> None:
        now = dt_util.as_local(now)
        if not self.opts.get(CONF_EV_SOC):
            self.decision, self.car = None, None
            return
        car, cfg = self.read_car(), self.config()
        self.car = car
        self.decision = decide(car, now, cfg)
        self.slow_alert = self.watch.update(car, now, cfg)
        if self.slow_alert:
            self.brain.log("ev", self.slow_alert)

        action = self.decision.action
        if action not in (ACTION_START, ACTION_STOP) or not self.enabled():
            return
        if self._cool_until and now < self._cool_until:
            return
        result = await self._apply(action)
        if result is None:
            return
        self._cool_until = now + COOLDOWN
        self.last_action = {"action": action, "at": now.isoformat(), "reason": self.decision.reason, "result": result}
        self.brain.log("ev", f"Sealion 7 {action}: {self.decision.reason}")
        self.brain.save()

    async def _apply(self, action: str) -> str | None:
        entity = self.opts.get(CONF_EV_START) if action == ACTION_START else self.opts.get(CONF_SL7_STOP)
        if not entity:
            return None
        domain = entity.split(".")[0]
        if domain == "switch":
            service = "turn_on" if action == ACTION_START else "turn_off"
        else:
            service = "press"
            domain = "button"
        try:
            await self.hass.services.async_call(domain, service, {"entity_id": entity}, blocking=True)
        except HomeAssistantError as err:
            return f"failed: {err}"
        return "sent"

    # panel -----------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        cfg = self.config()
        car = self.car
        d = self.decision
        soc = car.soc if car else None
        return {
            "configured": bool(self.opts.get(CONF_EV_SOC)),
            "missing": self.missing(),
            "enabled": self.enabled(),
            "target": cfg.target_soc,
            "min_soc": cfg.min_soc,
            "kwh": cfg.kwh,
            "window": self.opts.get(CONF_SL7_WINDOW),
            "peak": self.opts.get(CONF_SL7_PEAK),
            "soc": soc,
            "plugged": car.plugged if car else False,
            "charging": car.charging if car else False,
            "power_kw": car.power_kw if car else None,
            "voltage": car.voltage if car else None,
            "current_a": car.current_a if car else None,
            "pure_range_km": car.pure_range_km if car else None,
            "total_range_km": car.total_range_km if car else None,
            "fuel_pct": car.fuel_pct if car else None,
            "needed_kwh": energy_needed_kwh(soc, cfg),
            "minutes_to_target": time_to_target_min(soc, cfg),
            "action": d.action if d else None,
            "reason": d.reason if d else "waiting for data",
            "warnings": d.warnings if d else [],
            "slow_alert": self.slow_alert,
            "last_action": self.last_action,
            "entities": {key: self.opts.get(key) or "" for key in ENTITY_KEYS},
            "updated": dt_util.now().isoformat(),
        }
