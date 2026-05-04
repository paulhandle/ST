# PerformanceProtocol Web — Dashboard / Home Tab Design Prompt

> Use alongside `web-design-context.md` (full project brief). This document
> focuses only on the **Dashboard** tab. Other tabs (Today / Week / Plan)
> are designed separately.

---

## Tab structure

The web app has 4 main tabs (bottom nav on mobile, sidebar on desktop):

```
[ 概览 Dashboard ]  ← first / default tab — this prompt
[ 今天 Today ]      ← single workout, full detail, mark done
[ 本周 Week ]       ← 7-day strip, drill into any day
[ 计划 Plan ]       ← whole plan as weeks list / calendar
```

Optional 5th: **教练 Coach** — AI chat panel (or accessed via a floating
button on every page). Not part of the dashboard.

---

## What the Dashboard *is* (and isn't)

### It IS

A **synthesis screen** that answers two questions in under 5 seconds:

1. **"Am I on track to my goal?"**  (信心)
2. **"What's the state of my training right now?"**  (状态)

It pulls signal from Today / Week / Plan / Activity / Goal / Readiness data
and presents the synthesis. Tapping any section drills into the relevant tab.

### It is NOT

- **Not where you execute today's workout** → that's the Today tab.
- **Not where you browse the full plan** → that's the Plan tab.
- **Not a re-do of the week view** → that's the Week tab. Dashboard only
  shows a *compressed* view of the week.

This separation is the most important UX principle. If something belongs in
another tab, it shouldn't appear in full here.

---

## Dashboard sections (top to bottom, mobile-first scroll)

### 1. 顶部状态条 — Top status bar

A thin sticky bar:
- Greeting: "早上好，Paul · 周五 5/2"  (auto-detect time-of-day greeting)
- Current Skill badge: `🧠 赵可方法论` → tappable, shows current Skill name + version
- Sync icon with last-sync time relative ("4h ago") + tap to manual sync

If a sync is in progress, show a tiny spinner. If sync errored, show a small
red dot on the icon.

### 2. 调整建议横幅 — Adjustment banner (conditional)

If there's a pending plan adjustment (`PlanAdjustment.status == "proposed"`):

```
⚠ 本周建议调整：训练负荷过高，建议下调强度 [查看 →]
```

- Dismissible (× button) but persists in DB.
- Shows only the headline (`reason`); tapping goes to Coach tab with full
  recommendation prefilled.
