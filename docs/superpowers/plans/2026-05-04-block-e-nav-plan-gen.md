# Block E: Navigation & Plan Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the tab bar (replace 今天 with 运动), add per-date workout detail pages at `/workouts/[date]`, and build a 5-step plan generation wizard on the Plan tab.

**Architecture:** Tab restructure is a pure layout change. `/workouts/[date]` reuses the existing `get_today` backend pattern with a date parameter. The wizard is a self-contained page at `/plan/generate` (outside tabs group, no tab bar) that chains five API calls sequentially through local state.

**Tech Stack:** Next.js 14 App Router, TypeScript, SWR, FastAPI, SQLAlchemy, Vitest + RTL

---

## File Map

### Created
| File | Purpose |
|------|---------|
| `web/app/(tabs)/activities/page.tsx` | Activities tab (replaces standalone `/activities`) |
| `web/app/workouts/[date]/page.tsx` | Workout detail page for any date |
| `web/lib/hooks/useWorkoutByDate.ts` | SWR hook — `GET /athletes/1/workout/{date}` |
| `web/app/plan/generate/page.tsx` | 5-step plan generation wizard |
| `web/__tests__/blockE.test.tsx` | Frontend tests for new functionality |
| `tests/test_block_e.py` | Backend test for workout-by-date endpoint |

### Modified
| File | Change |
|------|--------|
| `web/app/(tabs)/layout.tsx` | Remove 今天 tab, add 运动 tab |
| `web/app/(tabs)/today/page.tsx` | Replace with client-side redirect to `/workouts/[today]` |
| `web/app/(tabs)/week/page.tsx` | Wrap `DayRow` in `Link href=/workouts/[date]` |
| `web/components/dashboard/TodayCard.tsx` | Change `href="/today"` → `/workouts/[today's date]` |
| `web/components/EmptyPlanState.tsx` | Change CTA `href="/onboarding"` → `/plan/generate` |
| `app/api/routes.py` | Add `GET /athletes/{id}/workout/{date}` endpoint |
| `web/lib/api/types.ts` | Add `RunningAssessmentOut` and `HistoryImportOut` types |

### Deleted
| File | Reason |
|------|--------|
| `web/app/activities/page.tsx` | Moved into `(tabs)` group to gain tab bar |

---

## Task 1: Tab bar restructure + Activities tab

**Files:**
- Modify: `web/app/(tabs)/layout.tsx`
- Create: `web/app/(tabs)/activities/page.tsx`
- Delete: `web/app/activities/page.tsx`

- [ ] **Step 1: Write failing test**

Add `web/__tests__/blockE.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ replace: vi.fn() }),
}))
vi.mock('next/link', () => ({
  default: ({ href, children, ...p }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    React.createElement('a', { href, ...p }, children),
}))
vi.mock('@/components/CoachButton', () => ({ default: () => null }))

import TabsLayout from '@/app/(tabs)/layout'

describe('Tab bar', () => {
  it('shows 运动 tab and no 今天 tab', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('运动')).toBeInTheDocument()
    expect(screen.queryByText('今天')).not.toBeInTheDocument()
  })

  it('shows 概览 本周 计划 tabs', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('概览')).toBeInTheDocument()
    expect(screen.getByText('本周')).toBeInTheDocument()
    expect(screen.getByText('计划')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -15
```
Expected: FAIL — "运动" not found in DOM.

- [ ] **Step 3: Restructure tab bar in layout.tsx**

Replace the `TABS` array and add `TabIconActivities`:

```tsx
const TABS = [
  { href: '/dashboard', label: '概览',  icon: TabIconDashboard },
  { href: '/activities', label: '运动', icon: TabIconActivities },
  { href: '/week',       label: '本周',  icon: TabIconWeek },
  { href: '/plan',       label: '计划',  icon: TabIconPlan },
]
```

Add after `TabIconDashboard`:

```tsx
function TabIconActivities({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="6" r="2.5" stroke={c} strokeWidth="1.5" />
      <path d="M7 11l2 2 4-4" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 19l2-4h8l2 4" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
```

Remove `TabIconToday` function (no longer needed).

- [ ] **Step 4: Create `web/app/(tabs)/activities/page.tsx`**

Copy the full content of `web/app/activities/page.tsx` verbatim into `web/app/(tabs)/activities/page.tsx`.

- [ ] **Step 5: Delete `web/app/activities/page.tsx`**

```bash
rm /Users/paul/Work/ST/web/app/activities/page.tsx
```

- [ ] **Step 6: Run tests — should pass**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -10
```
Expected: PASS — 2 tests.

- [ ] **Step 7: Run full frontend suite**

```bash
cd /Users/paul/Work/ST/web && pnpm test 2>&1 | tail -8
```
Expected: all tests pass (52 or more).

- [ ] **Step 8: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/\(tabs\)/layout.tsx web/app/\(tabs\)/activities/page.tsx web/__tests__/blockE.test.tsx
git rm web/app/activities/page.tsx
git commit -m "feat(web): restructure tabs — add 运动, remove 今天

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Replace `/today` with per-date redirect

**Files:**
- Modify: `web/app/(tabs)/today/page.tsx`

- [ ] **Step 1: Replace content with redirect**

Replace the entire file content of `web/app/(tabs)/today/page.tsx` with:

```tsx
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TodayRedirect() {
  const router = useRouter()
  useEffect(() => {
    router.replace(`/workouts/${new Date().toISOString().slice(0, 10)}`)
  }, [router])
  return null
}
```

- [ ] **Step 2: Run full frontend suite**

```bash
cd /Users/paul/Work/ST/web && pnpm test 2>&1 | tail -8
```
Expected: all tests still pass.

- [ ] **Step 3: Commit**

```bash
git add web/app/\(tabs\)/today/page.tsx
git commit -m "feat(web): redirect /today to /workouts/[date]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Backend — `GET /athletes/{id}/workout/{date}`

