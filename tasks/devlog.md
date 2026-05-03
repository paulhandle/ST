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

## 2026-05-01 - Project re-read and current-state summary

Why: The user asked to understand the project, and the repository has evolved beyond the initial README summary. Future work needs a fresh map of the actual code state, verification commands, and risks.

How: Reviewed `tasks/todo.md`, `tasks/devlog.md`, `tasks/lessons.md`, `README.md`, `rules.md`, `pyproject.toml`, app startup/config/database files, SQLAlchemy models, schemas, API routes, COROS automation/sync, ingestion, running assessment, marathon planning, adjustment/check-in modules, legacy device adapters, tests, CLI, and COROS probe scripts. Added a new "Project Re-Read" checklist and summary to `tasks/todo.md`.

Result: `uv run python -m py_compile app/models.py app/schemas.py app/api/routes.py app/coros/credentials.py app/coros/automation.py app/ingestion/service.py app/assessment/running.py app/planning/marathon.py app/planning/adjustment.py app/coros/sync.py app/planning/checkin.py app/planning/llm.py scripts/st_cli.py` passed. `uv run python -m unittest discover -s tests -v` passed with 2 tests, but took 186 seconds because tests currently allow `generate_marathon_plan()` to attempt a real LLM call before rule-based fallback. Noted current risks: README is behind real COROS direct-API sync, `scripts/st_cli.py` references nonexistent `SportType.RUNNING` on first-run athlete creation, there is no migration layer, and credential encryption remains personal-use MVP strength.

## 2026-05-01 - Skill architecture refactor (MVP+1)

Why: The user wants ST to evolve into a comprehensive personal training platform with pluggable training methodologies (Daniels, 80/20, Norwegian threshold, user-extracted skills), multi-sport support, and multi-platform device integration. The existing marathon planner was tightly coupled in `app/planning/marathon.py` + `app/planning/llm.py`, making it impossible to swap methodologies or add new sports without changing core code.

How: Followed the plan at `~/.claude/plans/golden-roaming-acorn.md`. Pure structural refactor — no new features. Five phases:

- **Phase A** — Defined platform contracts: `app/core/context.py` (`SkillContext`, `PlanDraft`, `WorkoutDraft`, `StepDraft`, `Assessment`, `HistoryView`, `AvailabilityView`, `GoalSpec`, `Signal`, `Adjustment`); `app/skills/__init__.py` (`Skill` Protocol, `load_skill(slug)`, `list_skills()`); `app/skills/base.py` (`SkillManifest`); `app/kb/__init__.py` (`KnowledgeBase` Protocol).
- **Phase B** — Built the first skill `marathon_st_default` under `app/skills/marathon_st_default/`: extracted rules from `planning/marathon.py` into `code/rules.py` (now consumes `SkillContext` and produces `WorkoutDraft` lists); extracted LLM prompt template into `code/llm_prompt.md`; LLM call code into `code/llm.py`; the skill class in `skill.py` tries LLM first, falls back to rules. Added `skill.md` (human-readable methodology) and `spec.yaml` (machine-readable manifest).
- **Phase C** — Wrote `app/core/orchestrator.py` with `generate_plan_via_skill(db, athlete, request, skill_slug, race_goal)` that owns DB I/O, builds `SkillContext`, calls the skill, and persists `PlanDraft` to `TrainingPlan` + `StructuredWorkout` + `WorkoutStep` + `TrainingSession`. Wired `/marathon/plans/generate` route, `/marathon/goals` route, and `scripts/st_cli.py cmd_plan` through the orchestrator with `skill_slug="marathon_st_default"`. Fixed the `SportType.RUNNING` bug at `scripts/st_cli.py:114`.
- **Phase D** — Module relocations: `app/coros/` → `app/tools/coros/`; `app/devices/` → `app/tools/devices/`; `app/assessment/running.py` → `app/kb/running_assessment.py`; `app/planning/adjustment.py` → `app/core/adjustment.py`; `app/planning/checkin.py` → `app/core/checkin.py`. Created `app/kb/running.py` for distance constants and pace helpers. Bulk-rewrote 7 files of stale imports via Python regex pass. Deleted now-empty `app/planning/` and `app/assessment/` directories.
- **Phase E** — Added architecture section + skill addition guide to `README.md`. Added `pyyaml>=6.0` to `pyproject.toml` (used by skill registry). Updated `tasks/todo.md`, `tasks/devlog.md`, `tasks/lessons.md`.

