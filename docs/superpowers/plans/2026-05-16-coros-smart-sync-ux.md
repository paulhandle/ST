# COROS Smart Sync UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three improvements: (1) fix `last_sync_at` never being written, (2) add a smart "Sync since last import" option that computes the window from `last_import_at`, (3) show the "synced through date" prominently after a sync completes.

**Architecture:** Backend writes `account.last_sync_at` at sync completion (one-line fix). Frontend computes `suggestedDaysBack` from `status.last_import_at` and adds a sentinel option (`-1`) to the period selector that resolves to the computed value before the API call. The "synced through" date is already present in `syncJob.message`; we surface it as a dedicated status row when a job has completed.

**Tech Stack:** Python/FastAPI backend, Next.js 14 + TypeScript frontend, i18n via copy.ts

---

## Files

- Modify: `app/tools/coros/full_sync.py` (add one line at ~132)
- Modify: `web/app/settings/coros/page.tsx` (smart option + completed-through display)
- Modify: `web/lib/i18n/copy.ts` (two new keys per language)
- Modify: `tests/test_coros_full_sync.py` (assert last_sync_at is set)
- Modify: `web/__tests__/corosSettings.test.tsx` (assert smart option renders)

---

### Task 1: Fix `last_sync_at` in full_sync.py

**Files:**
- Modify: `app/tools/coros/full_sync.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_coros_full_sync.py`. Add this test inside the existing test class (after imports and before the first test method):

```python
def test_last_sync_at_is_written_on_success(self):
    """last_sync_at must be set alongside last_import_at when a sync job succeeds."""
    from app.tools.coros.full_sync import run_coros_full_sync_job
    from unittest.mock import MagicMock, patch
    import datetime

    session = self.Session()
    # Create a device account without last_sync_at
    account = session.query(DeviceAccount).filter_by(athlete_id=self.athlete_id).first()
    if account is None:
        self.skipTest("no device account fixture")
    account.last_sync_at = None
    session.commit()
    session.close()

    # Run the sync job with a mocked client that returns minimal results
    fake_history = {
        "activities": [],
        "raw_pages": {},
        "stats": {"synced_until": "2026-01-01"},
    }
    with patch("app.tools.coros.full_sync.RealCorosAutomationClient") as MockClient:
        MockClient.return_value.__enter__ = lambda s: MockClient.return_value
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.login = MagicMock()
        MockClient.return_value.fetch_full_history = MagicMock(return_value=fake_history)

        session2 = self.Session()
        job = ProviderSyncJob(
            athlete_id=self.athlete_id,
            status="queued",
            phase="login",
            sync_days_back=30,
        )
        session2.add(job)
        session2.commit()
        job_id = job.id
        session2.close()

        run_coros_full_sync_job(job_id, self.db_url)

    session3 = self.Session()
    refreshed = session3.query(DeviceAccount).filter_by(athlete_id=self.athlete_id).first()
    self.assertIsNotNone(refreshed.last_sync_at, "last_sync_at must be set after successful sync")
    session3.close()
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_coros_full_sync.CORSFullSyncTest.test_last_sync_at_is_written_on_success -v 2>&1 | tail -10
```

Expected: fails with `AssertionError: last_sync_at must be set after successful sync`.

- [ ] **Step 3: Fix full_sync.py**

Open `app/tools/coros/full_sync.py`. Find the block around line 132 that reads:

```python
            account.last_import_at = now
```

Add one line directly after it:

```python
            account.last_import_at = now
            account.last_sync_at = now
```

- [ ] **Step 4: Run the test again — must pass**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_coros_full_sync.CORSFullSyncTest.test_last_sync_at_is_written_on_success -v 2>&1 | tail -5
```

Expected: `OK`.

- [ ] **Step 5: Run full COROS sync test suite**

```bash
cd /Users/paul/Work/ST && uv run python -m unittest tests.test_coros_full_sync tests.test_real_coros_client -v 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/paul/Work/ST
git add app/tools/coros/full_sync.py tests/test_coros_full_sync.py
git commit -m "fix(coros): write last_sync_at on successful data import"
```

---

### Task 2: Add i18n keys for smart sync

**Files:**
- Modify: `web/lib/i18n/copy.ts`

- [ ] **Step 1: Add English keys to the `en` block**

In `web/lib/i18n/copy.ts`, find the `corosSettings` section under the `en` object. After the `importHistory` key, add:

```ts
      syncSinceLast: 'Sync since last import',
      syncedThrough: 'Synced through',
```

- [ ] **Step 2: Add Chinese keys to the `zh` block**

Find the same `corosSettings` section under the `zh` object. After `importHistory`, add:

```ts
      syncSinceLast: '上次导入后的增量同步',
      syncedThrough: '同步至',
```

- [ ] **Step 3: Type-check to confirm no missing keys**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check 2>&1 | grep -E "error|syncSinceLast|syncedThrough" | head -10
```

Expected: no errors about these keys.

---

### Task 3: Add smart sync option to frontend

**Files:**
- Modify: `web/app/settings/coros/page.tsx`

The approach:
- Add a helper `suggestedDaysBack(lastImportAt: string | null | undefined): number` that rounds up to the nearest sync period (30/90/365/3650).
- Add a select option with value `-1` labelled "Sync since last import (X days)".
- In `startFullSync()`, resolve `-1` to the computed days before the API call.
- Add a `completedThrough` string extracted from `syncJob?.message` when the job succeeded, and show it as a status row.

- [ ] **Step 1: Write the failing frontend test**

Open `web/__tests__/corosSettings.test.tsx`. Add a test asserting the "Since last import" option appears when `last_import_at` is set:

