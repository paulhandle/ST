# Plan Preview + Workout List + Settings Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Expand the plan generation wizard with a Plan Overview step and a Workout List preview step before the user confirms. (2) Add a "My Plan" entry in Settings showing confirmed workout count with a link to the plan. (3) Add a Revoke Plan action on the Plan page that resets the plan to draft state. (4) Backend endpoint `POST /marathon/plans/{plan_id}/revoke`.

**Architecture:**
- The `/api/marathon/plans/generate` response already returns `structured_workouts`. The frontend `GeneratedPlan` type currently drops them. We extend it to retain the workouts in state.
- The wizard gains two new steps (5a and 5b) between the existing "generating" spinner (step 4) and the confirm button (now step 6). Total steps becomes 6; the dot indicator updates accordingly.
- The Settings page gains one new row linking to `/plan` with a workout count badge fetched from the plan API.
- The Plan page gains a destructive "Revoke plan" button that calls the new backend endpoint.
- The backend endpoint sets `plan.status = DRAFT`, `plan.is_confirmed = False`, and resets all future-dated workouts to `DRAFT` status. No new Alembic migration is needed — no schema change, only data writes.

**Tech Stack:** Python/FastAPI backend, Next.js 14 App Router, TypeScript

---

## Files

- Modify: `web/app/plan/generate/page.tsx` (extend GeneratedPlan type, add steps 5a/5b, update step count)
- Modify: `web/app/(tabs)/plan/page.tsx` (add revoke button and confirmation)
- Modify: `web/app/settings/page.tsx` (add My Plan row)
- Modify: `web/lib/i18n/copy.ts` (new i18n keys)
- Modify: `app/api/routes.py` (add revoke endpoint)
- Modify: `tests/test_block_e.py` or new `tests/test_marathon_plan.py` (backend revoke test)
- Modify: `web/__tests__/planPage.test.tsx` (frontend revoke and settings entry tests)

---

### Task 1: Backend revoke endpoint

**Files:**
- Modify: `app/api/routes.py`

- [ ] **Step 1: Write the failing backend test**

Open `tests/test_block_e.py` (or `tests/test_auth.py` — pick whichever has marathon plan fixtures). Add this test:

```python
def test_revoke_plan_resets_to_draft(self):
    """POST /marathon/plans/{id}/revoke sets status=draft and is_confirmed=False."""
    # Create a user, athlete, and confirmed plan
    token = self._create_user_and_get_token()
    athlete_id = self._create_athlete(token)
    plan_id = self._generate_and_confirm_plan(token, athlete_id)

    # Confirm it is active
    res = self.client.get(f"/marathon/plans/{plan_id}", headers={"Authorization": f"Bearer {token}"})
    self.assertEqual(res.status_code, 200)
    self.assertTrue(res.json()["is_confirmed"])

    # Revoke it
    res = self.client.post(f"/marathon/plans/{plan_id}/revoke", headers={"Authorization": f"Bearer {token}"})
    self.assertEqual(res.status_code, 200)
    body = res.json()
    self.assertEqual(body["status"], "draft")
    self.assertFalse(body["is_confirmed"])
```

