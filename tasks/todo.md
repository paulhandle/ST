# COROS Full Sync

**Branch:** `feat/coros-full-sync`

## Brand Icon: P Squared App Mark

Objective: add a real app/browser icon using the compact `P²` mark, with italic `P` and right-superscript `2`, so constrained surfaces can use the product icon instead of the full name.

1. [x] Add `web/public/icons/pp-icon.svg` with the black/orange brand palette.
2. [x] Register the icon in `web/public/manifest.json` and Next metadata.
3. [x] Add a manifest regression test.
4. [x] Verify:
   - `cd web && pnpm test __tests__/manifest.test.ts __tests__/components.test.tsx` -> pass.
   - `cd web && pnpm build` -> pass.
   - `cd web && pnpm type-check` -> pass after build regenerated `.next/types`.
   - `git diff --check` -> pass.

## Bugfix: First-Run Skill Selection And Plan Creation

Objective: fix the first-login onboarding flow so configuring COROS/goal does not leave the Plan tab empty. Onboarding must expose the available skills, require a skill choice, generate the matching training plan, confirm it, and then route the user into the app with an active plan.

1. [x] Read current onboarding and plan generation contracts:
   - [x] Confirm onboarding currently creates an athlete and optional COROS connection but does not call `/marathon/plans/generate`.
   - [x] Confirm `/marathon/plans/generate` accepts `skill_slug` and `/plans/{plan_id}/confirm` activates generated workouts.

2. [x] Update onboarding UX:
   - [x] Add skill loading and skill selection as a first-run step.
   - [x] Show the chosen skill in confirmation.
   - [x] Keep COROS connection failure non-blocking, but make plan generation failure blocking and visible.

3. [x] Update onboarding submit behavior:
   - [x] Create athlete.
   - [x] Optionally connect COROS.
   - [x] Create marathon goal when a race date/target is provided.
   - [x] Generate plan with selected `skill_slug`, target, weeks, and availability.
   - [x] Confirm the generated plan before routing to `/plan`.

4. [x] Verification:
   - [x] Add frontend regression tests proving onboarding fetches skills, posts plan generation with selected skill, confirms the plan, and routes to `/plan`.
   - [x] Run focused onboarding tests and frontend type-check.
   - [x] Update `tasks/devlog.md` with why/how/result.

Review:
- First-run onboarding now has five steps: COROS, goal, availability, skill, and confirmation.
- On finish, onboarding creates the athlete, saves the returned athlete id locally, optionally connects COROS, creates a marathon goal when goal data exists, generates a plan with the selected skill, confirms that plan, and routes to `/plan`.
- The web app now reads the saved athlete id instead of assuming athlete `1` for dashboard, today, calendar, workout, activity detail, COROS settings, coach sheet, and manual plan generation surfaces.
- Verification passed:
  - `cd web && pnpm test` -> 82/82 pass.
  - `cd web && pnpm type-check` -> pass.
  - `cd web && pnpm build` -> pass.
  - `git diff --check` -> pass.

## Objective

Replace the current one-shot COROS history import with a real full-sync flow: users enter COROS credentials in Settings, the backend logs into COROS, imports all available activity data and raw detail payloads, and the frontend shows progress for the long-running sync.

## Context

- This is stacked on top of PR #5 (`feat/i18n-sms-coros-hardening`) because it uses the new `/settings/coros` page.
- Current local default `COROS_AUTOMATION_MODE=fake` produces synthetic history, which is confusing for real account testing.
- Current real importer only reads `/activity/query`, filters to running sport types, and limits history to 365 days.
- User wants COROS username/password entered only in the app settings page, not stored in `.env`.
- User wants all available COROS sport/activity data and raw information from COROS pages/APIs, not only normalized activity summaries.

## Implementation Plan

