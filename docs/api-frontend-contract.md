# API ↔ Frontend Contract

Reconciles the wireframes in `var/design/` with the backend API.
Every screen's data needs are mapped to either an existing endpoint or
a new one to build.

---

## Tab structure (locked)

```
[ 概览 Dashboard ]  [ 今天 Today ]  [ 本周 Week ]  [ 计划 Plan ]  + Coach FAB
```

---

## 1. Dashboard (`/dashboard`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Status bar | greeting, weekday, week index, active skill chip, last sync | `GET /athletes/{id}/dashboard` (NEW, aggregate) |
| Adjustment banner | pending adjustment id + headline | included in dashboard |
| Today compressed | StructuredWorkout (today) + match status | included |
| Goal card | target time, race date, days_until, predicted finish trend (12 pts), delta | included |
| Volume card | last 8 weeks of {executed_km, planned_km} | included |
| Week strip | 7 days of {date, weekday, status} | included |
| Recent activities | last 5–7 activities + match info | included |
| Readiness panel | resting_hr, training_load_7d, lthr, ltsp + trend arrows | included |
| Footer | skill name + version, last sync time | included |

**Required endpoint**: `GET /athletes/{id}/dashboard` — see schema in §6.

---

## 2. Today (`/today`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Header | active skill chip, last sync | `GET /athletes/{id}/today` (existing) |
| Workout title + week tag | week_index, title, purpose | existing |
| Big numbers row | distance_m, duration_min, pace range, HR range, RPE range | existing |
| Pace target viz | pace_min/max sec/km | existing |
| Adherence banner | `adaptation_notes` field on workout | existing |
| Steps list | `WorkoutStep[]` | existing |
| Yesterday compare | matched activity for yesterday + diff | **enhance** — yesterday's workout + match info |
| Mark done buttons | 3 buttons → POST feedback | `POST /workouts/{id}/feedback` (existing) |

**No new endpoints**, but `today` response should also include yesterday's
workout/activity for the inline compare card (variant C).

---

## 3. Week (`/week`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Header | week_index, phase, total_km/plan_km, quality count | `GET /plans/{id}/week?week_index=N` (existing) |
| Day rows / strip | 7 days each with {date, weekday, title, km, min, status} | existing |
| Volume bar (variant B) | week's executed/planned km | existing |
| Prev / next week | navigation | use `?week_index=N±1` |

**No new endpoints**.

---

## 4. Plan (`/plan`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Header | plan title, weeks, start_date, race_date, is_confirmed | `GET /marathon/plans/{id}` (existing) |
| Phase strip | phases (e.g. base 6w / build 6w / peak 4w / taper 2w) | **derive** from plan_weeks ratios |
| Volume curve | weekly km for all weeks (planned + executed) | **NEW** `GET /plans/{id}/volume-curve` |
| Week list | each week's volume + day status dots | **derive** from existing week endpoint |

**New endpoint**: `GET /plans/{id}/volume-curve` — returns an array of
`{week_index, executed_km, planned_km, phase, is_recovery}`. (Could also be
absorbed into `GET /marathon/plans/{id}`.)

---

## 5. Skills (`/skills/*`)

| Screen | Data needed | Source |
|--------|-------------|--------|
| Skill picker | skills list with active flag, tags | `GET /skills` (existing) |
| Methodology reader | full skill.md | `GET /skills/{slug}` (existing) |
| Switch dialog | counts: completed / missed / future-to-regenerate; days affected; new skill applicable | **NEW** `GET /plans/{id}/regenerate-preview?skill_slug=X` |
| Apply switch | actual regeneration | `POST /plans/{id}/regenerate-from-today` (existing) |

**New endpoint**: `GET /plans/{id}/regenerate-preview?skill_slug=X` — returns
`{frozen_completed: N, frozen_missed: M, regenerated_count: K, weeks_affected: int, applicable: bool, applicability_reason: str}`. No DB writes.

---

## 6. Adjustment panel (`/adjustments/{id}`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Reason text | from adjustment | `GET /plan-adjustments/{id}` (NEW) |
| Recommendation text | from adjustment | included |
| Affected workouts | `[{workout_id, date, title, change_summary, before, after}]` | included — **extend model** |
| Accept | apply → mutate workouts | **NEW** `POST /plan-adjustments/{id}/apply` (different from current `confirm` which only changes status) |
| Reject | mark rejected | existing |

**Backend changes**:
- Add `affected_workouts_json` column to `PlanAdjustment`
- New `POST /plan-adjustments/{id}/apply` that confirms AND mutates the
  referenced workouts atomically
- `evaluate_plan_adjustment()` should populate `affected_workouts_json` with
  per-workout diffs

---

## 7. Activity history (`/activities`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Activity rows | date, title (planned or "自由跑"), executed km, planned km, match status, delta string | `GET /athletes/{id}/history` (existing, **enhance**) |

**Backend change**: enrich `AthleteActivityOut` schema to include:
- `matched_workout_title: str | None`
- `matched_workout_planned_distance_m: float | None`
- `match_status: "completed" | "partial" | "miss" | "rest" | "unmatched"`
- `delta_summary: str | None` (e.g. "配速 +12s/km", "HR +3 bpm") — formatted from `compute_match_diff()`

---

## 8. Coach (`/coach`)

| Section | Data needed | Source |
|---------|-------------|--------|
| Conversation history | message bubbles | **NEW** `GET /coach/conversations/{athlete_id}` |
| Send message | user input → AI reply + suggested adjustments | **NEW** `POST /coach/message` |
| Quick-action chips | structured suggestions ("调整时间", "不用") | within message payload |

