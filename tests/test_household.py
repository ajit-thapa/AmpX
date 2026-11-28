"""Around the house: bin day, safety sensors, appliances finishing, big loads.

Every part finds its own entities and stays empty when the house has none."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ampx.const import DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY


async def _setup(hass: HomeAssistant, **opts):
    pushes = async_mock_service(hass, "notify", "phone")
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={}, options={**DEFAULTS, **LEGACY, "notify": "notify.phone", **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id], pushes


async def test_nothing_found_means_empty(hass: HomeAssistant):
    brain, _ = await _setup(hass)
    st = brain.household.status()
    assert st == {"bins": [], "bins_tomorrow": None, "safety": [], "appliances": [], "events": [], "loads": []}


async def test_bins_from_waste_collection_schedule(hass: HomeAssistant):
    hass.states.async_set("sensor.red_bin", "Tomorrow", {"daysTo": 1, "friendly_name": "Red bin"})
    hass.states.async_set("sensor.yellow_bin", "in 8 days", {"daysTo": 8, "friendly_name": "Yellow bin"})
    hass.states.async_set("sensor.green_bin", "Tomorrow", {"daysTo": 1, "friendly_name": "Green bin"})
    brain, pushes = await _setup(hass)
    st = brain.household.status()
    assert [b["name"] for b in st["bins"]] == ["Green bin", "Red bin", "Yellow bin"]
    assert st["bins_tomorrow"] == "Bins out tonight: Green bin and Red bin."
    assert "Bins out tonight" in brain.briefing.build(["reminders"])
    await brain.household.remind_bins()
    await hass.async_block_till_done()
    assert pushes and "Green bin and Red bin" in pushes[-1].data["message"]


async def test_leak_alarm_is_a_health_issue_right_away(hass: HomeAssistant):
    hass.states.async_set("binary_sensor.laundry_leak", "off", {"device_class": "moisture", "friendly_name": "Laundry leak"})
    brain, pushes = await _setup(hass)
    assert brain.household.status()["safety"] == [{"entity_id": "binary_sensor.laundry_leak", "name": "Laundry leak", "kind": "leak", "on": False}]
    hass.states.async_set("binary_sensor.laundry_leak", "on", {"device_class": "moisture", "friendly_name": "Laundry leak"})
    await hass.async_block_till_done()
    assert any("Laundry leak" in i and "leak" in i for i in brain.health)
    assert any("Laundry leak" in p.data["message"] for p in pushes)


async def test_washer_finishing_is_an_event_and_a_push(hass: HomeAssistant):
    hass.states.async_set("sensor.washer_status", "running", {"friendly_name": "Washer status"})
    brain, pushes = await _setup(hass)
    assert brain.household.status()["appliances"][0]["name"] == "Washer"
    hass.states.async_set("sensor.washer_status", "finished", {"friendly_name": "Washer status"})
    await hass.async_block_till_done()
    ev = brain.household.status()["events"]
    assert ev and ev[0]["text"] == "Washer finished"
    assert any("Washer finished" in p.data["message"] for p in pushes)
    # numeric power sensors with washer in the name are not a status
    hass.states.async_set("sensor.washer_power", "410", {"unit_of_measurement": "W", "device_class": "power"})
    assert [a["entity_id"] for a in brain.household.status()["appliances"]] == ["sensor.washer_status"]


async def test_big_loads_skip_the_energy_system(hass: HomeAssistant):
    brain, _ = await _setup(hass)
    hass.states.async_set("sensor.fridge_power", "120", {"unit_of_measurement": "W", "device_class": "power", "friendly_name": "Fridge power"})
    hass.states.async_set("sensor.pool_pump_power", "1.1", {"unit_of_measurement": "kW", "device_class": "power", "friendly_name": "Pool pump power"})
    hass.states.async_set("sensor.ness_pv_power", "5.0", {"unit_of_measurement": "kW", "device_class": "power"})
    hass.states.async_set("sensor.neovolt_local_grid_power", "900", {"unit_of_measurement": "W", "device_class": "power"})
    loads = brain.household.status()["loads"]
    assert [(l["name"], l["kw"]) for l in loads] == [("Pool pump", 1.1), ("Fridge", 0.12)]


async def test_overview_carries_household(hass: HomeAssistant, hass_ws_client):
    hass.states.async_set("sensor.red_bin", "Tomorrow", {"daysTo": 1, "friendly_name": "Red bin"})
    await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/overview"})
    assert (await ws.receive_json())["result"]["household"]["bins"][0]["name"] == "Red bin"