1. [x] Remove COROS username/password from environment docs/examples:
   - [x] Delete `COROS_USERNAME` / `COROS_PASSWORD` from `.env.example`.
   - [x] Remove local `COROS_USERNAME` / `COROS_PASSWORD` from `.env` without printing values.
   - [x] Update README to say credentials are entered through Settings and stored encrypted.
   - [x] Keep `COROS_AUTOMATION_MODE` for fake/real runtime selection.

2. [x] Backend full-sync persistence:
   - [x] Add raw COROS/provider record storage for endpoint/page payloads.
   - [x] Add sync job/event tracking models for long-running imports.
   - [x] Add schemas for job status, progress events, and raw record counts.

3. [x] Backend full-sync APIs:
   - [x] Add `POST /coros/sync/start` to start a background full sync for an athlete.
   - [x] Add `GET /coros/sync/jobs/{id}` for polling job progress.
   - [x] Add `GET /coros/sync/jobs/{id}/events` for recent phase/event log.
   - [x] Keep existing `/coros/import` compatible or route it to a short refresh if needed.

4. [x] Real COROS client expansion:
   - [x] Stop filtering to running-only activity types.
   - [x] Stop limiting the first full sync to 365 days.
   - [x] Page through all available `/activity/query` results.
   - [x] Fetch per-activity detail payloads from the discovered detail endpoint(s).
   - [x] Capture dashboard/profile/schedule/plan raw payloads where safely available.
   - [x] Preserve normalized activity fields for dashboard/assessment while storing full raw payloads.

5. [x] Frontend progress UX:
   - [x] Change `/settings/coros` from one-shot import button to a full-sync progress flow.
   - [x] Show phases: login, list pages, activity details, metrics/raw pages, save/complete.
   - [x] Show processed/total/imported/updated/failed counts and recent event log.
   - [x] Make fake/test data visually explicit in fake mode, or avoid starting fake full sync for real testing.

6. [x] Tests and verification:
   - [x] Backend tests for job lifecycle, duplicate job handling, raw record upsert, and detail failures.
   - [x] Real client unit tests for all-sport/all-pages/detail capture using mocked COROS responses.
   - [x] Frontend tests for Settings progress states.
   - [x] Run backend unittest, frontend test/type-check/build, and `git diff --check`.

## Review / Summary

- COROS account credentials are no longer in `.env` or `.env.example`; app setup now stores them through Settings with encrypted DB storage.
- Added persisted full-sync jobs, progress events, and raw provider records, with Alembic migration `4b7d0f8e2c6a_coros_full_sync_tables.py`.
- Added full-sync APIs:
  - `POST /coros/sync/start`
  - `GET /coros/sync/jobs/{id}`
  - `GET /coros/sync/jobs/{id}/events`
- Expanded real COROS full sync to page all activities, include all sport types, attempt per-activity detail capture, preserve list data when detail fails, and capture dashboard/profile/team/schedule/plan raw payloads where available.
- Reworked `/settings/coros` to show fake/real mode, start full sync, poll progress, and display counters/events.
- Tightened legacy `/coros/import` so it no longer auto-creates a fake COROS account and instead requires encrypted Settings credentials.
- Verification passed:
  - `uv run python -m unittest discover -s tests -v` -> 96/96 pass.
  - `cd web && pnpm test` -> 76/76 pass.
  - `cd web && pnpm type-check` -> pass.
  - `cd web && pnpm build` -> pass.
  - `uv run python -m py_compile ... scripts/st_cli.py` -> pass.
  - `git diff --check` -> pass.

## Out Of Scope

- Reworking generated workout sync back to COROS calendar.
- Official COROS API partnership.
- CAPTCHA/MFA bypass.
- A production-grade distributed task queue; local MVP can use FastAPI background tasks and DB-persisted progress.

## Follow-up: Real COROS Testing Loop

Objective: make it clear how to run real COROS sync locally, make Settings navigation obvious, and provide standalone scripts to inspect whether the fetched COROS data is complete enough.

