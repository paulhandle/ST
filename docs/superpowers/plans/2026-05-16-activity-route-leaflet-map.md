# Activity Route Leaflet Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static SVG polyline in the activity detail route section with an interactive Leaflet map using OpenStreetMap tiles — showing the GPS track with start/end markers, zoom controls, and tile-based geographic context.

**Architecture:** Install `leaflet` and `@types/leaflet`. Create a new `RouteMap` client component that lazy-loads leaflet inside `useEffect` (to avoid SSR). Import Leaflet's CSS in `web/app/layout.tsx`. In the activity detail page, replace the existing `RouteChart` component (and its function definition) with a `dynamic`-imported `RouteMap`. The rest of the activity detail page (metrics charts, laps, interpretation) is unchanged.

**Tech Stack:** leaflet 1.x, TypeScript, Next.js 14 App Router dynamic imports

---

## Files

- New: `web/components/activities/RouteMap.tsx`
- Modify: `web/app/layout.tsx` (add leaflet CSS import)
- Modify: `web/app/activities/[id]/page.tsx` (replace RouteChart with RouteMap)
- Modify: `web/__tests__/activityDetail.test.tsx` (update/add map rendering test)

---

### Task 1: Install leaflet

**Files:** none (package.json + lockfile)

- [ ] **Step 1: Install the packages**

```bash
cd /Users/paul/Work/ST/web && pnpm add leaflet && pnpm add -D @types/leaflet
```

- [ ] **Step 2: Verify they appear in package.json**

```bash
grep -E '"leaflet"' /Users/paul/Work/ST/web/package.json
```

Expected output: `"leaflet": "^1.x.x"` (exact version may vary).

---

### Task 2: Add Leaflet CSS to layout

**Files:**
- Modify: `web/app/layout.tsx`

- [ ] **Step 1: Add the CSS import**

Open `web/app/layout.tsx`. At the top of the file, after the existing CSS imports (e.g. `import './globals.css'`), add:

```tsx
import 'leaflet/dist/leaflet.css'
```

- [ ] **Step 2: Build to verify the CSS is included**

```bash
cd /Users/paul/Work/ST/web && pnpm build 2>&1 | grep -E "error|Error|leaflet" | head -10
```

Expected: no errors.

---

### Task 3: Create RouteMap component

**Files:**
- New: `web/components/activities/RouteMap.tsx`

- [ ] **Step 1: Write the failing test**

Open `web/__tests__/activityDetail.test.tsx`. Find how the activity detail page is tested (look for GPS sample mocks). Add this test:

```ts
it('renders a map container when GPS samples are present', async () => {
  // Mock dynamic import so RouteMap renders synchronously in tests
  // The component renders a div with data-testid="route-map"
  const sampleWithGps = {
    sample_index: 0,
    timestamp: '2026-01-01T08:00:00Z',
    elapsed_sec: 0,
    distance_m: 0,
    latitude: 31.2304,
    longitude: 121.4737,
    altitude_m: 10,
    heart_rate: 140,
    cadence: 170,
    speed_mps: 3.0,
    pace_sec_per_km: 333,
    power_w: null,
    temperature_c: null,
  }
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      activity: {
        id: 1, athlete_id: 1, started_at: '2026-01-01T08:00:00Z',
        discipline: 'run', title: 'Morning Run',
        distance_m: 10000, duration_sec: 3600,
        avg_pace_sec_per_km: 360, avg_hr: 140,
        feedback_text: null, distance_km: null, duration_min: null,
      },
      samples: [sampleWithGps, { ...sampleWithGps, sample_index: 1, elapsed_sec: 300, distance_m: 1000, latitude: 31.2350, longitude: 121.4780 }],
      laps: [],
      route_bounds: { min_lat: 31.2304, max_lat: 31.2350, min_lon: 121.4737, max_lon: 121.4780 },
      returned_sample_count: 2,
      total_sample_count: 2,
      source: null,
      interpretation: {},
    }),
  })

  render(<ActivityDetailPage params={{ id: '1' }} />)
  await waitFor(() => {
    expect(screen.getByTestId('route-map')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/activityDetail.test.tsx -- --reporter=verbose 2>&1 | grep -E "FAIL|PASS|route-map|map container"
```

Expected: fails — `route-map` test id does not exist.

- [ ] **Step 3: Create `RouteMap.tsx`**

Create `web/components/activities/RouteMap.tsx` with this content:

