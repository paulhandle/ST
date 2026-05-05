# I18n, Compact Brand Mark, SMS Prep, COROS Hardening

**Branch:** `feat/i18n-sms-coros-hardening`

## Objective

Prepare the product for bilingual Chinese/English UI, introduce a compact `P²` brand mark for constrained surfaces, prepare SMS OTP integration with international dialing-code selection, clean up merged local branches, and harden COROS onboarding/import behavior so first-time or disconnected users do not hit a dead end.

## Context

- PR #4 is merged and deployed to fly.io.
- Production web/API are healthy: homepage is public, `/dashboard` remains protected, web/API certs are active.
- Current login OTP is mock-only: backend returns `otp_code` directly and accepts only mainland China mobile numbers (`^1[3-9]\d{9}$`).
- App UI currently mixes Chinese operational copy with English brand/homepage copy. User wants Chinese and English versions, with code and technical identifiers staying English.
- Compact icon requirement: use `P²`, with italic `P` and the `2` rendered as a true upper-right superscript; use this instead of the full brand name in icon or constrained spaces.
- Political naming requirement: country/region selector must use correct wording for Taiwan, e.g. `Taiwan, China` / `中国台湾`.

## Files Likely To Change

- `tasks/todo.md`
- `tasks/devlog.md`
- `README.md`
- `app/api/auth.py`
- `app/schemas.py`
- `app/core/config.py`
- new backend SMS provider module under `app/tools/sms/`
- backend auth/SMS tests under `tests/`
- `web/components/BrandLogo.tsx`
- new frontend i18n helpers under `web/lib/i18n/`
- `web/app/login/page.tsx`
- relevant homepage/app shell components using brand mark or language text
- frontend tests under `web/__tests__/`
- COROS onboarding/plan generation code in `web/app/onboarding/page.tsx`, `web/app/plan/generate/page.tsx`, and possibly `app/api/routes.py`

## Implementation Approach

1. [x] Local branch cleanup:
   - [x] Switch from merged `brand-cleanup` to latest `main`.
   - [x] Delete merged local `brand-cleanup`.
   - [x] Create this feature branch.

2. [x] Bilingual UI foundation:
   - [x] Add a minimal local i18n layer for web copy with `en` and `zh`.
   - [x] Use a cookie/localStorage-backed language preference, defaulting to browser language when possible.
   - [x] Add a compact language toggle in public, login, and authenticated app surfaces.
   - [x] Cover fixed UI copy across the primary authenticated app shell/pages. Backend/content data such as workout titles, skill descriptions, and adjustment reasons remains source-language text.

3. [x] Compact brand mark:
   - [x] Extend `BrandLogo` with a compact `P²` mark variant.
   - [x] Ensure the `2` is implemented as superscript, visually upper-right, and the `P` remains italic.
   - [x] Use the mark where space is constrained: app topbar compact logo and homepage footer.

4. [x] SMS provider preparation:
   - [x] Add backend SMS provider abstraction with `mock` provider as current default.
   - [x] Add config variables for provider selection and future credentials without requiring real vendor credentials now.
   - [x] Normalize phone numbers to E.164 from `country_code + national_number`.
   - [x] Keep test/dev mock responses returning `otp_code`; production/provider mode must not expose the code.
   - [x] Add country/region selector on login with a short mainstream list: China mainland, United States, United Kingdom, Singapore, Hong Kong SAR, Taiwan, China, Japan, Australia.
   - [x] Keep identifiers/code in English.

5. [x] COROS hardening:
   - [x] Make plan generation resilient when COROS is not connected, import fails, assessment fails, or API payload is malformed.
   - [x] Surface clear next actions instead of blocking the user at assessment failure.
   - [x] Preserve existing fake/real COROS tests and add focused regression coverage for disconnected/no-history cases.

6. [x] COROS settings and i18n cleanup:
   - [x] Translate the Plan tab empty-state copy in Chinese mode.
   - [x] Add a real `/settings/coros` flow instead of the current 404 link.
   - [x] Cover COROS settings connect/status/import behavior with frontend tests.
   - [x] Re-run focused frontend tests and type-check.

7. [x] Duplicate COROS account hardening:
   - [x] Fix `_device_account()` so duplicate historical rows do not crash dashboard/status with `MultipleResultsFound`.
   - [x] Add backend regression coverage for duplicate COROS accounts.
   - [x] Re-run focused Block A1 tests and full backend unittest.

## Verification Commands

```bash
uv run python -m unittest discover -s tests -v
cd web && pnpm test
cd web && pnpm type-check
cd web && pnpm build
```

Manual/visual verification:

- `/` can switch between English and Chinese copy.
- `/login` can switch language and choose a country/region code.
- Authenticated app shell and primary pages can switch fixed UI labels between English and Chinese.
- Login sends normalized phone data and still works with mock OTP.
- Compact app topbar/logo surfaces use `P²` without text overflow.
- Plan generation does not dead-end if COROS is disconnected or has no importable history.

## Acceptance Criteria

- Bilingual foundation exists and covers homepage/login/auth-critical surfaces.
- Compact `P²` mark is reusable and visually correct.
- Login region selector includes the current mainstream launch list, including `Taiwan, China` / `中国台湾`.
- Backend OTP accepts normalized international phone input through a provider abstraction.
- Mock OTP remains testable locally; production provider mode does not return the OTP code.
- COROS disconnected/no-history flows have a usable fallback path.
- All tests/type-check/build pass.

## Out Of Scope

- Selecting or paying for a real SMS vendor.
- Translating backend/content data such as generated workout titles, skill descriptions, adjustment reasons, methodology markdown, and imported activity titles.
- Real COROS selector remapping or new browser automation work beyond failure handling.
- Changing internal `ST_*` compatibility identifiers.

## Review/Summary

- Implemented web i18n foundation for homepage, login, onboarding, app shell, and primary authenticated fixed UI using `en`/`zh`, `localStorage`, cookie persistence, and browser-language defaulting.
- Added reusable compact `P²` brand mark in `BrandLogo`; the `P` remains italic and the `2` is a superscript. App topbar and homepage footer use the compact mark.
- Prepared SMS OTP integration with `app/tools/sms/`, runtime SMS config, E.164 normalization, `mock` and `dry_run` providers, and no OTP exposure outside configured mock mode.
- Updated login to send `country_code + national_number`, with country/region options including `Taiwan, China` / `中国台湾`.
- Hardened `/plan/generate` so COROS import/assessment/skills failures fall back to a conservative assessment and let the user continue to goal setup.
- Added `/settings/coros` so Settings > COROS sync no longer 404s; the page can view status, connect credentials, and manually import history.
- Fixed the Plan tab empty state Chinese copy.
- Hardened device-account lookup so duplicate local COROS rows no longer crash dashboard/status.
- Updated `.env.example` and `README.md` for SMS config and the new OTP request shape.
- Deleted merged local branches `feat/block-c-screens`, `feat/block-d-nav-and-auth`, and `feat/fly-deploy`.
- Verification passed: backend unittest 90/90, frontend vitest 76/76, frontend build passed, and frontend type-check passed after Next rebuilt `.next/types`.
