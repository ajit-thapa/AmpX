"""Expose the shared brain to any conversation agent as an LLM API."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util

from datetime import timedelta

from .const import CONF_AS_NOTES, CONF_AS_STYLE, DOMAIN
from .memory import CATEGORIES
from .runtime import Cortex

PROMPT = (
    "You share a household memory with every other assistant in the house. "
    "Use cortex tools to remember durable facts the user tells you, recall them "
    "before answering questions about the household, and set reminders. "
    "Energy questions: use energy_status instead of guessing; for why the battery did something, use autopilot_status. "
    "For what to do right now with energy, use energy_advice. To start or stop battery export or grid charging, or change "
    "how the battery is controlled, use battery_control and say what you did. "
    "For house questions (doors, visitors, parcels, what happened today) use house_status or timeline. "
    "Answer briefly and in plain words, then say what you did if you changed anything. "
    "Never invent numbers: if a tool has no value, say so."
)


def _out(data: dict[str, Any]) -> Any:
    """Wrap tool output in ToolResult where this Home Assistant has it."""
    result = getattr(llm, "ToolResult", None)
    return result(data=data) if result else data


class _Tool(llm.Tool):
    integration = DOMAIN  # required for custom tools from HA 2027.10

    def __init__(self, brain: Cortex) -> None:
        self.brain = brain


class RememberTool(_Tool):
    name = "remember"
    description = "Save a short durable fact about the household or its people."
    parameters = vol.Schema(
        {
            vol.Required("text"): str,
            vol.Optional("category", default="fact"): vol.In(CATEGORIES),
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> dict[str, Any]:
        args = tool_input.tool_args
        memory = self.brain.remember(args["text"], args.get("category", "fact"), "llm")
        return _out({"saved": memory.text, "id": memory.id})


class RecallTool(_Tool):
    name = "recall"
    description = "Search shared household memory."
    parameters = vol.Schema({vol.Optional("query", default=""): str})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        found = self.brain.book.recall(tool_input.tool_args.get("query", ""))
        return _out({"memories": [m.text for m in found]})


class ForgetTool(_Tool):
    name = "forget"
    description = "Remove a memory by id or by describing it."
    parameters = vol.Schema({vol.Required("memory"): str})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        gone = self.brain.forget(tool_input.tool_args["memory"])
        return _out({"forgotten": gone.text if gone else None})


class RemindTool(_Tool):
    name = "remind"
    description = (
        "Speak a reminder aloud. Give in_minutes for a delay, or at as a 24 hour HH:MM clock time "
        "(today, or tomorrow if that time has passed)."
    )
    parameters = vol.Schema(
        {
            vol.Required("message"): str,
            vol.Optional("in_minutes"): vol.All(int, vol.Range(min=1, max=60 * 24 * 14)),
            vol.Optional("at"): vol.Match(r"^([01]?\d|2[0-3]):[0-5]\d$"),
        }
    )

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        args = tool_input.tool_args
        from datetime import timedelta

        now = dt_util.now()
        if args.get("at"):
            hh, mm = (int(x) for x in args["at"].split(":"))
            when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if when <= now:
                when += timedelta(days=1)
        elif args.get("in_minutes"):
            when = now + timedelta(minutes=args["in_minutes"])
        else:
            return _out({"error": "give in_minutes or at"})
        item = self.brain.add_reminder(args["message"], when)
        return _out({"reminder": item["id"], "at": item["at"]})


class RemindersTool(_Tool):
    name = "reminders"
    description = "List pending reminders, or cancel one by id."
    parameters = vol.Schema({vol.Optional("cancel"): str})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        cancel = tool_input.tool_args.get("cancel")
        cancelled = self.brain.cancel_reminder(cancel) if cancel else None
        out: dict[str, Any] = {"pending": [{"id": r["id"], "message": r["message"], "at": r["at"]} for r in self.brain.reminders]}
        if cancel:
            out["cancelled"] = bool(cancelled)
        return _out(out)


class AutopilotStatusTool(_Tool):
    name = "autopilot_status"
    description = "Battery autopilot mode and its latest decisions with the reasons (top-up and evening export)."
    parameters = vol.Schema({vol.Optional("count", default=3): vol.All(int, vol.Range(min=1, max=10))})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        ap, n = self.brain.autopilot, tool_input.tool_args.get("count", 3)
        keep = ("window", "do", "reason", "result", "source", "kw", "target_soc", "floor_soc", "outcome", "time")
        return _out({
            "mode": ap.mode,
            "active": ap.active,
            "decisions": [{k: d[k] for k in keep if k in d} for d in ap.decisions[-n:][::-1]],
        })


class HouseStatusTool(_Tool):
    name = "house_status"
    description = "Security sweep, house health issues, visitors today and parcels waiting."
    parameters = vol.Schema({})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        b = self.brain
        return _out({
            "security": b.security.check(),
            "health_issues": list(b.health),
            "visitors_today": b.visitors.today_count(),
            "parcels_waiting": b.visitors.parcels_waiting,
            "recent_visitors": [f"{v['kind']}: {v['text']}" for v in b.visitors.log[-5:][::-1]],
        })


class TimelineTool(_Tool):
    name = "timeline"
    description = "What happened recently around the house, newest first, plus this week's totals."
    parameters = vol.Schema({vol.Optional("count", default=10): vol.All(int, vol.Range(min=1, max=30))})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        n = tool_input.tool_args.get("count", 10)
        return _out({"events": list(self.brain.timeline.items)[:n], "week": self.brain.timeline.week()})


class EnergyStatusTool(_Tool):
    name = "energy_status"
    description = "Current tariff period, rates, solar forecast, battery and EV storage."
    parameters = vol.Schema({})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        self.brain.refresh()
        s = dict(self.brain.snapshot)
        s["next_change"] = s["next_change"].isoformat()
        return _out(s)


class EnergyAdviceTool(_Tool):
    name = "energy_advice"
    description = "Up to four plain tips on what to do with energy right now (EV, battery, peak, solar spill), most urgent first."
    parameters = vol.Schema({})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        self.brain.refresh()
        return _out({"tips": self.brain.advice(), "control_mode": self.brain.control_mode()})


class BatteryControlTool(_Tool):
    name = "battery_control"
    description = (
        "Control the home battery. action: export (discharge to the grid), topup (charge from the grid), "
        "stop (back to normal), or mode (who controls it: off = manual, timers, shadow = advise only, auto = Autopilot). "
        "kw is the power (0.5-10), soc the floor for export or the target for topup (10-100). Omit them to use the saved limits."
    )
    parameters = vol.Schema({
        vol.Required("action"): vol.In(["export", "topup", "stop", "mode"]),
        vol.Optional("kw"): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10)),
        vol.Optional("soc"): vol.All(vol.Coerce(float), vol.Range(min=10, max=100)),
        vol.Optional("mode"): vol.In(["off", "timers", "shadow", "auto"]),
    })

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        args, energy = tool_input.tool_args, self.brain.energy
        action = args["action"]
        if action == "export":
            return _out({"result": await energy.start_export(True, args.get("kw"), args.get("soc"))})
        if action == "topup":
            return _out({"result": await energy.start_topup(True, args.get("kw"), args.get("soc"))})
        if action == "stop":
            self.brain.autopilot.active = None
            return _out({"result": await energy.stop()})
        mode = args.get("mode")
        if not mode:
            return _out({"error": "give mode: off, timers, shadow or auto", "current": self.brain.control_mode()})
        opts = {"off": {"autopilot_mode": "off", "auto_topup": False, "auto_export": False},
                "timers": {"autopilot_mode": "off", "auto_topup": True, "auto_export": True},
                "shadow": {"autopilot_mode": "shadow", "auto_topup": False, "auto_export": False},
                "auto": {"autopilot_mode": "auto"}}[mode]
        entry = self.brain.entry
        hass.config_entries.async_update_entry(entry, options={**entry.options, **opts})  # Cortex reloads
        return _out({"result": f"battery control set to {mode}"})


class AnnounceTool(_Tool):
    name = "announce"
    description = "Say something out loud on the house speakers (quiet hours and hush still apply unless urgent). Optionally push it to the phone."
    parameters = vol.Schema({
        vol.Required("message"): vol.All(str, vol.Length(min=1, max=300)),
        vol.Optional("urgent", default=False): bool,
        vol.Optional("area"): str,
        vol.Optional("push", default=False): bool,
    })

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        a = tool_input.tool_args
        rec = await self.brain.speaker.say(a["message"], a.get("urgent", False), a.get("area"), a.get("push") or None)
        return _out({"spoken": bool(rec.get("spoken")), "reason": rec.get("reason"), "pushed": bool(rec.get("pushed"))})


class CameraLookTool(_Tool):
    name = "camera_look"
    description = "Look at a camera and describe what it sees, or answer a question about the picture. Cameras: use the camera entity id."
    parameters = vol.Schema({vol.Required("camera"): str, vol.Optional("question"): str})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        a = tool_input.tool_args
        cam = a["camera"] if a["camera"].startswith("camera.") else "camera." + a["camera"]
        if hass.states.get(cam) is None:
            return _out({"error": f"no camera {cam}", "cameras": sorted(s.entity_id for s in hass.states.async_all("camera"))})
        try:
            return _out({"camera": cam, "sees": await self.brain.look(cam, a.get("question"))})
        except Exception as err:  # noqa: BLE001 - tell the model, it can explain to the user
            return _out({"error": str(err)})


class SaveRoutineTool(_Tool):
    name = "save_routine"
    description = (
        "Create or replace a named routine. steps is a list; each step is one of {say: text}, {push: text}, "
        "{service: 'domain.service', target: {entity_id: ...}, data: {...}} or {delay: seconds}. "
        "Optional schedule {at: 'HH:MM', days: daily|weekdays|weekends} or on_state {entity_id, to}. Confirm with the user first."
    )
    parameters = vol.Schema({
        vol.Required("name"): str,
        vol.Required("steps"): list,
        vol.Optional("schedule"): dict,
        vol.Optional("on_state"): dict,
    })

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        try:
            saved = self.brain.routines.save(dict(tool_input.tool_args))
        except vol.Invalid as err:
            return _out({"error": f"routine not valid: {err}"})
        return _out({"saved": saved["name"], "steps": len(saved["steps"]), "schedule": saved.get("schedule"), "on_state": saved.get("on_state")})


class DeleteRoutineTool(_Tool):
    name = "delete_routine"
    description = "Delete a saved routine by name."
    parameters = vol.Schema({vol.Required("name"): str})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        return _out({"deleted": bool(self.brain.routines.delete(tool_input.tool_args["name"]))})


class WatchTool(_Tool):
    name = "watch"
    description = "Tell the household when an entity changes (optionally only to a given state), e.g. tell me when the garage door opens."
    parameters = vol.Schema({
        vol.Required("entity_id"): str,
        vol.Required("message"): vol.All(str, vol.Length(min=1, max=200)),
        vol.Optional("to_state"): str,
        vol.Optional("urgent", default=False): bool,
    })

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        a = tool_input.tool_args
        if hass.states.get(a["entity_id"]) is None:
            return _out({"error": f"unknown entity {a['entity_id']}"})
        item = self.brain.add_watch(a["entity_id"], a["message"], a.get("to_state"), urgent=a.get("urgent", False))
        return _out({"watching": item["entity_id"], "id": item["id"]})


class QuietTool(_Tool):
    name = "quiet"
    description = "Stop Cortex speaking for a number of minutes (0 to resume)."
    parameters = vol.Schema({vol.Required("minutes"): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440))})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        m = tool_input.tool_args["minutes"]
        self.brain.gate.hush(dt_util.now() + timedelta(minutes=m) if m else None)
        self.brain.notify_update()
        return _out({"hushed_minutes": m})


class BriefingTool(_Tool):
    name = "briefing"
    description = "Today's household briefing (weather, energy, reminders) or the weekly summary as text."
    parameters = vol.Schema({vol.Optional("kind", default="today"): vol.In(["today", "week"])})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        kind = tool_input.tool_args.get("kind", "today")
        return _out({"text": self.brain.briefing.weekly_text() if kind == "week" else self.brain.briefing_text()})


class RunRoutineTool(_Tool):
    name = "run_routine"
    description = "Run a saved Cortex routine by name (for example goodnight or leaving)."
    parameters = vol.Schema({vol.Required("name"): str})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        name = tool_input.tool_args["name"]
        if name not in self.brain.routines.items:
            return _out({"error": f"No routine called {name}", "known": sorted(self.brain.routines.items)})
        await self.brain.routines.run(name)
        return _out({"ran": name})


class SecurityCheckTool(_Tool):
    name = "security_check"
    description = "Read-only check for open doors and windows, unlocked locks and disarmed alarms."
    parameters = vol.Schema({})

    async def async_call(self, hass, tool_input, llm_context) -> dict[str, Any]:
        return _out(self.brain.security.check())


class CortexAPI(llm.API):
    """The ``cortex`` LLM API."""

    def __init__(self, hass: HomeAssistant, brain: Cortex) -> None:
        super().__init__(hass=hass, id=DOMAIN, name="Cortex")
        self.brain = brain

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        tools: list[llm.Tool] = [
            RememberTool(self.brain),
            RecallTool(self.brain),
            ForgetTool(self.brain),
            RemindTool(self.brain),
            RemindersTool(self.brain),
            EnergyStatusTool(self.brain),
            AutopilotStatusTool(self.brain),
            EnergyAdviceTool(self.brain),
            BatteryControlTool(self.brain),
            HouseStatusTool(self.brain),
            TimelineTool(self.brain),
            RunRoutineTool(self.brain),
            SaveRoutineTool(self.brain),
            DeleteRoutineTool(self.brain),
            AnnounceTool(self.brain),
            CameraLookTool(self.brain),
            WatchTool(self.brain),
            QuietTool(self.brain),
            BriefingTool(self.brain),
            SecurityCheckTool(self.brain),
        ]
        if self.brain.routines.items:
            prompt_routines = ", ".join(sorted(self.brain.routines.items))
        top = self.brain.book.recall("", 5)
        prompt = PROMPT + f" Now: {dt_util.now().strftime('%A %d %B %H:%M')}."
        style = self.brain.opts.get(CONF_AS_STYLE) or "brief"
        prompt += {"brief": " Keep answers to one or two sentences.", "normal": " Answer in a short paragraph.",
                   "detailed": " Give a full answer with the numbers and reasons; short lists are fine."}.get(style, "")
        notes = (self.brain.opts.get(CONF_AS_NOTES) or "").strip()
        if notes:
            prompt += " Household instructions: " + notes[:600]
        if self.brain.routines.items:
            prompt += " Routines you can run: " + prompt_routines + "."
        if top:
            prompt += " Known so far: " + "; ".join(m.text for m in top) + "."
        return llm.APIInstance(api=self, api_prompt=prompt, llm_context=llm_context, tools=tools)
