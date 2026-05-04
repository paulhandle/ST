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

# Project Re-Read Plan - 2026-05-01

Objective: Re-understand the current ST repository state after the COROS-first implementation work, including API/backend flows, CLI entry points, verification commands, and known risks.

- [x] Review existing task/dev logs, lessons, README, rules, and project docs.
- [x] Map repository structure, dependencies, app startup, database configuration, and ignored local artifacts.
- [x] Trace the FastAPI API surface, SQLAlchemy domain model, ingestion, assessment, plan generation, adjustment, and COROS sync flows.
- [x] Inspect the CLI/probe scripts and identify non-API entry points.
- [x] Run verification commands for current import/test health.
- [x] Add a review summary for future agents.

## Project Re-Read Review/Summary

Current shape: ST is a Python 3.11+ FastAPI + SQLAlchemy + SQLite backend for endurance training planning, now centered on a personal-use COROS-first full-marathon loop. `app/main.py` creates the API, creates tables on startup, and seeds training method definitions. `app/db.py` stores SQLite at repo-root `st.db` and `app/core/config.py` loads local `.env` automatically.

Primary API flow: create athlete -> connect COROS -> import COROS history -> run road-running assessment -> generate structured full-marathon plan -> confirm plan -> sync confirmed future workouts to COROS -> evaluate weekly adjustment. The main route file is `app/api/routes.py`; normalized models live in `app/models.py`; API contracts live in `app/schemas.py`.

Core services: `app/coros/automation.py` has fake and real COROS automation clients. Fake mode is deterministic and used by tests. Real mode logs in with COROS' MD5-password login API, reads activity/dashboard endpoints, maps running activities and metrics, and writes calendar workouts via `training/schedule/update` one workout per request. `app/ingestion/service.py` upserts activities and metric snapshots. `app/assessment/running.py` scores recent run history and goal feasibility. `app/planning/marathon.py` attempts LLM plan generation first, then falls back to a rule-based marathon plan. `app/coros/sync.py` decrypts stored credentials, logs into COROS, syncs confirmed future structured workouts, and records `ProviderSyncRecord` rows.

Secondary flows: legacy `/plans/generate`, `/devices/connect`, and `/plans/{id}/sync` still exist for generic marathon/trail/triathlon mock plans and Garmin/COROS mock adapter compatibility. `scripts/st_cli.py` is a separate CLI that bypasses FastAPI and directly performs setup, COROS import, plan generation, optional real COROS sync, and LLM-based check-ins. `scripts/probe_coros_training_hub.py`, `scripts/probe_coros_api.py`, and `scripts/analyze_coros_bundles.py` are local COROS reverse-engineering/probe tools that write ignored artifacts to `var/coros_probe/`.

Verification run on 2026-05-01:

- `uv run python -m py_compile app/models.py app/schemas.py app/api/routes.py app/coros/credentials.py app/coros/automation.py app/ingestion/service.py app/assessment/running.py app/planning/marathon.py app/planning/adjustment.py app/coros/sync.py app/planning/checkin.py app/planning/llm.py scripts/st_cli.py` passed.
- `uv run python -m unittest discover -s tests -v` passed: 2 tests ran successfully.

Current risks and gaps:

- Test runtime was 186 seconds because `generate_marathon_plan()` tried a real LLM call before falling back to rule-based generation. Tests set `COROS_AUTOMATION_MODE=fake`, but they do not disable LLM usage, and local `.env` can make unit tests depend on network timeouts.
- `scripts/st_cli.py` has a likely first-run bug: `_get_or_create_athlete()` uses `SportType.RUNNING`, but the enum currently has `MARATHON`, `TRAIL_RUNNING`, and `TRIATHLON` only.
- README says COROS sync is currently fake in the top-level product bullets and still lists real COROS selector work as future, while code/devlog indicate real direct-API ingestion and calendar sync are implemented. Documentation should be reconciled before treating README as source of truth.
- There is no migration layer; tests drop/create all tables against the configured SQLite database. Existing local `st.db` is operational state rather than a managed schema.
- Credential encryption is a personal-use stdlib stream/HMAC scheme with a default fallback secret if `ST_SECRET_KEY` is absent; acceptable for MVP but not production-grade.
- [x] Implement RealCorosAutomationClient.login() with MD5 + JSON POST (no Playwright required).
- [x] Implement RealCorosAutomationClient.fetch_history(): paginates last 90 days of running activities + dashboard metrics.
- [x] Map runScoreList type=1 duration directly as marathon race prediction (COROS-native value, no Riegel formula).
- [x] Improve probe_coros_api.py to capture auth token from account/query response and use context.request with accessToken header for direct API calls.
- [x] Verify end-to-end: 32 real activities imported, 6 metrics including 4:03:48 marathon prediction.
- [x] All tests pass (2/2).

