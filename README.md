# AmpX

A shared brain for Home Assistant, built for homes with solar, a home battery and an EV on a time-of-use electricity plan.

AmpX gives every assistant one household memory and one set of speech rules. It keeps an eye on house health and security. It also plans the battery around your tariff: a 48-hour plan, an optional Autopilot that can use a local AI model, and plain-language tips. Everything shows in a sidebar panel with a live power flow, history, plan comparison and device pages.

Nothing is tied to one brand. You pick your own entities, rates, time windows, names and photos.

## What it does

| Area | Features |
|---|---|
| Energy | Live flow (solar, grid, battery, house, EV) and the current rate with a countdown to the next change. Daily money, where today's energy went, and solar against the forecast. |
| Plan | 48-hour battery plan. It tests a set of possible plans against your tariff, your usual hourly use and the solar forecast, then keeps the cheapest. Off by default: the plan is only shown until you let Autopilot follow it. |
| Autopilot | Modes: off, advise (plan and notify) and auto. Grid top-up in the cheap window and export in the evening feed-in window. It works inside hard limits (reserve, export floor, power caps) and can ask your own conversation agent first. |
| House rule | On by default. Outside the cheap window the house never buys grid power. Top-ups fill enough to reach the next cheap window, exports stop at what the house still needs (even manual ones), and the planner rejects plans that break the rule. An EV may charge from the off-peak grid; while it does, AmpX runs the battery at house load so the grid feeds only the car. In peak it asks you to pause the EV. |
| EV first | While the EV charges, the battery feeds the car first and exports only enough to cover the daily supply charge. |
| History | 7/14/30-day energy, money, self-sufficiency, battery cycling, rate-period split, a typical day, and how other retailers' plans would have priced your real usage. |
| Devices | Battery control (manual, timers, advise, Autopilot) and your inverter's own settings, found on its device. EV and charger pages show whatever your car and charger integrations expose. |
| Memory and voice | Household facts, reminders and watches, with quiet hours, banned words and repeat suppression. Replies go to the room where someone last spoke. Urgent alerts are pushed to your phone, and the same notification is never pushed twice within 12 hours. |
| House | Safety sensors (smoke, CO, water), offline devices, night watch, a security sweep, doorbell snapshots described by your AI Task entity, parcels, motion lights, heating pre-warm, learned routines and briefings. |
| Assistant | Chat in the panel with any conversation agent. Tools for assistants: remember, recall, remind, energy status, run routine, security check, look at a camera. |

## Install

1. In HACS, go to **Custom repositories** and add `https://github.com/ajit-thapa/AmpX` as an **Integration**.
2. Install **AmpX** and restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration > AmpX**.
4. Open **AmpX** in the sidebar, then the gear icon. **Setup check** lists what is still missing. **Pick entities** opens the options.
5. To let a voice assistant use AmpX's tools, enable **AmpX** under *Control Home Assistant* in that assistant's settings.

## Setting it up

All of these are optional. A page whose entities aren't set shows a short note instead of empty charts.

| Options page | What to pick |
|---|---|
| Your home | Names for the battery, EV, charger and plan. Photo addresses (you can also upload from the panel). A daily summary sensor, extra house sensors, bill sensors, and your own energy automations. |
| Energy Studio sources | Live power: solar, grid, battery and EV charger, with a sign flip for each if needed. Daily counters: solar, used, exported, imported, battery in and out. Optional: house load, the solar forecast for right now, and the charger's lifetime energy. |
| Energy and EV | Battery level and its control entities (dispatch mode, power, duration, charge and discharge targets, stop button). Solar forecast for today and tomorrow, the holiday calendar, EV level, plug, target and start button. Capacities, reserve, efficiency, power limits and floors. |
| Tariff rates and windows | Cheap (shoulder), off-peak and peak rates, supply charge and three feed-in rates. When each window starts and ends, which days peak applies, and the high-season months. |
| Autopilot | Mode, whether to ask the AI, whether to follow the 48-hour plan, battery wear cost, timeouts. |
| Voice, briefings, house | Speakers, TTS engine, phone notify service, quiet hours, briefing times, cameras, doorbells, night watch and learning. |

The panel's **Settings** page also edits names, capacities, the tariff and photos directly. Each photo (car, battery, background) is resized in the browser and saved under `<config>/ampx/`. A PNG with a transparent or plain background works best for the battery and car. With no photo, AmpX draws a battery tower and a car instead.

Battery control is limited to one battery (one dispatch mode select with a power number, a duration number, a charge target, a discharge target and a stop button). Many local battery integrations expose these.

Energy actions are off by default, and Autopilot starts in advise mode. If your own automations already do the same top-up or export, add them under **Your home** so they show up under Devices. Turn them off before you let AmpX act, or both will drive the battery.

## Tariff model

- The cheap (shoulder) window, peak window and both feed-in windows are whole hours you set.
- Peak can apply on weekdays except public holidays, on all weekdays, or every day. Holidays come from a calendar entity (for example one of the Holidays integration's calendars).
- The peak rate switches between high and low season by month.
- Anything outside the cheap and peak windows is off-peak.
- **Compare plans** lets you enter other retailers' offers as hour bands and replays your real hourly usage against them.

## Services

`ampx.say`, `ask`, `remember`, `recall`, `forget`, `remind`, `cancel_reminder`, `watch`, `unwatch`, `briefing`, `hush`, `run_checks`, `energy_action` (`topup`, `export`, `stop`; `force` skips the checks), `save_routine`, `delete_routine`, `run_routine`, `accept_suggestion`, `dismiss_suggestion`, `add_motion_light`, `remove_motion_light`, `add_heating`, `remove_heating`, `security_check`, `look`, `set_spot`, `parcels_collected`, `weekly_report`, `backup`, `restore`, `autopilot_decide`.

## Sensors

Tariff period, import and feed-in rate, next period and change, export needed to cover the daily charge, solar shortfall, solar day, battery and EV storage, energy summary, battery plan, Autopilot, memories, last spoken, likely room, house health issues, routine suggestions, visitors, parcels, security issues and last event.

## Upgrading from 0.20 or earlier

Earlier versions shipped with one home's entities as defaults. On the first start of 0.21, those values are copied into your options wherever you hadn't set your own, so nothing changes. From then on, every value lives in your own options.

## Development

```
pip install -r requirements_test.txt
pytest -q
```

MIT licensed.
