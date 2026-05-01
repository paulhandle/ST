# Project Reading Plan

- [x] Review repository README, config, tests, and source layout.
- [x] Identify application entry points, domain model, API surface, and data flow.
- [x] Note verification commands and any current risks or gaps.
- [x] Add a completion summary for future agents.

## Review/Summary

Objective: Read the ST backend project and summarize its architecture, behavior, verification commands, and current risks.

Architecture: This is a FastAPI + SQLAlchemy + SQLite MVP for endurance-athlete training planning. `app/main.py` creates the FastAPI app, initializes tables at startup, and seeds training method definitions. `app/api/routes.py` exposes athlete creation, training method/mode listing, plan generation/listing/status update, device account connection, and mock device sync endpoints.

Domain model: `app/models.py` defines enums for sport, athlete level, training goal, training mode, plan status, device type, and sync status. Core tables are training methods, athlete profiles, training plans, training sessions, device accounts, and sync tasks.

Training flow: `app/training/knowledge_base.py` stores seeded training-method data and mode recommendation rules. `app/training/engine.py` generates week/day session templates for marathon, trail running, and triathlon using a simple base/build/taper phase split.

Device flow: `app/devices/service.py` chooses a Garmin or COROS adapter and writes a sync task. `app/devices/garmin.py` and `app/devices/coros.py` are mock adapters that return generated remote plan IDs.

Verification: `python3 -m unittest -v` reports 0 tests because default discovery did not find the `tests/` directory. `python3 -m unittest discover -s tests -v` finds 1 test but fails during import because `app/models.py:75` has invalid syntax. `python3 -m py_compile app/models.py` confirms the same syntax error.

Current risks: The project is not runnable until `app/models.py:75` is repaired. The existing test expects `/athletes/{id}/history/import`, `/athletes/{id}/history`, and `/athletes/{id}/assessment`, but those routes and related models/schemas are not present in the inspected source. The available `python3` is `/usr/bin/python3` version 3.9.6 while `pyproject.toml` requires Python 3.11+.

# Requirements Clarification - COROS-first MVP

- [x] Capture confirmed product direction from the user.
- [x] Confirm COROS automation, credential handling, and compliance boundaries.
- [x] Confirm first-stage scope and explicit non-goals.
- [x] Confirm training assessment and plan-adjustment product behavior.
- [ ] Convert confirmed decisions into a formal PRD/technical design after clarification.

## Current Confirmed Direction

The first product stage is COROS-first and road-running-first. It should read user history from COROS automatically, analyze road-running ability, generate structured running plans, and automatically sync confirmed plans or plan changes back into COROS.

Confirmed user preferences:

- COROS support must cover both historical data ingestion and plan synchronization.
- Historical import should be automatic rather than relying on a manual export/upload flow.
- Web automation/hack approaches are acceptable for discussion, including recording COROS credentials, but the exact safety and compliance boundary still needs confirmation.
- Daily health data can be included if accessible from the COROS web experience.
- First sport focus is road running; triathlon should follow after road running works.
- Plan changes should be suggestions first, then imported/synced only after user confirmation.
- Internal plan model should be structured workouts, not free-text plans.
- Coach view is future roadmap, not first-stage scope.
- COROS automatic sync is a core value, especially after user confirms a plan or adjustment.

Additional confirmed constraints:

- First stage is a personal-use product, not a public commercial launch.
- COROS integration should directly use username/password automation rather than coach/team mode or plugin-first flow.
- Credentials can be stored with simple encryption for now.
- Compliance disclosure is not urgent for this personal-use phase.
- Data target is all accessible COROS data from the web experience, including activity, performance, fatigue, daily health, and feedback where available.
- MVP sync success means confirmed future workouts appear in the COROS calendar and can reach the app/watch through normal COROS behavior.
- Existing COROS calendar items do not block sync because COROS allows multiple tasks on the same day.
- First plan target is full marathon road running.
- The system is allowed to reject unsafe or unrealistic goals.
- Monitoring runs continuously after each imported activity, but formal plan-adjustment suggestions are weekly unless severe fatigue/pain is detected.
- User feedback may be available through COROS workout voice/text feedback; the product should ingest it where possible.
- The underlying model should support triathlon-ready multi-discipline structure even while the first UI/algorithm focus is road running.

Final clarified product decisions:

- Marathon goals should support user-specific targets such as "sub-4:00" as well as broader completion goals.
- Training duration is user-selectable; the product should warn or reject if the target window is too short for the current ability and goal.
- The user can provide available weekly training days and constraints, but the system should recommend a safer range and warn when the user's chosen volume is too high or too low.
- COROS automation should support both manual one-click sync/import and scheduled background import/sync.
- If COROS login or page automation fails due to page changes, MFA, CAPTCHA, or risk controls, the product can ask the user to intervene rather than bypassing those controls.

# PRD and Technical Design Plan

