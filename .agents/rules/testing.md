# Mandatory Testing Rules (Test-First, Isolated, Machine-Checked)

These rules are MANDATORY and PERMANENT for every fix or feature in this repository.
Agreed with the owner on 2026-10-22.

## 1. Tests first, then implementation
1. Write the tests that describe the required behaviour before writing the implementation:
   - Backend logic: `backend/app/test_*.py` (pytest).
   - Flutter UI and controllers: `frontend/test/*_test.dart`.
   - Live end-to-end checks: `backend/scripts/live_*.py` (see §4).
2. Run them and confirm they fail for the expected reason. Record the failure message. A new test that already
   passes proves nothing; fix the test first.
3. Only then implement, until the new tests and all existing tests pass.
4. Never weaken, skip, or delete a test to make it pass. If a test is wrong, say so and explain the change.

## 2. Each kind of test has its own database
- Unit tests (`backend/app/test_*.py`) always run against a fresh temporary SQLite database created for that run.
  A shared `conftest.py` sets `DATABASE_URL` before the app is imported.
- pytest refuses to start if `DATABASE_URL` points at any Supabase / Postgres host, even when set on purpose.
- Only `backend/scripts/live_*.py` may touch production. Postgres-specific behaviour is proven there.
- Never write to the old Mumbai project.

## 3. No outside services in unit tests
AI summary, speech synthesis, Hugging Face, and push notifications are always replaced with fakes in unit tests.
Real services are used only by live scripts.

## 4. Live scripts: real assertions, deadlines, guaranteed cleanup
1. **Every check is an assertion.** Never print "VERIFIED" / "PASSED" unless an assertion just proved it.
   A script without assertions is a demo, not a test.
2. **Wait for conditions, not time.** Poll until the condition holds or a deadline passes; no fixed `sleep` as a
   proof step. Report the measured time.
3. **Test data is tagged.** Titles start with `[ES-TEST <run-id>]`; use the narrowest audience available.
4. **Cleanup always runs**, also on failure (`try/finally`). Afterwards the script searches for its own
   `[ES-TEST <run-id>]` prefix and fails if anything is left in announcements, queue, repeat schedules,
   notifications, or audio files.
5. **Default proof goes through the backend API**, logging in with `ES_PASSWORD_ESDEV01` from `backend/.env`.
   Clicking through the live website (`https://echosphere-2jf.pages.dev/`) is additionally required only when the
   change touches website or app screens; the owner signs in once in the browser, Claude never types the password.

## 5. ESP32 proof is machine-checked
1. **When required:** any change touching the speaker queue, repeats, emergency handling, speech / audio, the
   speaker push socket or heartbeat, or the firmware. Screen-only changes need unit tests + live site, not the ESP32.
2. The live script opens the ESP32 serial port itself (`COM7`, 115200 baud) and owns it for the whole run; close
   any other serial monitor first.
3. It asserts on specific firmware log lines with deadlines (e.g. stream started, playback complete, paused within
   1 s, emergency preempts within 1 s, LCD shows `! EMERGENCY BROADCAST !`). Watching a monitor by eye is not proof.

## 6. App screens: overflow is tested
Every changed screen gets a Flutter widget test at 320 px width and at tablet width that fails on any overflow
(`RenderFlex overflowed`) error.

## 7. Tests run on every push
- A GitHub Actions workflow runs pytest and `flutter test` on each push to `main`.
- Claude runs the same tests locally before every push. A push with failing tests is not "done".

## 8. Existing tests follow these rules
Tests that break these rules are rewritten to them or deleted: empty test files are removed; unit tests move onto
the test database and fakes; old `backend/scripts/test_live_*` scripts are rebuilt on the shared live-test helper
or deleted if they were one-off.

## 9. Honest reporting
Report each layer on its own line, e.g. `unit ✓ · live backend ✓ · ESP32 ✗ not tested`, never a single "works".
A layer that was not run is reported as "not tested", never left out. Include the failing run before the change
and the passing run after it. A task is done only when every required layer passed.
