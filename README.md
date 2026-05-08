# PerformanceProtocol

[performanceprotocol.io](https://performanceprotocol.io)

PerformanceProtocol is an endurance training platform for serious athletes. The current product supports the complete road-running loop for marathon and half-marathon training, with trail running, triathlon, and long-distance cycling planned as future extensions.

The product-facing brand is **PerformanceProtocol**. `ST` remains only as a legacy internal codename in package names, database filenames, environment variables such as `ST_SECRET_KEY` / `ST_DATABASE_URL`, and a few compatibility paths. Do not use `ST` in product UI, marketing copy, OpenAPI display names, or user-facing documentation.

## Product Loop

1. Sign in with phone OTP and complete first-run onboarding.
2. Connect COROS and import historical training data, FIT detail exports, and performance metrics.
3. Choose one training skill for the cycle.
4. Generate and confirm a structured training cycle from that skill, goal, and weekly availability.
5. Sync confirmed future workouts to the COROS calendar.
6. Track execution, inspect activity detail, and propose weekly adjustments.

Legacy generic training-method and mock device-sync endpoints are still present for compatibility.

## Architecture

```text
app/
├── core/        Platform contracts and orchestration
├── skills/      Training methodologies; each skill is a filesystem package
│   └── marathon_st_default/   Built-in PerformanceProtocol marathon skill
├── kb/          Sport knowledge: distance constants, assessment logic, helpers
├── tools/       Platform-owned external integrations
│   ├── coros/   COROS direct API client and calendar sync
│   ├── sms/     SMS OTP provider abstraction and phone normalization
│   └── devices/ Legacy mock Garmin/COROS adapters
├── ingestion/   Unified activity and metric ingestion
├── api/         FastAPI routes
├── training/    Legacy generic training-method metadata
├── models.py    SQLAlchemy ORM
└── schemas.py   Pydantic schemas
```

Core rules:

- Skills are pure functions of `SkillContext`; they do not access the DB or external APIs.
- Tools are owned by the platform, not by skills.
- One training cycle uses one skill. Different cycles can use different skills.
- Skills are filesystem artifacts with `skill.md`, `spec.yaml`, `skill.py`, and optional `code/` or `data/`.

To add a skill:

1. Create `app/skills/<slug>/`.
2. Add `skill.md`, `spec.yaml`, and `skill.py`.
3. Export a `skill` instance implementing the `Skill` protocol.
4. Load it with `app.skills.load_skill("<slug>")`; API routes call it through the orchestrator.

## Stack

Backend:

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- SQLite locally, Postgres in production
- Alembic migrations
- uv for Python dependency management

Frontend:

- Next.js 14 App Router
- TypeScript
- Tailwind CSS
- SWR
- Recharts
- Vitest + React Testing Library
- pnpm for Node dependency management

## Web Internationalization

The web app supports English and Simplified Chinese fixed UI copy through `web/lib/i18n/`.

- `I18nProvider` wraps the app in `web/app/layout.tsx`.
- The language preference is stored as `pp_language` in localStorage and a cookie.
- `LanguageToggle` is available on the homepage, login page, and authenticated app shell.
- Backend/content data such as workout titles, skill descriptions, and adjustment reasons is displayed in the source language returned by the API.

## Local Development

```bash
# Backend
cd /Users/paul/Work/ST
uv run uvicorn app.main:app --reload

# Frontend
cd web
pnpm install
pnpm dev
```

Local URLs:

- API: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Web: `http://localhost:3000`

## Environment

Copy `.env.example` to `.env` for local runtime configuration. `.env` is ignored by git.

```bash
cp .env.example .env
```

Important variables:

| Variable | Purpose |
|---|---|
| `ST_SECRET_KEY` | Legacy env var for JWT signing and local credential encryption. Keep the name for compatibility. |
| `ST_DATABASE_URL` | Legacy env var for local DB override. Defaults to `sqlite:///st.db`; tests use `sqlite:///st_test.db`. |
| `COROS_AUTOMATION_MODE` | Defaults to `real` for the direct COROS API client. Set `fake` only for automated tests or explicit synthetic-data development. COROS account credentials are entered in Settings and stored encrypted in the database, not in `.env`. |
| `COROS_TRAINING_HUB_URL` | Training Hub probe base URL. |
| `COROS_HEADLESS` | Set `false` when running browser probes interactively. |
| `SMS_PROVIDER` | `mock` by default. `dry_run` exercises provider wiring without returning OTP codes. |
| `SMS_MOCK_RETURN_CODE` | `true` in local/test mock mode to include `otp_code` in responses; set `false` outside local development. |
| `SMS_API_KEY` / `SMS_API_SECRET` / `SMS_SENDER_ID` | Reserved for the future real SMS vendor adapter. |
| `GOOGLE_CLIENT_ID` | Google OAuth client id for `/auth/google` ID-token verification. If unset, Google login returns 503. |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Same Google OAuth client id exposed to the Next.js browser bundle so Google Identity Services can render the login button. Required at web build time. |
| `NEXT_PUBLIC_SMS_LOGIN_ENABLED` | Controls whether the web login page shows the SMS fallback entry. Use `true` locally; production build currently sets `false` until an SMS vendor is ready. |
| `WEBAUTHN_RP_ID` | WebAuthn relying-party id. Use `performanceprotocol.io` in production; defaults to `localhost` for local development. |
| `WEBAUTHN_RP_NAME` | WebAuthn relying-party display name. Defaults to `PerformanceProtocol`. |
| `WEBAUTHN_ALLOWED_ORIGINS` | Comma-separated origins accepted for passkey ceremonies. Defaults to localhost plus production domains. |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | Optional LLM configuration for skill personalization and coach interpretation. |

## COROS Real Sync

`COROS_AUTOMATION_MODE` defaults to `real`, which uses the direct COROS API client. Do not put COROS account username/password in `.env`. Enter the account in **Settings -> COROS Sync**; the backend stores the password encrypted in `device_accounts.encrypted_password` and uses it for import/sync jobs. Use `COROS_AUTOMATION_MODE=fake` only for automated tests or deliberate synthetic-data development.

For standalone real-data inspection without starting the web UI:

```bash
uv run python scripts/coros_real_fetch_probe.py --athlete-id 1
uv run python scripts/coros_db_inspect.py --athlete-id 1
uv run python scripts/coros_export_activity_sample.py --athlete-id 1
uv run python scripts/coros_export_file_probe.py 477263761401479169 --athlete-id 1 --file-types 4,3,1,0
uv run python scripts/coros_import_fit_export.py var/coros_real_sync/exports/477263761401479169/477263761401479169.fit --athlete-id 1 --provider-activity-id 477263761401479169
```

`coros_real_fetch_probe.py` first tries the encrypted DB credential for that athlete. If none exists, it prompts for the COROS username/password without echoing the password. Probe output is written under ignored `var/coros_real_sync/`.

`coros_export_file_probe.py` uses the same encrypted DB credential to call the Training Hub export path (`POST /activity/detail/download`) and downloads real `.fit`, `.tcx`, `.gpx`, `.kml`, or `.csv` files under ignored `var/coros_real_sync/exports/`. For production ingestion, the app downloads only `.fit` (`fileType=4`) per activity, archives the raw FIT bytes, and parses GPS, per-sample metrics, and laps from that single file. TCX/GPX/CSV exports are debugging/reference tools only.

`coros_import_fit_export.py` imports a downloaded `.fit` file into the activity detail tables for local review. For example, the current real sample `477263761401479169` imports as 4092 samples and 11 laps.

If old synthetic COROS rows are present in a local database, remove only those tagged fake rows with:

```bash
uv run python scripts/coros_cleanup_fake_data.py --athlete-id 1 --dry-run
uv run python scripts/coros_cleanup_fake_data.py --athlete-id 1
```
To import a saved probe artifact into the local DB for review:

```bash
uv run python scripts/coros_import_fetch_file.py var/coros_real_sync/full-fetch-1-YYYYMMDD-HHMMSS.json --athlete-id 1
```

To debug the COROS detail endpoint for one activity:

```bash
uv run python scripts/coros_detail_probe.py <label_id> --athlete-id 1 --sport-type 100
```

COROS data storage:

| Table | What it stores |
|---|---|
| `device_accounts` | COROS account state, username, encrypted password, last login/import/sync timestamps, last error. |
| `provider_sync_jobs` | Full-sync job status, phase, progress counters, imported/updated/metric/raw/failed counts. |
| `provider_sync_events` | Progress/event log for each sync job, including warnings when a detail endpoint fails. |
| `provider_raw_records` | Raw COROS endpoint/page/detail payloads, keyed by provider, record type, and provider record id. |
| `athlete_activities` | Normalized activity rows used by dashboard/history/assessment, with the activity raw payload also stored in `raw_payload_json`. |
| `activity_laps` | Normalized laps when available from imported activity payloads. |
| `activity_detail_exports` | Raw FIT export archive and metadata: source format, byte size, payload hash, download/parse timestamps, parser warnings, sample/lap counts. |
| `activity_detail_samples` | Parsed FIT record samples: timestamp, elapsed seconds, distance, GPS latitude/longitude, altitude, heart rate, cadence, speed/pace, power, temperature, and raw field JSON. |
| `activity_detail_laps` | Parsed FIT lap records: duration, distance, heart rate, cadence, speed, power, ascent/descent, calories, temperature, and raw field JSON. |
| `athlete_metric_snapshots` | Normalized metrics such as LTHR, threshold pace, fatigue, marathon prediction, and related dashboard metrics. |

The current full sync fetches all `/activity/query` pages, keeps all sport types, captures dashboard/profile/team/schedule/plan raw payloads where COROS returns them, then downloads one FIT export per discovered activity through `POST /activity/detail/download?labelId=...&sportType=...&fileType=4`. The older `/activity/detail/filter` variants are not used for production detail ingestion because they returned COROS service/parameter errors during real testing.

## Auth

The app uses its own 30-day bearer token after any successful sign-in method. Google login and passkeys are the primary low-cost paths; SMS OTP remains as a fallback and for phone linking in Settings.

Google login uses Google Identity Services in the browser with `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, then posts the returned Google ID token to `/auth/google`. The backend verifies the token against `GOOGLE_CLIENT_ID`, uses Google's stable `sub` as the identity subject, creates or links the user, then returns the same JWT response shape as OTP login. These two Google client-id variables should contain the same OAuth web client id; the `NEXT_PUBLIC_` value is public and compiled into the web bundle.

All successful login methods return account state as well as the app token: `is_new_user`, `has_athlete`, and `athlete_id`. `is_new_user` only means the account record was newly created. The web app routes to `/dashboard` only when `has_athlete=true` and a valid `athlete_id` is present; otherwise it clears any stale local athlete id and routes to `/onboarding`.

Passkeys use WebAuthn server-side ceremonies:

- `POST /auth/passkeys/register/options`
- `POST /auth/passkeys/register/verify`
- `POST /auth/passkeys/login/options`
- `POST /auth/passkeys/login/verify`

Production passkeys require HTTPS and domain-bound WebAuthn settings on the API runtime:

```bash
flyctl secrets set \
  WEBAUTHN_RP_ID=performanceprotocol.io \
  WEBAUTHN_RP_NAME=PerformanceProtocol \
  WEBAUTHN_ALLOWED_ORIGINS=https://performanceprotocol.io,https://www.performanceprotocol.io \
  --app st-api
```

Local passkey testing uses localhost defaults:

```env
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=PerformanceProtocol
WEBAUTHN_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

SMS fallback phone numbers are normalized to E.164. The preferred request shape is `country_code + national_number`; legacy mainland China `phone` requests are still accepted for compatibility. OTP sends are rate-limited per phone and per IP, and failed verification attempts are rate-limited per phone. Development/test mode can return a mock OTP code.

```bash
curl -X POST http://127.0.0.1:8000/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"country_code": "+86", "national_number": "13800138000"}'

curl -X POST http://127.0.0.1:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"country_code": "+86", "national_number": "13800138000", "code": "123456"}'

curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

OTP codes expire after 10 minutes and can be used once. The initial country/region list in the web login selector covers China mainland, United States, United Kingdom, Singapore, Hong Kong SAR, Taiwan, China, Japan, and Australia.

Account identity storage:

| Table | What it stores |
|---|---|
| `users` | Product account, optional phone/email/profile fields, and related athletes. |
| `account_aliases` | Login aliases by provider: `phone`, `email`, `google`, or `passkey`, keyed by provider subject. `users` is the account owner table; provider credentials and profile claims live here instead of on `users`. |
| `webauthn_credentials` | Passkey credential id, public key, sign count, transports, display name, and last-used time. |
| `auth_challenges` | Short-lived OTP/passkey challenges plus rate-limit audit rows. |

## First-Run Onboarding

After first authentication, users without an athlete profile complete `/onboarding`. The flow collects COROS credentials, target race information, weekly training availability, and the training skill for the first cycle. Finishing onboarding is intentionally blocking on plan generation: the web app creates the athlete, stores the returned athlete id in `pp_athlete_id`, optionally connects COROS, creates a marathon goal when target data is present, calls `/marathon/plans/generate` with the selected `skill_slug`, confirms the returned plan through `/plans/{id}/confirm`, then routes to `/plan`.

COROS connection failure does not block onboarding because the athlete can reconnect later from Settings. Plan generation failure does block onboarding because an empty Plan tab means the core product flow did not complete.

## Skills

| Slug | Description | Use Case |
|---|---|---|
| `marathon_st_default` | PerformanceProtocol Marathon Plan; hybrid rules plus optional LLM personalization. | Marathon runners with an existing training base. |
| `coach_zhao_unified` | Coach Zhao Unified Marathon Methodology; seasonal marathon plan distilled from historical coach-prescribed workouts. | Athletes following that methodology. |
| `running_beginner` | Beginner Runner Plan; rule-based, RPE-only progression. | New runners or athletes under 40 km/week. |

## Web Routes

| Route | Purpose |
|---|---|
| `/login` | Phone OTP sign-in |
| `/onboarding` | First-run setup: COROS, goal, training days, skill selection, plan generation, confirmation |
| `/dashboard` | Training overview |
| `/today` | Redirects to today's workout detail |
| `/week` | Legacy current-week training calendar route; not shown in primary navigation |
| `/plan` | Plan overview and pending adjustment entry |
| `/plan/generate` | Plan generation wizard |
| `/activities` | Calendar strip and activity timeline |
| `/activities/[id]` | Activity detail with route, metric timelines, laps, interpretation, and FIT source metadata |
| `/me` | Profile, device sync, language, account, and settings entry points |
| `/skills` | Skill selection |
| `/skills/[slug]` | Skill methodology detail |
| `/adjustments/[id]` | Adjustment detail and apply/reject flow |
| `/settings` | Training, data, and account settings |
| `/settings/security` | Passkeys and SMS fallback phone linking |

## Key API Routes

- `GET /health`
- `GET /sports`
- `GET /skills`
- `GET /skills/{slug}`
- `POST /auth/send-otp`
- `POST /auth/verify-otp`
- `POST /auth/google`
- `POST /auth/passkeys/register/options`
- `POST /auth/passkeys/register/verify`
- `POST /auth/passkeys/login/options`
- `POST /auth/passkeys/login/verify`
- `POST /auth/phone/link/start`
- `POST /auth/phone/link/verify`
- `GET /auth/me`
- `POST /athletes`
- `GET /athletes/{id}/dashboard`
- `GET /athletes/{id}/today`
- `GET /athletes/{id}/week`
- `GET /athletes/{id}/history`
- `GET /athletes/{id}/calendar`
- `GET /athletes/{id}/activities/{activity_id}`
- `POST /coros/connect`
- `POST /coros/import`
- `POST /coros/sync/start`
- `GET /coros/sync/jobs/{id}`
- `GET /coros/sync/jobs/{id}/events`
- `POST /athletes/{id}/assessment/run`
- `POST /marathon/goals`
- `POST /marathon/plans/generate`
- `POST /plans/{id}/confirm`
- `POST /plans/{id}/sync/coros`
- `GET /plans/{id}/volume-curve`
- `GET /plans/{id}/regenerate-preview`
- `POST /plans/{id}/regenerate-from-today`
- `POST /workouts/{id}/feedback`
- `GET /athletes/{id}/workout/{date}`
- `GET /plan-adjustments/{id}`
- `POST /plan-adjustments/{id}/apply`
- `POST /plan-adjustments/{id}/reject`
- `POST /coach/message`
- `GET /coach/conversations/{athlete_id}`

## Verification

```bash
# Backend
uv run python -m py_compile $(find app -name "*.py")
uv run python -m unittest discover -s tests -v

# Frontend
cd web
pnpm test
pnpm type-check

# Skill registry smoke test
uv run python -c "from app.skills import list_skills; print([m.slug for m in list_skills()])"
```

Tests set `ST_DATABASE_URL=sqlite:///st_test.db` so they do not touch local operational data.

## Deployment

Production runs on Fly.io in the Singapore region:

| Host | Fly App |
|---|---|
| `performanceprotocol.io` | `pp-web` |
| `www.performanceprotocol.io` | `pp-web` |
| `api.performanceprotocol.io` | `st-api` |

Postgres runs as Fly app `pp-db` and is attached to `st-api`.

Daily deployment:

1. Push to `main`.
2. `.github/workflows/deploy.yml` runs backend tests and frontend tests/type-check.
3. If verification passes, GitHub Actions deploys `st-api` and `pp-web`.
4. The API deploy runs `alembic upgrade head` through Fly `release_command`.

Required GitHub secret:

| Secret | Purpose |
|---|---|
| `FLY_API_TOKEN` | Fly deploy token for GitHub Actions |

Runtime Fly secrets:

| Secret | App | Purpose |
|---|---|---|
| `DATABASE_URL` | `st-api` | Set by `flyctl postgres attach` |
| `OPENAI_API_KEY` | `st-api` | Optional LLM calls |
| `OPENAI_BASE_URL` | `st-api` | Optional custom OpenAI-compatible gateway |
| `OPENAI_MODEL` | `st-api` | Optional model selection |
| `ST_SECRET_KEY` | `st-api` | JWT signing and credential encryption; legacy env name retained |
| `SMS_PROVIDER` | `st-api` | Set to `dry_run` until a real SMS vendor adapter is configured |
| `SMS_MOCK_RETURN_CODE` | `st-api` | Set to `false` outside local development so OTP codes are never exposed |
| `COROS_AUTOMATION_MODE` | `st-api` | `real` in production |

Rollback:

```bash
flyctl releases --app st-api
flyctl releases rollback v123 --app st-api
```

Database migration workflow:

```bash
DATABASE_URL=sqlite:///alembic_dev.db uv run alembic revision --autogenerate -m "your change"
rm alembic_dev.db
```

Review generated migration files before committing them.
