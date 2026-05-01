# Dev Log

## 2026-04-30 - Project reading setup

Why: The project instructions require persistent task and dev logs for non-trivial work. The repository did not yet have a `tasks/` directory, so project-reading context needed to be recorded before deeper inspection.

How: Added `tasks/todo.md` with a checkable reading plan and initialized this dev log for future session continuity.

Result: Task tracking files now exist. No application code has been changed.

## 2026-04-30 - Project architecture read-through

Why: The user asked to read the project, so future work needs a concise map of the repository and a clear record of whether the current code can be verified.

How: Reviewed `README.md`, `pyproject.toml`, `rules.md`, `tests/test_history_assessment.py`, and all modules under `app/`. Identified FastAPI routes, SQLAlchemy models, training recommendation/generation logic, seed data, database configuration, and mock Garmin/COROS sync adapters.

Result: The project shape is documented in `tasks/todo.md`. Verification found that `python3 -m unittest -v` discovers 0 tests, while `python3 -m unittest discover -s tests -v` discovers the history/assessment workflow test but fails on import due to an invalid syntax error in `app/models.py:75`. `python3 -m py_compile app/models.py` confirms the same syntax error. No application code was changed during the read-through.

## 2026-04-30 - COROS-first requirements clarification

Why: The user clarified the product direction and wants requirements made rigorous before design starts. The key shift is that COROS automatic ingestion and synchronization are core MVP values, not optional later integrations.

How: Recorded the confirmed direction in `tasks/todo.md`: road running first, COROS first, automatic history ingestion, structured plan generation, user-confirmed plan adjustments, and automatic COROS sync after confirmation. Flagged credential storage, web automation, compliance, and safety boundaries as unresolved items that must be confirmed before formal design.

Result: Requirements discussion has a clear baseline. No application code was changed.

## 2026-04-30 - Personal-use COROS automation decisions

Why: The user clarified that the first version is for personal use and values automatic COROS synchronization highly enough to accept direct credential-based web automation.

How: Updated `tasks/todo.md` with confirmed constraints: username/password automation, simple encrypted credential storage, all accessible COROS data ingestion, full marathon road-running MVP, weekly user-confirmed plan adjustments, automatic sync of confirmed future workouts into the COROS calendar, and triathlon-ready data modeling for later expansion.

Result: The main product and integration assumptions are now explicit. Remaining work is to turn these decisions into a formal PRD and technical design before implementation. No application code was changed.

## 2026-04-30 - PRD and technical design authored

Why: The COROS-first MVP requirements were sufficiently clarified to create durable source-of-truth documents before implementation.

How: Added `docs/prd-coros-marathon-mvp.md` for product scope, user flows, safety rules, and acceptance criteria. Added `docs/technical-design-coros-marathon-mvp.md` for architecture, COROS automation, credential storage, data model, ingestion, running assessment, marathon plan generation, adjustment, sync, API surface, jobs, verification strategy, implementation sequence, and risks.

Result: Documentation review was performed by reading the generated files and checking line counts. No application code was changed and no tests were rerun for this documentation-only step. Next implementation should start by repairing `app/models.py:75`, then adding the normalized data model and fake COROS automation tests before real browser automation.

## 2026-04-30 - COROS-first marathon MVP backend implementation

Why: The user asked to complete the full first-stage product direction. The codebase previously could not import due to `app/models.py:75`, and the expected history/assessment endpoints were missing.

How: Rebuilt `app/models.py` to fix the syntax error and add normalized models for activities, laps, metric snapshots, race goals, availability, structured workouts, workout steps, provider sync records, and plan adjustments while preserving existing athlete/plan/session/device/sync models. Rebuilt `app/schemas.py` with the new request/response contracts. Added service modules for simple credential encryption, fake COROS automation, ingestion upsert, running assessment, marathon plan generation, COROS sync records, and weekly adjustment recommendations. Replaced `app/api/routes.py` with compatible legacy routes plus COROS-first endpoints for connect/import/status, history, assessment, goal creation, marathon plan generation, plan confirmation, COROS sync, and adjustment evaluation. Added `tests/test_coros_marathon_mvp.py` and added `httpx` to `pyproject.toml` because FastAPI/Starlette `TestClient` requires it. Updated `README.md` with the new flow and verification commands.