- If no pending adjustment, skip this section entirely (don't reserve space).

### 3. 今日卡片 — Today summary (compressed)

A compact card pointing to the Today tab:

```
┌──────────────────────────────────────┐
│ 今天 · W05 周五                     │
│ 速度训练 6x200                       │
│ 5.6 km · 36 min · 4:55–5:25/km       │
│ [开始训练 →]   [✓]   [⏭]           │
└──────────────────────────────────────┘
```

- Tappable card → goes to Today tab.
- Status badge in top-right of card if executed:
  - `✓ 已完成` (green)
  - `⚠ 部分完成` (yellow)
  - `⏭ 已跳过` (gray)
- If today is a rest day:
  ```
  ┌──────────────────────────────────────┐
  │ 今天休息 ☕                          │
  │ 明天 · 周六 · W05 16K轻松跑          │
  │ 16.0 km · 113 min                    │
  └──────────────────────────────────────┘
  ```
  Show tomorrow's workout title + distance + duration as a preview, tappable
  to go to Week tab on tomorrow.
- Buttons "✓" and "⏭" trigger inline feedback (no navigation): ✓ marks
  completed, ⏭ marks skipped, both prompt for an optional RPE before
  saving. The "开始训练 →" button takes them to Today tab for full detail.

### 4. 本周进度 — Week progress strip (compressed)

Compressed week view (NOT full Week tab — that's a separate tab):

```
本周 W05/18 · base 阶段
──────────────────────────────────
Mon  Tue  Wed  Thu  Fri  Sat  Sun
 ✓    ✓   ⚠   ●    ☕   ⏳   ☕
                ↑ today
完成 23.2 / 46.6 km · 2/3 quality
```

- 7 dot indicators with status colors (legend below).
- "Today" arrow under the current weekday.
- One-line summary: completed km / planned km · completed quality / planned quality.
- Whole strip is tappable → goes to Week tab.
- Horizontal swipe within the strip optionally lets the user peek at last
  week / next week without leaving the dashboard. Strip header changes
  to "上周 / 下周" when swiped.

### 5. 目标进度 — Goal tracking (the centerpiece)

This is the most signal-dense part of the dashboard. Two charts, side-by-side
on desktop, stacked on mobile, with section header:

```
目标 sub-3:30 · 距离 2027-03-07 · 还有 309 天
```

#### 5a. Predicted finish trend (chart 1)

```
[Line chart, 8-12 most recent data points]
Y axis: predicted marathon finish time (h:mm)
X axis: weeks
Series: predicted time (line) + target time (dashed horizontal) +
        confidence band (light gray fill)
```

- Data: each week's `race_predictor_marathon` value from the most recent
  COROS dashboard sync of that week.
- Annotation: a small label on the latest point ("4:03 — now")
- Color: line is muted blue; target line is bold; current point is solid dot.
- Caption below: "本月预测已下降 4 分钟" or "本月预测无变化".
- If no prediction data yet ("data still loading from COROS"): empty state
  with explanation, no broken chart.

#### 5b. Weekly volume executed vs planned (chart 2)

```
[Horizontal bars, last 8 weeks, today's week last]
Each row: week label · two-segment bar (executed in solid color,
          planned-not-executed in light color) · numeric "X / Y km"
```

- Color: green for ≥ 90 % of plan, yellow for 60–90 %, red for < 60 %,
  gray for "still in progress" (current week).
- Caption below: "近 8 周平均完成率 87%".

These two charts together let the athlete answer "am I on track?" in one
glance.

### 6. 最近活动 — Recent activities (compressed list)

Last 5–7 imported COROS activities, list form:

```
最近活动                              [全部 →]
─────────────────────────────────────────────
5/01  16K轻松跑       16.0 km  6:15/km  HR 142  ✓
4/29  40min+200x5      7.2 km  varied   HR 152  ✓
4/27  自由跑           5.8 km  6:45/km  HR 134  ●
4/24  半马训练        21.1 km  5:35/km  HR 161  ⚠
4/22  恢复跑           2.8 km  6:50/km  HR 122  ✓
```

- Title: matched workout title if there's a `matched_workout_id`, else
  "自由跑" with dot icon (●) for unmatched.
- Status icon at right: ✓ matched-completed, ⚠ matched-partial, ⏭
  matched-skipped, ● unmatched.
- Tap a row → drill into that activity's detail (a sheet showing matched
  workout + actual numbers side-by-side; can be a Coach-tab style sheet).

### 7. 状态指标 — Readiness panel

A small grid of 4 metrics with trend arrows:

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  静息心率    │  7天负荷     │   LTHR       │  威胁配速    │
│   47 bpm ↘  │   412 ↗     │   165 bpm    │  4:40 /km    │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

- 静息心率: trend arrow vs 14-day average. Lower is better (down arrow green).
- 7天负荷: training load trend, 7-day rolling. Up usually means accumulating
  fitness OR fatigue — show neutral arrow style.
- LTHR / 威胁配速 (LTSP): from latest COROS dashboard metric. No trend if
  unchanged in last 14 days.
- All values come from `latest_metrics` + assessment data.

If a value is missing (no data ever): show "—" (em-dash) and a "Sync to
update" tooltip.

### 8. 底部小字 — Footer

```
当前 Skill · 赵可方法论 v0.1.0   [切换 →]
COROS 上次同步 · 5/2 09:14       [立即同步]
```

Compact. Tappable.

---

## Data shapes available (for the API contract)

The dashboard will need a single endpoint or a small set of endpoints. The
backend designer will adjust as needed; here's what to assume is available:

```typescript
// GET /athletes/{id}/dashboard
{
  greeting: { time_of_day: "morning" | "afternoon" | "evening", date: "2026-05-02", weekday: "Fri" },
  athlete: { id: 1, name: "Paul", current_skill_slug: "coach_zhao_unified" },
  pending_adjustment: { id: 17, headline: "本周建议调整：训练负荷过高" } | null,
  today: {
    plan_id: 4,
    week_index: 5,
    workout: StructuredWorkout | null,   // null = rest day
    tomorrow_preview: StructuredWorkout | null,  // shown when today is rest
    matched_activity_id: number | null,
    matched_status: "completed" | "partial" | "skipped" | null,
  },
  week: {
    week_index: 5,
    plan_total_weeks: 18,
    phase: "base" | "block" | "taper",
    days: [
      { date: "2026-04-28", weekday: 1, status: "completed", title: "...", distance_km: 7.2 },
      // ... 7 entries
    ],
    completed_km: 23.2,
    planned_km: 46.6,
    completed_quality: 2,
    planned_quality: 3,
  },
  goal: {
    label: "sub-3:30",
    race_date: "2027-03-07",
    days_until: 309,
    target_time_sec: 12600,
    prediction_history: [
      { week: "2026-W14", predicted_time_sec: 14628 },
      { week: "2026-W15", predicted_time_sec: 14400 },
      // ... up to 12 most recent
    ],
    weekly_volume_history: [
      { week_index: -2, label: "W03", executed_km: 38, planned_km: 42, completion_pct: 90.5 },
      // last 8 weeks ending in current week
    ],
  },
  recent_activities: [
    { id: 142, started_at: "2026-05-01T18:32:00", matched_workout_title: "16K轻松跑",
      distance_km: 16.0, duration_min: 113, avg_pace_sec_per_km: 375, avg_hr: 142,
      match_status: "completed" },
    // 5-7 items
  ],
  readiness: {
    resting_hr: 47, resting_hr_trend: "down" | "up" | "flat",
    weekly_training_load: 412, weekly_training_load_trend: "up",
    lthr: 165, ltsp_sec_per_km: 280,
  },
  meta: {
    skill_slug: "coach_zhao_unified",
    skill_name: "赵可方法论",
    skill_version: "0.1.0",
    last_sync_at: "2026-05-02T09:14:00",
    last_sync_status: "ok" | "error" | "in_progress",
  },
}
```

---

## Decisions already made

| Question | Answer |
|----------|--------|
| Today on dashboard: full or compressed? | **Compressed**. Full lives in Today tab. |
| Today rest day: show what? | "今天休息" + **tomorrow preview** card from week plan. |
| Goal-gap chart: which? | **Two charts** — predicted finish trend + weekly volume planned vs executed. |
| Weekly volume chart: how many weeks? | **Last 8 weeks**, current week last. |
| Week strip: scrollable? | **Yes** — horizontal swipe to peek prev/next week. |
| Calendar / month view? | **Not on dashboard**. Lives in Plan tab. |

---

## Visual / interaction notes

1. **Mobile-first**: vertical scroll, sections stacked. Each section is a
   visually distinct card with its own padding and background.

2. **Density**: dashboard should feel rich but not crowded. On a 6.1" iPhone,
   sections 1–3 (status bar + adjustment + today) should fit above the fold.
   Goal charts at second-screen scroll.

3. **Color language**:
   - Primary action: a single bold color (e.g. coral or saturated blue)
   - Status: green / yellow / red / gray as listed
   - Skill badge: subtly tinted (different per Skill if possible — `coach_zhao_unified` could be a warm tone)
   - Charts: muted; use fills for emphasis

4. **Typography**:
   - Title sizes scale: H1 (greeting) > H2 (section headers) > body
   - Numbers (paces, HR, km) in a slightly heavier weight + tabular figures
   - Chinese + English mixed gracefully — use a font stack that handles both
     well (PingFang SC, Hiragino, SF Pro)

5. **Empty states**:
   - No active plan: dashboard becomes a single CTA "创建训练计划 →" with
     the readiness panel still shown, everything else hidden.
   - No COROS sync ever: today / week / activities sections show placeholders
     with "连接 COROS 后开始" CTAs.
   - No prediction data yet: chart area shows "等待 COROS 数据更新".

6. **Skeleton / loading states**: the dashboard pulls many things; design
   skeletons for each section that match the final layout (don't use
   spinners that shift things).

---

## What NOT to include on the dashboard

- Full step-by-step workout breakdown (that's Today tab)
- Full week with workout details (that's Week tab)
- Plan calendar / month view (that's Plan tab)
- AI coach chat input (Coach is its own tab / floating)
- Activity full detail (drill-in only)
- Settings, profile editing, account management
- Onboarding wizard for first-time users (separate flow)

---

## Open questions for the designer

1. **Two charts side-by-side or stacked?** On wider screens (tablet/desktop)
   side-by-side makes sense; on mobile probably stacked. What's the
   breakpoint? What if a horizontal swipe between charts could keep them in
   one card?

2. **Recent activities: list vs cards?** A list is denser; cards are easier
   to tap. 5-7 items either way.

3. **Readiness panel position**: above or below recent activities? Argument
   for above: it's always-relevant context. Argument for below: it's a
   reference, not action.

4. **Skill badge prominence**: the active Skill is core to the methodology
   message but doesn't change daily. Is putting it in the top status bar
   enough, or does it deserve its own section near the bottom?

5. **Pull-to-refresh** behavior: trigger a manual COROS sync on pull?
   Or just refresh dashboard data without re-syncing?

6. **Adjustment banner**: dismissible per session or persistent? If
   persistent (must accept/reject), where do they go to act on it?

7. **Chart legends and explanations**: charts should be self-explanatory at
   a glance, but some users want to drill in. Tap-to-explain modal? Tooltip?

---

## One-sentence brief

> Build a mobile-first dashboard tab that shows, top to bottom: today's
> workout (compressed, with quick mark-done), this week's progress at a
> glance, two goal-tracking charts (predicted finish trend + weekly volume
> executed vs planned over the last 8 weeks), recent COROS activities, and
> readiness metrics — with everything else (full execution, full week,
> full plan) deferred to other tabs.
