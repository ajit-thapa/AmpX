from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.cortex.const import DEFAULTS, DOMAIN


async def _setup(hass: HomeAssistant, **opts):
    entry = MockConfigEntry(domain=DOMAIN, title="Cortex", data={}, options={**DEFAULTS, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_and_energy_sensors(hass: HomeAssistant):
    hass.states.async_set("sensor.neovolt_online_soc", "54")
    hass.states.async_set("sensor.pv_forecast_ingleburn", "42.2")
    hass.states.async_set("sensor.byd_sealion_7_battery_level", "40")
    entry = await _setup(hass)
    assert entry.state.value == "loaded"
    brain = hass.data[DOMAIN][entry.entry_id]
    brain.refresh()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.cortex_battery_stored")
    assert state is not None and float(state.state) == 27.0
    assert float(hass.states.get("sensor.cortex_battery_room_left").state) == 23.0
    assert float(hass.states.get("sensor.cortex_ev_room_left").state) == 49.5
    assert hass.states.get("sensor.cortex_solar_day").state == "ok"
    assert hass.states.get("sensor.cortex_tariff_period").state in ("peak", "shoulder", "off_peak")
    assert "Battery 27.0/50 kWh" in hass.states.get("sensor.cortex_storage_summary").state


async def test_memory_services_and_llm_api(hass: HomeAssistant):
    await _setup(hass)
    res = await hass.services.async_call(
        DOMAIN, "remember", {"text": "The rabbits live by the shed", "category": "place"},
        blocking=True, return_response=True,
    )
    assert res["text"].startswith("The rabbits")
    found = await hass.services.async_call(
        DOMAIN, "recall", {"query": "rabbit"}, blocking=True, return_response=True
    )
    assert len(found["memories"]) == 1
    assert hass.states.get("sensor.cortex_memories").state == "1"
    api = await llm.async_get_api(
        hass, DOMAIN,
        llm.LLMContext(platform="test", context=None, language="en", assistant=None, device_id=None),
    )
    assert {t.name for t in api.tools} >= {"remember", "recall", "energy_status", "autopilot_status", "house_status", "timeline", "reminders", "energy_advice", "battery_control"}
    tools = {t.name: t for t in api.tools}
    ctx = llm.LLMContext(platform="test", context=None, language="en", assistant=None, device_id=None)

    def call(name, **args):
        return tools[name].async_call(hass, llm.ToolInput(tool_name=name, tool_args=args), ctx)

    out = await call("remind", message="Bins out", at="23:59")
    out = getattr(out, "data", out)
    assert out["reminder"]
    listed = getattr(await call("reminders"), "data", None) or await call("reminders")
    listed = getattr(listed, "data", listed)
    assert any(r["message"] == "Bins out" for r in listed["pending"])
    gone = getattr(await call("reminders", cancel=out["reminder"]), "data", None)
    assert gone is None or gone["cancelled"]
    ap = await call("autopilot_status")
    assert getattr(ap, "data", ap)["mode"] in ("off", "shadow", "auto")
    hs = await call("house_status")
    assert "parcels_waiting" in getattr(hs, "data", hs)


async def test_say_respects_quiet_hours_and_speaks(hass: HomeAssistant):
    calls = async_mock_service(hass, "assist_satellite", "announce")
    await _setup(hass, speakers=["assist_satellite.kitchen"], quiet_start="00:00:00", quiet_end="00:00:00")
    rec = await hass.services.async_call(
        DOMAIN, "say", {"message": "Dinner is ready"}, blocking=True, return_response=True
    )
    assert rec["spoken"] and len(calls) == 1
    again = await hass.services.async_call(
        DOMAIN, "say", {"message": "Dinner is ready"}, blocking=True, return_response=True
    )
    assert again["reason"] == "duplicate" and len(calls) == 1


async def test_safety_alarm_is_urgent(hass: HomeAssistant):
    calls = async_mock_service(hass, "assist_satellite", "announce")
    hass.states.async_set("binary_sensor.kitchen_smoke", "off", {"device_class": "smoke", "friendly_name": "Kitchen smoke"})
    await _setup(hass, speakers=["assist_satellite.kitchen"], quiet_start="00:00:01", quiet_end="23:59:59", notify="")
    hass.states.async_set("binary_sensor.kitchen_smoke", "on", {"device_class": "smoke", "friendly_name": "Kitchen smoke"})
    await hass.async_block_till_done()
    assert len(calls) == 1 and "smoke" in calls[0].data["message"]


async def test_reminder_and_unload(hass: HomeAssistant):
    entry = await _setup(hass)
    res = await hass.services.async_call(
        DOMAIN, "remind", {"message": "Bins out", "in_minutes": 5}, blocking=True, return_response=True
    )
    brain = hass.data[DOMAIN][entry.entry_id]
    assert len(brain.reminders) == 1 and res["id"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not hass.services.has_service(DOMAIN, "say")


async def test_topup_runs_when_short(hass: HomeAssistant):
    modes = async_mock_service(hass, "select", "select_option")
    async_mock_service(hass, "number", "set_value")
    hass.states.async_set("sensor.neovolt_online_soc", "20")
    hass.states.async_set("sensor.pv_forecast_ingleburn", "10")
    entry = await _setup(hass, notify="")
    brain = hass.data[DOMAIN][entry.entry_id]
    assert await brain.energy.start_topup() == "started"
    assert modes[0].data["option"] == "Force Charge"
    hass.states.async_set("sensor.pv_forecast_ingleburn", "60")
    assert (await brain.energy.start_topup()).startswith("skipped")


async def test_options_flow(hass: HomeAssistant):
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "menu"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "tariff"})
    assert result["type"] == "form"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"fit_evening": 30.0})
    assert result["type"] == "create_entry"
    assert entry.options["fit_evening"] == 30.0