**New backend**:
- Add `CoachMessage` model: `id, athlete_id, role (user/coach), text, suggested_actions_json, created_at`
- `POST /coach/message` calls existing `interpret_checkin()` and persists
- `GET /coach/conversations/{athlete_id}?limit=50` returns recent thread

---

## 9. Empty states

| State | Trigger | Behavior |
|-------|---------|----------|
| No plan | athlete has no `TrainingPlan` | dashboard / today render the "set goal" CTA + skill browser link |
| Missed week | last 7 days >50% missed | dashboard shows a special banner with the methodology's 缺训不补 quote + auto-degraded workout for today |

**Backend addition**: a small helper `compute_recovery_recommendation(plan, recent_activities)` returning either `None` (normal) or `{"degraded_workout": ..., "ethos_quote": "..."}`. Surface inside `GET /athletes/{id}/today`.

---

## Aggregate endpoint schema (for the dashboard)

```typescript
// GET /athletes/{id}/dashboard
{
  athlete: { id, name, current_skill: { slug, name, version } },
  greeting: { time_of_day, date, weekday_short, week_index, week_phase },
  pending_adjustment: null | { id, reason_headline },
  today: {
    plan_id, week_index,
    workout: StructuredWorkoutOut | null,           // null = rest
    matched_activity: { id, distance_m, duration_sec, avg_pace_sec_per_km, status } | null
  },
  this_week: {
    plan_id, week_index, total_weeks, phase, is_recovery,
    days: [{ date, weekday, title, distance_km, duration_min, status }],
    completed_km, planned_km, completed_quality, planned_quality
  },
  goal: {
    label,                    // e.g. "sub-3:30"
    race_date, days_until, target_time_sec,
    prediction_history: [{ measured_at, predicted_time_sec }],   // last 12
    monthly_delta_sec: number    // +ve = slower, -ve = faster
  },
  volume_history: [             // last 8 weeks
    { week_index, week_label, executed_km, planned_km, completion_pct }
  ],
  recent_activities: [          // last 7
    { id, started_at, title, distance_km, duration_min, avg_pace_sec_per_km, avg_hr, match_status, delta_summary }
  ],
  readiness: {
    resting_hr, resting_hr_trend,
    weekly_training_load, weekly_training_load_trend,
    lthr, ltsp_sec_per_km
  },
  meta: {
    skill_slug, skill_name, skill_version,
    last_sync_at, last_sync_status
  }
}
```

---

## Endpoint summary — Block A1 to build

```
GET  /athletes/{id}/dashboard                aggregate everything for the home tab
GET  /plans/{id}/volume-curve                planned + executed weekly km for all weeks
GET  /plans/{id}/regenerate-preview          counts only, no writes
GET  /plan-adjustments/{id}                  full adjustment incl. affected_workouts
POST /plan-adjustments/{id}/apply            commit the diff (current confirm only changes status)
POST /coach/message                          AI coach chat send (uses interpret_checkin)
GET  /coach/conversations/{athlete_id}       recent message history
```

Plus enhancements (no new routes):

```
GET  /athletes/{id}/history                  enrich each row with matched workout + delta_summary
GET  /athletes/{id}/today                    add yesterday_workout + yesterday_activity for inline compare
                                             add recovery_recommendation for missed-week empty state
```

---

## Frontend stack recommendation

Given mobile-first, Chinese-primary, single-user, fast iteration:

- **Framework**: Next.js 14 (App Router) — file-system routing, easy deploy
- **Language**: TypeScript
- **Styling**: Tailwind CSS — matches Claude Design's utility class style
- **Components**: shadcn/ui — copy-paste, no runtime dep, customizable
- **Charts**: Recharts (line + bar both straightforward)
- **Fonts**: Kalam + Caveat from Google Fonts (matches the wireframe handwritten aesthetic)
- **Data fetching**: SWR or TanStack Query — built-in caching for the
  dashboard refresh story
- **API client**: hand-rolled fetch wrapper with TS types generated from
  Pydantic schemas (`scripts/gen_ts_types.py` to regenerate from
  `app/schemas.py`)

Project layout:

```
web/
├── app/                    Next.js routes
│   ├── (tabs)/dashboard/   each tab as a route
│   ├── (tabs)/today/
│   ├── (tabs)/week/
│   ├── (tabs)/plan/
│   ├── coach/              modal/sheet
│   └── settings/
├── components/             reusable UI primitives
├── lib/api/                generated types + fetch client
├── lib/hooks/               SWR-wrapped data hooks
└── styles/                 globals.css + tailwind config
```

Local dev: `pnpm dev` on port 3000, backend on port 8000, CORS already
configured.

---

## Implementation order

1. **Block A1 backend endpoints** (this document, ~1 day)
2. **TypeScript types generation** from Pydantic (~2h)
3. **Frontend scaffolding**: Next.js + Tailwind + shadcn + base layout with bottom-nav tabs (~half day)
4. **Dashboard tab** end-to-end: data hook + page + sub-components matching variant A (~1 day)
5. **Today tab** with one of the 3 pace visualizations (start with range-bar variant A) (~1 day)
6. **Week tab** + **Plan tab** (~half day each)
7. **Skill picker + methodology reader + switch dialog** (~1 day)
8. **Adjustment panel + Coach sheet + activity history** (~1 day)
9. **Empty states + onboarding flow** (~half day)

Total ~7–8 working days for a polished v1 of the web frontend.