Result: `uv run python -m unittest discover -s tests`: **2/2 pass in ~5 seconds**. End-to-end smoke test: `uv run python -c "from app.skills import load_skill, list_skills; print(list_skills()); skill = load_skill('marathon_st_default'); ..."` produces a 12-week, 4-workouts/week marathon plan with `BASE_BUILD_PEAK` mode and proper warmup/work/cooldown step structure. The `/marathon/plans/generate` route preserves its existing API contract — clients see no behavior change.

Out of scope (deferred to MVP+1.5): skill-creator UI/flow, COROS `/training/schedule/query` historical date-range probe, second skill (e.g., 80/20 polarized), second sport (half marathon).

## 2026-05-02 - Independent verification fixes

Why: Independent code review found high-priority README/code inconsistency (README claimed fake-only COROS while real direct-API was fully implemented) and medium-priority gaps: test suite used the same `st.db` as operational data, and real COROS client had zero automated test coverage.

How:
- `app/core/config.py`: `DATABASE_URL` now reads `ST_DATABASE_URL` env var first, falling back to `st.db`. This is the single change that enables test isolation.
- All 4 existing test files: added `os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")` before any app imports. Tests now write to `st_test.db` and never touch the operational `st.db`.
- `.gitignore`: added `st_test.db`.
- `tests/test_real_coros_client.py`: 14 new unit tests for `RealCorosAutomationClient`, using `unittest.mock.patch("urllib.request.urlopen", ...)` with `MagicMock` context managers (`__enter__.return_value = m`). Covers: MD5 password hashing, token/host extraction, region routing, network error handling, field unit mapping (distance/time/pace/timezone), pagination cutoff, dashboard metric extraction, marathon prediction extraction, sync idInPlan sequencing, schedule/update call count, and error propagation.
- `README.md`: updated intro item 4, `/coros/connect` API description, `COROS_AUTOMATION_MODE` documentation (fake vs real behavior), and added `ST_DATABASE_URL` env var.
- `tasks/todo.md`: closed all deferred items from the Project Re-Read phase.

Result: `uv run python -m unittest discover -s tests -v` → **47/47 pass in 2.2s**. `st.db` is untouched by tests.

## 2026-05-01 - Block A1 frontend-contract endpoints

Why: The web frontend needs aggregate + detail endpoints that the existing API does not provide. `docs/api-frontend-contract.md` specifies eight new/enhanced endpoints (dashboard, volume curve, regenerate preview, adjustment detail+apply, coach chat send/list, plus enrichments to today/history). Implementing them on the backend unblocks the Next.js frontend work.

How: Followed the actionable spec from the user prompt.

