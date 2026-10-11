---
name: echosphere-guardian
description: >-
  Master control, diagnostics, and operational verification skill for EchoSphere v2.2.
  Use when managing the speaker notice queue, inspecting ESP32 hardware or ST7735 LCD display,
  checking live heartbeats on COM7/Wokwi, auditing audio streams for speech vs. beep integrity,
  verifying Hugging Face ZeroGPU deployments, or running the production verification matrix.
---

# EchoSphere Guardian Skill

This skill provides comprehensive operational instructions and runbooks for using the `echosphere-mcp` tools across the entire EchoSphere v2.2 ecosystem.

## Available MCP Tools

| MCP Tool | Purpose & Capability |
|---|---|
| `echosphere_system_health_audit` | Full multi-tier audit (Render Backend, Database, ZeroGPU, ESP32, Nodes). |
| `echosphere_speaker_queue_control` | Inspect queue status, advance notice lifecycle (`PENDING` $\to$ `PLAYING` $\to$ `COMPLETED`), and dequeue upon `PLAYBACK_DONE`. |
| `echosphere_repeat_schedule_manager` | Manage repeat announcement schedules, campus acoustic break windows (IST), and enforce RBAC (Admin/Principal only). |
| `echosphere_hardware_node_manager` | Enforce 15s ping / 45s offline heartbeat rule on `Node-HW-ESP32` (COM7) and `Node-SIM-Wokwi`, eliminating fake online status. |
| `echosphere_esp32_driver_checker` | Validate MAX98357A I2S driver pinouts (BCLK=26, LRC=25, DIN=27), 0 PSRAM DMA SRAM buffer, and ST7735 LCD differential rendering. |
| `echosphere_audio_integrity_auditor` | Guarantee spoken speech output, purge legacy 16kHz sine-burst dummy WAVs, and verify 880Hz boot chime. |
| `echosphere_zerogpu_space_auditor` | Audit Hugging Face ZeroGPU Space configuration against Errors 1-4 (Line 1 `import spaces`, `@spaces.GPU`, Pydantic boolean schema patch). |
| `echosphere_render_safeguard_auditor` | Check Render 512MB RAM cloud safeguard, remote Kokoro worker forwarding, and Edge-TTS fallback (~120MB idle). |
| `echosphere_zero_jargon_scanner` | Scan UI for prohibited developer terms (`Kokoro`, `Qwen`, `Gemma`, `Edge-TTS`, `af_heart`, etc.) and ensure compliant replacements. |
| `echosphere_ai_summarizer_validator` | Validate AI text sanitizer, executive summary rules (min 15 words, bulleted dates/venues), and collapsible UI format. |
| `echosphere_database_and_git_guard` | Enforce zero database binaries (`*.db`) and zero credentials in git staging. |
| `echosphere_run_verification_matrix` | Run the complete Chapter 12 Production Verification Matrix. |

## Quick Runbooks

### 1. Speaker Not Playing / Audio Glitches
1. Run `echosphere_audio_integrity_auditor` with action `scan_code_for_beeps`.
2. Run `echosphere_hardware_node_manager` with action `check_heartbeat`.
3. Run `echosphere_esp32_driver_checker` to verify pin mappings and DMA buffer.

### 2. Notice Looping in Queue
1. Run `echosphere_speaker_queue_control` with action `verify_play_once`.
2. Inspect `echosphere_repeat_schedule_manager` with action `list`.

### 3. Deploying to Hugging Face ZeroGPU
1. Run `echosphere_zerogpu_space_auditor` to verify all 4 platform checks pass before pushing.
