# Workspace Rules for EchoSphere

## UI Consistency Rule Across User Roles
- UI improvements and design changes made to the Developer Administrator (`devadmin`) role's pages must automatically be applied to the pages of all other roles (Student, Teacher, Head of Department, College Admin, Principal).
- Note: This rule applies ONLY to UI/UX design, styling, and visual aesthetics — feature permissions and role capabilities must remain strictly enforced.

## Primary Target & Zero Overflow Guarantee
- **Primary Build Target**: Android (`flutter build apk --debug`) is the primary target for all builds, feature updates, and layout testing.
- **Zero Overflow Constraint**: All UI layouts, headers, stat cards, dialogs, chip rows, and text fields must use responsive constraints (`Expanded`, `Flexible`, `SingleChildScrollView`, `Wrap`) to guarantee zero layout overflow errors on all Android device screen sizes (from 320px compact mobile screens to large tablets).

## Strict Prohibition of Developer / Model-Specific Info in User-Facing UI
- **Zero Internal / Technical Jargon in UI**: Never expose or mention application development-specific info, internal model names, model versions, voice IDs, or backend library names in any user-facing UI, label, button, chip, dialog, tooltip, toast, snackbar, or status message.
  - Prohibited technical terms in user-facing text include: `Kokoro`, `Qwen`, `Gemma`, `Edge-TTS`, `SAPI`, `pyttsx3`, `af_heart`, `am_adam`, `af_adam`, `en-US-AriaNeural`, or any other voice/model identifiers.
  - Use clean, user-centric, professional terminology instead:
    - Voice selection: "Speaker Voice" (header), "Female Voice" and "Male Voice" (options/chips).
    - Summarization: "AI Summary", "✨ AI Summary generated!", "Generating AI Summary...".
    - Audio playback: "Listen to Notice", "Reading AI Summary Aloud", "Reading Full Notice Aloud".
- This rule applies unconditionally to all future features, menus, dialogs, screens, and functions across the entire application.

## Database Integrity & Cloud-First Source of Truth
- **Canonical Database**: The production database is hosted on **Supabase PostgreSQL** (`aws-0-ap-south-1.pooler.supabase.com:6543/postgres`).
- **Render Backend Connection**: Render's web service must ALWAYS connect to Supabase PostgreSQL via the private cloud `DATABASE_URL` environment variable. Never configure Render to use local/ephemeral SQLite.
- **Local SQLite Boundary**: Any local SQLite database (`backend/echosphere.db`) is strictly for offline testing/development. No commands or scripts may create duplicate databases in the project root.
- **Idempotent Schema Migrations**: Any schema updates (new columns, indexes) must be added as idempotent SQL migrations in `backend/app/main.py` (e.g., `ALTER TABLE announcements ADD COLUMN IF NOT EXISTS ...`) so they apply automatically to Supabase upon deployment without downtime or data loss.

## Git Security & Zero-Secrets Guarantee
- **Zero Database Commits**: Never commit, stage, or push any database binary or log files (`*.db`, `*.sqlite*`, `*.db-shm`, `*.db-wal`, `*.db-journal`) to GitHub. Keep them strictly ignored in `.gitignore`.
- **Zero Credentials in Git**: Never commit Supabase passwords, Render API keys, JWT production secrets, or real database connection URIs to files tracked by Git. Production secrets must reside exclusively in the Render Environment Dashboard.
- **Pre-Push Validation**: Before running `git commit` or `git push`, always inspect `git status` to verify that no `.db`, `.env`, or sensitive credentials are being staged.

## Deployment & GitHub Push Protocol
- **Staging Rule**: Only stage verified application code explicitly (`git add frontend/ backend/` or targeted file paths). Avoid indiscriminate staging of untracked files.
- **Continuous Deployment**: Code pushed to `main` is automatically built and deployed by Render. Render connects directly to Supabase, guaranteeing zero data loss, zero reset of user accounts, and zero reset of announcements across all redeployments and restarts.
- **Production Server Independence**: The frontend app must always point to the live Render backend (`https://echosphere-backend-9lv8.onrender.com`). Never require or assume a running local server for user-facing app functionality.