Result: Verification passed with `uv run python -m py_compile ...` and `uv run python -m unittest discover -s tests -v`. The test suite now has two workflow tests: the existing history/assessment compatibility test and a new COROS marathon closed-loop test. Remaining known limitations: COROS integration uses deterministic fake automation, not real Training Hub browser selectors; Python 3.14 reports `datetime.utcnow()` deprecation warnings; tests report a sqlite resource warning at process shutdown.

## 2026-04-30 - Real COROS probe preparation

Why: The next milestone is using the user's real COROS account locally to inspect Training Hub login, navigation, and page structure. Credentials must not be sent in chat or committed to the repository.

How: Added `.env.example`, ignored `.env` and `var/`, and added a small local env loader in `app/core/config.py`. Refactored COROS automation behind a protocol/factory in `app/coros/automation.py`, keeping fake mode as the default and adding a real-mode placeholder that fails clearly until page mapping exists. Updated API and sync code to use the factory. Added `scripts/probe_coros_training_hub.py`, a Playwright-based probe that reads local `.env`, attempts login, and writes sanitized summaries/screenshots to `var/coros_probe/`. Tests now force `COROS_AUTOMATION_MODE=fake` so local real credentials do not affect verification. Added Playwright to project dependencies and documented the setup in `README.md`.

Result: `uv run python -m py_compile app/core/config.py app/coros/automation.py app/api/routes.py app/coros/sync.py scripts/probe_coros_training_hub.py` passed. `uv run python -m unittest discover -s tests -v` passed. Playwright Python package is installed in the uv environment; the Chromium browser may still need `uv run playwright install chromium` before the real probe can run.

## 2026-04-30 - COROS Training Hub login probe

Why: The user asked to begin running the real COROS probe with credentials stored in local `.env`.

How: Verified `.env` exists without printing secret values, installed Playwright Chromium, and ran `uv run python scripts/probe_coros_training_hub.py` several times. The probe script was improved during the run to support COROS' Chinese login form placeholders, capture pre-login page artifacts, click the required privacy-policy checkbox rather than the remember-password checkbox, capture network request/response URLs, and safely summarize the login API response without storing tokens or passwords in logs.

Result: The Training Hub login page loads at `https://training.coros.com/login?lastUrl=%2Fadmin%2Fviews%2Fdash-board`. The login form fields are text/password inputs with placeholders `请输入邮箱账号` and `请输入6-20个字符的密码`. Login submission calls `https://teamapi.coros.com/account/login`. COROS returned HTTP 200 with application-level result `1030` and message `The login credentials you entered do not match our records.`, and the UI showed `用户名或密码错误`. No authenticated session or activity data was reached. Stop retrying until the local `.env` credentials are checked to avoid account lockout or risk controls.

## 2026-04-30 - COROS Training Hub authenticated probe

Why: After the `.env` credentials were corrected, the real COROS probe needed to verify login, dashboard access, and likely API endpoints for future real ingestion.

How: Re-ran `uv run python scripts/probe_coros_training_hub.py`, improved the script to click the privacy-policy checkbox, capture login response metadata safely, redact personal fields from summaries, tolerate COROS China-region SPA redirects, and collect visible dashboard text, cookies, storage keys, console messages, and request URLs. Added and ran `scripts/analyze_coros_bundles.py` to extract likely API paths from COROS static JS bundles.

Result: Login succeeded via `https://teamapi.coros.com/account/login` with result `0000`. The app redirected to `https://trainingcn.coros.com/admin/views/dash-board`. Dashboard text was visible and included running ability, training load, recent workouts, threshold pace/HR zones, personal records, race predictions, and HRV assessment. Important cookies include `CPL-coros-token`, `CPL-coros-region`, `csrfToken`, `_warden_device_id`, and `_warden_session_id`. Observed candidate API endpoints include `https://teamcnapi.coros.com/dashboard/query`, `https://teamcnapi.coros.com/dashboard/detail/query`, `https://teamcnapi.coros.com/profile/private/query`, `https://teamcnapi.coros.com/team/user/teamlist`, `https://teamcnapi.coros.com/activity/query`, `https://teamcnapi.coros.com/activity/detail/filter`, `https://teamcnapi.coros.com/training/schedule/query`, `https://teamcnapi.coros.com/training/schedule/update`, `https://teamcnapi.coros.com/training/plan/query`, and related plan/workout endpoints from the bundle analysis. Probe artifacts are under ignored `var/coros_probe/`.

## 2026-04-30 - Real COROS API probe and ingestion implementation