- [x] Write PRD for personal-use COROS-first full-marathon MVP.
- [x] Write technical design for COROS automation, data ingestion, assessment, planning, adjustment, and sync.
- [x] Document acceptance criteria, non-goals, and implementation sequencing.
- [x] Review documents for unresolved assumptions and update dev log.

## PRD/Technical Design Review

Created `docs/prd-coros-marathon-mvp.md` and `docs/technical-design-coros-marathon-mvp.md`.

The PRD captures the personal-use COROS-first full-marathon MVP, including automatic COROS import, full-marathon goal evaluation, structured plan generation, user-confirmed COROS calendar sync, monitoring, weekly adjustment suggestions, and explicit non-goals.

The technical design defines subsystem boundaries for COROS automation, ingestion, assessment, planning, adjustment, and sync. It also proposes normalized models for activities, metric snapshots, race goals, availability, structured workouts, workout steps, and provider sync records. The implementation sequence starts with repairing the existing `app/models.py` syntax error and establishing a Python 3.11+ environment.

Verification performed: reviewed the generated documents with `sed` and checked line counts with `wc -l`. No application code was changed, so tests were not rerun during this documentation-only step.

# Implementation Plan - COROS-First Marathon MVP Backend

Objective: Turn the PRD and technical design into a runnable backend MVP while keeping existing API compatibility.

Likely files to change:

- `app/models.py`
- `app/schemas.py`
- `app/api/routes.py`
- new service modules under `app/coros/`, `app/ingestion/`, `app/assessment/`, and `app/planning/`
- `tests/`
- `README.md`
- `tasks/devlog.md`

Approach:

- [x] Repair the existing `app/models.py` syntax error.
- [x] Add normalized activity, metric, race goal, availability, structured workout, workout step, sync record, and adjustment models.
- [x] Add schemas for COROS connect/import/status, history, assessment, marathon goals, plan generation, plan confirmation, sync, and adjustment.
- [x] Implement simple encrypted credential storage using stdlib only.
- [x] Implement a fake COROS automation adapter that exercises the complete import/sync flow without requiring live COROS credentials.
- [x] Implement ingestion upsert and history endpoints.
- [x] Implement road-running assessment and full-marathon goal feasibility.
- [x] Implement structured full-marathon plan generation.
- [x] Implement plan confirmation, sync record creation, and weekly adjustment recommendation.
- [x] Preserve existing `/devices/connect`, `/plans/generate`, `/plans/{id}/sync`, and history/assessment test compatibility.
- [x] Add tests for the new MVP flow.
- [x] Update README with the new COROS-first MVP flow and verification commands.
- [x] Run targeted and full tests.

Acceptance criteria:

- Existing `tests/test_history_assessment.py` passes.
- New COROS marathon MVP workflow test passes.
- `python3 -m py_compile` succeeds for touched app modules.
- API can connect a COROS credential, import fake COROS history, assess marathon readiness, generate a structured full-marathon plan, confirm it, sync it, and create an adjustment suggestion.

Out of scope for this implementation pass:

- Real COROS browser selectors and production page automation, because no COROS account/session/page map is available in this environment.
- CAPTCHA/MFA bypass.
- Public-commercial compliance packaging.

## Implementation Review/Summary

Implemented a runnable backend MVP for the COROS-first full-marathon flow. The app now supports fake COROS credential connection, deterministic fake COROS history import, normalized activity and metric storage, road-running assessment, full-marathon goal feasibility, structured full-marathon plan generation, plan confirmation, fake COROS calendar sync records, and adjustment recommendation.

The old history/assessment test compatibility is preserved. The real COROS browser automation remains intentionally out of scope until a real account/session and page map are available.

Verification:

- `uv run python -m py_compile app/models.py app/schemas.py app/api/routes.py app/coros/credentials.py app/coros/automation.py app/ingestion/service.py app/assessment/running.py app/planning/marathon.py app/planning/adjustment.py app/coros/sync.py`
- `uv run python -m unittest discover -s tests -v`

Both commands passed before final review. Python 3.14 emitted deprecation warnings for `datetime.utcnow()` and a sqlite resource warning from the test process; these do not fail the suite but should be cleaned up in a later hardening pass.

# Real COROS Probe Plan

Objective: Prepare the codebase for real COROS Training Hub probing with user-provided credentials in local `.env`, without putting credentials in chat or source control.

- [x] Add `.env` ignore and `.env.example` for local COROS credentials and automation mode.
- [x] Add a small local env loader in config so scripts and app code can read `.env` without adding a dependency.
- [x] Introduce a COROS automation client protocol/factory so tests keep using fake automation while real probing can use Playwright.
- [x] Add a Playwright probe script that logs into COROS Training Hub and writes sanitized local artifacts under `var/coros_probe/`.
- [x] Update README with the `.env` keys and probe command.
- [x] Run compile/tests after refactor.

Acceptance criteria:

- Credentials are only read from environment or local `.env`.
- `.env` and probe artifacts are ignored by git.
- Existing fake COROS tests continue to pass.
- The real probe fails clearly if Playwright is not installed or credentials are missing.

## Real COROS Probe Review/Summary

Added local `.env` support, `.env.example`, git ignores for `.env` and `var/`, a COROS automation protocol/factory, and `scripts/probe_coros_training_hub.py`. The API remains on fake COROS automation by default; setting `COROS_AUTOMATION_MODE=real` makes the API fail clearly until the probe produces a real page map. Tests force fake mode so local credentials do not affect CI-style verification.

Verification:

- `uv run python -m py_compile app/core/config.py app/coros/automation.py app/api/routes.py app/coros/sync.py scripts/probe_coros_training_hub.py`
- `uv run python -m unittest discover -s tests -v`

Both passed. Playwright Python package was installed by `uv`; Chromium browser installation may still be needed before running the real probe.

## COROS Probe Run Result

- [x] Install Playwright Chromium.
- [x] Load COROS Training Hub login page.
- [x] Identify username/password input placeholders.
- [x] Identify required privacy-policy checkbox behavior.
- [x] Identify login endpoint: `https://teamapi.coros.com/account/login`.
- [x] Reach authenticated Training Hub dashboard.
- [x] Map initial activity/history, dashboard, plan, and schedule API candidates from live requests and bundles.

Authenticated probe findings:

- Login success response: `result=0000` from `https://teamapi.coros.com/account/login`.
- Region redirect target: `https://trainingcn.coros.com/admin/views/dash-board`.
- Dashboard data is visible in page text and includes running ability, training load, recent workouts, threshold zones, personal records, race predictions, and HRV.
- Candidate CN API host: `https://teamcnapi.coros.com`.
- Observed/candidate endpoints include `/dashboard/query`, `/dashboard/detail/query`, `/profile/private/query`, `/team/user/teamlist`, `/activity/query`, `/activity/detail/filter`, `/training/schedule/query`, `/training/schedule/update`, `/training/plan/query`, `/training/plan/add`, and `/training/plan/update`.

Next implementation target:

- [x] Add an authenticated API probe that logs in, captures the COROS token/cookies in memory, and calls read-only dashboard/activity/schedule endpoints with sanitized response summaries.
- [x] Use read-only API probes to define the real COROS ingestion parser before attempting plan write/sync.

# Read-Only COROS API Probe Plan

Objective: Capture sanitized response structures from real COROS read-only endpoints after authenticated login, without persisting access tokens or calling write/update endpoints.

- [x] Add `scripts/probe_coros_api.py`.
- [x] Reuse Playwright login and authenticated browser context.
- [x] Visit dashboard, activity list, and schedule pages to trigger read-only API calls.
- [x] Capture sanitized `teamcnapi.coros.com` JSON responses for dashboard/activity/schedule endpoints.
- [x] Save endpoint summaries under ignored `var/coros_probe/`.
- [x] Run compile/tests.

Non-goals:

- Do not call `/training/schedule/update`, `/training/plan/add`, or any write endpoint.
- Do not save raw token/cookie values.
- Do not save full personal activity payloads beyond sanitized structural samples.

# Real COROS Ingestion Implementation

Objective: Replace the fake COROS automation stub with a working direct-API implementation.

- [x] Confirm COROS login API: POST teamapi.coros.com/account/login with MD5-hashed password, returns accessToken + regionId.
- [x] Confirm activity list endpoint: GET teamcnapi.coros.com/activity/query with accessToken header, sportType=100 for running.
- [x] Decode field units: distance=meters, totalTime=seconds, startTime=unix-seconds, startTimezone=15-min increments, adjustedPace=sec/km.
- [x] Confirm dashboard metrics: lthr, ltsp, aerobicEnduranceScore, staminaLevel, recoveryPct, runScoreList (type=1→marathon prediction).
- [x] Implement RealCorosAutomationClient.login() with MD5 + JSON POST (no Playwright required).
- [x] Implement RealCorosAutomationClient.fetch_history(): paginates last 90 days of running activities + dashboard metrics.
- [x] Map runScoreList type=1 duration directly as marathon race prediction (COROS-native value, no Riegel formula).
- [x] Improve probe_coros_api.py to capture auth token from account/query response and use context.request with accessToken header for direct API calls.
- [x] Verify end-to-end: 32 real activities imported, 6 metrics including 4:03:48 marathon prediction.
- [x] All tests pass (2/2).

Next:
- [x] Probe and implement /training/schedule/update (write endpoint) for real COROS calendar sync.
- [ ] Wire real mode into the API (currently only used via RealCorosAutomationClient directly; the factory uses fake mode by default).
- [ ] Clean up datetime.utcnow() deprecation warnings across routes, sync, planning modules.
- [ ] Add test coverage for real-mode sync path (currently all tests force fake mode).