Next:
- [x] Probe and implement /training/schedule/update (write endpoint) for real COROS calendar sync.
- [x] Replace rule-based marathon plan generation with LLM (OpenAI) with rule-based fallback.
- [x] Wire real mode into the API — `COROS_AUTOMATION_MODE=real` env var already routes to RealCorosAutomationClient via factory; documented in README.
- [x] Clean up datetime.utcnow() deprecation warnings — already resolved; all modules use datetime.now(UTC).
- [x] Add test coverage for real-mode sync path — tests/test_real_coros_client.py added (14 tests: login, fetch_history, sync_workouts with mocked urllib).

# LLM-Based Plan Generation

- [x] Add openai>=1.0 to pyproject.toml.
- [x] Add OPENAI_* keys to .env and .env.example.
- [x] Create app/planning/llm.py with generate_marathon_plan_llm().
- [x] Modify app/planning/marathon.py to use LLM with rule-based fallback.
- [x] Verify: 2/2 tests pass; LLM produces correct structured workouts with real API.

## LLM Plan Review/Summary

Created `app/planning/llm.py` which calls OpenAI (configurable base URL + model via .env) to generate a full periodized marathon training plan as structured JSON. The LLM receives the athlete's assessment data, race goal, available training days, and target paces; it returns a week-by-week plan with workout types, distances, paces, and RPE bands. `marathon.py` tries LLM first and falls back to the original rule-based generator on any exception, so tests and offline scenarios degrade gracefully. Verified end-to-end: LLM returned correct 4-workout weeks with proper types (easy_run, threshold, long_run, marathon_pace) and realistic distances.

# Skill Architecture Refactor (MVP+1) — Complete

Plan reference: `~/.claude/plans/golden-roaming-acorn.md`

- [x] Phase A: Define Skill / KB / Context contracts
- [x] Phase B: Build first Skill (`marathon_st_default`)
- [x] Phase C: Wire orchestrator + routes/CLI through Skill
- [x] Phase D: Move coros / devices / assessment / planning into new layout
- [x] Phase E: Update README, devlog, lessons

## Final layout

```
app/
├── core/        Platform contracts + orchestration
├── skills/      Methodologies (one directory per skill)
│   └── marathon_st_default/
├── kb/          Sport knowledge bases
├── tools/
│   ├── coros/
│   └── devices/
├── ingestion/
├── api/
├── training/    (legacy KB of method definitions, kept as building blocks)
├── models.py
└── schemas.py
```

## Verification

`uv run python -m unittest discover -s tests`: 2/2 pass in ~5 seconds.

`uv run python -c "from app.skills import list_skills; print([m.slug for m in list_skills()])"` →
`['marathon_st_default']`.

`/marathon/plans/generate` route behavior preserved end-to-end.

## Deferred to MVP+1.5

- Skill-creator chat flow: read user's COROS history + dialogue → distill methodology → write `app/skills/user_extracted/<slug>/`
- Probe COROS `/training/schedule/query` with historical date range to capture coach-prescribed past plans
- Second skill (e.g., 80/20 polarized) to validate skill-swap independence
- Second sport (half marathon) to validate sport-swap independence

---

# Block A — Backend API for Frontend (2026-05-02) — COMPLETE

Objective: Add REST endpoints required by the frontend: skill catalog, today/week views, workout feedback, skill regenerate, activity matching.

Verification: `uv run python -m unittest discover -s tests -v` — 19/19 pass.

---

# Block A1 — Aggregate Endpoints for Frontend Dashboard (2026-05-02) — COMPLETE

Objective: Add 7 aggregate/new endpoints and enrich 2 existing ones per `docs/api-frontend-contract.md`.

New endpoints:
- `GET /athletes/{id}/dashboard`
- `GET /plans/{id}/volume-curve`
- `GET /plans/{id}/regenerate-preview`
- `GET /plan-adjustments/{id}`
- `POST /plan-adjustments/{id}/apply`
- `POST /coach/message`
- `GET /coach/conversations/{athlete_id}`

Enhanced:
- `GET /athletes/{id}/history` (match_status + delta_summary)
- `GET /athletes/{id}/today` (yesterday + recovery_recommendation)