```ts
it('shows smart sync option when device has a previous import date', async () => {
  // Set last_import_at to 45 days ago
  const fortyFiveDaysAgo = new Date(Date.now() - 45 * 86400 * 1000).toISOString()
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/api/coros/status')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          connected: true,
          auth_status: 'connected',
          automation_mode: 'real',
          username: 'athlete@example.com',
          last_login_at: fortyFiveDaysAgo,
          last_import_at: fortyFiveDaysAgo,
          last_sync_at: null,
          last_error: null,
        }),
      })
    }
    return Promise.resolve({ ok: false })
  })

  render(<CorosSettingsPage />)
  await waitFor(() => {
    // Option for smart sync should be present (using the "Sync since last import" text)
    expect(screen.getByRole('option', { name: /Sync since last import/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/corosSettings.test.tsx -- --reporter=verbose 2>&1 | grep -E "FAIL|PASS|smart sync|Since last"
```

Expected: fails — option does not exist yet.

- [ ] **Step 3: Add `suggestedDaysBack` helper and smart sync state to coros/page.tsx**

In `web/app/settings/coros/page.tsx`, add the helper function just before the `CorosSettingsPage` component:

```tsx
function suggestedDaysBack(lastImportAt: string | null | undefined): number {
  if (!lastImportAt) return 365
  const daysSince = Math.ceil((Date.now() - new Date(lastImportAt).getTime()) / (1000 * 86400))
  if (daysSince <= 30) return 30
  if (daysSince <= 90) return 90
  if (daysSince <= 365) return 365
  return 3650
}

function completedThroughLabel(message: string | null | undefined): string | null {
  if (!message) return null
  const match = message.match(/through\s+(\d{4}-\d{2}-\d{2})/i)
  return match ? match[1] : null
}
```

- [ ] **Step 4: Update `startFullSync` to resolve the smart sentinel**

Find the `startFullSync` function in `CorosSettingsPage`. Replace:

```tsx
  async function startFullSync() {
    setStartingSync(true)
    setError(null)
    setMessage(null)
    try {
      const job = await postJson<ProviderSyncJobOut>('/api/coros/sync/start', {
        athlete_id: athleteId,
        days_back: syncDaysBack,
      })
```

With:

```tsx
  async function startFullSync() {
    setStartingSync(true)
    setError(null)
    setMessage(null)
    const resolvedDaysBack = syncDaysBack === -1
      ? suggestedDaysBack(status?.last_import_at)
      : syncDaysBack
    try {
      const job = await postJson<ProviderSyncJobOut>('/api/coros/sync/start', {
        athlete_id: athleteId,
        days_back: resolvedDaysBack,
      })
```

- [ ] **Step 5: Add the `-1` sentinel option to the period select**

Find the `<select>` for `syncDaysBack`. Add a new option as the **first** option, shown only when `status?.last_import_at` is truthy:

```tsx
        <Field label={c.syncPeriod}>
          <select
            value={syncDaysBack}
            onChange={event => setSyncDaysBack(Number(event.target.value))}
            className="hand"
            style={{ ...inputStyle, marginTop: 12 }}
            disabled={startingSync || isActiveJob(syncJob)}
          >
            {status?.last_import_at && (
              <option value={-1}>
                {c.syncSinceLast} ({suggestedDaysBack(status.last_import_at)} {language === 'zh' ? '天' : 'days'})
              </option>
            )}
            <option value={30}>{c.sync30}</option>
            <option value={90}>{c.sync90}</option>
            <option value={365}>{c.sync365}</option>
            <option value={3650}>{c.syncAll}</option>
          </select>
        </Field>
```

Also change the default state to `-1` when `last_import_at` is present. Update the effect:

```tsx
  useEffect(() => {
    if (status?.last_import_at) {
      setSyncDaysBack(-1)
    }
  }, [status?.last_import_at])
```

- [ ] **Step 6: Show "Synced through" row when a job has completed**

In the status `<section>` (where `InfoRow` components are), add after the `lastSync` row:

```tsx
        {(() => {
          const through = completedThroughLabel(syncJob?.message)
          return through
            ? <InfoRow label={c.syncedThrough} value={through} />
            : null
        })()}
```

- [ ] **Step 7: Run the failing frontend test again — must pass**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/corosSettings.test.tsx -- --reporter=verbose 2>&1 | grep -E "FAIL|PASS|smart sync|Since last"
```

Expected: passes.

- [ ] **Step 8: Run full COROS settings test suite**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/corosSettings.test.tsx __tests__/settings.test.tsx
```

Expected: all pass.

- [ ] **Step 9: Type-check and build**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check && pnpm build 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
cd /Users/paul/Work/ST
git add web/app/settings/coros/page.tsx web/lib/i18n/copy.ts web/__tests__/corosSettings.test.tsx
git commit -m "feat(coros): add smart incremental sync option and show synced-through date"
```

---

## Acceptance Criteria

- [ ] `DeviceAccount.last_sync_at` is non-null after a successful COROS data import.
- [ ] When `last_import_at` is set, the period selector shows "Sync since last import (X days)" as the first and default option.
- [ ] Starting sync with the smart option sends the computed `days_back` (30/90/365/3650) to the backend — never `-1`.
- [ ] After a sync completes, a "Synced through: YYYY-MM-DD" row appears in the status section.
- [ ] All existing COROS sync and settings tests pass.

## Out of Scope

- True checkpoint resume (continuing a partial sync that was interrupted mid-job).
- Per-activity sync status tracking.
- Automatic background sync scheduling.
