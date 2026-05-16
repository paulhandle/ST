# Fix Google Login Loading State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake interactive button shown during Google Identity Services initialization with a visible loading skeleton, eliminating the need for multiple clicks.

**Architecture:** During GIS script load (`googleReady === false`), show an animated pulse skeleton with the same height as the real button. When `googleScriptFailed === true`, show a non-interactive error button. Only show the real GIS button once `googleReady === true`. No state machine changes — only the rendering of the loading branch changes.

**Tech Stack:** Next.js 14 App Router, React, CSS keyframe animation in globals.css

---

## Root Cause

`web/app/login/page.tsx` lines 323–329: when `googleReady` is false, a fully interactive `<button>` appears. Clicking it fires `setError(t.googleLoading)` which shows "Google sign-in is still loading." The user sees a button, clicks it, gets an error, and doesn't know they must wait. Once GIS loads the real button replaces the fake one, requiring a second click.

---

## Files

- Modify: `web/app/login/page.tsx` (lines 313–336 and bottom style section)
- Modify: `web/app/globals.css` (add `@keyframes sk-pulse`)
- Modify: `web/__tests__/login.test.tsx` (add loading skeleton test case)

---

### Task 1: Add pulse keyframe to globals.css

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: Write the failing test** — verify the skeleton element exists in the DOM during GIS loading

Open `web/__tests__/login.test.tsx`. Add this test inside the `describe('LoginPage')` block, **before** the existing Google tests:

```ts
it('shows a loading skeleton when google client id is set but GIS has not initialised', () => {
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'test-google-client-id'
  // Do NOT stub window.google — GIS script hasn't loaded yet
  render(<LoginPage />)
  // Should NOT show a clickable "Continue with Google" button
  expect(screen.queryByRole('button', { name: /Continue with Google/i })).toBeNull()
  // Should show the loading skeleton container
  expect(screen.getByLabelText(/Continue with Google/i)).toBeInTheDocument()
  expect(screen.getByLabelText(/Continue with Google/i).getAttribute('aria-busy')).toBe('true')
})
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/login.test.tsx -- --reporter=verbose 2>&1 | grep -E "FAIL|PASS|✓|✗|shows a loading"
```

Expected: test fails because the current code renders a `<button>` (not an `aria-busy` skeleton).

- [ ] **Step 3: Add `@keyframes sk-pulse` to globals.css**

Open `web/app/globals.css`. Find the end of the file and append:

```css
@keyframes sk-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
```

- [ ] **Step 4: Replace the loading-state button in login/page.tsx**

In `web/app/login/page.tsx`, find and replace the block starting at line 313:

Old block (lines 313–336):
```tsx
{googleClientId ? (
  <>
    <div
      ref={googleButtonRef}
      aria-label={t.google}
      style={{
        ...googleButtonContainerStyle,
        display: googleReady ? 'block' : 'none',
      }}
    />
    {!googleReady && (
      <button
        onClick={() => setError(googleScriptFailed ? t.googleError : t.googleLoading)}
        style={secondaryButtonStyle}
      >
        {t.google}
      </button>
    )}
  </>
) : (
  <button onClick={unavailablePrimaryMethod} style={secondaryButtonStyle}>
    {t.google}
  </button>
)}
```

New block:
```tsx
{googleClientId ? (
  <>
    <div
      ref={googleButtonRef}
      aria-label={t.google}
      style={{
        ...googleButtonContainerStyle,
        display: googleReady ? 'block' : 'none',
      }}
    />
    {!googleReady && !googleScriptFailed && (
      <div
        aria-label={t.google}
        aria-busy="true"
        style={googleSkeletonStyle}
      />
    )}
    {!googleReady && googleScriptFailed && (
      <button
        onClick={() => setError(t.googleError)}
        style={secondaryButtonStyle}
      >
        {t.google}
      </button>
    )}
  </>
) : (
  <button onClick={unavailablePrimaryMethod} style={secondaryButtonStyle}>
    {t.google}
  </button>
)}
```

- [ ] **Step 5: Add `googleSkeletonStyle` constant at the bottom of the file**

At the end of `web/app/login/page.tsx`, after `googleButtonContainerStyle`, add:

```tsx
const googleSkeletonStyle: React.CSSProperties = {
  width: '100%',
  height: 44,
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  background: 'var(--surface-low)',
  animation: 'sk-pulse 1.5s ease-in-out infinite',
}
```

- [ ] **Step 6: Run the failing test again — it must pass now**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/login.test.tsx -- --reporter=verbose 2>&1 | grep -E "FAIL|PASS|✓|✗|loading skeleton"
```

Expected: the new test passes. All existing Google tests must still pass.

- [ ] **Step 7: Run full login test suite**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/login.test.tsx
```

Expected: all tests pass.

- [ ] **Step 8: Type-check**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
cd /Users/paul/Work/ST
git checkout -b fix/google-login-skeleton
git add web/app/login/page.tsx web/app/globals.css web/__tests__/login.test.tsx
git commit -m "fix(auth): show loading skeleton while Google Identity Services initialises"
```

---

## Acceptance Criteria

- [ ] When `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set but GIS script has not loaded, a non-interactive skeleton div renders (not a clickable button).
- [ ] The skeleton has `aria-busy="true"` and `aria-label` equal to the "Continue with Google" copy.
- [ ] When GIS load fails (`googleScriptFailed === true`), the error button renders as before.
- [ ] Once `googleReady === true`, the real GIS button is the only thing visible.
- [ ] All existing login tests pass.

## Out of Scope

- Retrying GIS script load on failure.
- Timeout detection for slow GIS loads.
- Changing the GIS button width calculation.
