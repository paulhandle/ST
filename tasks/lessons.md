# Lessons

## 2026-05-01 — Architectural patterns confirmed during the Skill refactor

These were validated by the user during the MVP+1 design discussion. Apply going forward:

1. **Skill = Hybrid (rules + LLM)**, not pure LLM and not pure code. Hard safety rules (volume bounds, taper, no back-to-back hard) are deterministic; creative slots (workout choice this week, intensity nudges) are LLM. Pure LLM was rejected because it can't be formally verified for athlete safety.

2. **Skills are pure functions of `SkillContext`**. They never see the DB or external APIs. The orchestrator does all I/O. This makes skills replayable, testable, version-controllable.

3. **One skill per training cycle**. Mixing methodologies (e.g., Daniels VO2max work + Norwegian sub-threshold in the same week) is scientifically unsound — competing adaptation signals. Across cycles you can switch skills; within a cycle you cannot.

4. **Tools belong to the platform, not skills**. Skills receive summarized data via the context; they do not call COROS / Garmin / Strava directly. This keeps caching, rate limiting, error handling, and auditing in one place.

5. **Skills are filesystem artifacts, not DB rows**. Each skill is a directory with `skill.md` + `spec.yaml` + `skill.py` + `code/`. This aligns with Claude Skill format, supports git versioning, and lets users edit / share skills as plain text.

6. **Increment, don't big-bang**. The user wanted a clean refactor *first*, before adding the skill-creator feature, even though skill-creator is the differentiating value. Rationale: easier to validate the abstraction with one bundled skill before building the harder UX flow that creates new skills.

## 2026-05-01 — Process patterns

- **macOS sed has no `\b` word boundary**. Fall back to a Python regex one-liner via `python3 -c "..."` for bulk file rewrites. Pattern `default=datetime\.utcnow\b` failed silently with `sed -i ''`.
- **`git mv` requires the source to be tracked**. Untracked new files (e.g., a freshly created `checkin.py` that hadn't been committed) need plain `mv`. Mixing tracked and untracked file moves means doing the operation in two passes.
- **Stale SQLite DB lock from a previous test run will block the next test run**. If `database is locked` shows up at `Base.metadata.drop_all(...)`, look for a leftover `python -m unittest` process via `lsof <db file>` and kill it.
- **AthleteProfile DB model and AthleteProfileData TOML dataclass are different shapes**. The DB model only has `id, name, sport, level, weekly_training_days, weekly_training_hours, notes` — `age`, `sex`, etc. live in the local TOML profile. Use `getattr(athlete, "age", None)` when bridging the two, never direct attribute access.

## 2026-05-01 — User preferences confirmed

- For exploratory or architectural questions, the user wants me to **push back** with concrete tensions, not write more agreeable design docs. Listing real risks/IP-issues/scientific-issues is more valuable than a polished diagram.
- The user wants **directory structure that visibly separates skill from business logic** — not just module-level discipline. Skills live in their own top-level directory; tools in their own; KB in its own.
- For projects without active git remotes / branches, **don't propose CI integration or extensive feature flags** — keep changes simple and purely structural.

## 2026-05-05 — Clarify SMS rollout scope before narrowing

- When SMS country scope changes mid-turn, confirm whether the user means product support or only the immediate test/default path before removing existing country options. The current implementation keeps the mainstream launch list rather than China-only.

## 2026-05-05 — Shared SQLite tests must run sequentially

- Backend unittest classes rebuild the same `st_test.db` with `Base.metadata.drop_all/create_all`. Do not run two backend unittest commands in parallel against that shared SQLite file; parallel runs can produce transient `no such table` or missing-row failures unrelated to the application code.

## 2026-05-05 — COROS account credentials belong in app storage, not env

- Do not document or require `COROS_USERNAME` / `COROS_PASSWORD` as app environment variables. Users enter COROS credentials in Settings, and the backend stores them encrypted in the database for sync jobs. Local probe scripts may still accept temporary env credentials as a developer-only tool, but `.env`, `.env.example`, README app setup, Fly secrets, and production docs must not ask users to put COROS account passwords there.

## 2026-05-06 — Real COROS validation must not default to synthetic data

- For user-facing COROS validation and local product testing, default runtime behavior should use real COROS data when credentials are configured. Keep fake COROS only as an explicit automated-test or synthetic-development mode, and label/remove old fake rows before asking the user to validate captured data.
- COROS activity list/detail API payloads are not enough for user validation of a real activity. When the user asks for "all data" or checks against Training Hub pages, use the Training Hub export path (`POST /activity/detail/download`) and inspect `.fit/.tcx/.gpx/.csv` exports for GPS, trackpoints, laps, and split data.

## 2026-05-07 — COROS detail production path is FIT-only

- Do not revive `/activity/detail/filter` as the normal detail source unless a fresh real probe proves it returns richer, reliable data. The production detail path should discover activities from `/activity/query`, then download one `.fit` export (`fileType=4`) per activity and parse GPS/time-series/laps from that canonical raw archive. TCX/GPX/CSV are for debugging and manual comparison, not routine sync.
- Existing local SQLite databases may have application tables without an Alembic version stamp. When a local migration hits "table already exists", do not drop or reset the real review database. Use a non-destructive table creation path for local inspection and keep Alembic migrations valid for clean/prod databases.

## 2026-05-07 — First-run onboarding must create the training plan

- Do not treat onboarding as profile/COROS setup only. The product core is skill selection plus plan generation, so first-run onboarding must load available skills, let the user choose one, call the plan generation API with that `skill_slug`, confirm the generated plan, and route to the plan/dashboard only after a plan exists. A successful onboarding that leaves Plan empty is a broken core flow.

## 2026-05-07 — SMS login is fallback-only visually

- On login surfaces, Google and passkey are the primary actions. SMS should remain available but visually quiet: use a small one-line text link, not a full-width button or anything that competes with the primary auth methods.

## 2026-05-08 — Auth success is not onboarding completion

- Do not use `is_new_user` as the dashboard routing gate. A repeated Google/passkey/SMS login can be an existing account with no `AthleteProfile` yet. Login responses must expose setup state (`has_athlete`, `athlete_id`), and the web app should route to dashboard only when a valid athlete id is present.
- When auth state says onboarding is incomplete, clear stale local `pp_athlete_id` before routing. A previous account's athlete id in localStorage can otherwise cause `Athlete not found` errors under a different authenticated user.
- After successful auth, prefer a full browser navigation over Next client `router.replace()` for the first transition out of `/login`. This guarantees the freshly written auth cookie is present on the next protected-route document request and prevents the login page client state from swallowing the first Google callback.
- Onboarding-created athletes must be owned by the authenticated `User`. Any endpoint that creates `AthleteProfile` during product setup should persist `user_id=current_user.id`; otherwise auth responses will keep reporting `has_athlete=false` and completed users will repeat onboarding forever.

## 2026-05-10 — Settings pages need deterministic exits

- Settings and nested settings pages must include explicit visible navigation back to the containing surface. Do not rely on browser history, tiny unlabeled symbols, or the user guessing the app shell route. Root settings should link back to `/me`; nested settings pages should link back to `/settings`, with tests asserting the href.

## 2026-05-10 — Auth token readers need cookie fallback

- Protected pages can be entered because middleware sees the `st_token` cookie even when `localStorage` is empty or unavailable. Any client API helper that builds `Authorization` headers must read the cookie as a fallback, or onboarding/API requests can omit auth and fail with backend 401 after a seemingly successful login.
