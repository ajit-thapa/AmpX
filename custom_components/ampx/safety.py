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
