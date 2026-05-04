# Brand Cleanup: PerformanceProtocol

**Branch:** `brand-cleanup`

## Objective

Remove product-facing `ST`, Chinese product names, and marathon-only positioning from the web app, public metadata, API display metadata, skill names, and README. Use **PerformanceProtocol** as the only product brand.

## Context

Deployment PR #3 (`feat/fly-deploy` -> `main`) is open, mergeable, and CI passed. Production deployment, DNS, TLS, and health checks were already verified. This branch is intentionally separate from the Fly.io deployment PR.

## Files Likely To Change

- `README.md`
- `pyproject.toml`
- `app/main.py`
- `app/api/routes.py`
- `app/core/profile.py`
- `app/skills/marathon_st_default/`
- `app/skills/running_beginner/spec.yaml`
- `app/skills/user_extracted/coach_zhao_unified/`
- `web/app/login/page.tsx`
- `web/app/layout.tsx`
- `web/public/manifest.json`
- `web/components/EmptyPlanState.tsx`
- affected frontend tests under `web/__tests__/`
- relevant design docs under `docs/`

## Implementation Approach

- Keep internal compatibility identifiers unchanged where renaming would create migration risk: package name `st`, env vars such as `ST_SECRET_KEY` / `ST_DATABASE_URL`, `st_token`, Fly app names, database filenames, and historical route names.
- Replace user-visible brand with `PerformanceProtocol`.
- Remove `PerformanceProtocol · 表现提升协议` and similar Chinese product naming; README and metadata should present the product in English.
- Replace “smart marathon training” / marathon-only labels with endurance-training positioning where the UI is not specifically about a marathon race plan.
- Rename bundled skill display text from `ST Default Marathon Plan` to `PerformanceProtocol Marathon Plan`.
- Update tests that assert old brand text.

## Verification Commands

```bash
rg -n "ST|智能马拉松训练|表现提升协议|ST Default|ST team|ST Platform|ST ·" README.md pyproject.toml app web docs -g '!web/node_modules' -g '!web/.next' -g '!web/pnpm-lock.yaml'
uv run python -m unittest discover -s tests -v
cd web && pnpm test
cd web && pnpm type-check
```

Expected `rg` leftovers are only internal compatibility identifiers or historical task/dev logs, not current product-facing UI/docs.

## Progress

- [x] Confirm branch and existing brand residue.
- [x] Write scoped plan and acceptance criteria.
- [x] Replace login page brand copy with `PerformanceProtocol`.
- [x] Replace web metadata and PWA manifest brand copy.
- [x] Replace API title/root/health service display.
- [x] Rename bundled skill display names/authors and generated titles.
- [x] Rewrite README in English with explicit legacy/internal `ST_*` compatibility note.
- [x] Refresh design docs that still described the product as `ST`.
- [x] Update frontend tests for new copy.
- [x] Run verification.

## Acceptance Criteria

- Login page uses `PerformanceProtocol` and no Chinese product subtitle.
- Web app metadata/manifest uses `PerformanceProtocol`.
- README clearly states the product brand is `PerformanceProtocol`; `ST` is only documented as a legacy internal codename for environment variables/package paths.
- OpenAPI title and health responses use `PerformanceProtocol`.
- Bundled skill display names and generated workout titles do not start with `ST`.
- Frontend/backend tests and type-check pass.

## Out Of Scope

- Renaming Python package/module paths, database files, env vars, cookie keys, Fly app names, or GitHub repository name.
- Implementing the homepage design.
- Implementing SMS provider integration.
- Merging PR #3 or changing production DNS/Fly infrastructure.

## Review/Summary

Brand cleanup is complete on branch `brand-cleanup`.

Changed:

- Login page now displays `PerformanceProtocol` and `Endurance performance system`.
- App metadata and PWA manifest now use `PerformanceProtocol`.
- FastAPI title plus root/health service names now use `PerformanceProtocol`.
- Built-in skill display names changed to `PerformanceProtocol Marathon Plan` and `Beginner Runner Plan`.
- Generated default marathon workout titles no longer start with `ST`.
- README was rewritten in English and clarifies that `ST` remains only for legacy/internal compatibility identifiers.
- Outdated web design docs were refreshed to describe PerformanceProtocol, current auth, deployment, and route reality.

Verification:

- `uv run python -m py_compile app/main.py app/api/routes.py app/core/profile.py app/skills/marathon_st_default/skill.py app/skills/marathon_st_default/code/rules.py app/skills/running_beginner/skill.py app/skills/running_beginner/code/rules.py app/skills/user_extracted/coach_zhao_unified/skill.py`: pass
- `uv run python -m unittest discover -s tests -v`: 83/83 pass
- `cd web && pnpm test`: 62/62 pass
- `cd web && pnpm type-check`: pass
- Brand residue scan shows `ST` only in explicit legacy/internal codename notes and the local `/Users/paul/Work/ST` path.

Notes:

- `pnpm install --lockfile-only` could not complete because the sandbox proxy blocked npm registry metadata (`ERR_PNPM_META_FETCH_FAIL`). No lockfile change was needed for the package display-name change.
- Untracked `.DS_Store` files and `docs/homepage-design/` were present before finalization and were not touched by this task.