Files changed: `app/models.py`, `app/schemas.py`, `app/api/routes.py`, `tests/test_block_a1.py` (14 new tests).

Verification: `uv run python -m unittest discover -s tests -v` — 33/33 pass in 2.4s (independently verified 2026-05-02).

Bug fixed as side-effect: `_AvailabilityShim.unavailable_weekdays` was returning a list instead of a comma-string; fixed so regenerate-preview path through `_build_context` works.

Not committed — awaiting review.

---

# Frontend Scaffold — Next.js web/ (2026-05-02) — DONE, TESTS MISSING

Objective: Scaffold `web/` with Next.js 14 App Router + TypeScript + Tailwind + shadcn/ui + SWR matching the sketch wireframes.

Files created: `web/package.json`, `web/tsconfig.json`, `web/next.config.js`, `web/tailwind.config.ts`, `web/app/layout.tsx`, `web/app/(tabs)/layout.tsx`, four tab pages (dashboard/today/week/plan), all sub-components, `lib/api/client.ts`, `lib/api/types.ts`, SWR hooks.

Verification run:
- `pnpm type-check` — exit 0, no errors.
- `pnpm build` — exit 0, 9 pages compiled.
- `curl http://localhost:3000/dashboard` — HTTP 200 with dev server running.

**KNOWN DEBT — rules.md violation:**
- Iron Law 3: No automated tests exist for the frontend. This was not caught before implementation started.
- No plan was written to `tasks/todo.md` before implementation.

**Required follow-up (must complete before this task is "done"):**
- [ ] Write frontend tests (at minimum: route rendering, API hook mock, tab navigation).
- [ ] Choose test framework (Vitest + React Testing Library recommended for Next.js App Router).
- [ ] Write failing tests first, then verify they pass against current scaffold.

Out of scope for scaffold phase: E2E Playwright tests, visual regression, CI pipeline.

---

# Task: Commit Block A1 backend (2026-05-02) — COMPLETE

Objective: Commit verified Block A1 backend changes to git with atomic message.

Acceptance criteria:
- [x] `uv run python -m unittest discover -s tests -v` exits 0 immediately before commit
- [x] Commit message follows `feat(api): ...` pattern from repo history
- [x] `web/` directory excluded from this commit (separate frontend commit after tests pass)

Commit: e5f33bf — feat(api): add Block A1 aggregate endpoints for web frontend

---

# Task: Frontend tests — Vitest + RTL (2026-05-02) — COMPLETE

Objective: Add automated unit tests for the Next.js frontend to satisfy Iron Law 3.

Files added:
- `web/vitest.config.ts`, `web/vitest.setup.ts`
- `web/__tests__/lib.test.ts` — 5 pure helper tests
- `web/__tests__/hooks.test.ts` — 4 SWR URL tests
- `web/__tests__/components.test.tsx` — 5 component tests (PaceRangeBar zone logic, WorkoutSteps count, SkillChip name)

Acceptance criteria:
- [x] `pnpm test` exits 0
- [x] 14 tests pass in 1.05s (> 9 required minimum)
- [x] No snapshot tests
- [x] Tests run in < 30s
- [x] `pnpm type-check` exits 0 after adding test files

Independently verified 2026-05-02 before commit.

---

# Independent Verification Fixes (2026-05-02) — COMPLETE

Objective: Resolve high and medium priority issues found during independent code review.

High priority (source-of-truth inconsistency):
- [x] README updated to accurately reflect real COROS direct-API implementation (items 1, 4; `/coros/connect` description; `COROS_AUTOMATION_MODE` explanation).
- [x] README documents `ST_DATABASE_URL` env var.

Medium priority:
- [x] Test DB isolation: `app/core/config.py` now reads `ST_DATABASE_URL` env var (falls back to `st.db`). All 4 existing test files set `ST_DATABASE_URL=sqlite:///st_test.db` before app imports. `st_test.db` added to `.gitignore`.
- [x] Real COROS path test coverage: `tests/test_real_coros_client.py` added — 14 tests covering login (success/failure/network error/MD5/region), fetch_history (field mapping, pagination cutoff, metric extraction), sync_workouts (empty input, call count, idInPlan increment, failure handling, not-logged-in guard).

Verification: `uv run python -m unittest discover -s tests -v` → **47/47 pass in 2.2s**.

---

# Block B — Auth + Onboarding + Beginner Skill (2026-05-02) — COMPLETE

## Objective

Add multi-user auth (phone OTP → JWT), new-user onboarding wizard,
`running_beginner` skill as fallback, and Plan tab adjustment entry.

