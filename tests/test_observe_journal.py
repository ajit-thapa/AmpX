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