1. [x] Add explicit Settings navigation:
   - [x] Replace history-dependent back behavior on `/settings/coros` with a deterministic link to `/settings`.
   - [x] Add an obvious close/back affordance.

2. [x] Document real sync configuration:
   - [x] Explain that `COROS_AUTOMATION_MODE=real` enables real API calls.
   - [x] Explain credentials are entered in Settings or prompted by the standalone probe, not stored in `.env`.
   - [x] List exactly what DB tables/fields store normalized activities, metrics, raw provider payloads, sync jobs, and events.

3. [x] Add standalone testing scripts:
   - [x] Add a real COROS fetch probe that writes complete fetched JSON under ignored `var/`.
   - [x] Add a DB inspection script that summarizes stored COROS activities, metrics, raw records, jobs, and events.
   - [x] Ensure scripts do not print or persist passwords outside encrypted DB/app flow.

4. [x] Verify:
   - [x] Run script help/compile checks.
   - [x] Run backend/frontend targeted tests.
   - [x] Run `git diff --check`.

Review:
- Settings > COROS now has deterministic `/settings` back and close links.
- README documents real sync configuration, standalone probe commands, import-from-probe command, detail endpoint probe, and exact DB storage tables.
- Real fetch was run from encrypted DB credentials for athlete 1. Artifact: `var/coros_real_sync/full-fetch-1-20260506-015256.json`.
- Real fetch summary: 694 activities, 6 metrics, 39 raw records, 2022-11-22 through 2026-05-05, running/cycling/swimming/strength/other included.
- Imported real fetch into local DB as sync job 3. Latest DB inspect reports 694 real-like activities and 96 fake-like activities for athlete 1.
- Current gap: COROS activity detail endpoint still returns service/parameter errors for tested request variants, so per-activity track/detail payloads are not solved yet.

## Follow-up: Real-Only Local Data

Objective: remove old fake COROS records from the local test database, make real mode the default runtime path, and export one real activity case for manual COROS field validation.

1. [ ] Add repeatable cleanup/export tooling:
   - [x] Add a local DB cleanup script that deletes fake COROS activities, fake metrics, fake raw records, fake sync jobs/events, and fake device accounts while preserving real imports.
   - [x] Add a real activity sample export script that writes normalized DB fields plus raw COROS payload JSON under ignored `var/coros_real_sync/`.

2. [ ] Switch runtime defaults to real data:
   - [x] Change code and `.env.example` so omitted `COROS_AUTOMATION_MODE` resolves to `real`.
   - [x] Update README wording so fake mode is explicit test-only behavior.

3. [ ] Clean local database and pick one real sample:
   - [x] Run the cleanup script for athlete 1.
   - [x] Verify fake activity/raw-record counts are zero.
   - [x] Export one recent real COROS activity sample for user review.

4. [x] Verify and document:
   - [x] Run targeted backend tests and script compile checks.
   - [x] Run `git diff --check`.
   - [x] Update `tasks/devlog.md` with why/how/result and final counts.

Review:
- COROS runtime now defaults to real mode; fake mode requires explicit `COROS_AUTOMATION_MODE=fake`.
- Added repeatable cleanup and sample export scripts:
  - `scripts/coros_cleanup_fake_data.py`
  - `scripts/coros_export_activity_sample.py`
- Local athlete 1 cleanup removed 96 fake activities, 96 fake laps, 9 fake metrics, 1 fake raw record, 3 fake sync events, 1 fake sync job, and 1 fake device account.
- Fresh DB inspect reports 694 COROS activities, 694 real-like numeric COROS ids, 0 fake-like activities, and 0 fake raw records.
- Exported real sample `477263761401479169` to `var/coros_real_sync/activity-sample-477263761401479169.json`.
- Verification passed:
  - `.venv/bin/python -m py_compile scripts/coros_cleanup_fake_data.py scripts/coros_export_activity_sample.py app/tools/coros/automation.py app/api/routes.py`
  - `.venv/bin/python -m unittest tests.test_coros_full_sync tests.test_real_coros_client -v`
  - `git diff --check`

