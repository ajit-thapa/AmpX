# AmpX requirements

What AmpX is built to do, and where each piece lives. Written from the owner's requirements
(this session) and the code as it stands on `feat/write-safety-journal`.

Status key: **built** (in the code with tests) · **owner** (needs an action only the owner can take).

## 1. Purpose

Native Home Assistant custom integration, domain `ampx`, repo `ajit-thapa/cortex`, panel served at
`/ampx_static/ampx-studio.js`. One brain for a home with solar, a home battery and an EV on a
time-of-use plan: minimise the bill, protect the hardware, and explain every decision.

## 2. The home it runs

| Hardware | Entities |
|---|---|
| Sungrow inverter and PV | studio PV, grid, battery power (sign flip per source) |
| Neovolt / Byte-Watt 50 kWh battery | SOC, dispatch mode, power, duration, charge/discharge target SOC, stop button |
| Tesla Wall Connector Gen3 (~7.2 kW, read-only) | charger power, EV draw |
| BYD Sealion 7 (plug-in hybrid, ~40 kWh) | battery level, plug, power, voltage, current, pure/total range, fuel |
| AGL plan, Sydney, NSW holidays | tariff rates and windows, `calendar.australia_nsw` |
| Solcast, Helios | PV forecast today/tomorrow |

Nothing is hard-wired: entities, rates, windows, names and photos are all options. New installs start
blank; `migrate.py` fills the one legacy home only for entries older than schema 2.

## 3. Hard rules — built

- House never buys grid power outside the cheap window. Exports stop at the house's share; an off-peak
  EV charges from the grid while the battery covers only the house. (`ladder.py`: `house_rule`, `ev_grid`.)
- The EV never charges from the grid in peak, even below its minimum SOC (the car has fuel). (`sealion7.py`.)
- Evening export only above the floor (30% default), raised for overnight need by `autopilot_rules.py`;
  a forced export also stops at the reserve. (`ladder.py`: `reserve`, `export_cap`.)
- No keys or tokens in the code or the frontend. The AI provider key is entered by the owner in HA. **owner**

## 4. Tariff — built

Rates and windows are options (`tariff.Plan`), defaulting to the AGL plan: shoulder 10–14, peak 14–21 on
business days (holidays excluded), off-peak otherwise; feed-in 28c 17–21 else 3c. `export_pays` is true only
while feed-in is at the plan's best, so nothing is exported at 3c unless the owner starts it.

## 5. Decision ladder — built

`ladder.evaluate` returns the first matching rule with an action and a reason. Order:

1. **stale** — battery level missing, or grid and battery readings stuck, for 10 min: hand the battery back
   to the inverter. Only for a dispatch AmpX started, or any dispatch while AmpX runs the battery.
2. **peak_guard** — peak rate: never charge the battery from the grid; pause an EV the battery can't carry.
3. **ev_grid** — EV on the off-peak grid, nothing to spare: battery covers only the house.
4. **reserve** / **house_rule** / **export_cap** — floors on a forced discharge: the reserve, the house's
   share until the cheap window, and no export while feed-in is low.
5. **manual / plan / autopilot** — a running dispatch, named by who started it.
6. **self_consumption** — nothing above applies.

At a tariff window edge, timers and Autopilot get two minutes to stop their own dispatch before the
peak-charge guard or the export cap steps in. Every verdict carries a rule name and reason and is logged
to the journal (`journal.py`) when it changes; `sensor.ampx_decision` exposes the latest.

## 6. Write safety — built

From the EnergyWizard review. In `safety.py`, applied in `energy.py`:

- **Freeze watch**: a reading missing or stuck for 10 min is not trusted (rule 1 above).
- **Command gate**: 200 W deadband and a 5 min dwell on automatic power changes. A change that keeps the
  house off the grid, or a new situation, skips the dwell.
- **No-export cap**: a discharge covers the house's need, not full power.
- **Observe mode**: the single write gate `_set` sends nothing. Default on for new installs; the schema 3
  upgrade turns it off for existing installs so they keep controlling the battery.

## 7. Sealion 7 — built

Standalone pure module (`sealion7.py`) plus HA feature (`sealion7_feature.py`), every 60 s. Order:
unplugged, no reading, at target, peak pause, below minimum, cheap window, wait. Cheap and peak windows
follow the tariff (and its peak days) unless set for the car. Observe by default; control mode presses
start/stop with a 5 min cooldown, and nothing while Hermes is the engine or AmpX is in observe mode.
Warns when the car's own schedule is on; alerts on slow charging after 5 min.

## 8. Engine — built

`decision_engine` option: `ampx` (the ladder) or `hermes` (external agent; AmpX only watches the house
rule and shows Hermes's decisions). Shown and switchable in the panel.

## 9. UI — built

Panel `ampx-studio.js`: Now (live flow), Energy (today, tariff, bill, history), Devices (Battery, EV,
Sealion 7, Charger, All), House, Assistant. Battery view adds the Observe-only toggle and the Decision
journal. Every control saves through `ampx/set_options`, validated in `websocket.CONTROL_OPTIONS`.

## 10. Notifications — built / owner

Push, daily summary, peak-import watch, battery-temperature alert are built. The AI advisor and briefing
need an AI provider configured in HA. **owner**

## 11. Engineering rules — built

Pure logic modules (`safety.py`, `ladder.py`, `sealion7.py`, `tariff.py`) have no HA imports and are unit
tested. Features follow load/start/stop/dump. Panel writes are validated at the websocket boundary. Branch
per change; merge to `main` only on the owner's say.

## 12. Open items — owner

- Deploy `feat/write-safety-journal` (0.24.0) to HA, restart, hard-refresh. New install → observe mode on;
  watch the journal for a day, then turn observe off to let AmpX control the battery.
- Map the Sealion 7 sensors in Devices → Sealion 7 (power, voltage, current, ranges, fuel, stop button).
- Add an AI provider and key in HA for the advisor and briefing.
- Confirm dispatch power (owner said 10 kW; entity showed 3.0/7.6).
- Decide the fate of the old AGL automations (peak guard, EV shoulder, EV gate) now the ladder covers them.
- Turn off the car's own 21:00–08:00 schedule, or it fights AmpX.

## Review findings fixed this round

| # | Finding |
|---|---|
| R1 | Panel read `control.decision_engine` but the overview never sent it; now sent. |
| R2 | Sealion 7 charged from the grid in peak when below minimum; peak is now the hard rule. |
| R3 | Sealion 7 used hard-coded windows and ignored peak days; now follows the tariff. |
| R4 | Sealion 7 control pressed the car's buttons under Hermes; now gated. |
| R5 | Power follow-up writes had a 0.1 kW deadband and no dwell; now 200 W and 5 min. |
| R6 | EV-first exported at full power at 3c feed-in; now a trickle unless export pays. |
| R7 | No guard stopped a grid charge still running in peak; now `peak_guard`. |
| R8 | Nothing reacted to stale readings during a forced dispatch; now `stale` → hand back. |
| R9 | `tariff.py` peak 16–20 is only the dataclass default; the live window is options. No change. |
