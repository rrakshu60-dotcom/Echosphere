# Mandatory Live Browser & ESP32 Hardware Monitor Verification Rule

This rule is MANDATORY and PERMANENT for all tasks in this repository involving playback, scheduling, queues, emergency priority overrides, hardware smart speakers, and audio broadcasting.

## Verification Requirements
Whenever diagnosing, fixing, developing, or confirming solutions:

1. **Simultaneous Real-Time Testing**:
   - MUST open the live production website (`https://echosphere-2jf.pages.dev/`) using the browser subagent.
   - MUST log in using verified credentials (`ESDEV01` / `rakshitha@1228`).
   - MUST simultaneously access the physical ESP32 microcontroller (`COM5`) and actively monitor its live serial logs (`python -u backend/scripts/live_esp32_monitor.py` or active serial task).

2. **End-to-End User Scenario Confirmation**:
   - MUST trigger and test the action directly from the website UI (e.g. broadcasting normal notice, then broadcasting emergency notice or clicking Emergency Override).
   - MUST verify on the live ESP32 serial monitor:
     - Immediate (<1s) interruption/preemption of any active audio stream.
     - Red LCD styling (`! EMERGENCY BROADCAST !`) and siren triggering.
     - Resumption/recovery of paused notices after emergency concludes.
   - NEVER consider a task completed until both the live browser interaction and physical ESP32 serial monitor confirm 100% success.