async def test_sensors_fill_when_sources_appear_after_start(hass: HomeAssistant):
    entry = await _setup(hass)  # nothing exists yet, like a restart race
    assert hass.states.get("sensor.cortex_battery_stored").state == "unknown"
    hass.states.async_set("sensor.neovolt_online_soc", "50")
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.cortex_battery_stored").state) == 25.0
    assert hass.states.get(f"sensor.cortex_storage_summary").state.startswith("Battery 25.0/50")


async def test_llm_tools_declare_integration_and_return_dicts(hass: HomeAssistant):
    await _setup(hass)
    api = await llm.async_get_api(
        hass, DOMAIN,
        llm.LLMContext(platform="test", context=None, language="en", assistant=None, device_id=None),
    )
    assert api.tools and all(getattr(t, "integration", None) == DOMAIN for t in api.tools)
    tool = next(t for t in api.tools if t.name == "recall")
    out = await tool.async_call(hass, llm.ToolInput("recall", {"query": ""}), api.llm_context)
    data = getattr(out, "data", out)
    assert "memories" in data


async def test_battery_control_and_advice_tools(hass: HomeAssistant):
    brain = await _setup(hass)
    hass.states.async_set("sensor.neovolt_online_soc", "80")
    for domain, svc in (("number", "set_value"), ("select", "select_option"), ("button", "press")):
        hass.services.async_register(domain, svc, lambda call: None)
    ctx = llm.LLMContext(platform="test", context=None, language="en", assistant=None, device_id=None)
    api = await llm.async_get_api(hass, DOMAIN, ctx)
    tools = {t.name: t for t in api.tools}
    run = lambda n, **a: tools[n].async_call(hass, llm.ToolInput(tool_name=n, tool_args=a), ctx)  # noqa: E731
    out = await run("energy_advice")
    assert getattr(out, "data", out)["tips"]
    out = await run("battery_control", action="export", kw=5.0, soc=40)
    assert getattr(out, "data", out)["result"] == "started"
    out = await run("battery_control", action="stop")
    assert getattr(out, "data", out)["result"] == "stopped"
    out = await run("battery_control", action="mode", mode="auto")
    await hass.async_block_till_done()
    assert hass.config_entries.async_entries(DOMAIN)[0].options["autopilot_mode"] == "auto"


async def test_assistant_tools_and_style(hass: HomeAssistant):
    entry = await _setup(hass, assistant_style="detailed", assistant_notes="Call me Ajit.")
    brain = hass.data[DOMAIN][entry.entry_id]
    ctx = llm.LLMContext(platform="test", context=None, language="en", assistant=None, device_id=None)
    api = await llm.async_get_api(hass, DOMAIN, ctx)
    assert "full answer" in api.api_prompt and "Call me Ajit." in api.api_prompt
    tools = {t.name: t for t in api.tools}
    assert {"announce", "camera_look", "save_routine", "delete_routine", "watch", "quiet", "briefing"} <= set(tools)
    run = lambda n, **a: tools[n].async_call(hass, llm.ToolInput(tool_name=n, tool_args=a), ctx)  # noqa: E731
    d = lambda x: getattr(x, "data", x)  # noqa: E731
    out = d(await run("save_routine", name="lights out", steps=[{"service": "light.turn_off", "target": {"entity_id": "light.all"}}], schedule={"at": "23:00"}))
    assert out["saved"] == "lights out" and "lights out" in brain.routines.items
    assert "error" in d(await run("save_routine", name="bad", steps=[{"service": "not valid"}]))
    assert d(await run("delete_routine", name="lights out"))["deleted"]
    hass.states.async_set("cover.garage", "closed")
    assert d(await run("watch", entity_id="cover.garage", message="Garage opened", to_state="open"))["watching"] == "cover.garage"
    assert "error" in d(await run("watch", entity_id="cover.nope", message="x"))
    assert d(await run("quiet", minutes=30))["hushed_minutes"] == 30 and brain.gate.hushed_until
    assert "error" in d(await run("camera_look", camera="front"))
    assert isinstance(d(await run("briefing"))["text"], str)
    assert "spoken" in d(await run("announce", message="Dinner is ready"))
