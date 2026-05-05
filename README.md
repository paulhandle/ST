# PerformanceProtocol

[performanceprotocol.io](https://performanceprotocol.io)

PerformanceProtocol is an endurance training platform for serious athletes. The current product supports the complete road-running loop for marathon and half-marathon training, with trail running, triathlon, and long-distance cycling planned as future extensions.

The product-facing brand is **PerformanceProtocol**. `ST` remains only as a legacy internal codename in package names, database filenames, environment variables such as `ST_SECRET_KEY` / `ST_DATABASE_URL`, and a few compatibility paths. Do not use `ST` in product UI, marketing copy, OpenAPI display names, or user-facing documentation.

## Product Loop

1. Import historical training data and performance metrics from COROS.
2. Assess current running fitness and target feasibility.
3. Generate a structured training cycle from a selected training skill.
4. Let the athlete confirm the plan.
5. Sync confirmed future workouts to the COROS calendar.
6. Track execution and propose weekly adjustments.

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

Copy `.env.example` to `.env` for local credentials. `.env` is ignored by git.

```bash
cp .env.example .env
```

Important variables:

| Variable | Purpose |
|---|---|
| `ST_SECRET_KEY` | Legacy env var for JWT signing and local credential encryption. Keep the name for compatibility. |
| `ST_DATABASE_URL` | Legacy env var for local DB override. Defaults to `sqlite:///st.db`; tests use `sqlite:///st_test.db`. |
| `COROS_AUTOMATION_MODE` | `fake` for tests/dev; `real` enables the direct COROS API client. |
| `COROS_USERNAME` / `COROS_PASSWORD` | Local probe credentials only. The app stores user credentials through `/coros/connect`. |
| `COROS_TRAINING_HUB_URL` | Training Hub probe base URL. |
| `COROS_HEADLESS` | Set `false` when running browser probes interactively. |
| `SMS_PROVIDER` | `mock` by default. `dry_run` exercises provider wiring without returning OTP codes. |
| `SMS_MOCK_RETURN_CODE` | `true` in local/test mock mode to include `otp_code` in responses; set `false` outside local development. |
| `SMS_API_KEY` / `SMS_API_SECRET` / `SMS_SENDER_ID` | Reserved for the future real SMS vendor adapter. |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | Optional LLM configuration for skill personalization and coach interpretation. |

## Auth

The app currently uses phone OTP login and a 30-day bearer token. Development/test mode can return a mock OTP code. Phone numbers are normalized to E.164. The preferred request shape is `country_code + national_number`; legacy mainland China `phone` requests are still accepted for compatibility.

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
| `/onboarding` | First-run setup: COROS, goal, training days, confirmation |
| `/dashboard` | Training overview |
| `/today` | Redirects to today's workout detail |
| `/week` | Current-week training calendar |
| `/plan` | Plan overview and pending adjustment entry |
| `/plan/generate` | Plan generation wizard |
| `/activities` | Calendar strip and activity timeline |
| `/skills` | Skill selection |
| `/skills/[slug]` | Skill methodology detail |
| `/adjustments/[id]` | Adjustment detail and apply/reject flow |
| `/settings` | Training, data, and account settings |

## Key API Routes

- `GET /health`
- `GET /sports`
- `GET /skills`
- `GET /skills/{slug}`
- `POST /auth/send-otp`
- `POST /auth/verify-otp`
- `GET /auth/me`
- `POST /athletes`
- `GET /athletes/{id}/dashboard`
- `GET /athletes/{id}/today`
- `GET /athletes/{id}/week`
- `GET /athletes/{id}/history`
- `GET /athletes/{id}/calendar`
- `POST /coros/connect`
- `POST /coros/import`
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