**Files:**
- Modify: `app/api/routes.py` (add after `get_today` at line ~631)
- Create: `tests/test_block_e.py`

- [ ] **Step 1: Write failing backend test**

Create `tests/test_block_e.py`:

```python
import os
os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")

import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _get_token() -> str:
    client.post("/auth/send-otp", json={"phone": "13900000099"})
    res = client.post("/auth/verify-otp", json={"phone": "13900000099", "code": "000000"})
    if res.status_code != 200:
        # real OTP: get code from send-otp response
        send = client.post("/auth/send-otp", json={"phone": "13900000099"})
        code = str(send.json()["otp_code"])
        res = client.post("/auth/verify-otp", json={"phone": "13900000099", "code": code})
    return res.json()["access_token"]


class WorkoutByDateTestCase(unittest.TestCase):

    def setUp(self):
        from app.db import engine, Base
        Base.metadata.create_all(bind=engine)
        self.token = _get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        # Create athlete
        r = client.post("/athletes", json={
            "name": "BlockE", "sport": "marathon",
            "level": "intermediate", "weekly_training_days": 5,
        }, headers=self.headers)
        self.athlete_id = r.json()["id"]

    def test_no_plan_returns_200_with_null_workout(self):
        r = client.get(f"/athletes/{self.athlete_id}/workout/2099-06-15",
                       headers=self.headers)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsNone(body["workout"])
        self.assertIsNone(body["plan_id"])

    def test_invalid_date_returns_422(self):
        r = client.get(f"/athletes/{self.athlete_id}/workout/not-a-date",
                       headers=self.headers)
        self.assertEqual(r.status_code, 422)

    def test_requires_auth(self):
        r = client.get(f"/athletes/{self.athlete_id}/workout/2099-06-15")
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/paul/Work/ST && uv run python -m pytest tests/test_block_e.py -v 2>&1 | tail -15
```
Expected: FAIL — 404 or attribute error (endpoint doesn't exist yet).

- [ ] **Step 3: Add endpoint to `app/api/routes.py`**

Insert immediately after the `get_today` function (after line ~630):

```python
@router.get("/athletes/{athlete_id}/workout/{workout_date}", response_model=TodayOut)
def get_workout_by_date(
    athlete_id: int,
    workout_date: str,
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
) -> TodayOut:
    """Return workout details for any specific date. Returns null workout fields when
    no plan exists or the date is a rest day — never raises 404 for missing workouts."""
    _athlete_or_404(db, athlete_id)
    try:
        target = date.fromisoformat(workout_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")

    plan = _active_or_draft_plan_for_athlete(db, athlete_id)
    if plan is None:
        return TodayOut(
            plan_id=None, plan_title=None, skill_slug=None,
            week_index=None, workout=None, matched_activity_id=None,
            yesterday_workout=None, yesterday_activity=None,
            recovery_recommendation=None,
        )

    yesterday = target - timedelta(days=1)
    workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == target), None
    )
    yesterday_workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == yesterday), None
    )

    matched_activity_id: int | None = None
    workout_out: StructuredWorkoutOut | None = None
    if workout is not None:
        workout_out = StructuredWorkoutOut.model_validate(workout)
        activity = match_workout_to_activity(db, workout)
        if activity is not None:
            matched_activity_id = activity.id

    yesterday_workout_out: StructuredWorkoutOut | None = None
    yesterday_activity_out: AthleteActivityOut | None = None
    if yesterday_workout is not None:
        yesterday_workout_out = StructuredWorkoutOut.model_validate(yesterday_workout)
        y_activity = match_workout_to_activity(db, yesterday_workout)
        if y_activity is not None:
            yesterday_activity_out = _activity_with_match(db, y_activity)

    return TodayOut(
        plan_id=plan.id,
        plan_title=plan.title,
        skill_slug=plan.active_skill_slug,
        week_index=workout.week_index if workout else None,
        workout=workout_out,
        matched_activity_id=matched_activity_id,
        yesterday_workout=yesterday_workout_out,
        yesterday_activity=yesterday_activity_out,
        recovery_recommendation=None,
    )
```

- [ ] **Step 4: Run backend tests — should pass**

```bash
uv run python -m pytest tests/test_block_e.py -v 2>&1 | tail -10
```
Expected: PASS — 3 tests.

- [ ] **Step 5: Run full backend suite**

```bash
uv run python -m unittest discover -s tests -v 2>&1 | tail -5
```
Expected: all pass (80 or more).

- [ ] **Step 6: Commit**

```bash
git add app/api/routes.py tests/test_block_e.py
git commit -m "feat(api): add GET /athletes/{id}/workout/{date} endpoint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Frontend — `useWorkoutByDate` hook + `/workouts/[date]` page

**Files:**
- Create: `web/lib/hooks/useWorkoutByDate.ts`
- Create: `web/app/workouts/[date]/page.tsx`
- Modify: `web/lib/api/types.ts` (add missing types used by wizard)

- [ ] **Step 1: Add test for workout detail page**

Add to `web/__tests__/blockE.test.tsx`:

```tsx
vi.mock('@/lib/hooks/useWorkoutByDate', () => ({
  useWorkoutByDate: (date: string) => ({
    workout: date === '2026-05-04' ? {
      plan_id: 1, week_index: 3,
      workout: {
        id: 10, title: 'Easy Run', purpose: '轻松跑', duration_min: 50,
        distance_m: 10000, target_min: 330, target_max: 360,
        workout_type: 'easy_run', rpe_min: null, rpe_max: null,
        adaptation_notes: null, steps: [],
      },
      matched_activity_id: null,
      yesterday_workout: null, yesterday_activity: null, recovery_recommendation: null,
    } : { plan_id: null, workout: null },
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}))

import WorkoutDetailPage from '@/app/workouts/[date]/page'

describe('WorkoutDetailPage', () => {
  it('renders workout title for given date', () => {
    render(<WorkoutDetailPage params={{ date: '2026-05-04' }} />)
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
  })

  it('shows rest day when no workout', () => {
    render(<WorkoutDetailPage params={{ date: '2026-05-05' }} />)
    expect(screen.getByText(/休息/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -15
```
Expected: FAIL — WorkoutDetailPage not found.

- [ ] **Step 3: Create `web/lib/hooks/useWorkoutByDate.ts`**

```typescript
import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { TodayOut } from '@/lib/api/types'

const ATHLETE_ID = 1

export function useWorkoutByDate(date: string) {
  const { data, error, isLoading, mutate } = useSWR<TodayOut>(
    date ? `/api/athletes/${ATHLETE_ID}/workout/${date}` : null,
    fetcher,
  )
  return { workout: data, isLoading, error, refresh: mutate }
}
```

- [ ] **Step 4: Add types to `web/lib/api/types.ts`**

Append to the end of the file:

```typescript
/* ── Running assessment ──────────────────────────────────── */

export interface RunningAssessmentOut {
  athlete_id: number
  overall_score: number
  readiness_level: string
  safe_weekly_distance_range_km: number[]
  safe_training_days_range: number[]
  long_run_capacity_km: number
  estimated_marathon_time_range_sec: number[]
  goal_status: string
  limiting_factors: string[]
  warnings: string[]
  confidence: string
  summary: string
}

/* ── COROS import result ─────────────────────────────────── */

export interface HistoryImportOut {
  athlete_id: number
  provider: string
  imported_count: number
  updated_count: number
  metric_count: number
  message: string
}
```

- [ ] **Step 5: Create `web/app/workouts/[date]/page.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useWorkoutByDate } from '@/lib/hooks/useWorkoutByDate'
import { postJson } from '@/lib/api/client'
import { formatPace, formatKm } from '@/lib/api/types'
import PaceRangeBar from '@/components/today/PaceRangeBar'
import WorkoutSteps from '@/components/today/WorkoutSteps'
import YesterdayCompare from '@/components/today/YesterdayCompare'

export default function WorkoutDetailPage({ params }: { params: { date: string } }) {
  const { date } = params
  const router = useRouter()
  const { workout: data, isLoading, error, refresh } = useWorkoutByDate(date)
  const [marking, setMarking] = useState(false)
  const [marked, setMarked] = useState<string | null>(null)

  const displayDate = (() => {
    try {
      return new Date(date + 'T00:00:00').toLocaleDateString('zh-CN', {
        month: 'long', day: 'numeric', weekday: 'short',
      })
    } catch { return date }
  })()

  async function mark(status: 'completed' | 'partial' | 'skipped') {
    if (!data?.workout || marking) return
    setMarking(true)
    try {
      await postJson(`/api/workouts/${data.workout.id}/feedback`, {
        status, rpe_actual: null, notes: null,
      })
      setMarked(status)
      refresh()
    } finally {
      setMarking(false)
    }
  }

  if (isLoading) {
    return (
      <div style={{ minHeight: '100dvh', display: 'flex', alignItems: 'center',
                    justifyContent: 'center' }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>加载中…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 16 }}>
        <span className="hand text-faint" style={{ fontSize: 14 }}>{error.message}</span>
        <button onClick={() => router.back()} className="hand"
          style={{ background: 'none', border: 'none', color: 'var(--ink-faint)',
                   cursor: 'pointer', fontSize: 14 }}>
          ← 返回
        </button>
      </div>
    )
  }

  const workout = data?.workout ?? null
  const matched_activity = null  // matched_activity_id only; full data not fetched here
  const yesterday_workout = data?.yesterday_workout ?? null
  const yesterday_activity = data?.yesterday_activity ?? null
  const recovery_recommendation = data?.recovery_recommendation ?? null

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--paper)' }}>
      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--rule-soft)',
                    display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => router.back()}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 22, color: 'var(--ink-faint)', padding: 0, lineHeight: 1 }}>
          ‹
        </button>
        <div>
          <div className="hand" style={{ fontSize: 16, fontWeight: 700 }}>{displayDate}</div>
          {data?.week_index && (
            <div className="annot text-faint" style={{ fontSize: 12 }}>第 {data.week_index} 周</div>
          )}
        </div>
      </div>

      {!workout ? (
        <div style={{ padding: '48px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🌿</div>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            休息日
          </div>
          {recovery_recommendation ? (
            <div style={{ padding: '12px 16px', background: 'var(--accent-light)',
                          border: '1.5px solid var(--accent)', borderRadius: 8, textAlign: 'left',
                          margin: '0 16px' }}>
              <div className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>
                "{recovery_recommendation.ethos_quote}"
              </div>
            </div>
          ) : (
            <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
              好好恢复 💪
            </div>
          )}
        </div>
      ) : (
        <>
          {/* ── Workout title ───────────────────────────────── */}
          <div style={{ padding: '16px 16px 12px' }}>
            <div className="hand" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.2 }}>
              {workout.title}
            </div>
            <div className="annot text-faint" style={{ fontSize: 13, marginTop: 4 }}>
              {workout.purpose}
            </div>
          </div>

          {/* ── Big numbers ─────────────────────────────────── */}
          <div style={{ display: 'flex', padding: '0 16px 16px',
                        borderBottom: '1px solid var(--rule-soft)' }}>
            {workout.distance_m && (
              <BigNum label="公里" value={formatKm(workout.distance_m)} />
            )}
            <BigNum label="分钟" value={`${workout.duration_min}`} />
            {workout.target_min != null && workout.target_max != null && (
              <BigNum
                label="配速"
                value={`${formatPace(workout.target_min)}–${formatPace(workout.target_max)}`}
              />
            )}
            {workout.rpe_min != null && workout.rpe_max != null && (
              <BigNum label="RPE" value={`${workout.rpe_min}–${workout.rpe_max}`} />
            )}
          </div>

          {/* ── Pace bar ────────────────────────────────────── */}
          {workout.target_min != null && workout.target_max != null && (
            <div style={{ padding: '16px' }}>
              <PaceRangeBar
                targetMin={workout.target_min}
                targetMax={workout.target_max}
                actualPace={null}
              />
            </div>
          )}

          {/* ── Adaptation notes ────────────────────────────── */}
          {workout.adaptation_notes && (
            <div style={{ margin: '0 16px 16px', padding: '10px 14px',
                          background: 'var(--accent-light)',
                          border: '1.5px solid var(--accent)', borderRadius: 6 }}>
              <span className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>
                {workout.adaptation_notes}
              </span>
            </div>
          )}

          {/* ── Steps ───────────────────────────────────────── */}
          {workout.steps.length > 0 && <WorkoutSteps steps={workout.steps} />}

          {/* ── Yesterday compare ───────────────────────────── */}
          {yesterday_workout && (
            <YesterdayCompare workout={yesterday_workout} activity={yesterday_activity} />
          )}

          {/* ── Mark done ───────────────────────────────────── */}
          {!matched_activity && (
            <div style={{ padding: '16px', display: 'flex', gap: 10, flexDirection: 'column' }}>
              <div className="hand text-faint" style={{ fontSize: 12, textAlign: 'center' }}>
                完成了吗？
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {(['completed', 'partial', 'skipped'] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => mark(s)}
                    disabled={marking || !!marked}
                    style={{
                      flex: 1, padding: '10px', borderRadius: 8,
                      fontFamily: 'var(--font-hand)', fontSize: 14,
                      cursor: (marking || !!marked) ? 'default' : 'pointer',
                      opacity: (marking || !!marked) && marked !== s ? 0.5 : 1,
                      border: s === 'skipped' ? 'none' : '1.5px solid var(--ink)',
                      background: (s === 'completed' || marked === s) ? 'var(--ink)' : 'var(--paper)',
                      color: (s === 'completed' || marked === s) ? 'var(--paper)' : 'var(--ink)',
                    }}
                  >
                    {s === 'completed' ? '完成 ✓' : s === 'partial' ? '部分' : '跳过'}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function BigNum({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ flex: 1, textAlign: 'center' }}>
      <div className="hand" style={{ fontSize: 28, fontWeight: 700, lineHeight: 1.1 }}>{value}</div>
      <div className="annot text-faint" style={{ fontSize: 12 }}>{label}</div>
    </div>
  )
}
```

- [ ] **Step 6: Run tests — should pass**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -10
```
Expected: PASS — 4 tests (2 tab + 2 workout detail).

- [ ] **Step 7: Run type-check**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check 2>&1 | tail -5
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
cd /Users/paul/Work/ST
git add web/lib/hooks/useWorkoutByDate.ts web/app/workouts/ web/lib/api/types.ts web/__tests__/blockE.test.tsx
git commit -m "feat(web): add /workouts/[date] detail page and useWorkoutByDate hook

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Wire navigation links (Week rows + TodayCard)

**Files:**
- Modify: `web/app/(tabs)/week/page.tsx`
- Modify: `web/components/dashboard/TodayCard.tsx`

- [ ] **Step 1: Update `DayRow` in week page to use Link**

In `web/app/(tabs)/week/page.tsx`:

1. Add import at top: `import Link from 'next/link'`

2. Replace the entire `DayRow` function:

```tsx
function DayRow({ day }: { day: WeekDay }) {
  const WEEKDAY = ['一', '二', '三', '四', '五', '六', '日']
  const isToday = day.date === new Date().toISOString().slice(0, 10)

  return (
    <Link
      href={`/workouts/${day.date}`}
      style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px 16px',
        borderBottom: '1px solid var(--rule-soft)',
        background: isToday ? 'rgba(214, 59, 47, 0.04)' : undefined,
      }}>
        <div style={{ width: 36, flexShrink: 0, textAlign: 'center' }}>
          <div className="hand" style={{
            fontSize: 15,
            fontWeight: isToday ? 700 : 400,
            color: isToday ? 'var(--accent)' : 'var(--ink)',
          }}>
            {WEEKDAY[day.weekday]}
          </div>
          <div className="annot text-faint" style={{ fontSize: 11 }}>
            {day.date.slice(5).replace('-', '/')}
          </div>
        </div>

        <span className={`status-dot ${day.status}`} style={{ margin: '0 12px', flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="hand" style={{
            fontSize: 14,
            color: day.status === 'future' ? 'var(--ink-faint)' : 'var(--ink)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {day.title ?? (day.status === 'rest' ? '休息' : '—')}
          </div>
          {(day.distance_km || day.duration_min) && (
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {day.distance_km != null ? `${day.distance_km.toFixed(1)} km` : ''}
              {day.distance_km != null && day.duration_min != null ? ' · ' : ''}
              {day.duration_min != null ? `${day.duration_min} 分钟` : ''}
            </div>
          )}
        </div>

        <div className="hand" style={{
          fontSize: 12,
          color: day.status === 'completed' ? 'var(--ink)' :
                 day.status === 'miss' ? 'var(--accent)' : 'var(--ink-faint)',
          flexShrink: 0, marginLeft: 8,
        }}>
          {STATUS_LABEL[day.status]}
        </div>

        <span style={{ color: 'var(--ink-faint)', marginLeft: 6, fontSize: 14 }}>›</span>
      </div>
    </Link>
  )
}
```

- [ ] **Step 2: Update `TodayCard` to link to today's workout date**

In `web/components/dashboard/TodayCard.tsx`, replace:

```tsx
    <Link href="/today" style={{ textDecoration: 'none', display: 'block' }}>
```

with:

```tsx
    <Link href={`/workouts/${new Date().toISOString().slice(0, 10)}`} style={{ textDecoration: 'none', display: 'block' }}>
```

- [ ] **Step 3: Run full frontend suite**

```bash
cd /Users/paul/Work/ST/web && pnpm test 2>&1 | tail -8
```
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/\(tabs\)/week/page.tsx web/components/dashboard/TodayCard.tsx
git commit -m "feat(web): link week rows and today card to /workouts/[date]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Plan generation wizard `/plan/generate`

**Files:**
- Create: `web/app/plan/generate/page.tsx`

- [ ] **Step 1: Write failing test for wizard**

Add to `web/__tests__/blockE.test.tsx`:

```tsx
vi.mock('@/lib/auth', () => ({
  getToken: () => 'mock-token',
}))

describe('PlanGeneratePage', () => {
  it('shows loading state on mount while importing data', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ imported_count: 5, updated_count: 2, message: 'ok', metric_count: 1,
                           athlete_id: 1, provider: 'coros' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { default: PlanGeneratePage } = await import('@/app/plan/generate/page')
    render(<PlanGeneratePage />)
    expect(screen.getByText(/分析/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -15
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create `web/app/plan/generate/page.tsx`**

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from '@/lib/auth'
import type { RunningAssessmentOut, HistoryImportOut, SkillManifestOut } from '@/lib/api/types'

const ATHLETE_ID = 1

type Step = 1 | 2 | 3 | 4 | 5

interface GeneratedPlan {
  id: number
  title: string | null
  weeks: number
  start_date: string | null
  race_date: string | null
  target_time_sec: number | null
}

interface WizardState {
  step: Step
  loading: boolean
  error: string | null
  importResult: HistoryImportOut | null
  assessment: RunningAssessmentOut | null
  skills: SkillManifestOut[] | null
  selectedSkill: string
  targetH: number
  targetM: number
  planWeeks: number
  weeklyDays: number
  generatedPlan: GeneratedPlan | null
  syncResult: { synced_count: number; failed_count: number } | null
}

const INIT: WizardState = {
  step: 1, loading: true, error: null,
  importResult: null, assessment: null, skills: null,
  selectedSkill: 'marathon_st_default',
  targetH: 4, targetM: 0,
  planWeeks: 16, weeklyDays: 5,
  generatedPlan: null, syncResult: null,
}

function authHdr(token: string | null) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function secToHM(s: number) {
  return { h: Math.floor(s / 3600), m: Math.floor((s % 3600) / 60) }
}

function hmToSec(h: number, m: number) { return h * 3600 + m * 60 }

function fmtTime(sec: number) {
  const { h, m } = secToHM(sec)
  return `${h}:${m.toString().padStart(2, '0')}`
}

export default function PlanGeneratePage() {
  const router = useRouter()
  const [s, setS] = useState<WizardState>(INIT)

  function patch(p: Partial<WizardState>) { setS(prev => ({ ...prev, ...p })) }

  // Step 1: auto-run on mount
  useEffect(() => { runStep1() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function runStep1() {
    const token = getToken()
    patch({ loading: true, error: null })
    try {
      // Import COROS — non-blocking; failure just shows 0 count
      let importResult: HistoryImportOut = {
        athlete_id: ATHLETE_ID, provider: 'coros',
        imported_count: 0, updated_count: 0, metric_count: 0, message: '未连接 COROS',
      }
      const importRes = await fetch(`/api/coros/import?athlete_id=${ATHLETE_ID}`, {
        method: 'POST', headers: authHdr(token),
        body: JSON.stringify({ device_type: 'coros' }),
      })
      if (importRes.ok) importResult = await importRes.json()

      // Assessment
      const assessRes = await fetch(
        `/api/athletes/${ATHLETE_ID}/assessment/run?target_time_sec=14400&plan_weeks=16&weekly_training_days=5`,
        { method: 'POST', headers: authHdr(token) },
      )
      if (!assessRes.ok) throw new Error('能力评估失败，请确认已有运动记录')
      const assessment: RunningAssessmentOut = await assessRes.json()

      // Skills list
      const skillsRes = await fetch('/api/skills', { headers: authHdr(token) })
      if (!skillsRes.ok) throw new Error('获取训练方案失败')
      const skills: SkillManifestOut[] = await skillsRes.json()

      // Pre-fill target time from assessment midpoint
      const range = assessment.estimated_marathon_time_range_sec
      const mid = range.length >= 2 ? Math.round((range[0] + range[1]) / 2) : 14400
      const { h, m } = secToHM(mid)

      patch({
        loading: false, step: 2,
        importResult, assessment, skills,
        selectedSkill: skills[0]?.slug ?? 'marathon_st_default',
        targetH: h, targetM: m,
      })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : '出错了，请重试' })
    }
  }

  async function generatePlan() {
    const token = getToken()
    patch({ loading: true, error: null, step: 4 })
    try {
      const res = await fetch('/api/marathon/plans/generate', {
        method: 'POST', headers: authHdr(token),
        body: JSON.stringify({
          athlete_id: ATHLETE_ID,
          target_time_sec: hmToSec(s.targetH, s.targetM),
          plan_weeks: s.planWeeks,
          skill_slug: s.selectedSkill,
          availability: {
            weekly_training_days: s.weeklyDays,
            preferred_long_run_weekday: 6,
          },
        }),
      })
      if (!res.ok) {
        const msg = await res.text().catch(() => '生成失败')
        throw new Error(msg)
      }
      const plan: GeneratedPlan = await res.json()
      patch({ loading: false, generatedPlan: plan, step: 5 })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : '生成失败', step: 3 })
    }
  }

  async function confirmAndSync() {
    if (!s.generatedPlan) return
    const token = getToken()
    patch({ loading: true, error: null })
    try {
      const cRes = await fetch(`/api/plans/${s.generatedPlan.id}/confirm`, {
        method: 'POST', headers: authHdr(token),
      })
      if (!cRes.ok) throw new Error('确认计划失败')

      const sRes = await fetch(`/api/plans/${s.generatedPlan.id}/sync/coros`, {
        method: 'POST', headers: authHdr(token),
      })
      const syncResult = sRes.ok ? await sRes.json() : { synced_count: 0, failed_count: 0 }
      patch({ loading: false, syncResult })
    } catch (e) {
      patch({ loading: false, error: e instanceof Error ? e.message : '同步失败' })
    }
  }

  /* ── Render ─────────────────────────────────────────── */

  return (
    <div style={{ minHeight: '100dvh', background: 'var(--paper)', display: 'flex',
                  flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--rule-soft)',
                    display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          onClick={() => router.back()}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 22, color: 'var(--ink-faint)', padding: 0, lineHeight: 1 }}
        >‹</button>
        <div className="hand" style={{ fontSize: 17, fontWeight: 700 }}>生成训练计划</div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          {([1, 2, 3, 4, 5] as Step[]).map(n => (
            <div key={n} style={{
              width: 6, height: 6, borderRadius: '50%',
              background: n <= s.step ? 'var(--ink)' : 'var(--rule)',
            }} />
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: '24px 20px', maxWidth: 440, width: '100%',
                    alignSelf: 'center', overflowY: 'auto' }}>
        {s.error && (
          <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 8,
                        background: 'var(--accent-light)', border: '1.5px solid var(--accent)' }}>
            <span className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>{s.error}</span>
          </div>
        )}

        {s.step === 1 && <Step1Loading />}
        {s.step === 2 && s.assessment && s.importResult && (
          <Step2Status assessment={s.assessment} importResult={s.importResult} />
        )}
        {s.step === 3 && s.skills && (
          <Step3Config
            skills={s.skills}
            selectedSkill={s.selectedSkill}
            targetH={s.targetH} targetM={s.targetM}
            planWeeks={s.planWeeks} weeklyDays={s.weeklyDays}
            onChange={patch}
          />
        )}
        {s.step === 4 && <Step4Generating planWeeks={s.planWeeks} />}
        {s.step === 5 && s.generatedPlan && (
          <Step5Preview
            plan={s.generatedPlan}
            syncResult={s.syncResult}
            loading={s.loading}
            onConfirmSync={confirmAndSync}
            onDone={() => router.replace('/plan')}
          />
        )}
      </div>

      {/* Footer CTA */}
      {!s.loading && (
        <div style={{ padding: '16px 20px 32px', maxWidth: 440, width: '100%', alignSelf: 'center' }}>
          {s.step === 2 && (
            <PrimaryBtn onClick={() => patch({ step: 3 })}>设定目标 →</PrimaryBtn>
          )}
          {s.step === 3 && (
            <PrimaryBtn onClick={generatePlan}>生成计划 →</PrimaryBtn>
          )}
          {s.step === 5 && !s.syncResult && (
            <PrimaryBtn onClick={confirmAndSync} loading={s.loading}>
              确认并同步到 COROS →
            </PrimaryBtn>
          )}
          {s.step === 5 && s.syncResult && (
            <PrimaryBtn onClick={() => router.replace('/plan')}>查看计划 →</PrimaryBtn>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Step components ───────────────────────────────────── */

function Step1Loading() {
  return (
    <div style={{ textAlign: 'center', paddingTop: 60 }}>
      <div style={{ fontSize: 40, marginBottom: 16 }}>⚙️</div>
      <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
        分析中…
      </div>
      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
        正在导入 COROS 数据并评估你的跑步能力
      </div>
    </div>
  )
}

function Step2Status({ assessment, importResult }: {
  assessment: RunningAssessmentOut
  importResult: HistoryImportOut
}) {
  const [lo, hi] = assessment.estimated_marathon_time_range_sec
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>你的状态</div>
      <div className="hand text-faint" style={{ fontSize: 13, marginBottom: 20 }}>
        基于 {importResult.imported_count} 条历史活动
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <StatBox label="综合评分" value={`${assessment.overall_score}`} unit="/100" />
        <StatBox
          label="预测完赛"
          value={fmtTime(lo)}
          unit={`– ${fmtTime(hi)}`}
        />
      </div>

      <div className="sk-card-soft" style={{ marginBottom: 16 }}>
        <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 4 }}>评估结论</div>
        <div className="hand" style={{ fontSize: 14, lineHeight: 1.6 }}>{assessment.summary}</div>
      </div>

      {assessment.limiting_factors.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 6 }}>限制因素</div>
          {assessment.limiting_factors.map((f, i) => (
            <div key={i} className="hand" style={{ fontSize: 13, padding: '4px 0',
                 borderBottom: '1px solid var(--rule-soft)' }}>
              · {f}
            </div>
          ))}
        </div>
      )}

      {assessment.warnings.length > 0 && (
        <div style={{ padding: '10px 14px', background: 'var(--accent-light)',
                      border: '1.5px solid var(--accent)', borderRadius: 8 }}>
          {assessment.warnings.map((w, i) => (
            <div key={i} className="hand" style={{ fontSize: 13, color: 'var(--accent)' }}>⚠ {w}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function Step3Config({ skills, selectedSkill, targetH, targetM, planWeeks, weeklyDays, onChange }: {
  skills: SkillManifestOut[]
  selectedSkill: string
  targetH: number; targetM: number
  planWeeks: number; weeklyDays: number
  onChange: (p: Partial<WizardState>) => void
}) {
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>设定目标</div>

      <FormField label="目标完赛时间">
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            value={targetH}
            onChange={e => onChange({ targetH: Number(e.target.value) })}
            style={selectStyle}
            className="hand"
          >
            {[2, 3, 4, 5, 6].map(h => (
              <option key={h} value={h}>{h} 小时</option>
            ))}
          </select>
          <select
            value={targetM}
            onChange={e => onChange({ targetM: Number(e.target.value) })}
            style={selectStyle}
            className="hand"
          >
            {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map(m => (
              <option key={m} value={m}>{m.toString().padStart(2, '0')} 分</option>
            ))}
          </select>
        </div>
      </FormField>

      <FormField label="训练周数">
        <div style={{ display: 'flex', gap: 8 }}>
          {[12, 16, 20, 24].map(w => (
            <button key={w} onClick={() => onChange({ planWeeks: w })} className="hand"
              style={{
                flex: 1, padding: '10px 4px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                border: `1.5px solid ${planWeeks === w ? 'var(--ink)' : 'var(--rule)'}`,
                background: planWeeks === w ? 'var(--ink)' : 'var(--paper)',
                color: planWeeks === w ? 'var(--paper)' : 'var(--ink)',
              }}>
              {w}周
            </button>
          ))}
        </div>
      </FormField>

      <FormField label="每周训练天数">
        <div style={{ display: 'flex', gap: 8 }}>
          {[3, 4, 5, 6].map(d => (
            <button key={d} onClick={() => onChange({ weeklyDays: d })} className="hand"
              style={{
                flex: 1, padding: '10px 4px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                border: `1.5px solid ${weeklyDays === d ? 'var(--ink)' : 'var(--rule)'}`,
                background: weeklyDays === d ? 'var(--ink)' : 'var(--paper)',
                color: weeklyDays === d ? 'var(--paper)' : 'var(--ink)',
              }}>
              {d}天
            </button>
          ))}
        </div>
      </FormField>

      <FormField label="训练方案">
        {skills.map(skill => (
          <div key={skill.slug} onClick={() => onChange({ selectedSkill: skill.slug })}
            style={{
              padding: '12px 14px', marginBottom: 10, borderRadius: 8, cursor: 'pointer',
              border: `1.5px solid ${selectedSkill === skill.slug ? 'var(--ink)' : 'var(--rule)'}`,
              background: selectedSkill === skill.slug ? 'var(--paper-warm)' : 'var(--paper)',
            }}>
            <div className="hand" style={{ fontSize: 15, fontWeight: 700 }}>{skill.name}</div>
            <div className="hand text-faint" style={{ fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
              {skill.description}
            </div>
            {skill.tags.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {skill.tags.map(t => (
                  <span key={t} className="sk-pill" style={{ fontSize: 11 }}>{t}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </FormField>
    </div>
  )
}

function Step4Generating({ planWeeks }: { planWeeks: number }) {
  return (
    <div style={{ textAlign: 'center', paddingTop: 60 }}>
      <div style={{ fontSize: 40, marginBottom: 16 }}>🏗️</div>
      <div className="hand" style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
        生成中…
      </div>
      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
        正在为你生成 {planWeeks} 周训练计划
      </div>
    </div>
  )
}

function Step5Preview({ plan, syncResult, loading, onConfirmSync, onDone }: {
  plan: GeneratedPlan
  syncResult: { synced_count: number; failed_count: number } | null
  loading: boolean
  onConfirmSync: () => void
  onDone: () => void
}) {
  if (syncResult) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 40 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          计划已就绪
        </div>
        <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
          已同步 {syncResult.synced_count} 个训练到 COROS 手表
          {syncResult.failed_count > 0 && `，${syncResult.failed_count} 个失败`}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        {plan.title ?? '训练计划'}
      </div>
      {plan.target_time_sec && (
        <div className="hand" style={{ fontSize: 14, color: 'var(--accent)', marginBottom: 16 }}>
          目标 sub-{fmtTime(plan.target_time_sec)}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
        <PreviewRow label="总周数" value={`${plan.weeks} 周`} />
        {plan.start_date && (
          <PreviewRow label="开始日期" value={plan.start_date} />
        )}
        {plan.race_date && (
          <PreviewRow label="比赛日期" value={plan.race_date} />
        )}
      </div>

      <div className="hand text-faint" style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 8 }}>
        确认后计划将同步到你的 COROS 手表，开始后将每周生成调整建议。
      </div>
    </div>
  )
}

/* ── UI helpers ──────────────────────────────────────────── */

function StatBox({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div style={{ flex: 1, padding: '12px 14px', background: 'var(--paper-warm)',
                  borderRadius: 8, textAlign: 'center' }}>
      <div className="hand text-faint" style={{ fontSize: 11, marginBottom: 4 }}>{label}</div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {unit && <div className="hand text-faint" style={{ fontSize: 11, marginTop: 2 }}>{unit}</div>}
    </div>
  )
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between',
                  padding: '10px 0', borderBottom: '1px solid var(--rule-soft)' }}>
      <span className="hand text-faint" style={{ fontSize: 13 }}>{label}</span>
      <span className="hand" style={{ fontSize: 13 }}>{value}</span>
    </div>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div className="hand text-faint" style={{ fontSize: 12, marginBottom: 8 }}>{label}</div>
      {children}
    </div>
  )
}

function PrimaryBtn({ children, onClick, loading }: {
  children: React.ReactNode
  onClick: () => void
  loading?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        width: '100%', padding: '14px',
        background: loading ? 'var(--rule)' : 'var(--ink)',
        color: 'var(--paper)', border: 'none', borderRadius: 8,
        fontFamily: 'var(--font-hand)', fontSize: 16,
        cursor: loading ? 'default' : 'pointer',
      }}
    >
      {loading ? '处理中…' : children}
    </button>
  )
}

const selectStyle: React.CSSProperties = {
  flex: 1, padding: '10px 12px',
  border: '1.5px solid var(--rule)', borderRadius: 8,
  fontSize: 15, background: 'var(--paper)', color: 'var(--ink)',
  fontFamily: 'var(--font-hand)', outline: 'none',
}
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -15
```
Expected: PASS — all blockE tests pass.

- [ ] **Step 5: Type check**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check 2>&1 | tail -5
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/plan/generate/page.tsx web/__tests__/blockE.test.tsx
git commit -m "feat(web): add 5-step plan generation wizard at /plan/generate

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Wire `EmptyPlanState` + final cleanup

**Files:**
- Modify: `web/components/EmptyPlanState.tsx`

- [ ] **Step 1: Update CTA href**

In `web/components/EmptyPlanState.tsx`, replace:

```tsx
        href="/onboarding"
```

with:

```tsx
        href="/plan/generate"
```

Also update the button label for clarity. Replace:

```tsx
        设定目标 →
```

with:

```tsx
        生成训练计划 →
```

- [ ] **Step 2: Run full frontend test suite**

```bash
cd /Users/paul/Work/ST/web && pnpm test 2>&1 | tail -8
```
Expected: all tests pass (57+ tests).

- [ ] **Step 3: Type check**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check 2>&1 | tail -5
```
Expected: no errors.

- [ ] **Step 4: Run full backend suite**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest discover -s tests -v 2>&1 | tail -5
```
Expected: all tests pass (80+).

- [ ] **Step 5: Final commit**

```bash
cd /Users/paul/Work/ST
git add web/components/EmptyPlanState.tsx
git commit -m "feat(web): update EmptyPlanState CTA to /plan/generate

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Acceptance Criteria

- [ ] Tab bar shows 概览 | 运动 | 本周 | 计划 (no 今天)
- [ ] Navigating to `/today` redirects to `/workouts/2026-MM-DD`
- [ ] Week page: tapping any day navigates to `/workouts/[date]`
- [ ] Dashboard TodayCard navigates to `/workouts/[today]`
- [ ] `GET /athletes/{id}/workout/{date}` returns 200 with null workout when no plan, 422 on bad date
- [ ] `/workouts/[date]` shows workout title + big numbers + steps; shows 休息日 on rest days
- [ ] `/plan/generate` auto-runs COROS import + assessment on mount, shows 分析中 loading state
- [ ] Wizard progresses through 5 steps: 分析中 → 你的状态 → 设定目标 → 生成中 → 预览
- [ ] Skill cards are selectable in step 3
- [ ] Confirm button triggers confirm + COROS sync, shows success count
- [ ] EmptyPlanState on Plan tab links to `/plan/generate`
- [ ] All backend tests pass, all frontend tests pass, `pnpm type-check` exit 0

## Known Limitations (out of scope)

- `ATHLETE_ID = 1` is hardcoded throughout — multi-user support deferred
- `/workouts/[date]` shows `matched_activity_id` only (not full activity detail) — sufficient for mark-done
- No skeleton loading state on workout detail page — plain spinner is acceptable
- No back navigation from wizard to a specific step (wizard is forward-only)
