# Cortex backlog

Statuses: `proposed` · `ready` (bot may implement) · `in-progress` · `done`.
Priority: P1 broken/unsafe · P2 user-visible gap · P3 polish.

| id | pri | status | item | acceptance |
|---|---|---|---|---|
| verify-house-rule | P1 | proposed | House rule (0.22.0) not yet seen working on the real system. Owner to watch Energy → Plan and battery control for a week. Report any grid import 00:00–10:00 or 14:00–24:00 that the house caused. | Owner confirms, or a bug item is filed with evidence. |
| autopilot-follow | P2 | proposed | Decide when planner output may drive Autopilot (currently shadow). Needs owner data from verify-house-rule. | Owner decision recorded here. |
| wall-connector-pause | P2 | proposed | Tesla Wall Connector is read-only, so the "Pause EV" alert cannot pause the car. Investigate an integration that can. | Written option list for owner. |
| readme-sync | P3 | proposed | README house-rule row and setup steps vs current config flow. | README matches config flow labels. |
| deploy-0.24 | P1 | proposed | Owner deploys 0.24.0 to HA: restart, hard-refresh, map Sealion 7 sensors, add AI provider key. New install starts in observe mode — watch the journal a day, then turn observe off. | Owner confirms the panel, journal and Sealion 7 work on the real system. |
| replan-after-stale | P2 | proposed | When readings return after a stale hand-back, re-decide the running window instead of waiting for the next timer. | Battery resumes its planned dispatch within a minute of readings returning. |
| sl7-charging-sensor | P3 | proposed | Sealion 7 "charging (on/off)" entity unset; charging is inferred from power > 0.1 kW. Map a real binary sensor if the car exposes one. | Charging state reads from an entity, or confirmed that power is enough. |