(If the test helper methods `_create_user_and_get_token`, `_create_athlete`, and `_generate_and_confirm_plan` do not exist in that test class, look for the pattern used in the existing marathon plan tests — e.g., `test_block_e.py` — and replicate the same setup steps inline in the new test method.)

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_block_e -k test_revoke_plan -v 2>&1 | tail -10
```

Expected: fails with `404` (endpoint does not exist yet).

- [ ] **Step 3: Add the revoke endpoint to routes.py**

Open `app/api/routes.py`. Find the block near `@router.post("/plans/{plan_id}/confirm")` (around line 532). Add the following new endpoint **after** it:

```python
@router.post("/marathon/plans/{plan_id}/revoke", response_model=MarathonPlanOut)
def revoke_marathon_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = db.get(MarathonPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    athlete = db.get(AthleteProfile, plan.athlete_id)
    if athlete is None or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised")
    plan.status = PlanStatus.DRAFT
    plan.is_confirmed = False
    today = date.today()
    for w in plan.structured_workouts:
        if w.scheduled_date >= today:
            w.status = WorkoutStatus.DRAFT
    db.commit()
    db.refresh(plan)
    return plan
```

Verify that `MarathonPlan`, `AthleteProfile`, `PlanStatus`, `WorkoutStatus`, `date` are all already imported in the file (they should be). If `WorkoutStatus` is not imported, add it to the existing model imports at the top of the file.

- [ ] **Step 4: Run the failing test — must pass**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_block_e -k test_revoke_plan -v 2>&1 | tail -5
```

Expected: `OK`.

- [ ] **Step 5: Run full backend tests**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest discover -s tests -v 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/paul/Work/ST
git add app/api/routes.py tests/test_block_e.py
git commit -m "feat(plan): add revoke plan endpoint (reset to draft)"
```

---

### Task 2: Add i18n keys

**Files:**
- Modify: `web/lib/i18n/copy.ts`

- [ ] **Step 1: Add English keys to the `en` object**

In `web/lib/i18n/copy.ts`, find the `planGenerate` section inside the `en` block. Add these keys after the existing ones:

```ts
      overviewTitle: 'Plan Overview',
      overviewPhase: 'Phase',
      overviewWeeks: 'weeks',
      overviewLongRun: 'Long run up to',
      overviewTotalWorkouts: 'Total workouts',
      workoutsTitle: 'All Workouts',
      workoutsWeek: 'Week',
      workoutsConfirmTitle: 'Ready to import',
      workoutsConfirmBody: 'These workouts will be added to your training calendar. You can sync to COROS or revoke the plan from Settings later.',
      revokePlan: 'Revoke plan',
      revokeConfirm: 'This will reset the plan to draft and remove all future workouts from your calendar. Continue?',
      revokeSuccess: 'Plan revoked.',
      myPlan: 'My Training Plan',
      myPlanSub: 'workouts in current cycle',
```

- [ ] **Step 2: Add Chinese keys to the `zh` object**

In the same file, find `planGenerate` under the `zh` block. Add:

```ts
      overviewTitle: '计划概览',
      overviewPhase: '阶段',
      overviewWeeks: '周',
      overviewLongRun: '最长跑距离最多',
      overviewTotalWorkouts: '总课程数',
      workoutsTitle: '全部课程',
      workoutsWeek: '第',
      workoutsConfirmTitle: '准备导入',
      workoutsConfirmBody: '以下课程将加入你的训练日历。可以同步到 COROS，也可以之后在设置中撤销计划。',
      revokePlan: '撤销计划',
      revokeConfirm: '这将把计划重置为草稿并从日历中移除所有未来课程。确认继续？',
      revokeSuccess: '计划已撤销。',
      myPlan: '我的训练计划',
      myPlanSub: '个课程（当前周期）',
```

Also find the `settings` section (not `planGenerate`) and check that it has no `myPlan` key clash. The keys above live under `planGenerate`.

For the settings page row, add to the `settings` section (both `en` and `zh`):

```ts
// in en.settings:
      myPlan: 'My Training Plan',
      myPlanSub: 'View and manage current cycle',
// in zh.settings:
      myPlan: '我的训练计划',
      myPlanSub: '查看和管理当前周期',
```

- [ ] **Step 3: Type-check**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check 2>&1 | grep -i "error" | head -10
```

Expected: no errors.

---

### Task 3: Extend plan generate wizard with preview steps

**Files:**
- Modify: `web/app/plan/generate/page.tsx`

The current wizard flow: Step 1 (loading) → Step 2 (assessment) → Step 3 (config) → Step 4 (generating) → Step 5 (confirm).

New flow: Step 1 → Step 2 → Step 3 → Step 4 → Step 5 (overview) → Step 6 (workout list) → Step 7 (confirm+sync).

- [ ] **Step 1: Write the failing test**

Open `web/__tests__/planPage.test.tsx`. Add:

```ts
// At the top, import the generate page if not already present:
// import PlanGeneratePage from '@/app/plan/generate/page'

it('shows plan overview step with phase and workout count after generation', async () => {
  const mockWorkouts = Array.from({ length: 48 }, (_, i) => ({
    id: i + 1,
    scheduled_date: `2026-06-${String((i % 28) + 1).padStart(2, '0')}`,
    week_index: Math.floor(i / 3),
    day_index: i % 7,
    discipline: 'run',
    workout_type: i % 7 === 5 ? 'long_run' : 'easy',
    title: `Workout ${i + 1}`,
    purpose: 'aerobic base',
    duration_min: 60,
    distance_m: i % 7 === 5 ? 25000 : 10000,
    target_intensity_type: 'easy',
    target_pace_min_sec_per_km: null,
    target_pace_max_sec_per_km: null,
    status: 'draft',
    adaptation_notes: null,
    steps: [],
  }))

  mockFetch
    // Step 1: assessment
    .mockResolvedValueOnce({ ok: false })  // coros import fails (non-blocking)
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        athlete_id: 1, overall_score: 75, readiness_level: 'moderate',
        safe_weekly_distance_range_km: [40, 60],
        safe_training_days_range: [4, 5],
        long_run_capacity_km: 20,
        estimated_marathon_time_range_sec: [12600, 14400],
        goal_status: 'achievable',
        limiting_factors: [],
        warnings: [],
        confidence: 'moderate',
        summary: 'Good base fitness.',
      }),
    })
    .mockResolvedValueOnce({ ok: true, json: async () => [{ slug: 'marathon_st_default', name: 'PP Marathon Plan', version: '0.1.0', sport: 'marathon', author: null, tags: [], description: 'desc', is_active: true }] })
    // generate call
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 42, athlete_id: 1, race_goal_id: null,
        title: '16-Week Marathon Plan', sport: 'marathon', goal: 'finish',
        mode: 'structured', weeks: 16,
        status: 'draft', start_date: '2026-06-01', race_date: '2026-09-20',
        target_time_sec: 14400, is_confirmed: false,
        created_at: '2026-05-16T00:00:00Z', updated_at: '2026-05-16T00:00:00Z',
        structured_workouts: mockWorkouts,
      }),
    })

  render(<PlanGeneratePage />)

  // Wait for step 2 (status) to appear
  await waitFor(() => expect(screen.getByText(/Set goal/i)).toBeInTheDocument())
  fireEvent.click(screen.getByText(/Set goal/i))

  // Step 3: click generate
  await waitFor(() => expect(screen.getByText(/Generate plan/i)).toBeInTheDocument())
  fireEvent.click(screen.getByText(/Generate plan/i))

  // Wait for step 5 overview
  await waitFor(() => {
    expect(screen.getByText(/Plan Overview/i)).toBeInTheDocument()
    expect(screen.getByText(/48/)).toBeInTheDocument() // total workout count
  })
})
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/planPage.test.tsx -- -t "plan overview step" --reporter=verbose 2>&1 | tail -15
```

Expected: fails — "Plan Overview" text does not appear.

- [ ] **Step 3: Extend `GeneratedPlan` and `WizardState` types**

In `web/app/plan/generate/page.tsx`, find the `interface GeneratedPlan` (line ~12):

Old:
```ts
interface GeneratedPlan {
  id: number
  title: string | null
  weeks: number
  start_date: string | null
  race_date: string | null
  target_time_sec: number | null
}
```

New:
```ts
interface WorkoutPreview {
  id: number
  scheduled_date: string
  week_index: number
  day_index: number
  workout_type: string
  title: string
  duration_min: number
  distance_m: number | null
}

interface GeneratedPlan {
  id: number
  title: string | null
  weeks: number
  start_date: string | null
  race_date: string | null
  target_time_sec: number | null
  structured_workouts: WorkoutPreview[]
}
```

Also update `type Step = 1 | 2 | 3 | 4 | 5` to `type Step = 1 | 2 | 3 | 4 | 5 | 6 | 7`.

- [ ] **Step 4: Update the step dot indicator**

Find the dot indicator map in the JSX:
```tsx
{([1, 2, 3, 4, 5] as Step[]).map(n => (
```
Change to:
```tsx
{([1, 2, 3, 4, 5, 6, 7] as Step[]).map(n => (
```

- [ ] **Step 5: Update step navigation and rendering**

Find `generatePlan()`. Change `step: 5` to `step: 5`:
(no change needed — step 5 is now overview)

Find the JSX step rendering block. Replace:
```tsx
        {s.step === 5 && s.generatedPlan && (
          <Step5Preview
            plan={s.generatedPlan}
            syncResult={s.syncResult}
            loading={s.loading}
            onConfirmSync={confirmAndSync}
            onDone={() => router.replace('/plan')}
          />
        )}
```

With:
```tsx
        {s.step === 5 && s.generatedPlan && (
          <Step5Overview plan={s.generatedPlan} />
        )}
        {s.step === 6 && s.generatedPlan && (
          <Step6WorkoutList plan={s.generatedPlan} />
        )}
        {s.step === 7 && s.generatedPlan && (
          <Step7Confirm
            plan={s.generatedPlan}
            syncResult={s.syncResult}
            loading={s.loading}
          />
        )}
```

Find the bottom action buttons block. Replace:
```tsx
          {s.step === 5 && !s.syncResult && (
            <PrimaryBtn onClick={confirmAndSync} loading={s.loading}>
              {t.planGenerate.confirmAndSync} →
            </PrimaryBtn>
          )}
          {s.step === 5 && s.syncResult && (
            <PrimaryBtn onClick={() => router.replace('/plan')}>{t.planGenerate.viewPlan} →</PrimaryBtn>
          )}
```

With:
```tsx
          {s.step === 5 && (
            <PrimaryBtn onClick={() => patch({ step: 6 })}>
              {t.planGenerate.workoutsTitle} →
            </PrimaryBtn>
          )}
          {s.step === 6 && (
            <PrimaryBtn onClick={() => patch({ step: 7 })}>
              {t.planGenerate.workoutsConfirmTitle} →
            </PrimaryBtn>
          )}
          {s.step === 7 && !s.syncResult && (
            <PrimaryBtn onClick={confirmAndSync} loading={s.loading}>
              {t.planGenerate.confirmAndSync} →
            </PrimaryBtn>
          )}
          {s.step === 7 && s.syncResult && (
            <PrimaryBtn onClick={() => router.replace('/plan')}>{t.planGenerate.viewPlan} →</PrimaryBtn>
          )}
```

- [ ] **Step 6: Add `Step5Overview`, `Step6WorkoutList`, `Step7Confirm` components**

At the bottom of `web/app/plan/generate/page.tsx`, before the style constants, add:

```tsx
function Step5Overview({ plan }: { plan: GeneratedPlan }) {
  const { t } = useI18n()
  const pg = t.planGenerate
  const totalWorkouts = plan.structured_workouts.length
  const longRunKm = plan.structured_workouts
    .filter((w) => w.workout_type === 'long_run' && w.distance_m)
    .reduce((max, w) => Math.max(max, (w.distance_m ?? 0) / 1000), 0)

  // Group weeks into phases based on week_index quartiles
  const phases: Array<{ label: string; weeks: string }> = []
  if (plan.weeks >= 12) {
    const base = Math.round(plan.weeks * 0.375)
    const build = Math.round(plan.weeks * 0.375)
    const taper = plan.weeks - base - build
    phases.push(
      { label: 'Base', weeks: `${base} ${pg.overviewWeeks}` },
      { label: 'Build', weeks: `${build} ${pg.overviewWeeks}` },
      { label: 'Taper', weeks: `${taper} ${pg.overviewWeeks}` },
    )
  }

  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 16 }}>{pg.overviewTitle}</div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <StatBox label={pg.overviewTotalWorkouts} value={`${totalWorkouts}`} />
        {longRunKm > 0 && <StatBox label={pg.overviewLongRun} value={`${longRunKm.toFixed(0)} km`} />}
      </div>
      {phases.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
          {phases.map((p) => (
            <div key={p.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--rule-soft)' }}>
              <span className="hand text-faint" style={{ fontSize: 13 }}>{pg.overviewPhase}: {p.label}</span>
              <span className="hand" style={{ fontSize: 13 }}>{p.weeks}</span>
            </div>
          ))}
        </div>
      )}
      <div className="hand text-faint" style={{ fontSize: 13, lineHeight: 1.6 }}>{pg.workoutsConfirmBody}</div>
    </div>
  )
}

function Step6WorkoutList({ plan }: { plan: GeneratedPlan }) {
  const { t } = useI18n()
  const pg = t.planGenerate
  // Group workouts by week_index
  const byWeek = plan.structured_workouts.reduce<Record<number, WorkoutPreview[]>>((acc, w) => {
    ;(acc[w.week_index] ??= []).push(w)
    return acc
  }, {})
  const weekNumbers = Object.keys(byWeek).map(Number).sort((a, b) => a - b)

  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 16 }}>{pg.workoutsTitle}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {weekNumbers.map((w) => (
          <div key={w}>
            <div className="hand text-faint" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
              {pg.workoutsWeek}{w + 1}
            </div>
            {byWeek[w].sort((a, b) => a.day_index - b.day_index).map((workout) => (
              <div key={workout.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--rule-soft)' }}>
                <span className="hand" style={{ fontSize: 13 }}>{workout.title}</span>
                <span className="hand text-faint" style={{ fontSize: 12, flexShrink: 0 }}>
                  {workout.distance_m ? `${(workout.distance_m / 1000).toFixed(1)} km` : `${workout.duration_min} min`}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function Step7Confirm({ plan, syncResult, loading }: {
  plan: GeneratedPlan
  syncResult: { synced_count: number; failed_count: number } | null
  loading: boolean
}) {
  const { t } = useI18n()
  const pg = t.planGenerate
  void loading
  if (syncResult) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 40 }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{pg.ready}</div>
        <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.6 }}>
          {syncResult.synced_count} {pg.syncedToCoros}
          {syncResult.failed_count > 0 && `, ${syncResult.failed_count} ${pg.syncFailures}`}
        </div>
      </div>
    )
  }
  return (
    <div>
      <div className="hand" style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>{pg.workoutsConfirmTitle}</div>
      {plan.target_time_sec && (
        <div className="hand" style={{ fontSize: 14, color: 'var(--accent)', marginBottom: 16 }}>
          {pg.target} sub-{fmtTime(plan.target_time_sec)}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
        <PreviewRow label={pg.totalWeeks} value={`${plan.weeks} ${t.common.weeks}`} />
        {plan.start_date && <PreviewRow label={pg.startDate} value={plan.start_date} />}
        {plan.race_date && <PreviewRow label={pg.raceDate} value={plan.race_date} />}
      </div>
      <div className="hand text-faint" style={{ fontSize: 13, lineHeight: 1.6 }}>{pg.confirmNotice}</div>
    </div>
  )
}
```

Also delete the old `Step5Preview` function (it is now replaced by `Step7Confirm`).

- [ ] **Step 7: Run the failing test — must pass now**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/planPage.test.tsx -- -t "plan overview step" --reporter=verbose 2>&1 | tail -10
```

Expected: passes.

- [ ] **Step 8: Run full planPage tests**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/planPage.test.tsx
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/plan/generate/page.tsx web/lib/i18n/copy.ts web/__tests__/planPage.test.tsx
git commit -m "feat(plan): add plan overview and workout list preview steps before confirmation"
```

---

### Task 4: Add revoke button to Plan page

**Files:**
- Modify: `web/app/(tabs)/plan/page.tsx`

- [ ] **Step 1: Write the failing test**

In `web/__tests__/planPage.test.tsx`, add:

```ts
it('shows revoke plan button and calls revoke endpoint on confirmation', async () => {
  mockFetch
    .mockResolvedValueOnce({ ok: true, json: async () => ({ /* plan data */ id: 1, title: 'Test Plan', weeks: 16, start_date: '2026-06-01', race_date: '2026-09-20', status: 'active', is_confirmed: true, target_time_sec: 14400, athlete_id: 1, race_goal_id: null, sport: 'marathon', goal: 'finish', mode: 'structured', created_at: '2026-05-01T00:00:00Z', updated_at: '2026-05-01T00:00:00Z', structured_workouts: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan_id: 1, weeks: [], peak_planned_km: 50, peak_executed_km: 0 }) })  // volume curve
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 1, status: 'draft', is_confirmed: false, title: 'Test Plan', weeks: 16, start_date: null, race_date: null, target_time_sec: null, athlete_id: 1, race_goal_id: null, sport: 'marathon', goal: 'finish', mode: 'structured', created_at: '2026-05-01T00:00:00Z', updated_at: '2026-05-16T00:00:00Z', structured_workouts: [] }) })  // revoke response

  render(<PlanPage />)
  await waitFor(() => expect(screen.getByText(/Revoke plan/i)).toBeInTheDocument())

  // Click revoke — should show confirmation
  vi.stubGlobal('confirm', () => true)
  fireEvent.click(screen.getByText(/Revoke plan/i))

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/marathon\/plans\/\d+\/revoke/),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/planPage.test.tsx -- -t "revoke plan" --reporter=verbose 2>&1 | tail -10
```

Expected: fails — "Revoke plan" button not found.

- [ ] **Step 3: Add revoke state and handler to Plan page**

Open `web/app/(tabs)/plan/page.tsx`. Add these state variables near the top of the component:

```tsx
const [revoking, setRevoking] = useState(false)
const [revokeMessage, setRevokeMessage] = useState<string | null>(null)
```

Add this handler (uses `getToken` and `getAthleteId` which are already imported):

```tsx
async function revokePlan() {
  if (!plan) return
  if (!window.confirm(t.planGenerate.revokeConfirm)) return
  const token = getToken()
  setRevoking(true)
  setRevokeMessage(null)
  try {
    const res = await fetch(`/api/marathon/plans/${plan.id}/revoke`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Failed to revoke plan')
    setRevokeMessage(t.planGenerate.revokeSuccess)
    mutatePlan()
  } catch {
    setRevokeMessage('Error revoking plan.')
  } finally {
    setRevoking(false)
  }
}
```

(`mutatePlan` is the SWR mutate function from the plan SWR hook — check how it's named in the existing plan page and use the same name.)

Add the revoke button in the JSX, inside the active plan section, after the volume curve / weekly list, before the closing `</div>`:

```tsx
      {plan?.is_confirmed && (
        <div style={{ padding: '16px 0', borderTop: '1px solid var(--rule-soft)', marginTop: 16 }}>
          <button
            onClick={revokePlan}
            disabled={revoking}
            className="hand"
            style={{
              background: 'none',
              border: '1px solid var(--rule)',
              borderRadius: 'var(--radius)',
              color: 'var(--ink-faint)',
              fontSize: 13,
              padding: '8px 16px',
              cursor: revoking ? 'default' : 'pointer',
            }}
          >
            {revoking ? '...' : t.planGenerate.revokePlan}
          </button>
          {revokeMessage && (
            <div className="annot text-faint" style={{ fontSize: 12, marginTop: 8 }}>{revokeMessage}</div>
          )}
        </div>
      )}
```

- [ ] **Step 4: Run the failing test — must pass**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/planPage.test.tsx -- -t "revoke plan" --reporter=verbose 2>&1 | tail -10
```

Expected: passes.

- [ ] **Step 5: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/(tabs)/plan/page.tsx web/__tests__/planPage.test.tsx
git commit -m "feat(plan): add revoke plan action on plan page"
```

---

### Task 5: Add My Plan entry in Settings

**Files:**
- Modify: `web/app/settings/page.tsx`

- [ ] **Step 1: Write the failing test**

In `web/__tests__/settings.test.tsx`, add:

```ts
it('shows My Training Plan entry in settings with workout count', async () => {
  // Mock the active plan endpoint
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/api/marathon/plans/')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          id: 1, is_confirmed: true, structured_workouts: Array(48).fill({}),
          weeks: 16, title: 'My Plan',
        }),
      })
    }
    return Promise.resolve({ ok: false })
  })

  render(<SettingsPage />)
  await waitFor(() => {
    expect(screen.getByText(/My Training Plan/i)).toBeInTheDocument()
    expect(screen.getByText(/48/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/settings.test.tsx -- -t "My Training Plan" --reporter=verbose 2>&1 | tail -10
```

Expected: fails.

- [ ] **Step 3: Add plan row to Settings page**

Open `web/app/settings/page.tsx`. The settings page likely uses SWR or fetches data. Add a SWR fetch for the current plan.

First, add the fetch. Near the top of the `SettingsPage` component, add:

```tsx
const athleteId = getAthleteId()
const { data: activePlan } = useSWR<{ id: number; is_confirmed: boolean; structured_workouts: unknown[]; weeks: number; title: string | null }>(
  athleteId ? `/api/athletes/${athleteId}/dashboard` : null,
  fetcher,
  { revalidateOnFocus: false },
)
const workoutCount = activePlan && 'structured_workouts' in activePlan
  ? (activePlan as { structured_workouts: unknown[] }).structured_workouts?.length ?? 0
  : 0
```

(If `useSWR` and `fetcher` are not imported yet, add them. If the dashboard endpoint doesn't include `structured_workouts`, use `GET /marathon/plans/{planId}` instead — check `DashboardOut` for `current_plan_id` or similar. Adapt as needed.)

Then add a row in the training section:

```tsx
        <Link href="/plan" style={rowStyle}>
          <div>
            <div className="hand" style={{ fontSize: 15 }}>{t.settings.myPlan}</div>
            <div className="annot text-faint" style={{ fontSize: 13 }}>
              {workoutCount > 0 ? `${workoutCount} ${t.settings.myPlanSub}` : t.settings.myPlanSub}
            </div>
          </div>
          <ChevronRight size={16} style={{ color: 'var(--ink-faint)', flexShrink: 0 }} />
        </Link>
```

Adjust exact JSX structure to match the existing settings row pattern in the file.

- [ ] **Step 4: Run the failing test — must pass**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/settings.test.tsx -- -t "My Training Plan" --reporter=verbose 2>&1 | tail -10
```

Expected: passes.

- [ ] **Step 5: Run all settings and plan tests**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/settings.test.tsx __tests__/planPage.test.tsx __tests__/onboarding.test.tsx
```

Expected: all pass.

- [ ] **Step 6: Full frontend verification**

```bash
cd /Users/paul/Work/ST/web && pnpm test && pnpm type-check && pnpm build 2>&1 | tail -8
```

Expected: all pass.

- [ ] **Step 7: Full backend verification**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest discover -s tests -v 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 8: Final commit**

```bash
cd /Users/paul/Work/ST
git add web/app/settings/page.tsx web/__tests__/settings.test.tsx
git commit -m "feat(settings): add My Training Plan entry with workout count"
```

---

## Acceptance Criteria

- [ ] Plan generation wizard shows: Step 5 Plan Overview (phase breakdown, total workout count, max long run), Step 6 Workout List (all workouts grouped by week, scrollable), Step 7 Confirm + COROS sync.
- [ ] The existing "generating" spinner and "confirm" flow still work — just with 2 preview steps added before confirm.
- [ ] Settings page shows a "My Training Plan" row with the count of confirmed workouts, linking to `/plan`.
- [ ] Plan page shows a "Revoke plan" button for confirmed plans; clicking it calls the backend revoke endpoint after a browser confirmation prompt.
- [ ] Backend `POST /marathon/plans/{id}/revoke` sets `status=draft`, `is_confirmed=false`, and resets future workout statuses to `draft`.
- [ ] All tests pass; `pnpm build` exits 0.

## Out of Scope

- Individually toggling/unselecting workouts before import.
- Plan history / viewing past revoked plans.
- Regenerating a plan from mid-cycle.
