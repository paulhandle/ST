# ST Training Platform — Web Design Brief

> Self-contained context document for designing ST's web frontend.
> Backend is already built and stable. This doc describes **what to design**
> and **what data is available**, not how to implement the backend.

---

## 1. What ST is

**ST** is a personal training platform for endurance athletes (currently
single-user, the developer-athlete himself; multi-user is future work). It
closes the loop between a wrist device (COROS Training Hub), a methodology
(coach-style training plan), and the athlete's day-to-day execution.

The product's three differentiators:

1. **Bring-your-own methodology** via "Skills" — a Skill is a pluggable
   training methodology (e.g. "Coach Zhao's unified marathon method", "80/20
   polarized", "Norwegian threshold"). Same engine generates plans from any
   skill.
2. **Skill-creator** — extracts a Skill from the athlete's own past
   coach-prescribed training. The platform reads historical training plans
   from COROS, distills the methodology, and turns it into a reusable Skill.
3. **Closed loop with COROS** — pulls history automatically, pushes
   confirmed workouts to the COROS calendar/watch, monitors execution,
   suggests adjustments.

Target language: **Chinese (Simplified)** as primary, English fallback.
Workout names, coach names, and athlete-facing copy are all in Chinese.

Single-user MVP. No login flow needed; assume one athlete.

---

## 2. Tech reality check

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy + SQLite. Already running.
- **API**: REST, JSON, runs on `http://127.0.0.1:8000` locally.
- **No deployment yet** — runs on the athlete's Mac; web frontend will live
  alongside.
- **CORS / auth**: not configured; design for single-origin, no-auth MVP.
- **Frontend stack**: open. Recommend modern (React/Next or SvelteKit) but
  the design should be tech-agnostic.
- **Mobile-first**: this is checked daily on phone before runs. Desktop is
  secondary but should look good too.

---

## 3. Core domain model (what shows up in UI)

### Athlete profile
A single person. Stored in two places:
- **TOML profile** (`~/.st_profile.toml`): static identity — name, age, sex,
  height_cm, weight_kg, years_running, injury_history, last_race_distance,
  last_race_time, notes.
- **DB athlete row**: minimal — id, name, sport, level, weekly_training_days.

### Race goal
What the athlete is training for: target distance, optional target time,
race date, training_start_date, plan_weeks (8–24), feasibility status
(`accepted` / `warning` / `rejected`).

### Training plan
A generated plan tied to a race goal:
- `title` (e.g. "赵可方法论 全马 3:30 计划")
- `mode` (`polarized` / `pyramidal` / `threshold_focused` / `base_build_peak`)
- `weeks` (count, e.g. 18)
- `start_date`, `race_date`, `target_time_sec`
- `status`: `draft` / `active` / `completed` / `archived`
- `is_confirmed` (bool — gates COROS sync)
- `skill_slug` that produced it (e.g. `coach_zhao_unified`)

### Structured workout (a single training session)
Fields the UI cares about:
- `scheduled_date`, `week_index`, `day_index` (1-7)
- `discipline` (`run` | `strength` | `bike` | `swim`)
- `workout_type` (`easy_run` | `long_run` | `marathon_pace` | `threshold` | `speed` | `recovery_run` | `strength`)
- `title` (e.g. "W05 速度训练 6x200" — week + workout name)
- `purpose` (one-line why)
- `duration_min`, `distance_m`
- `target_pace_min_sec_per_km`, `target_pace_max_sec_per_km` (e.g. 280–310 → 4:40–5:10/km)
- `target_hr_min`, `target_hr_max`, `rpe_min`, `rpe_max`
- `adaptation_notes` (free text — for `coach_zhao_unified` this includes
  「完成 > 配速；今日课今日做；速度课恢复跑保持步频」)
- `status`: `draft` / `confirmed` / `synced` / `completed` / `missed`
- `steps[]` (see below)

### Workout step (interval inside a workout)
- `step_index`, `step_type` (`warmup` / `work` / `cooldown` / `recovery`)
- `duration_sec` and/or `distance_m`
- `target_type` (usually `pace_sec_per_km`)
- `target_min`, `target_max` (sec/km — display as `M:SS`)
- `repeat_count` (e.g. `5×` strides)
- `notes` (e.g. "75% LTHR · 5× repeat · rest 30s")

### Athlete activity (executed run)
What COROS pulled back after the run:
- `started_at`, `discipline`, `distance_m`, `duration_sec`
- `avg_pace_sec_per_km`, `avg_hr`, `max_hr`, `training_load`
- `feedback_text` (free-text from COROS app, optional)

### Plan adjustment
Weekly suggestion:
- `reason`, `recommendation`, `effective_start_date`, `effective_end_date`
- `status`: `proposed` / `confirmed` / `rejected`

---

## 4. The Skill system (critical for UI)

A Skill is a **methodology** that produces plans. The platform ships with
two skills today:

| Skill slug | Display name | Origin | Tags |
|------------|--------------|--------|------|
| `marathon_st_default` | ST Default Marathon Plan | Built-in fallback | hybrid · base-build-peak |
| `coach_zhao_unified` | Coach Zhao Unified Marathon Methodology | Distilled from athlete's COROS history | seasonal · northern-china · low-LSD · working-professional · tempo-and-strides · completion-first |

Each Skill has:
- `slug`, `name`, `version`, `sport`, `supported_goals` (e.g. `["finish", "target_time"]`)
- `description` (one paragraph)
- `author`
- `tags[]`
- A long-form `skill.md` (the methodology document) — Markdown that the UI
  can render in a "Read methodology" modal.

The web UI should:
- **List available skills** with their tags + one-line description
- **Show a skill's full methodology** on demand (render the skill.md)
- **Let the user pick which skill** generates the next plan
- **Show which skill produced the active plan** as a badge / link

### Skill switch semantics (already decided)

When the user switches skill mid-cycle:
1. Past completed/missed workouts stay frozen.
2. From **today forward**, the rest of the plan is regenerated by the new skill.
3. New skill must satisfy `applicable(athlete, goal, remaining_weeks)`.
4. UI must show a confirmation dialog stating exactly: "X completed sessions
   remain unchanged. Y future sessions will be regenerated by `<new skill>`."

### User-extracted skills

The skill-creator flow (planned, not yet built) reads the athlete's COROS
history → analyzes methodology → user reviews + edits → writes a new Skill
to disk. The web UI will eventually need:
- "Create a new Skill from my history" entry point
- A wizard that walks through analysis → review → naming → save
- This is **future work**; v1 web doesn't need it. But the surface where
  user-extracted skills will appear (next to built-in ones) is `app/skills/user_extracted/<slug>/`.

---

## 5. Daily / weekly workflows the UI must serve

### Daily (highest frequency, most polished)

**Morning (before run, on phone)**:
- Open app → see today's workout immediately (this is the home screen)
- Detailed view: title, distance, duration, target paces, all interval steps
- See `adaptation_notes` (the methodology's adherence rules)
- See yesterday's execution if any (matched / unmatched / skipped)

**After run (evening, on phone)**:
- See COROS-imported activity for today
- Did it match the plan? (auto-determined: same discipline + close in time)
- Mark execution: 「完成 / 部分完成 / 跳过」 + optional note + RPE 1–10
- Optionally trigger COROS pull manually (button)

### Weekly (Sunday or Monday)

- Week view: 7 days side-by-side, today highlighted
- Total volume planned vs executed
- See upcoming week's structure
- Optional: ask for a plan adjustment if anything's off

### Occasional (one-off events)

- Set up a new race goal → generate plan → confirm → sync to COROS
- Switch active Skill → preview new plan → confirm
- Browse plan as a calendar (month view)
- Read the methodology of the active Skill
- Manage device connection (COROS login state, last sync time)
- Quick chat-style check-in with the AI coach (already exists as backend
  function — UI can wrap as a chat panel)

---

## 6. What the web frontend should support (priorities)

### P0 — must-have for daily use

1. **Today screen** (default home). Detailed workout card with:
   - Workout title + week tag (e.g. `W05 · 速度训练 6x200`)
   - Discipline icon, distance, duration, calories estimate
   - Target pace range, target HR range (when available), target RPE band
   - Step-by-step breakdown (each `WorkoutStep` shown as a row)
   - Coach's adherence notes prominently displayed
   - Big "Mark complete" / "Mark skipped" / "Couldn't finish" buttons
   - If today's COROS activity already imported: show side-by-side comparison

2. **Manual COROS sync button**. Triggers a backend pull of recent
   activities. Shows last sync time. Failures should be visible and human.

3. **Week view**. 7 columns × 1 row. Each column shows the workout's title,
   distance, duration, status badge. Today is highlighted. Tap a day → drill
   into that day's detail (same view as Today screen but for a different date).

4. **Plan overview**. Whole plan as a vertical list of weeks. Each week
   shows its total km, total min, count of quality sessions. Expand a week
   → see the days. Visual cue for phase (base / block / taper).

5. **Skill picker** — when there's no plan, or user explicitly switches:
   - List skills with tags, description
   - "View methodology" button → modal that renders skill.md
   - Generate plan from selected skill

### P1 — important for sustainability

6. **Adjustment panel** — when an adjustment is suggested, show reason +
   recommendation, with `Accept` / `Reject` buttons.
7. **AI coach chat** — already a backend function. Wrap as a side panel
   that takes user message + recent context, returns reply + suggested
   plan changes.
8. **Skill switch dialog** with the "X completed, Y regenerated" confirmation.
9. **Activity history** — list of recent COROS activities with the matched
   plan workout (if any).

### P2 — nice-to-have

10. **Calendar / month view** for browsing the plan.
11. **Profile editor** — edit the TOML-backed profile from the web.
12. **Settings** — auto-sync schedule, COROS login state, language toggle.
13. **Volume curve chart** — show planned vs executed weekly km as a line
    chart over the plan's lifetime.

### P3 — future / not for v1

- Skill-creator wizard
- Multi-athlete (coach mode)
- Notifications / push
- Mobile native apps

---

## 7. The current API surface (what the frontend calls)

These endpoints exist. JSON. No auth.

### Read

```
GET  /health                              → server liveness
GET  /sports                              → list of supported sports
GET  /skills                              ⚠ NOT YET IMPLEMENTED — needs to be added
GET  /athletes/{id}                       → athlete profile
GET  /athletes/{id}/history?days=30       → recent activities
GET  /athletes/{id}/assessment            → cached running assessment
GET  /plans?athlete_id=1                  → list plans for athlete
GET  /plans/{id}                          → full plan (sessions only)
GET  /marathon/plans/{id}                 → full marathon plan with structured workouts
GET  /coros/status                        → COROS account/connection state
GET  /sync-tasks?plan_id=X                → recent sync tasks
```

### Write

```
POST /athletes                            → create athlete
POST /athletes/{id}/assessment/run        → recompute assessment
POST /coros/connect                       → save COROS credentials
POST /coros/import?athlete_id=1           → trigger COROS history pull
POST /marathon/goals                      → create race goal
POST /marathon/plans/generate             → generate a marathon plan
                                            ⚠ currently hardcoded to skill;
                                              needs `skill_slug` parameter
POST /plans/{id}/confirm                  → confirm plan + lock workouts
POST /plans/{id}/sync/coros               → push confirmed plan to COROS
POST /plans/{id}/adjustments/evaluate     → ask for adjustment suggestion
POST /plan-adjustments/{id}/confirm       → accept an adjustment
PATCH /plans/{id}/status                  → update plan status
```

### Endpoints the web will need but don't exist yet

The frontend designer should assume these are coming and design as if they
exist. Backend will catch up.

```
GET  /skills                              → list all skills with manifests
GET  /skills/{slug}                       → full skill detail incl. skill.md
GET  /athletes/{id}/today                 → today's workout (or null)
GET  /plans/{id}/week?week_index=5        → one week's workouts
POST /workouts/{id}/feedback              → mark complete/skip + RPE + note
POST /plans/{id}/regenerate-from-today    → skill switch flow
GET  /workouts/{id}/match-status          → was today's COROS activity matched?
```

---

## 8. Sample data the UI will display

### A workout card (today's view)

```json
{
  "id": 142,
  "scheduled_date": "2026-05-02",
  "week_index": 5,
  "title": "W05 速度训练 6x200",
  "discipline": "run",
  "workout_type": "speed",
  "purpose": "Speed-alactic strides — extracted from coach methodology.",
  "distance_m": 5600,
  "duration_min": 36,
  "target_pace_min_sec_per_km": 295,
  "target_pace_max_sec_per_km": 325,
  "rpe_min": 5,
  "rpe_max": 8,
  "adaptation_notes": "完成 > 配速；未达配速也要完成。当日缺训不补；今日做今日课。速度课内的恢复跑保持步频，速度可降。",
  "steps": [
    {"step_index": 1, "step_type": "warmup", "duration_sec": 1800,
     "target_min": 360, "target_max": 380, "notes": "75% LTHR"},
    {"step_index": 2, "step_type": "work", "duration_sec": 0, "notes": "open"},
    {"step_index": 3, "step_type": "work", "duration_sec": 30,
     "repeat_count": 6, "notes": "6× 200m · 119% LTHR · rest 30s",
     "target_min": 230, "target_max": 250},
    {"step_index": 4, "step_type": "cooldown", "duration_sec": 600,
     "target_min": 380, "target_max": 410}
  ],
  "status": "confirmed"
}
```

### A skill manifest

```json
{
  "slug": "coach_zhao_unified",
  "name": "Coach Zhao Unified Marathon Methodology",
  "version": "0.1.0",
  "sport": "marathon",
  "supported_goals": ["finish", "target_time"],
  "description": "Distilled from two complete coach-prescribed marathon programs. One unified philosophy with summer / winter strategy adaptation for Northern-China climate. Working-professional friendly: short sessions, capped long runs, tempo + strides instead of intervals.",
  "author": "赵可 (extracted by ST skill-creator)",
  "tags": ["marathon", "seasonal", "northern-china", "low-LSD",
           "working-professional", "tempo-and-strides", "completion-first"]
}
```

### A week summary

```json
{
  "week_index": 5,
  "phase": "base",
  "is_recovery": false,
  "total_km_planned": 46.6,
  "total_min_planned": 285,
  "quality_count": 2,
  "long_run_role": "long_run_easy",
  "days": [
    {"date": "2026-04-28", "weekday": 1, "title": "W05 40min+200x5", "distance_km": 7.2, "duration_min": 44, "status": "completed"},
    {"date": "2026-04-30", "weekday": 3, "title": "W05 16K轻松跑", "distance_km": 16.0, "duration_min": 113, "status": "completed"},
    {"date": "2026-05-01", "weekday": 4, "title": "W05 有氧基础60MIN", "distance_km": 9.2, "duration_min": 60, "status": "missed"},
    {"date": "2026-05-02", "weekday": 5, "title": "W05 速度训练 6x200", "distance_km": 5.6, "duration_min": 36, "status": "confirmed"},
    {"date": "2026-05-03", "weekday": 6, "title": "W05 16K轻松跑", "distance_km": 16.0, "duration_min": 113, "status": "scheduled"}
  ]
}
```

---

## 9. UX details / decisions already made

| Question | Answer |
|----------|--------|
| Today's workout view: detailed or summary? | **Detailed** — show all steps and adherence notes. |
| COROS sync frequency? | **Daily auto** + a manual sync button always visible. |
| Skill switch: keep history or rewrite? | Past frozen, future regenerated. **Show explicit count of affected sessions in confirmation dialog.** |
| Language? | **Chinese primary**, English ok where natural (`pace`, `LTHR`). |
| Mobile or desktop priority? | **Mobile-first** for daily use; desktop also looks good. |
| Single user or multi? | **Single user MVP**. No login. |
| Where does the AI coach live? | A side panel / sheet — not a separate page. Always reachable. |

### Visual hints

- The athlete is a 32-year-old runner training for marathon. The aesthetic
  should feel like a high-end training tool (think Stryd Power Center, Final
  Surge, or TrainerRoad), not a consumer fitness app (Strava / Nike Run).
- The `adaptation_notes` (methodology rules) are sacred — they should be
  visually prominent on every workout card, not buried in fine print.
- When workouts have many steps (some have 10+), the card should expand /
  collapse gracefully on mobile.
- Phase + week index should always be visible in the workout title — the
  athlete navigates by week.

---

## 10. Open questions for the designer

These deserve attention but the backend doesn't constrain them:

1. **Workout completion UX** — three buttons (done / partial / skip)? slider
   for completion %? freeform note? what's the right minimum friction so the
   athlete actually marks every workout?

2. **Pace target visualization** — when target is a range (e.g. 4:40–5:10/km),
   how to show? Bar? Range slider? Two pills? On mobile at a glance, what's
   the fastest-to-read?

3. **Step list density** — strides workouts have 10+ steps. Group by repeat?
   Show timeline? Collapse repeats into one card with `6×`?

4. **Plan vs reality comparison** — after a run, side-by-side or stacked?
   What's the minimum delta the athlete cares about — pace? HR? distance?

5. **Skill switch: when to surface** — buried in settings? prominent on home
   when there's no active plan? a "switch methodology" CTA after a bad week?

6. **AI coach chat affordance** — floating button? side sheet? dedicated tab?
   The chat backend exists and is the most powerful feature. UI shouldn't
   bury it but also shouldn't dominate.

7. **Onboarding** — first-time user has no plan, no goal, no Skill picked.
   What's the right wizard order: profile → goal → skill → plan?

8. **Empty states** — between plans, before first sync, after a missed week.
   What does the home screen show?

---

## 11. Things that intentionally **don't** belong on the web v1

- Athlete creation flow (single-user, profile is TOML-edited)
- Multi-language toggle (Chinese is fine for MVP)
- Workout editing UI (skill regenerates; manual edits are out of scope)
- Notifications / push
- Social / sharing
- Skill-creator wizard (deferred to MVP+2)
- Coach-mode for editing other athletes
- OAuth / login

If the designer suggests these, push back politely with "v2".

---

## 12. Glossary

| Term | Meaning |
|------|---------|
| **Skill** | A pluggable training methodology (e.g. Coach Zhao). One per active plan. |
| **Plan** | A multi-week training schedule generated by a Skill for a specific race goal. |
| **Workout / Structured Workout** | A single training session inside a plan, with structured intervals. |
| **Step** | One interval inside a workout (warmup, work, cooldown). |
| **Activity** | An executed run pulled from COROS. |
| **LTHR** | Lactate threshold heart rate (bpm). The athlete's anchor for intensity. |
| **LTSP** | Lactate threshold speed/pace (sec/km). |
| **Adherence rules** | Methodology-specific principles like "complete > pace". |
| **Specific block** | The high-volume race-specific phase, last ~25% of plan. |
| **Taper** | Final 1–2 weeks where volume drops sharply. |
| **赵可 / 刘征** | Real coach names from the athlete's history; appear as Skill authors. |

---

## 13. Single-question summary for the designer

> Design a mobile-first web app that, on opening, shows the athlete the
> single workout they should do today — with full detail and the
> methodology's adherence rules — plus a way to mark it done after the run,
> a way to see this week's shape, and a way to read or switch the
> methodology that's driving the plan. Everything else is secondary.