- **Models** (`app/models.py`): added `affected_workouts_json` Text column on `PlanAdjustment`; added new `CoachMessage` table (`id, athlete_id, role, text, suggested_actions_json, created_at`).
- **Schemas** (`app/schemas.py`): enriched `AthleteActivityOut` with `matched_workout_id`, `matched_workout_title`, `match_status`, `delta_summary`. Extended `TodayOut` with `yesterday_workout`, `yesterday_activity`, `recovery_recommendation`. Added Block A1 schemas: `Dashboard*`, `PlanVolumeCurve*`, `RegeneratePreviewOut`, `AdjustmentAffectedWorkout`, `PlanAdjustmentDetailOut`, `PlanAdjustmentApplyRequest`, `CoachMessage*`.
- **Routes** (`app/api/routes.py`):
  - `GET /athletes/{id}/dashboard` — aggregates greeting, today's workout + match, this-week strip, goal w/ prediction history (12 most recent `race_predictor_marathon` snapshots), 8-week volume history (planned vs executed), 7 most recent activities, readiness panel (rhr trend vs 14-day avg, weekly load trend, lthr, ltsp), pending adjustment, last sync meta.
  - `GET /plans/{id}/volume-curve` — full per-week planned/executed/longest-run with `is_current` flag and peak values.
  - `GET /plans/{id}/regenerate-preview?skill_slug=X` — read-only sibling of regenerate-from-today: builds derived race goal context, asks `skill.applicable(ctx)`, returns counts + applicability.
  - `GET /plan-adjustments/{id}` — adjustment detail with parsed `affected_workouts_json`.
  - `POST /plan-adjustments/{id}/apply` — atomic mutation: walks `affected_workouts_json`, applies `distance_m`, `duration_min`, `skip` (sets `MISSED` + zeroes distance), or `workout_type`. Returns 422 when a referenced workout is missing.
  - `POST /coach/message` — persists user msg, dispatches to `interpret_checkin()` when `OPENAI_API_KEY` is set; otherwise stub reply "AI 教练当前不可用，请稍后再试". Persists coach reply with optional `suggested_actions_json`.
  - `GET /coach/conversations/{athlete_id}?limit=50` — newest-first pagination.
  - Enhanced `GET /athletes/{id}/history` to wrap each row through `_activity_with_match(db, a)` so `match_status` and `delta_summary` are populated.
  - Enhanced `GET /athletes/{id}/today` with yesterday's workout + matched activity and the `recovery_recommendation` heuristic (≥4 missed in last 7 days).
  - Bug fix as side-effect: the `_AvailabilityShim` in `_availability_for()` was returning a Python list for `unavailable_weekdays`, but `app.core.orchestrator._parse_unavailable` expects the raw comma-string from the model. Replaced the list-comprehension with the raw string. This unblocked the regenerate-preview path that goes through `_build_context`.
- **Tests** (`tests/test_block_a1.py`): 14 tests across 7 TestCase classes covering dashboard with/without plan/activities, volume curve, regenerate preview applicable + not-applicable (frozen most weeks so derived `plan_weeks` < 12), adjustment apply happy paths + 422, coach stub fallback when `OPENAI_API_KEY` empty, coach conversation pagination, history enrichment, today recovery + yesterday surfacing.

Result: `uv run python -m py_compile $(find app -name "*.py")` clean. `uv run python -m unittest discover -s tests -v` reports **33 tests pass in ~2.3s** (19 existing + 14 new). No commit yet — awaiting user review.

## 2026-05-02 – Block B: Auth + running_beginner skill + frontend onboarding

### Why
多用户支持需要身份认证层。用户反馈缺少登录页、新人引导和无计划时的默认状态。同时发现新用户没有 COROS 历史时平台无法评估能力，需要一个入门级 skill 兜底。

### How

**后端 — Auth（`app/api/auth.py`、`app/core/auth.py`、`app/models.py`）**

- 新增 `User`（phone、created_at）和 `OTPCode`（phone、code、expires_at、used）模型
- `AthleteProfile` 增加可选 `user_id` FK，支持一个用户多个运动档案
- 30 天无 refresh 的 JWT（stdlib HMAC-SHA256，无第三方依赖）
- `POST /auth/send-otp`：生成 6 位 OTP，mock 模式直接返回 code；`POST /auth/verify-otp`：验证 OTP → 返回 JWT + user_id；`GET /auth/me`：需要 Bearer token
- OTP 10 分钟过期，单次使用

**后端 — `running_beginner` skill（`app/skills/running_beginner/`）**

- 纯规则，不调 LLM
- 16 周三阶段模板：适应期（1-4周）→ 建基期（5-10周）→ 巩固期（11-16周）
- 全程 RPE 4-5 强度，每周 1-3 次，每次不超过 90 分钟
- `applicable()` 门控：平均周跑量超过 40 km 时返回 False，建议使用进阶方法论