## Follow-up: COROS Export File Capture

Objective: replace incomplete activity-detail API guessing with the Training Hub export-file path, because the COROS UI exposes `.fit`, `.tcx`, `.gpx`, `.kml`, and `.csv` exports that include segment and GPS-level data.

1. [ ] Discover Training Hub export request shape:
   - [x] Confirm the frontend exposes `POST /activity/detail/download`.
   - [x] Confirm `activityExportFileTypes_prod.json` allows export types `[4,3,1,2,0]` for running `sportType=100`.
   - [x] Locate the `/activity-detail` frontend chunk and exact POST body fields.

2. [ ] Add standalone export probe:
   - [x] Use the encrypted DB COROS account for athlete 1.
   - [x] Download export files for activity `477263761401479169`, starting with `.fit` and `.tcx`/`.gpx`.
   - [x] Save files and a sanitized summary under ignored `var/coros_real_sync/`.

3. [ ] Parse and compare one export:
   - [x] Extract sample counts/fields from the downloaded file.
   - [x] Compare summary distance/duration/start time against the existing DB row.
   - [x] Document which format should become the canonical detailed ingest source.

4. [x] Verify and document:
   - [x] Run script compile checks and targeted backend tests.
   - [x] Update `tasks/devlog.md` and `tasks/lessons.md`.

Review:
- Training Hub frontend confirmed the export endpoint is `POST /activity/detail/download` with query params `labelId`, `sportType`, and `fileType`.
- Added `scripts/coros_export_file_probe.py`.
- Downloaded real export files for activity `477263761401479169`:
  - `var/coros_real_sync/exports/477263761401479169/477263761401479169.fit`
  - `var/coros_real_sync/exports/477263761401479169/477263761401479169.tcx`
  - `var/coros_real_sync/exports/477263761401479169/477263761401479169.gpx`
  - `var/coros_real_sync/exports/477263761401479169/477263761401479169.csv`
- Export summary: `var/coros_real_sync/exports/477263761401479169/export-summary-20260506-045613.json`.
- GPX has 4091 trackpoints; TCX has 4102 trackpoints and 11 laps; CSV has 12 split rows.
- Recommendation: archive `.fit` as canonical raw export, and parse `.tcx` or `.gpx` first for MVP detail ingestion because they are easy to inspect with standard XML tooling.
- Verification passed:
  - `.venv/bin/python -m py_compile scripts/coros_export_file_probe.py scripts/coros_cleanup_fake_data.py scripts/coros_export_activity_sample.py`
  - `git diff --check`

## Design: Activity Detail And Navigation

Objective: redesign the activity detail experience around exported COROS data and simplify the main tab structure by replacing the low-value Week tab with a personal/settings tab.

1. [x] Activity detail information architecture:
   - [x] Header: sport, name/location, date/time, device, duration, distance, training load, average/max heart rate.
   - [x] Map-first route view: GPS polyline from detailed export, start/end markers, distance/time scrubber.
   - [x] Metric timeline: heart rate, pace/speed, cadence, elevation, with synchronized hover/scrub against the map.
   - [x] Splits/laps table: per-km or lap rows with pace, moving pace, HR, cadence, stride length, elevation gain/loss, calories.
   - [x] Training interpretation: effort distribution, HR drift/decoupling, pace consistency, finishing surge/fade, unusual spikes/missing sensor notes.
   - [x] Raw/source section: show source file type, download timestamp, trackpoint/lap counts, and parsing warnings for debugging.

2. [x] Data-source decision:
   - [x] Prefer one export file per activity, not all formats.
   - [x] Choose production canonical raw format.
   - [x] Choose MVP parser format if different from canonical raw.

3. [x] Tab navigation redesign:
   - [x] Remove the Week tab from primary navigation for now.
   - [x] Add a Me tab that contains profile, device sync status, COROS settings, language, account, and debug/import tools.
   - [x] Keep Plans focused on plan generation/current cycle rather than weekly browsing.

