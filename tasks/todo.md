# Homepage + Global Theme

**Branch:** `brand-cleanup`

## Objective

Implement the Stitch-designed public homepage from `docs/homepage-design/`, make `/` public, and propagate the homepage's italic technical logo plus black/orange visual system across the web app.

## Prior Context

Brand cleanup is already complete on this branch:

- Product-facing brand is `PerformanceProtocol`.
- Old `ST` product copy and Chinese product names were removed.
- README is English and documents `ST_*` only as legacy/internal compatibility.
- Verification already passed: backend 83/83, frontend 62/62, type-check.

## Source Design

Read:

- `docs/homepage-design/stitch_performanceprotocol_endurance_platform/DESIGN.md`
- `docs/homepage-design/stitch_performanceprotocol_endurance_platform/code.html`
- `docs/homepage-design/stitch_performanceprotocol_endurance_platform/screen.png`

Design requirements extracted:

- Deep charcoal app background.
- Safety orange primary action color.
- Electric blue only for secondary data/sync states.
- Inter for functional UI; Space Grotesk for data labels and metrics.
- Logo: uppercase, bold, italic, tight technical wordmark.
- Sharp/engineered panels with crisp borders and tonal layering.
- Avoid gradients and soft decorative effects.

## Files Likely To Change

- `web/app/page.tsx`
- `web/middleware.ts`
- `web/app/globals.css`
- `web/app/layout.tsx`
- `web/app/login/page.tsx`
- `web/app/(tabs)/layout.tsx`
- shared components under `web/components/`
- frontend tests under `web/__tests__/`
- `tasks/devlog.md`

## Implementation Approach

- Add a reusable `BrandLogo` component so the italic wordmark is shared by homepage, login, and authenticated app chrome.
- Replace the root redirect with a real public homepage based on Stitch's structure: nav, hero, product preview, data panels, workflow/value sections, final CTA, footer.
- Update middleware so `/` is public while authenticated app routes stay protected.
- Move the black/orange theme into CSS tokens so existing pages inherit the new system without broad one-off rewrites.
- Keep functional page layouts intact; theme unification should be token-driven first, targeted component edits only where needed.
- Preserve existing Chinese product workflow copy inside app where it is not brand naming; this task is visual/theme and homepage, not full i18n.

## Progress Checklist

- [x] Read homepage design source under `docs/homepage-design/`.
- [x] Replace `/` redirect with public homepage implementation.
- [x] Add shared italic `BrandLogo` wordmark.
- [x] Apply shared logo to homepage, login, and authenticated app chrome.
- [x] Update global tokens to black/orange technical palette.
- [x] Keep `/` public while preserving auth protection for app routes.
- [x] Run frontend unit tests.
- [x] Run frontend type-check.
- [x] Run production build.
- [x] Run backend regression tests.
- [x] Manually verify homepage/login/app routing and visual consistency.
- [x] Update devlog with implementation and verification results.
- [x] Add final review summary.

## Verification Commands

```bash
cd web && pnpm test
cd web && pnpm type-check
cd web && pnpm build
uv run python -m unittest discover -s tests -v
```

Manual/visual verification:

- Run `cd web && pnpm dev`.
- Verify `/` renders homepage without auth.
- Verify `/login` still renders.
- Verify `/dashboard` still redirects to `/login` without auth.
- Check homepage, login, and at least one authenticated page share the same black/orange theme and italic logo.

## Acceptance Criteria

- `/` is a public homepage matching the Stitch direction closely enough to be recognizable.
- Homepage primary CTA links to `/login`; methodology CTA links to `/skills` or an appropriate public/placeholder target without breaking.
- Middleware allows `/` publicly but keeps app routes protected.
- Login and authenticated app chrome use the same italic uppercase logo treatment.
- Global visual tokens are black/orange-first across pages.
- Frontend tests/type-check/build pass.
- Backend tests still pass because middleware/API behavior changes should not affect backend.

## Out Of Scope

- SMS provider integration.
- Full authenticated app redesign.
- New marketing CMS/content system.
- Removing all Chinese operational copy from the app.
- Modifying Fly infrastructure or production DNS.

## Review/Summary

Homepage and global theme work is complete on branch `brand-cleanup`.

Changed:

- Replaced the root `/` redirect with a public PerformanceProtocol homepage based on the Stitch design.
- Added shared `BrandLogo` and applied the italic uppercase wordmark to homepage, login, authenticated app topbar, and footer.
- Updated middleware so `/` and `/login` are public while app routes such as `/dashboard` remain protected.
- Swapped the frontend font setup to Inter + Space Grotesk and moved the app to black/charcoal, safety orange, and electric-blue data accents.
- Rethemed primary buttons, selected states, panels, tab/app chrome, coach sheet, skill dialogs, plan controls, workout controls, and related shared components to match the homepage system.
- Fixed responsive homepage typography after screenshot verification caught mobile horizontal overflow and desktop title overlap risk.

Verification:

- `cd web && pnpm test`: 62/62 pass.
- `cd web && pnpm type-check`: pass.
- `cd web && pnpm build`: pass; 15 app routes generated and middleware compiled.
- `uv run python -m unittest discover -s tests -v`: 83/83 pass.
- `curl -i http://127.0.0.1:3000/`: HTTP 200.
- `curl -i http://127.0.0.1:3000/login`: HTTP 200.
- `curl -i http://127.0.0.1:3000/dashboard`: HTTP 307 redirect to `/login` without auth.
- Playwright visual checks passed for desktop and mobile homepage plus mobile login. Assertions covered visible logo, hero title, CTA, product preview, dark background token, orange accent token, and no mobile horizontal overflow. Screenshots are in `/private/tmp/pp-homepage-check/`.

Notes:

- `pnpm build` initially failed in the sandbox because Next.js needed to fetch Google Fonts; reran with approved network permission and the final build passed.
- No README change was needed because this did not alter startup commands, environment configuration, dependencies, or API contracts.
- Untracked `.DS_Store` files and `docs/homepage-design/` remain untouched.