**前端 — Auth（`web/lib/auth.ts`、`web/middleware.ts`、`web/lib/api/client.ts`）**

- JWT 存储在 `localStorage['st_token']`
- `middleware.ts`：所有非 `/login`、非 `/api` 路径检查 token，无则跳转 `/login`
- API client 所有请求自动加 `Authorization: Bearer <token>`

**前端 — 登录页（`web/app/login/page.tsx`）**

- 两步状态机：phone → OTP → 登录
- 新用户（is_new_user）跳转 `/onboarding`，返回用户跳转 `/dashboard`

**前端 — Onboarding（`web/app/onboarding/page.tsx`）**

- 4 步向导：COROS 连接（可跳过）→ 目标设定（比赛日期、目标时间、经验水平）→ 训练日选择 → 确认
- 完成后依次调：`POST /athletes`、`POST /coros/connect`（optional）、`POST /athletes/{id}/goals`

**前端 — 空状态 + 调整入口**

- `EmptyPlanState`：无计划时在 dashboard 和 plan tab 展示"设定目标 →"CTA，链接到 `/onboarding`
- `PendingAdjustmentSection`：plan tab 底部显示待处理调整数量 + 标题，链接到 `/adjustments/{id}`

### Result

- 后端新增 12 个 auth 测试 + 12 个 beginner skill 测试，全套 71/71 通过（2.6s）
- 前端新增 15 个测试（auth.test.ts、login.test.tsx、onboarding.test.tsx、step6.test.tsx），全套 35/35 通过（< 1s）
- `pnpm type-check` 和 `pnpm build` 通过
- **未解决**：auth 路由保护（`get_current_user` dependency）尚未加到现有 athlete/plan 路由上，待 Block C 前做路由级保护加固

## 2026-05-03 — Block C: Skills / Adjustment / Activities screens

### Why
前端缺少三个核心屏幕：skill 选择与方法论阅读、计划调整详情、历史活动列表。后端端点在 Block A/A1 已完成，本次纯前端工作。使用 feature branch `feat/block-c-screens`，通过 PR 合入 main。

### How

**组件（TDD — 15 个测试先写后实现）**

- `SkillList`：展示 skill 卡片，标记当前 skill，提供"切换"按钮（inactive skill）和"查看方法论"链接
- `SwitchSkillDialog`：显示 regenerate-preview 统计（重新生成课数、影响周数、保留已完成/缺训课数），applicable=false 时禁用确认按钮并展示原因
- `AffectedWorkoutRow`：展示受调整影响的单条课程（日期、标题、变更摘要）
- `ActivityRow`：展示单条历史活动（状态 dot、距离/配速、delta_summary）

**页面**

- `/skills` — 拉 `GET /skills`，点击"切换"先调 `GET /plans/{id}/regenerate-preview` 拿 preview，再弹 SwitchSkillDialog，确认后调 `POST /plans/{id}/regenerate-from-today` 并跳转 dashboard
- `/skills/[slug]` — 拉 `GET /skills/{slug}`，以 `<pre>` 渲染 `methodology_md`（暂不做 Markdown 渲染）
- `/adjustments/[id]` — 拉 `GET /plan-adjustments/{id}`，展示受影响课程列表，接受调用 `POST /plan-adjustments/{id}/apply`，拒绝调用 `POST /plan-adjustments/{id}/reject`，完成后 1.2s 内返回
- `/activities` — 拉 `GET /athletes/{id}/history`，顶部汇总统计（总次数/总公里/完成率），图例说明 5 种状态色点

### Result

- 50/50 前端测试通过（< 1s）
- `pnpm type-check` 通过
- `pnpm build` 通过，新增 5 个编译单元（/skills、/skills/[slug] 动态路由、/adjustments/[id]、/activities）
- 通过 `gh pr create` 提交 PR，分支 `feat/block-c-screens`