## Design decisions (confirmed 2026-05-02)

- User model: `User` (phone, jwt); `AthleteProfile` gains `user_id` FK; 1 user → N sports
- Auth: 30-day JWT, no refresh token (Method A); mock OTP returns code in response
- Onboarding: COROS-only path; self-report fallback when history < threshold
- Beginner skill: pure rule-based, RPE-only intensity, 1–3 runs/week
- Plan activation: preview → user confirms → activate
- Adjustments: accessible from Plan tab "待处理建议" section

## Files to change / add

### Backend
- `app/models.py` — add `User`, `OTPCode`; add `user_id` FK on `AthleteProfile`
- `app/core/auth.py` (NEW) — `create_access_token`, `decode_token`, `get_current_user` dependency
- `app/schemas.py` — add `SendOTPRequest/Response`, `VerifyOTPRequest/Response`, `UserOut`, `OnboardingStatusOut`
- `app/api/auth.py` (NEW) — `POST /auth/send-otp`, `POST /auth/verify-otp`, `GET /auth/me`
- `app/api/routes.py` — protect existing routes with `Depends(get_current_user)` where appropriate; add `GET /athletes/{id}/onboarding-status`
- `app/main.py` — include auth router
- `app/skills/running_beginner/` (NEW) — `spec.yaml`, `skill.md`, `skill.py`, `code/rules.py`
- `tests/test_auth.py` (NEW) — auth flow tests (TDD: write failing first)
- `tests/test_beginner_skill.py` (NEW) — skill generates valid PlanDraft (TDD)

### Frontend
- `web/app/login/page.tsx` (NEW) — phone input → OTP → verify
- `web/lib/auth.ts` (NEW) — JWT localStorage helpers, `isAuthenticated()`
- `web/lib/hooks/useAuth.ts` (NEW) — auth state hook
- `web/lib/api/client.ts` — add `Authorization` header from stored JWT
- `web/middleware.ts` (NEW) — redirect `/login` if no JWT
- `web/app/onboarding/` (NEW) — multi-step wizard (4 steps)
- `web/app/(tabs)/plan/page.tsx` — add "待处理调整" section
- `web/__tests__/auth.test.ts` (NEW) — login flow + redirect logic (TDD)

## Implementation order (each step independently verifiable)

### Step 1 — Backend auth foundation (TDD)
1. Write failing tests in `tests/test_auth.py`
2. Add `User` + `OTPCode` models, migrations-safe (create_all)
3. Implement `app/core/auth.py` (JWT utils)
4. Implement `app/api/auth.py` (3 endpoints)
5. Wire into `app/main.py`
6. Run tests → all pass

### Step 2 — Route protection
1. Add `get_current_user` dependency to athlete routes
2. Update existing tests to pass JWT header (or skip auth in test mode via env flag)
3. Run full suite → all pass

### Step 3 — `running_beginner` skill (TDD)
1. Write failing test: skill generates PlanDraft with ≥ 1 week, RPE-only intensity
2. Implement skill (spec.yaml + skill.py + rules.py)
3. Run test → pass

### Step 4 — Frontend auth + protected routes (TDD)
1. Write failing tests: login page renders, redirects when no JWT
2. Implement `web/app/login/page.tsx`, `web/lib/auth.ts`, `web/middleware.ts`
3. Update API client to send Authorization header
4. Run `pnpm test` → pass

### Step 5 — Onboarding wizard
1. Write failing test: wizard renders step 1
2. Implement 4-step wizard pages
3. Run test → pass

### Step 6 — Plan tab adjustment entry + beginner empty state
1. Add "待处理调整" section to plan page
2. Add "设定目标" CTA for empty state
3. Update component tests

## Verification commands

```bash
# Backend
uv run python -m unittest discover -s tests -v   # must stay green throughout

# Frontend
pnpm test          # vitest unit tests
pnpm type-check    # tsc --noEmit
pnpm build         # next build
```

## Acceptance criteria

- [ ] `POST /auth/send-otp` returns mock OTP code in dev mode
- [ ] `POST /auth/verify-otp` returns 30-day JWT on correct code
- [ ] All existing 47 backend tests still pass after route protection added
- [ ] `running_beginner` skill generates a valid PlanDraft for a user with no history
- [ ] Login page redirects to onboarding if new user, to dashboard if returning
- [ ] Onboarding: COROS connect → goal input → plan preview → confirm → dashboard
- [ ] Plan tab shows pending adjustment count when > 0
- [ ] `pnpm test` and `pnpm type-check` exit 0

