# Workspace Rules & Master Architecture for EchoSphere

## 1. Production Ecosystem & Cloud Deployment Topology
All components of EchoSphere are deployed, orchestrated, and permanently configured as follows:

| Component | Platform / Host | Identifier / Resource | Responsibility & Configuration |
|---|---|---|---|
| **Database** | **Supabase PostgreSQL** | `aws-0-ap-south-1.pooler.supabase.com:6543/postgres` (Project `wvugkkwykdnyzcmaoxgj`, Mumbai) | Permanent canonical source of truth for all announcements, user credentials, approval queues, repeat schedules, notifications, audit logs. Secured with Row-Level Security (RLS). |
| **Backend API** | **Render Web Service** | `https://echosphere-backend-9lv8.onrender.com` (Service `srv-dabdp2rtqb8s73fjp000`) | FastAPI + Uvicorn server handling auth, announcements, AI summarization, audio generation, and WebSockets. Connected via private cloud `DATABASE_URL` environment variable to Supabase. Memory guarded (<512MB RAM). |
| **Speech Worker** | **Hugging Face ZeroGPU** | `hf_kokoro_zerogpu` (`rrakshu60/hf_kokoro_zerogpu`) | Dedicated remote Gradio worker executing Kokoro-82M neural TTS on free NVIDIA A100 GPU (port 7860). Offloads heavy neural synthesis from Render. |
| **Hardware Node (Live)** | **ESP32 Microcontroller** | `Node-HW-ESP32` (Serial Port COM7, 115200 baud) | Physical corridor speaker node: ST7735 128x160 TFT LCD, MAX98357A I2S Class-D amplifier, sub-second 800ms heartbeat polling, multi-AP Wi-Fi failover (OnePlus 13 hotspot + Campus Wi-Fi). |
| **Hardware Node (Sim)** | **Wokwi Virtual Node** | `Node-SIM-Wokwi` | Virtual simulation speaker node for rapid browser-based hardware and audio testing. |
| **Web Client** | **Cloudflare Pages / GitHub Pages** | `.github/workflows/deploy-web.yml` | Hosted Flutter Web application. Communicates with Render backend over HTTPS & WebSockets. |
| **Keep-Alive Daemon** | **GitHub Actions Cron** | `.github/workflows/backend-keepalive.yml` | Pings the backend every 10 min during campus hours (7:30 AM - 11:30 PM IST), keeping the backend awake with zero cold starts during active hours while conserving free tier hours at night (consuming only ~496 of 750 monthly hours). |
| **Version Control** | **GitHub Repository** | `rrakshu60-dotcom/Echosphere` (`main` branch) | Auto-triggers Render backend rebuilds (~90s) and GitHub Actions CI/CD workflows upon push. |

---

## 2. Core Operational Rules (Failure-Prevention Mandates)

### Rule 1: UI Consistency Rule Across User Roles
- UI improvements, styling upgrades, and layout refinements made to the Developer Administrator (`devadmin`) role's pages must automatically and consistently be applied across all other user roles (`Student`, `Teacher`, `Head of Department` / `HoD`, `College Admin`, `Principal`).
- Feature permissions, RBAC authorization, and role capabilities must remain strictly enforced while keeping visual aesthetics, cyber glass components, and layout ergonomics 100% unified.

### Rule 2: Primary Target & Zero Overflow Guarantee
- **Primary Target**: Android (`flutter build apk --debug`) is the primary target for all builds, feature updates, and layout testing.
- **Zero Overflow Constraint**: All UI layouts, headers, stat cards, dialogs, chip rows, and text fields must use responsive constraints (`Expanded`, `Flexible`, `SingleChildScrollView`, `Wrap`, `LayoutBuilder`) to guarantee zero layout overflow errors (`RenderFlex overflowed`) on all device screen sizes (from 320px compact mobile screens to large tablets).

### Rule 3: Strict Prohibition of Developer / Model-Specific Info in User-Facing UI
- **Zero Internal / Technical Jargon in UI**: Never expose or mention application development-specific info, internal model names, model versions, voice IDs, or backend library names in any user-facing UI, label, button, chip, dialog, tooltip, toast, snackbar, or status message.
- **Prohibited technical terms**: `Kokoro`, `Kokoro-82M`, `Qwen`, `Qwen 2.5`, `Gemma`, `LLaMA`, `Edge-TTS`, `SAPI`, `pyttsx3`, `onnxruntime`, `af_heart`, `am_adam`, `af_adam`, `en-US-AriaNeural`, `en-IN-NeerjaNeural`, or any other voice/model identifiers.
- **Approved professional terminology**:
  - Voice selection: "Speaker Voice" (header), "Female Voice" and "Male Voice" (options/chips).
  - Summarization: "AI Summary", "✨ AI Summary generated!", "Generating AI Summary...".
  - Audio playback: "Listen to Notice", "Reading AI Summary Aloud", "Reading Full Notice Aloud".

### Rule 4: Strict Data Cleanliness & Zero Test Artifacts Rule
- **Mandatory Post-Test Cleanup**: Any test, synthetic, mock, or dummy announcements, queue items, notifications, or temporary test audio files created during manual or automated verification, hardware checks, or audio tests MUST be immediately and cleanly deleted from the database and filesystem upon test completion.
- **Zero Pollution of Production Data**: Never leave test records (e.g., "[TEST]", "Diagnostic Notice", dummy text, dummy audio files) persisting in Supabase or the live web/mobile app feeds. All tests must execute within a clean teardown lifecycle (`create` $\to$ `verify` $\to$ `clean up`).

