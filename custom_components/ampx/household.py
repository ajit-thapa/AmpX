"""Around the house: bin day, leak / smoke / CO alarms, appliances finishing, big loads.

Every part finds its own entities, so it stays empty (and silent) in a house that
does not have them:

- bins: Waste Collection Schedule sensors (they carry a ``daysTo`` attribute);
  a reminder the evening before, in the briefing and on the phone.
- safety: binary sensors of class moisture, smoke, carbon_monoxide, gas or safety;
  an alarm is a house health issue at once (which also pushes it).
- appliances: washer, dryer and dishwasher status entities (text or on/off, never
  a number); going from running to done is an event and a push, with a hint when
  there is solar to spare for the next load.
- loads: power sensors that are not part of the solar, battery, grid or EV system,
  biggest first.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, time, timedelta
import re
from typing import Any

from homeassistant.core import Event
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change, async_track_time_interval
from homeassistant.util import dt as dt_util

from .feature import Feature

BIN_REMIND = time(18, 30)
SAFETY = {"moisture": "leak", "smoke": "smoke", "carbon_monoxide": "carbon monoxide", "gas": "gas", "safety": "safety"}
APPLIANCES = (("dishwasher", "Dishwasher"), ("dryer", "Dryer"), ("washer", "Washer"), ("washing_machine", "Washer"))
RUNNING = {"on", "run", "running", "wash", "washing", "main_wash", "rinse", "rinsing", "spin", "spinning", "dry", "drying",
           "in_use", "active", "cycle", "heating", "cooling", "drain", "draining", "delay_start_running"}
DONE = {"off", "idle", "finished", "finish", "complete", "completed", "end", "done", "ready", "standby", "stopped"}
# Power sensors that belong to the energy system itself, not to an appliance.
SYSTEM = re.compile(r"pv|solar|grid|batter|inverter|house|home_|load|consum|neovolt|ness_|sungrow|solcast|amber|meter|"
                    r"feed|export|import|phase|total|forecast|wall_connector|charger|byd|sealion|ev_|_ev|ampx|emhass|globird", re.I)
EVENT_HOURS = 6


def _name(state) -> str:
    return str(state.attributes.get("friendly_name") or state.entity_id.split(".", 1)[1].replace("_", " ").title())


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


class Household(Feature):
    name = "household"

    def __init__(self, brain) -> None:
        super().__init__(brain)
        self.events: deque[dict[str, Any]] = deque(maxlen=20)
        self._watched: tuple[str, ...] = ()
        self._watch_unsub = None

    # ---- discovery -------------------------------------------------------
    def bins(self) -> list[dict[str, Any]]:
        out = []
        for s in self.hass.states.async_all("sensor"):
            days = s.attributes.get("daysTo")
            if isinstance(days, (int, float)) and days >= 0:
                out.append({"entity_id": s.entity_id, "name": _name(s), "days": int(days), "state": s.state})
        return sorted(out, key=lambda b: (b["days"], b["name"]))

    def bins_tomorrow(self) -> str | None:
        names = [b["name"] for b in self.bins() if b["days"] == 1]
        return f"Bins out tonight: {_and(names)}." if names else None

    def safety(self) -> list[dict[str, Any]]:
        return sorted(
            ({"entity_id": s.entity_id, "name": _name(s), "kind": SAFETY[s.attributes.get("device_class")], "on": s.state == "on"}
             for s in self.hass.states.async_all("binary_sensor") if s.attributes.get("device_class") in SAFETY),
            key=lambda x: (not x["on"], x["name"]),
        )

    def issues(self) -> list[str]:
        return [f"{x['name']}: {x['kind']} alarm" for x in self.safety() if x["on"]]

    def appliances(self) -> list[dict[str, Any]]:
        out, taken = [], set()
        for s in self.hass.states.async_all(("sensor", "binary_sensor", "select")):
            ident = s.entity_id.lower()
            label = next((lab for key, lab in APPLIANCES if key in ident), None)
            if not label or _number(s.state) is not None or s.attributes.get("device_class") in ("power", "energy", "timestamp", "duration"):
                continue
            if label in taken:
                continue
            taken.add(label)
            st = s.state.lower().replace(" ", "_")
            out.append({"entity_id": s.entity_id, "name": label, "state": s.state,
                        "running": st in RUNNING})
        return sorted(out, key=lambda a: a["name"])

    def loads(self, limit: int = 8) -> list[dict[str, Any]]:
        mine = {self.brain.opts.get(k) for k in ("studio_pv", "studio_grid", "studio_battery", "studio_ev", "studio_load")}
        out = []
        for s in self.hass.states.async_all("sensor"):
            if s.attributes.get("device_class") != "power" or s.entity_id in mine or SYSTEM.search(s.entity_id):
                continue
            v, unit = _number(s.state), str(s.attributes.get("unit_of_measurement") or "")
            if v is None or unit not in ("W", "kW"):
                continue
            kw = v / 1000 if unit == "W" else v
            name = re.sub(r"\s*power$", "", _name(s), flags=re.I) or _name(s)
            out.append({"entity_id": s.entity_id, "name": name, "kw": round(kw, 3)})
        return sorted(out, key=lambda x: -x["kw"])[:limit]

    def status(self) -> dict[str, Any]:
        cut = dt_util.now() - timedelta(hours=EVENT_HOURS)
        return {
            "bins": self.bins(),
            "bins_tomorrow": self.bins_tomorrow(),
            "safety": self.safety(),
            "appliances": self.appliances(),
            "events": [e for e in self.events if dt_util.parse_datetime(e["time"]) >= cut],
            "loads": self.loads(),
        }

    # ---- listeners -------------------------------------------------------
    async def start(self) -> None:
        self._rewatch()
        self._unsubs.append(async_track_time_change(self.hass, self._bin_time, hour=BIN_REMIND.hour, minute=BIN_REMIND.minute, second=0))
        self._unsubs.append(async_track_time_interval(self.hass, lambda _n: self._rewatch(), timedelta(minutes=30)))

    def stop(self) -> None:
        super().stop()
        if self._watch_unsub:
            self._watch_unsub()
            self._watch_unsub = None
        self._watched = ()

    def _rewatch(self) -> None:
        ids = tuple(sorted({x["entity_id"] for x in self.safety()} | {a["entity_id"] for a in self.appliances()}))
        if ids == self._watched:
            return
        if self._watch_unsub:
            self._watch_unsub()
        self._watched = ids
        self._watch_unsub = async_track_state_change_event(self.hass, list(ids), self._changed) if ids else None

    async def _bin_time(self, _now: datetime) -> None:
        await self.remind_bins()

    async def remind_bins(self) -> bool:
        text = self.bins_tomorrow()
        return bool(text) and await self.brain.speaker.push(text, title="Bin day")

    async def _changed(self, event: Event) -> None:
        new, old = event.data.get("new_state"), event.data.get("old_state")
        if new is None or old is None:
            return
        if new.attributes.get("device_class") in SAFETY:
            if new.state != old.state:
                await self.brain.run_health()  # an alarm is a health issue, and health pushes it
            return
        was, now_ = old.state.lower().replace(" ", "_"), new.state.lower().replace(" ", "_")
        if was in RUNNING and now_ in DONE:
            label = next((lab for key, lab in APPLIANCES if key in new.entity_id.lower()), "Appliance")
            await self._finished(label)

    async def _finished(self, label: str) -> None:
        text = f"{label} finished"
        self.events.appendleft({"time": dt_util.now().isoformat(timespec="seconds"), "kind": "appliance", "text": text})
        hint = ""
        fl = self.brain.live_flows()
        spare = fl["pv"] - fl["load"]
        if label == "Washer" and spare is not None and spare >= 1.5:
            hint = f" {spare:.1f} kW of solar to spare: a good time for the dryer."
        await self.brain.speaker.push(text + "." + hint, title="Appliance")
        self.brain.notify_update()
