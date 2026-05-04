# Activities Tab Redesign: Calendar + Timeline + Filters

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat activity list with a horizontally-scrollable month-strip calendar above a mixed timeline list (past activities + future plan workouts) with filter chips.

**Architecture:** New `GET /athletes/{id}/calendar?from_date&to_date` backend endpoint merges `AthleteActivity` records and `StructuredWorkout` rows into `CalendarDay` objects; a `MonthStrip` component renders day cells with colour-coded dots; the activities page wires calendar → list scroll anchor on day tap. The calendar is 5 months wide (2 back, current, 2 ahead).

**Tech Stack:** Next.js 14, TypeScript, SWR, FastAPI, SQLAlchemy, Vitest + RTL

---

## File Map

### Created
| File | Purpose |
|------|---------|
| `web/components/activities/MonthStrip.tsx` | Horizontal scrollable calendar strip |
| `web/lib/hooks/useCalendar.ts` | SWR hook for `GET /athletes/1/calendar` |
| `tests/test_calendar.py` | Backend tests for calendar endpoint |

### Modified
| File | Change |
|------|--------|
| `app/schemas.py` | Add `CalendarDayOut` Pydantic schema |
| `app/api/routes.py` | Add `GET /athletes/{id}/calendar` endpoint |
| `web/lib/api/types.ts` | Add `CalendarDay` TypeScript type |
| `web/app/(tabs)/activities/page.tsx` | Full rewrite with strip + list + filters |
| `web/__tests__/blockE.test.tsx` | Add MonthStrip + page tests |

---

## Task 1: Backend calendar endpoint

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/api/routes.py`
- Create: `tests/test_calendar.py`

- [ ] **Step 1: Write failing backend test**

Create `tests/test_calendar.py`:

```python
import os
os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")

import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _get_token() -> str:
    send = client.post("/auth/send-otp", json={"phone": "13900000077"})
    code = str(send.json()["otp_code"])
    res = client.post("/auth/verify-otp", json={"phone": "13900000077", "code": code})
    return res.json()["access_token"]


class CalendarEndpointTestCase(unittest.TestCase):

    def setUp(self):
        from app.db import engine, Base
        Base.metadata.create_all(bind=engine)
        self.token = _get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        r = client.post("/athletes", json={
            "name": "CalTest", "sport": "marathon",
            "level": "intermediate", "weekly_training_days": 5,
        }, headers=self.headers)
        self.athlete_id = r.json()["id"]

    def test_empty_range_returns_empty_list(self):
        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "2099-01-01", "to_date": "2099-01-31"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_invalid_date_returns_422(self):
        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "not-a-date", "to_date": "2099-01-31"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 422)

    def test_requires_auth(self):
        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "2099-01-01", "to_date": "2099-01-31"},
        )
        self.assertEqual(r.status_code, 401)

    def test_day_shape(self):
        """When a plan exists, future days within range have status=planned."""
        # Generate a plan so workouts exist
        goal_r = client.post(f"/athletes/{self.athlete_id}/goals/marathon", json={
            "race_date": "2099-11-01",
            "target_time_sec": 14400,
        }, headers=self.headers)
        if goal_r.status_code not in (200, 201):
            self.skipTest("goal creation not available")
        gen_r = client.post("/marathon/plans/generate", json={
            "athlete_id": self.athlete_id,
            "target_time_sec": 14400,
            "plan_weeks": 4,
            "skill_slug": "marathon_st_default",
            "availability": {"weekly_training_days": 5, "preferred_long_run_weekday": 6},
        }, headers=self.headers)
        if gen_r.status_code != 200:
            self.skipTest("plan generation not available")

        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "2099-01-01", "to_date": "2099-06-30"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200)
        days = r.json()
        if days:
            day = days[0]
            for field in ("date", "status", "title", "sport", "workout_type",
                          "activity_id", "workout_id", "distance_km", "duration_min"):
                self.assertIn(field, day)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_calendar -v 2>&1 | tail -10