Design decision:
- Production sync should download only `.fit` per activity as the canonical raw archive. It is the smallest file in the sample (`169KB` vs `1.2MB` GPX and `1.9MB` TCX) and is likely the richest sensor format.
- Detailed ingestion should parse `.fit` directly with a backend FIT parser; TCX/GPX remain debugging references only.
- Do not download `.csv` for ingestion. It is useful for manual split review but loses per-second GPS/timeline detail.
- Do not download `.gpx` if TCX is available. GPX is excellent for route visualization and has extensions for HR/cadence/speed, but TCX also carries laps more naturally for training analysis.

## Implementation: FIT-Based Activity Detail

Objective: implement the final COROS detail architecture: one `.fit` export per activity, structured GPS/time-series/lap storage, a detail API, a data-rich activity detail page, and bottom navigation with a Me tab instead of Week.

1. [x] Backend dependencies and parser:
   - [x] Add a FIT parser dependency to `pyproject.toml` and lock it.
   - [x] Implement `app/tools/coros/fit_parser.py` to parse `.fit` into samples, laps, summary, and warnings.
   - [x] Verify parser against `var/coros_real_sync/exports/477263761401479169/477263761401479169.fit`.

2. [x] Persistence:
   - [x] Add activity detail storage models for exported raw file metadata, GPS/time-series samples, and detailed laps.
   - [x] Add Alembic migration.
   - [x] Import the existing sample FIT into local DB for activity `477263761401479169`.

3. [x] COROS sync integration:
   - [x] Add real client method to request `POST /activity/detail/download` for `fileType=4`.
   - [x] Update full sync to download and parse `.fit` for activities, with progress and failure accounting.
   - [x] Avoid downloading `.tcx/.gpx/.csv` in normal sync.

4. [x] Activity detail API:
   - [x] Add `GET /athletes/{athlete_id}/activities/{activity_id}` returning summary, samples, laps, source metadata, and interpretation.
   - [x] Include compact/downsampled samples by default for frontend performance while preserving full samples in DB.

5. [x] Frontend activity detail:
   - [x] Link Activities rows to `/activities/{activity_id}` when an activity exists, not `/workouts/{date}`.
   - [x] Add `/activities/[id]` page with summary, route visualization, synchronized metric charts, splits/laps, training interpretation, and source/debug section.
   - [x] Use GPS coordinates in the route view; no fake map data.

6. [x] Navigation:
   - [x] Remove Week from primary tab bar.
   - [x] Add `/me` tab and move Settings entry points there.

7. [x] Verification and docs:
   - [x] Backend parser tests and activity detail API tests.
   - [x] Frontend render/type tests for activity detail and tab navigation.
   - [x] Update README, `tasks/devlog.md`, and `tasks/lessons.md`.
   - [x] Run backend/frontend targeted tests, type-check/build as needed, and `git diff --check`.

Review:
- Production COROS activity detail sync now downloads only FIT exports (`fileType=4`) per activity and parses them into stored raw FIT bytes, GPS/time-series samples, and detailed laps.
- The previous `/activity/detail/filter` guessing path is no longer part of full-history discovery; full sync discovers activities from `/activity/query` and uses Training Hub export files for detail.
- Local sample `477263761401479169` was imported into activity detail tables as activity id `145`: 173080 FIT bytes, 4092 samples, 11 laps, 0 parser warnings.
- Frontend activity rows now open `/activities/{activity_id}` for real activities, while planned rows keep `/workouts/{date}`.
- Added activity detail UI with real GPS route SVG, metric charts, laps, training interpretation, and source metadata. Removed Week from primary tabs and added Me.
- Local Alembic upgrade against existing `st.db` could not run because the DB has tables but no version stamp (`otp_codes already exists`). For local review, `Base.metadata.create_all()` was used to create only missing new tables; the Alembic migration remains for clean/prod databases.
