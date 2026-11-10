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