```tsx
'use client'

import { useEffect, useRef } from 'react'
import type { ActivityDetailSampleOut } from '@/lib/api/types'

interface RouteMapProps {
  samples: ActivityDetailSampleOut[]
  emptyText: string
}

export default function RouteMap({ samples, emptyText }: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<import('leaflet').Map | null>(null)

  const gpsPoints = samples
    .filter((s) => s.latitude != null && s.longitude != null)
    .map((s) => [s.latitude as number, s.longitude as number] as [number, number])

  useEffect(() => {
    if (!containerRef.current || gpsPoints.length < 2) return

    let cancelled = false

    import('leaflet').then((L) => {
      if (cancelled || !containerRef.current) return

      // Tear down any previous map instance (hot-reload or re-mount)
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }

      const map = L.map(containerRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
      })

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map)

      const polyline = L.polyline(gpsPoints, {
        color: 'var(--accent, #f5a623)',
        weight: 4,
        opacity: 0.9,
      }).addTo(map)

      map.fitBounds(polyline.getBounds(), { padding: [20, 20] })

      // Start marker — dark filled circle
      L.circleMarker(gpsPoints[0], {
        radius: 7,
        fillColor: '#111111',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 1,
      }).addTo(map)

      // End marker — accent filled circle
      L.circleMarker(gpsPoints[gpsPoints.length - 1], {
        radius: 7,
        fillColor: 'var(--accent, #f5a623)',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 1,
      }).addTo(map)

      mapRef.current = map
    })

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [gpsPoints.length]) // eslint-disable-line react-hooks/exhaustive-deps

  if (gpsPoints.length < 2) {
    return (
      <div
        className="annot text-faint"
        style={{
          padding: 24,
          border: '1px solid var(--rule-soft)',
          background: 'var(--paper-soft)',
          textAlign: 'center',
        }}
      >
        {emptyText}
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      data-testid="route-map"
      style={{
        width: '100%',
        height: 300,
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        border: '1px solid var(--rule-soft)',
      }}
    />
  )
}
```

- [ ] **Step 4: Add a Leaflet mock inside the test file**

Vitest/jsdom cannot run Leaflet DOM operations. At the top of `web/__tests__/activityDetail.test.tsx`, add a `vi.mock` call (must be before imports):

```ts
vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => ({
      remove: vi.fn(),
      fitBounds: vi.fn(),
    })),
    polyline: vi.fn(() => ({
      addTo: vi.fn(),
      getBounds: vi.fn(() => ({})),
    })),
    circleMarker: vi.fn(() => ({ addTo: vi.fn() })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  },
}))
```

Note: the `RouteMap` component lazy-loads leaflet inside `useEffect`. In Vitest, effects run synchronously after `render`. The `data-testid="route-map"` div is rendered before the effect fires, so `waitFor` will find it regardless of whether the leaflet mock resolves.

- [ ] **Step 5: Update the activity detail page to use RouteMap**

Open `web/app/activities/[id]/page.tsx`.

Add the dynamic import at the top (after existing imports):

```tsx
import dynamic from 'next/dynamic'
const RouteMap = dynamic(() => import('@/components/activities/RouteMap'), { ssr: false })
```

Replace the `<RouteChart ... />` call (line ~50):

Old:
```tsx
        <RouteChart samples={detail.samples} emptyText={t.activityDetail.noRoute} />
```

New:
```tsx
        <RouteMap samples={detail.samples} emptyText={t.activityDetail.noRoute} />
```

Also delete the entire `RouteChart` function definition (lines 124–145) since it is no longer used.

- [ ] **Step 7: Run the failing test — must pass now**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/activityDetail.test.tsx -- --reporter=verbose 2>&1 | grep -E "FAIL|PASS|route-map|map container"
```

Expected: passes.

- [ ] **Step 8: Run broader frontend tests**

```bash
cd /Users/paul/Work/ST/web && pnpm test __tests__/activityDetail.test.tsx __tests__/blockE.test.tsx
```

Expected: all pass.

- [ ] **Step 9: Type-check and build**

```bash
cd /Users/paul/Work/ST/web && pnpm type-check && pnpm build 2>&1 | tail -8
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
cd /Users/paul/Work/ST
git add web/components/activities/RouteMap.tsx web/__mocks__/leaflet.ts \
        web/app/activities/[id]/page.tsx web/app/layout.tsx \
        web/__tests__/activityDetail.test.tsx
git commit -m "feat(activities): replace SVG route chart with Leaflet OpenStreetMap map"
```

---

## Acceptance Criteria

- [ ] Activity detail page renders an interactive Leaflet map (not an SVG polyline) when GPS samples are present.
- [ ] Map shows OpenStreetMap tiles with start (dark) and end (accent) circle markers.
- [ ] Zoom controls are visible; scroll-wheel zoom is disabled to avoid accidental zoom while scrolling the page.
- [ ] When GPS samples are absent or fewer than 2, the empty-state message is shown as before.
- [ ] All existing activity detail and activities tests pass.
- [ ] `pnpm build` exits 0 with no type errors.

## Out of Scope

- Synchronized scrubbing between map and metric charts.
- Color-coding the route by pace/HR zones.
- Elevation profile overlay on the map.
- Offline tile caching.