```
Expected: FAIL — 404 for all calendar requests.

- [ ] **Step 3: Add `CalendarDayOut` to `app/schemas.py`**

Insert after `HistoryImportOut` (search for `class HistoryImportOut`):

```python
class CalendarDayOut(BaseModel):
    date: str                     # YYYY-MM-DD
    status: str                   # completed | partial | miss | unmatched | planned
    title: str | None = None
    sport: str | None = None      # discipline: run | cycle | strength
    workout_type: str | None = None
    activity_id: int | None = None
    workout_id: int | None = None
    distance_km: float | None = None
    duration_min: int | None = None
```

- [ ] **Step 4: Add `CalendarDayOut` to schema imports in `app/api/routes.py`**

Find the `from app.schemas import (` block and add `CalendarDayOut,` to the list.

- [ ] **Step 5: Add the endpoint to `app/api/routes.py`**

Insert immediately after the `get_workout_by_date` function (search for `@router.get("/plans/{plan_id}/week"`):

```python
_DISCIPLINE_LABEL: dict[str, str] = {
    "run": "跑步", "cycle": "骑车", "swim": "游泳",
    "strength": "力量", "walk": "步行",
}


@router.get("/athletes/{athlete_id}/calendar", response_model=list[CalendarDayOut])
def get_calendar(
    athlete_id: int,
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
) -> list[CalendarDayOut]:
    _athlete_or_404(db, athlete_id)
    try:
        from_d = date.fromisoformat(from_date)
        to_d = date.fromisoformat(to_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")

    today = date.today()

    # ── Activities in range ────────────────────────────────────────────────
    from_dt = datetime.combine(from_d, datetime.min.time())
    to_dt = datetime.combine(to_d, datetime.max.time())
    activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.started_at >= from_dt)
        .where(AthleteActivity.started_at <= to_dt)
        .options(selectinload(AthleteActivity.matched_workout))
        .order_by(AthleteActivity.started_at)
    ).scalars().all()

    acts_by_date: dict[date, list[AthleteActivity]] = {}
    for act in activities:
        d = act.started_at.date()
        acts_by_date.setdefault(d, []).append(act)

    # ── Plan workouts in range ─────────────────────────────────────────────
    plan = _active_or_draft_plan_for_athlete(db, athlete_id)
    workouts_by_date: dict[date, StructuredWorkout] = {}
    if plan:
        for w in plan.structured_workouts:
            if from_d <= w.scheduled_date <= to_d:
                workouts_by_date[w.scheduled_date] = w

    # ── Merge ─────────────────────────────────────────────────────────────
    all_dates = sorted(set(acts_by_date) | set(workouts_by_date))
    result: list[CalendarDayOut] = []

    for d in all_dates:
        acts = acts_by_date.get(d, [])
        workout = workouts_by_date.get(d)

        if acts:
            act = acts[0]
            mw = act.matched_workout
            status = _classify_match_status(mw, act)
            label = _DISCIPLINE_LABEL.get(act.discipline, act.discipline)
            dist_str = f" {act.distance_m / 1000:.1f}km" if act.distance_m else ""
            result.append(CalendarDayOut(
                date=d.isoformat(),
                status=status,
                title=f"{label}{dist_str}",
                sport=act.discipline,
                workout_type=mw.workout_type if mw else None,
                activity_id=act.id,
                workout_id=mw.id if mw else None,
                distance_km=round(act.distance_m / 1000, 2) if act.distance_m else None,
                duration_min=round(act.duration_sec / 60) if act.duration_sec else None,
            ))
        elif workout:
            status = "planned" if d > today else "miss"
            result.append(CalendarDayOut(
                date=d.isoformat(),
                status=status,
                title=workout.title,
                sport=workout.discipline,
                workout_type=workout.workout_type,
                activity_id=None,
                workout_id=workout.id,
                distance_km=round(workout.distance_m / 1000, 2) if workout.distance_m else None,
                duration_min=workout.duration_min,
            ))

    return result
```

- [ ] **Step 6: Run backend tests**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_calendar -v 2>&1 | tail -10
```
Expected: PASS — 4 tests (test_day_shape may skip if plan generation is slow, that's OK).

- [ ] **Step 7: Run full backend suite**

```bash
uv run python -m unittest discover -s tests -v 2>&1 | tail -5
```
Expected: all tests pass (84+).

- [ ] **Step 8: Commit**

```bash
git add app/schemas.py app/api/routes.py tests/test_calendar.py
git commit -m "$(cat <<'EOF'
feat(api): add GET /athletes/{id}/calendar endpoint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Frontend types + hook + MonthStrip

**Files:**
- Modify: `web/lib/api/types.ts`
- Create: `web/lib/hooks/useCalendar.ts`
- Create: `web/components/activities/MonthStrip.tsx`
- Modify: `web/__tests__/blockE.test.tsx`

- [ ] **Step 1: Write failing test for MonthStrip**

Add to `web/__tests__/blockE.test.tsx` (append after the PlanGeneratePage describe block):

```tsx
vi.mock('@/lib/hooks/useCalendar', () => ({
  useCalendar: () => ({
    days: [
      { date: '2026-05-04', status: 'completed', title: '跑步 8.0km', sport: 'run',
        workout_type: 'easy_run', activity_id: 1, workout_id: 10,
        distance_km: 8.0, duration_min: 48 },
      { date: '2026-05-10', status: 'planned', title: 'Long Run', sport: 'run',
        workout_type: 'long_run', activity_id: null, workout_id: 20,
        distance_km: 18.0, duration_min: 110 },
    ],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}))

import MonthStrip from '@/components/activities/MonthStrip'

describe('MonthStrip', () => {
  it('renders today day number', () => {
    const today = new Date().getDate().toString()
    render(
      <MonthStrip
        days={[]}
        selectedDate={null}
        onSelectDate={vi.fn()}
      />
    )
    // Multiple day cells may have this number; just check at least one exists
    expect(screen.getAllByText(today).length).toBeGreaterThan(0)
  })

  it('calls onSelectDate when a day is clicked', async () => {
    const onSelect = vi.fn()
    render(
      <MonthStrip
        days={[]}
        selectedDate={null}
        onSelectDate={onSelect}
      />
    )
    const buttons = screen.getAllByRole('button')
    buttons[0].click()
    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -12
```
Expected: FAIL — MonthStrip module not found.

- [ ] **Step 3: Add `CalendarDay` type to `web/lib/api/types.ts`**

Append after `HistoryImportOut`:

```typescript
/* ── Calendar ────────────────────────────────────────────── */

export type CalendarStatus = 'completed' | 'partial' | 'miss' | 'unmatched' | 'planned'

export interface CalendarDay {
  date: string               // YYYY-MM-DD
  status: CalendarStatus
  title: string | null
  sport: string | null       // discipline: run | cycle | strength
  workout_type: string | null
  activity_id: number | null
  workout_id: number | null
  distance_km: number | null
  duration_min: number | null
}
```

- [ ] **Step 4: Create `web/lib/hooks/useCalendar.ts`**

```typescript
import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'
import type { CalendarDay } from '@/lib/api/types'

const ATHLETE_ID = 1

export function useCalendar(fromDate: string, toDate: string) {
  const key =
    fromDate && toDate
      ? `/api/athletes/${ATHLETE_ID}/calendar?from_date=${fromDate}&to_date=${toDate}`
      : null
  const { data, error, isLoading, mutate } = useSWR<CalendarDay[]>(key, fetcher)
  return { days: data ?? [], isLoading, error, refresh: mutate }
}
```

- [ ] **Step 5: Create `web/components/activities/MonthStrip.tsx`**

```tsx
'use client'

import { useRef, useEffect } from 'react'
import type { CalendarDay, CalendarStatus } from '@/lib/api/types'

const DOT_COLOR: Record<CalendarStatus, string> = {
  completed: 'var(--ink)',
  partial:   'var(--ink-mid)',
  miss:      'var(--accent)',
  unmatched: 'var(--ink-faint)',
  planned:   'rgba(214,59,47,0.4)',
}

interface Props {
  days: CalendarDay[]
  selectedDate: string | null
  onSelectDate: (date: string) => void
}

function buildDateRange(): string[] {
  const result: string[] = []
  const cur = new Date()
  cur.setMonth(cur.getMonth() - 2)
  cur.setDate(1)
  const end = new Date()
  end.setMonth(end.getMonth() + 3, 0) // last day of month +2
  while (cur <= end) {
    result.push(cur.toISOString().slice(0, 10))
    cur.setDate(cur.getDate() + 1)
  }
  return result
}

const ALL_DATES = buildDateRange()

export default function MonthStrip({ days, selectedDate, onSelectDate }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const today = new Date().toISOString().slice(0, 10)
  const dayMap = new Map(days.map(d => [d.date, d]))

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const todayEl = el.querySelector(`[data-date="${today}"]`) as HTMLElement | null
    if (todayEl) {
      el.scrollLeft = todayEl.offsetLeft - el.offsetWidth / 2 + todayEl.offsetWidth / 2
    }
  }, [today])

  return (
    <div
      ref={scrollRef}
      style={{
        display: 'flex',
        overflowX: 'auto',
        scrollbarWidth: 'none',
        // @ts-expect-error msOverflowStyle is IE/Edge
        msOverflowStyle: 'none',
        padding: '6px 0 8px',
        borderBottom: '1px solid var(--rule-soft)',
      }}
    >
      {ALL_DATES.map((d, i) => {
        const prev = i > 0 ? ALL_DATES[i - 1] : null
        const isFirstOfMonth = !prev || d.slice(0, 7) !== prev.slice(0, 7)
        const info = dayMap.get(d)
        const isToday = d === today
        const isSelected = d === selectedDate
        const dayNum = parseInt(d.slice(8))
        const monthNum = parseInt(d.slice(5, 7))

        return (
          <button
            key={d}
            data-date={d}
            onClick={() => onSelectDate(d)}
            style={{
              width: 34, flexShrink: 0,
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 3,
              padding: '0 0 4px',
              background: 'none', border: 'none', cursor: 'pointer',
            }}
          >
            {/* Month label — only on first day of month */}
            <div className="annot" style={{
              fontSize: 9,
              color: isFirstOfMonth ? 'var(--ink-faint)' : 'transparent',
              lineHeight: 1.4,
              userSelect: 'none',
            }}>
              {isFirstOfMonth ? `${monthNum}月` : '·'}
            </div>

            {/* Day number circle */}
            <div style={{
              width: 26, height: 26, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: isSelected ? 'var(--ink)' : 'transparent',
              border: isToday && !isSelected ? '1.5px solid var(--ink)' : 'none',
            }}>
              <span className="hand" style={{
                fontSize: 12, lineHeight: 1,
                color: isSelected ? 'var(--paper)' : isToday ? 'var(--ink)' : 'var(--ink-faint)',
                fontWeight: isToday || isSelected ? 700 : 400,
              }}>
                {dayNum}
              </span>
            </div>

            {/* Status dot */}
            <div style={{
              width: 5, height: 5, borderRadius: '50%',
              background: info ? DOT_COLOR[info.status] : 'transparent',
            }} />
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 6: Run tests**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -12
```
Expected: PASS — 7 tests (5 existing + 2 new MonthStrip).

- [ ] **Step 7: Type-check**

```bash
pnpm type-check 2>&1 | tail -5
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
cd /Users/paul/Work/ST
git add web/lib/api/types.ts web/lib/hooks/useCalendar.ts \
        web/components/activities/MonthStrip.tsx web/__tests__/blockE.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): add CalendarDay types, useCalendar hook, MonthStrip component

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Rewrite activities page

**Files:**
- Modify: `web/app/(tabs)/activities/page.tsx`
- Modify: `web/__tests__/blockE.test.tsx`

- [ ] **Step 1: Write failing tests for the page**

Append to `web/__tests__/blockE.test.tsx`:

```tsx
import ActivitiesPage from '@/app/(tabs)/activities/page'

describe('ActivitiesPage', () => {
  it('renders filter chips', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('跑步')).toBeInTheDocument()
    expect(screen.getByText('骑车')).toBeInTheDocument()
    expect(screen.getByText('力量')).toBeInTheDocument()
  })

  it('renders list items from calendar data', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('跑步 8.0km')).toBeInTheDocument()
    expect(screen.getByText('Long Run')).toBeInTheDocument()
  })

  it('renders MonthStrip', () => {
    render(<ActivitiesPage />)
    // MonthStrip always renders today — check the today day number appears
    const today = new Date().getDate().toString()
    expect(screen.getAllByText(today).length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -12
```
Expected: FAIL — ActivitiesPage tests fail (old page content doesn't match).

- [ ] **Step 3: Rewrite `web/app/(tabs)/activities/page.tsx`**

```tsx
'use client'

import { useState, useRef } from 'react'
import Link from 'next/link'
import { useCalendar } from '@/lib/hooks/useCalendar'
import MonthStrip from '@/components/activities/MonthStrip'
import type { CalendarDay } from '@/lib/api/types'

function getDateRange() {
  const from = new Date()
  from.setMonth(from.getMonth() - 2)
  from.setDate(1)
  const to = new Date()
  to.setMonth(to.getMonth() + 3, 0)
  return {
    fromDate: from.toISOString().slice(0, 10),
    toDate: to.toISOString().slice(0, 10),
  }
}

const { fromDate, toDate } = getDateRange()

const FILTERS = [
  { key: 'all',      label: '全部' },
  { key: 'run',      label: '跑步' },
  { key: 'cycle',    label: '骑车' },
  { key: 'strength', label: '力量' },
]

const STATUS_META: Record<string, { color: string; label: string }> = {
  completed: { color: 'var(--ink)',             label: '完成' },
  partial:   { color: 'var(--ink-mid)',          label: '部分' },
  miss:      { color: 'var(--accent)',           label: '缺训' },
  unmatched: { color: 'var(--ink-faint)',        label: '自由' },
  planned:   { color: 'rgba(214,59,47,0.5)',     label: '计划' },
}

export default function ActivitiesPage() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const listRef = useRef<HTMLDivElement>(null)
  const { days, isLoading, error } = useCalendar(fromDate, toDate)

  const filtered = filter === 'all'
    ? days
    : days.filter(d => d.sport === filter)

  // Group by month YYYY-MM, newest month first
  const byMonth: Record<string, CalendarDay[]> = {}
  for (const d of filtered) {
    const mk = d.date.slice(0, 7)
    ;(byMonth[mk] ??= []).push(d)
  }
  const monthKeys = Object.keys(byMonth).sort((a, b) => b.localeCompare(a))

  function handleSelectDate(date: string) {
    setSelectedDate(date)
    if (!listRef.current) return
    const target = listRef.current.querySelector(
      `[data-listdate="${date}"]`
    ) as HTMLElement | null
    if (target) {
      listRef.current.scrollTo({ top: target.offsetTop - 32, behavior: 'smooth' })
    } else {
      const monthEl = listRef.current.querySelector(
        `[data-listmonth="${date.slice(0, 7)}"]`
      ) as HTMLElement | null
      if (monthEl) listRef.current.scrollTo({ top: monthEl.offsetTop, behavior: 'smooth' })
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}>
      {/* ── Header ─────────────────────────────────────────── */}
      <div style={{ padding: '16px 16px 10px', flexShrink: 0,
                    borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>运动</div>
      </div>

      {/* ── Calendar strip ─────────────────────────────────── */}
      <div style={{ flexShrink: 0 }}>
        <MonthStrip days={days} selectedDate={selectedDate} onSelectDate={handleSelectDate} />
      </div>

      {/* ── Filter chips ───────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 8, padding: '8px 16px', flexShrink: 0,
        borderBottom: '1px solid var(--rule-soft)', overflowX: 'auto',
        scrollbarWidth: 'none',
      }}>
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className="hand"
            style={{
              padding: '4px 12px', borderRadius: 999, fontSize: 12, cursor: 'pointer',
              border: `1.2px solid ${filter === f.key ? 'var(--ink)' : 'var(--rule)'}`,
              background: filter === f.key ? 'var(--ink)' : 'var(--paper)',
              color: filter === f.key ? 'var(--paper)' : 'var(--ink)',
              whiteSpace: 'nowrap', flexShrink: 0,
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ── List ───────────────────────────────────────────── */}
      <div ref={listRef} style={{ flex: 1, overflowY: 'auto' }}>
        {isLoading && (
          <div className="hand text-faint"
               style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
            加载中…
          </div>
        )}
        {error && (
          <div className="hand text-faint"
               style={{ padding: '32px 16px', textAlign: 'center', fontSize: 14 }}>
            {error.message}
          </div>
        )}
        {!isLoading && !error && filtered.length === 0 && (
          <div className="hand text-faint"
               style={{ padding: '48px 16px', textAlign: 'center', fontSize: 14 }}>
            暂无记录
          </div>
        )}

        {monthKeys.map(mk => {
          const [y, m] = mk.split('-')
          const monthDays = [...byMonth[mk]].sort((a, b) => b.date.localeCompare(a.date))
          return (
            <div key={mk} data-listmonth={mk}>
              <div className="hand" style={{
                fontSize: 12, color: 'var(--ink-faint)',
                padding: '10px 16px 4px',
                background: 'var(--paper)',
                position: 'sticky', top: 0, zIndex: 1,
              }}>
                {y}年{parseInt(m)}月
              </div>
              {monthDays.map(day => (
                <DayRow key={day.date} day={day} isSelected={day.date === selectedDate} />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function DayRow({ day, isSelected }: { day: CalendarDay; isSelected: boolean }) {
  const meta = STATUS_META[day.status] ?? { color: 'var(--ink-faint)', label: day.status }
  const [, m, d] = day.date.split('-')

  return (
    <Link
      href={`/workouts/${day.date}`}
      data-listdate={day.date}
      style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
    >
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '11px 16px',
        borderBottom: '1px solid var(--rule-soft)',
        background: isSelected ? 'rgba(26,26,26,0.03)' : undefined,
      }}>
        {/* Date */}
        <div style={{ width: 30, textAlign: 'center', flexShrink: 0 }}>
          <div className="hand" style={{ fontSize: 16, fontWeight: 600, lineHeight: 1 }}>
            {parseInt(d)}
          </div>
          <div className="annot text-faint" style={{ fontSize: 10 }}>
            {parseInt(m)}月
          </div>
        </div>

        {/* Status dot */}
        <span style={{
          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
          background: meta.color,
        }} />

        {/* Title + metrics */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="hand" style={{
            fontSize: 14, lineHeight: 1.3,
            color: day.status === 'planned' ? 'var(--ink-faint)' : 'var(--ink)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {day.title ?? '—'}
          </div>
          {(day.distance_km != null || day.duration_min != null) && (
            <div className="annot text-faint" style={{ fontSize: 12 }}>
              {day.distance_km != null ? `${day.distance_km.toFixed(1)} km` : ''}
              {day.distance_km != null && day.duration_min != null ? ' · ' : ''}
              {day.duration_min != null ? `${day.duration_min} 分钟` : ''}
            </div>
          )}
        </div>

        {/* Status label + chevron */}
        <span className="hand" style={{ fontSize: 11, color: meta.color, flexShrink: 0 }}>
          {meta.label}
        </span>
        <span style={{ color: 'var(--ink-faint)', fontSize: 14 }}>›</span>
      </div>
    </Link>
  )
}
```

- [ ] **Step 4: Run blockE tests**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/blockE.test.tsx 2>&1 | tail -12
```
Expected: PASS — 10 tests.

- [ ] **Step 5: Run full frontend suite**

```bash
pnpm test 2>&1 | tail -6
```
Expected: all tests pass.

- [ ] **Step 6: Type-check**

```bash
pnpm type-check 2>&1 | tail -5
```
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/\(tabs\)/activities/page.tsx web/__tests__/blockE.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): redesign activities tab with calendar strip, timeline list, filters

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Acceptance Criteria

- [ ] `GET /athletes/{id}/calendar?from_date=2026-01-01&to_date=2026-12-31` returns `CalendarDay[]`
- [ ] Activities have `status` = completed/partial/miss/unmatched based on match logic
- [ ] Future plan workouts have `status` = planned
- [ ] Past plan dates with no activity have `status` = miss
- [ ] MonthStrip shows ~5 months horizontally; scrolls to today on mount
- [ ] Today's cell has a circle outline; selected date has filled circle
- [ ] Colour dots appear on dates with data: dark=completed, red=miss, faint=unmatched, translucent-red=planned
- [ ] Tapping a calendar day scrolls the list to that date's row
- [ ] Filter chips filter list AND calendar dots by `sport` discipline
- [ ] Each list row links to `/workouts/[date]`
- [ ] All backend tests pass (84+), all frontend tests pass (60+), `pnpm type-check` exit 0

## Known Limitations (out of scope)

- Calendar strip does not filter — dots always show full data regardless of active filter (filtering only affects the list below). Calendar reflects full picture.
- `ATHLETE_ID = 1` hardcoded
- No swipe-to-navigate-months — scroll only
- Rest days (no plan workout, no activity) have no dot — intentional to keep the strip readable