Why: The MVP backend was complete with fake automation, but the real COROS integration needed API shape data before a real client could be written. The Playwright-based probe wasn't capturing /activity/query because the page didn't auto-trigger that call on load.

How: Improved scripts/probe_coros_api.py in three iterations: (1) added direct API calls via context.request after login to hit endpoints not triggered by navigation; (2) captured the accessToken from the /account/query network response and passed it as an HTTP header in direct requests (bypassing the browser CORS restriction); (3) increased the shape function field limit from 30 to 60 to capture all 57 activity item fields. Also switched page navigation to use CN-region URLs (trainingcn.coros.com) instead of training.coros.com to avoid login redirects after the CN-region auth.

Separately, confirmed via direct urllib.request that the COROS login API accepts a plain JSON POST with MD5-hashed password — no Playwright required. Implemented RealCorosAutomationClient in app/coros/automation.py with: login() via MD5+POST, fetch_history() paginating last 90 days of running activities (sportType=100, 102, 101) using the accessToken header, and _fetch_metrics() reading dashboard/query for lthr, ltsp, aerobicEnduranceScore, staminaLevel, recoveryPct, and marathon prediction. Fixed race_predictor_marathon to use runScoreList type=1 duration directly (COROS's own marathon time estimate) instead of a Riegel formula.

Key field units discovered: distance=meters, totalTime=seconds, startTime=unix-seconds, startTimezone=15-minute-increments (×15=UTC offset in minutes), adjustedPace=seconds/km, runScoreList type 1/2/4/5 = marathon/half/10k/5k predictions in seconds.

Result: uv run python -m py_compile ... all modules OK. uv run python -m unittest discover -s tests -v: 2/2 pass. End-to-end real mode test: 32 activities fetched, 6 metrics including race_predictor_marathon=14628s (04:03:48). sync_workouts() is a NotImplementedError placeholder pending write-endpoint probe.

## 2026-05-01 - Real COROS calendar sync implemented (sync_workouts)

Why: The last missing piece of the real COROS integration was `RealCorosAutomationClient.sync_workouts()`. Without it, the app could ingest history but couldn't push generated training plans back to the COROS watch/calendar.

How: Ran a series of Playwright probes against the COROS Training Hub web UI to capture the exact API calls made when adding a workout to the schedule. Discovered:

1. The calendar sync endpoint is POST `teamcnapi.coros.com/training/schedule/update` (not plan/add or schedule/add).
2. The payload structure is `{entities: [{happenDay, idInPlan, sortNo, ...}], programs: [{idInPlan, name, sportType, exercises, ...}], pbVersion: 2, versionObjects: [{id, status:1}]}`.
3. `happenDay` is a YYYYMMDD string in both entity and program fields; `idInPlan` is a sequential counter that must be maxIdInPlan+1 per new item.
4. The exercise template uses COROS system id=1 (T3001 running exercise) with `createTimestamp: 1587381919` (COROS system constant, not current timestamp), `defaultOrder: 2`, `sortNo: 2`.
5. COROS rejects multiple new `idInPlan` entries in a single `schedule/update` call ("Plan data is illegal"). Must send one workout per call.
6. A `program/calculate` call before `schedule/update` returns server-computed `planDistance`, `planDuration`, `planTrainingLoad` which should be merged into the program before syncing.
7. `exerciseNum` must be `""` (empty string), `estimatedTime` must be `0` in the program body.
8. `sourceId`, `sourceUrl`, `referExercise` must be included with the COROS system default values.

Added to `RealCorosAutomationClient`:
- `sync_workouts()`: builds entity+program pairs from the workout list, calls `program/calculate` per workout to get server metrics, calls `schedule/update` one-at-a-time (COROS constraint), returns sync result records.
- `_get_max_id_in_plan()`: queries `schedule/query` to get current `maxIdInPlan` for sequential ID assignment.
- `_build_exercise()`: builds the COROS T3001 exercise object with HR intensity zones from `_lthr`, mapping workout_type to %LTHR ranges.
- `_build_program()`: builds the full program object with estimated distance/duration/load.
- `_post()`: POST equivalent of existing `_get()` helper.

Also stored `self._lthr` during `_fetch_metrics()` for use in intensity zone calculations.

Result: `uv run python -m py_compile app/coros/automation.py` passes. `uv run python -m unittest discover -s tests -v`: 2/2 pass. End-to-end real test: 3 workouts (easy 45min, tempo 30min, long 90min) successfully appeared in COROS calendar on correct future dates with correct durations and HR zones.
