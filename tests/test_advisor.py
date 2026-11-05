"""Rule-based energy tips (pure)."""

from datetime import datetime, timedelta

from custom_components.cortex.advisor import tips

NOW = datetime(2026, 11, 3, 15, 0)


def snap(**kw):
    base = {"period": "off_peak", "import_rate": 32.12, "feed_in_rate": 3.0, "next_period": "peak",
            "next_change": NOW + timedelta(minutes=60), "battery_soc": 80.0, "battery_usable": 30.0,
            "ev_plugged": False, "ev_room": 0.0, "pv_shortfall": None, "pv_tomorrow": 40.0, "low_solar": 30.0}
    return {**base, **kw}


def test_peak_coming_while_ev_charges():
    out = tips(snap(), {"ev": 7.2, "grid": 7.6}, NOW)
    assert out[0]["level"] == "act" and "Peak starts at 16:00" in out[0]["text"]


def test_shoulder_ev_and_topup_when_manual():
    s = snap(period="shoulder", import_rate=11.11, next_period="off_peak", next_change=NOW.replace(hour=14),
             ev_plugged=True, ev_room=30.0, battery_soc=50.0, pv_shortfall=12.0)
    texts = " ".join(t["text"] for t in tips(s, {}, NOW.replace(hour=11), mode="off"))
    assert "start charging" in texts and "Top up the battery" in texts
    texts = " ".join(t["text"] for t in tips(s, {}, NOW.replace(hour=11), mode="auto"))
    assert "Top up" not in texts  # Autopilot handles it


def test_warn_on_peak_import_ranks_first_and_fallback():
    out = tips(snap(period="peak", import_rate=41.91, next_period="off_peak"), {"grid": 2.0}, NOW.replace(hour=17))
    assert out[0]["level"] == "warn" and "peak rate" in out[0]["text"]
    quiet = tips(snap(next_period="shoulder", next_change=NOW + timedelta(hours=8)), {}, NOW.replace(hour=2))
    assert quiet == [{"level": "info", "text": "Nothing needs doing right now.", "why": "off peak at 32c"}]


def test_solar_spill_tip():
    out = tips(snap(next_period="peak", next_change=NOW + timedelta(hours=4)), {"pv": 6.0, "grid": -4.0}, NOW.replace(hour=12), )
    assert not any("going to the grid" in t["text"] for t in out)  # battery not full
    s = snap(battery_soc=99.0, next_change=NOW + timedelta(hours=4))
    assert any("going to the grid" in t["text"] for t in tips(s, {"pv": 6.0, "grid": -4.0}, NOW.replace(hour=12)))


def test_ev_in_peak_from_solar_and_battery_is_not_flagged():
    s = snap(period="peak", import_rate=41.91, next_period="off_peak", battery_soc=70.0)
    out = tips(s, {"ev": 7.0, "pv": 3.5, "grid": 0.0, "batt": -4.0}, NOW.replace(hour=17))
    assert not any("Pause" in t["text"] or "from the grid" in t["text"] for t in out)
    assert any("EV charging at 7.0 kW from 3.0 kW solar, 4.0 kW battery" in t["text"] for t in out)
    # grid really feeding the car: say how much
    out = tips(s, {"ev": 7.0, "pv": 0.0, "grid": 3.0, "batt": -4.0}, NOW.replace(hour=17))
    assert out[0]["level"] == "act" and "pulling 3.0 kW from the grid" in out[0]["text"]