### Rule 5: Database Integrity & Cloud-First Source of Truth
- **Canonical Database**: The production database is hosted on **Supabase PostgreSQL** (`aws-0-ap-south-1.pooler.supabase.com:6543/postgres`).
- **Render Backend Connection**: Render's web service must ALWAYS connect to Supabase PostgreSQL via the private cloud `DATABASE_URL` environment variable. Never configure Render to use local/ephemeral SQLite.
- **Local SQLite Boundary**: Any local SQLite database (`backend/echosphere.db`) is strictly for offline testing/development. No commands or scripts may create duplicate databases in the project root.
- **Idempotent Schema Migrations**: Any schema updates (new columns, indexes) must be added as idempotent SQL migrations in `backend/app/main.py`:
  ```python
  if engine.dialect.name == "postgresql":
      conn.execute(text("ALTER TABLE <table_name> ADD COLUMN IF NOT EXISTS <col_name> <type>;"))
      conn.commit()
  ```
  This guarantees automatic execution against Supabase upon Render deployment without downtime or data loss.

### Rule 6: Git Security & Zero-Secrets Guarantee
- **Zero Database Commits**: Never commit, stage, or push any database binary or log files (`*.db`, `*.sqlite*`, `*.db-shm`, `*.db-wal`, `*.db-journal`) to GitHub. Keep them strictly ignored in `.gitignore`.
- **Zero Credentials in Git**: Never commit Supabase passwords, Render API keys, JWT production secrets, or real database connection URIs to files tracked by Git. Production secrets must reside exclusively in the Render Environment Dashboard and local untracked `.env` files.
- **Pre-Push Validation**: Before running `git commit` or `git push`, always inspect `git status` to verify that no `.db`, `.env`, or sensitive credentials are being staged.

### Rule 7: Render Deployment Protocol — GitHub Auto-Deploy Only (Zero API Deploy Triggers)
- **GitHub Auto-Deploy is Authoritative & Always Active**: Render web service `srv-dabdp2rtqb8s73fjp000` (`echosphere-backend`) has `autoDeploy: yes` permanently enabled. GitHub push events to `origin/main` automatically and authoritatively trigger Render builds.
- **Strict Prohibition of Render API Deploy Triggers**: NEVER trigger manual or duplicate deployments via the Render REST API (`POST /v1/services/{serviceId}/deploys`). Triggering deploys via the API creates redundant, concurrent build queues that collide with GitHub's automatic webhook deploy.
- **Sole Deployment Workflow**: The single, canonical way to deploy to Render is `git push origin main`. Once pushed, monitor the deploy passively via read-only inspection endpoints — NEVER call deploy trigger endpoints.

---

## 3. Subagent Architecture & Routing Protocol
EchoSphere uses four specialized subagent domains to eliminate errors and ensure zero-failure execution:

1. **Hardware Guardian (`echosphere-hardware-guardian`)**:
   - **Scope**: ESP32 C++ firmware (`hardware/ESp32/`), MAX98357A I2S driver (`audio_manager.h`), ST7735 128x160 TFT LCD differential rendering (`display_manager.h`), sub-second 800ms heartbeat polling & multi-AP Wi-Fi fallback (`network_manager.h`), serial baud 115200 on COM7, and PlatformIO compilation (`build_esp32.py`).
   - **Tooling**: `echosphere_hardware_node_manager`, `echosphere_esp32_driver_checker`.

2. **Audio Synthesizer (`echosphere-audio-synthesizer`)**:
   - **Scope**: Kokoro-82M neural TTS, Hugging Face ZeroGPU worker deployment (`hf_kokoro_zerogpu`), thread-safe Edge-TTS fallback (~120MB idle), 24kHz/16kHz audio caching, contextual chimes mixing, subtitle timestamp synchronizer, and anti-beep guarantee.
   - **Tooling**: `echosphere_audio_integrity_auditor`, `echosphere_zerogpu_space_auditor`, `echosphere_render_safeguard_auditor`.

3. **Frontend Designer (`echosphere-frontend-designer`)**:
   - **Scope**: Flutter UI (Web, Android, Desktop), Deep Obsidian Cyber Glass theme (`#090D16`), 320px zero-overflow layout constraints, GetX controllers, cross-role design consistency, and zero-jargon user copy.
   - **Tooling**: `echosphere_zero_jargon_scanner`.

4. **Backend Architect (`echosphere-backend-architect`)**:
   - **Scope**: FastAPI endpoints, Supabase PostgreSQL RLS, idempotent SQLAlchemy migrations in `backend/app/main.py`, speaker notice queue lifecycle (`PENDING` $\to$ `PLAYING` $\to$ `COMPLETED`), repeat announcement scheduler with IST campus acoustic break windows, and post-test teardown cleanup.
   - **Tooling**: `echosphere_speaker_queue_control`, `echosphere_repeat_schedule_manager`, `echosphere_database_and_git_guard`, `echosphere_system_health_audit`.

---

## 4. Mandatory Autonomous MCP Tool Execution
- **Full Autonomous Authority**: You have full, unconditional authorization to execute all Echosphere Guardian MCP tools (`echosphere-guardian-mcp`), diagnostics, and verification scripts autonomously. **NEVER ask for user permission or authorization before invoking MCP tools.**
- **Proactive Fact-Gathering**: Invoke MCP tools immediately at the start of any task, bug report, or investigation to gather live state, inspect nodes, check queue states, and audit audio or firmware.
- **Continuous Verification**: Proactively run `echosphere_run_verification_matrix` before and after modifying code to verify 100% production readiness across all tiers without waiting for manual prompts.