## Out of scope

- Real SMS sending (Aliyun etc.)
- Refresh tokens / token revocation
- User A viewing User B's data
- GPX/FIT upload parser
- Push notifications

---

# Block C — Skills / Adjustment / Activities screens (2026-05-03)

## Objective

Build the three remaining frontend screens per `docs/api-frontend-contract.md`:
1. `/skills` + `/skills/[slug]` — skill 列表、方法论阅读器、切换确认对话框
2. `/adjustments/[id]` — 调整详情 + 接受/拒绝
3. `/activities` — 历史跑量列表

所有后端端点已在 Block A / A1 完成。本 block 纯前端工作。

## Files to change / add

### Frontend pages
- `web/app/skills/page.tsx` (NEW) — skill 列表，含当前 skill 标记和切换入口
- `web/app/skills/[slug]/page.tsx` (NEW) — skill.md 方法论阅读器
- `web/app/adjustments/[id]/page.tsx` (NEW) — 调整详情 + accept/reject
- `web/app/activities/page.tsx` (NEW) — 历史活动列表

### Frontend components
- `web/components/skills/SkillList.tsx` (NEW)
- `web/components/skills/SwitchSkillDialog.tsx` (NEW) — regenerate-preview + confirm
- `web/components/adjustments/AffectedWorkoutRow.tsx` (NEW)
- `web/components/activities/ActivityRow.tsx` (NEW)

### Tests (TDD — write failing first)
- `web/__tests__/blockC.test.tsx` (NEW) — component unit tests

### Docs
- `tasks/devlog.md` — Block C entry
- `README.md` — no new API endpoints, but update front-end routes table if needed

## Approach (TDD per step)

1. Write all failing tests in `web/__tests__/blockC.test.tsx`
2. Run `pnpm test` — confirm failure
3. Implement components + pages
4. Run `pnpm test` — confirm pass
5. `pnpm type-check` + `pnpm build`
6. Push branch → `gh pr create`

## Test commands

```bash
cd web && pnpm test        # must stay green
pnpm type-check
pnpm build
```

## Acceptance criteria

- [ ] `/skills` renders skill list, marks active skill, has "切换" button
- [ ] `/skills/[slug]` renders skill.md content (as preformatted text minimum)
- [ ] SwitchSkillDialog shows regenerate-preview counts before confirming
- [ ] `/adjustments/[id]` shows reason, recommendation, affected workout rows
- [ ] Accept button calls `POST /plan-adjustments/{id}/apply`, reject calls existing endpoint
- [ ] `/activities` shows activity list with match_status dot + delta_summary
- [ ] All components have unit tests covering key rendering behavior
- [ ] `pnpm test` exits 0, `pnpm build` exits 0

## Out of scope

- Real markdown rendering (use `<pre>` for skill.md — full MDX overkill for now)
- Pagination for activities (show last 50, single page)
- Push notifications for new adjustments

---

# Block D — Navigation + Backend Route Protection (2026-05-03)

## Objective

1. **导航**：让 `/skills`、`/activities` 从应用内可达；升级 settings 页面
2. **后端认证保护**：对 athlete/plan 核心路由加 `get_current_user` 依赖，防止未认证访问

## Files to change

### Frontend
- `web/app/(tabs)/layout.tsx` — 将 Settings 加入底部 tab 或 header 入口
- `web/app/settings/page.tsx` — 替换为完整 settings 页（skills 入口、activities 入口、COROS 状态）
- `web/app/(tabs)/dashboard/page.tsx` — header 加 settings 图标入口

### Backend
- `app/api/routes.py` — 对 athlete/plan/adjustment/coach 相关路由加 `Depends(get_current_user)`
- `tests/test_auth.py` — 补充受保护路由的 401 测试（TDD）

### Docs
- `tasks/devlog.md`
- `README.md` — 更新 API 表格标注哪些路由需要认证

## Acceptance criteria

- [ ] Settings 页面可从 dashboard header 进入
- [ ] Settings 页面有 "Skill 方法论" 入口（→ /skills）和 "历史活动" 入口（→ /activities）
- [ ] `GET /athletes/{id}` 等核心路由未携带 token 返回 401
- [ ] 现有 71 个后端测试仍全部通过（测试文件需传入有效 token）
- [ ] 50 个前端测试仍全部通过
- [ ] `pnpm build` 通过

## Out of scope

- 细粒度权限（用户只能访问自己的数据）—— 留待用户规模增长后再做
- Token 刷新 / 登出接口
