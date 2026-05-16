import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'

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

vi.mock('next/link', () => ({
  default: ({ href, children, ...p }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    React.createElement('a', { href, ...p }, children),
}))

vi.mock('@/lib/hooks/useActivityDetail', () => ({
  useActivityDetail: () => ({
    isLoading: false,
    error: null,
    activity: {
      activity: {
        id: 145,
        provider_activity_id: '477263761401479169',
        started_at: '2026-05-05T00:45:44',
        discipline: 'run',
        feedback_text: 'Beijing run',
        distance_m: 10011.72,
        duration_sec: 4092,
        avg_pace_sec_per_km: 409,
        avg_hr: 154,
        matched_workout_title: null,
        match_status: 'unmatched',
        delta_summary: null,
      },
      source: {
        source_format: 'fit',
        file_size_bytes: 173080,
        payload_hash: 'b434f43c2422b788eb388cf291e1597f27c1fb0cdbc9649f4f38b6f933a93e73',
        file_url_host: null,
        downloaded_at: '2026-05-06T05:00:00',
        parsed_at: '2026-05-06T05:01:00',
        stored_sample_count: 4092,
        stored_lap_count: 11,
        warnings: [],
      },
      samples: [
        { sample_index: 0, timestamp: '2026-05-05T00:45:44', elapsed_sec: 0, distance_m: 0, latitude: 40.0, longitude: 116.0, altitude_m: 40, heart_rate: 100, cadence: 170, speed_mps: 2.4, pace_sec_per_km: 410, power_w: 240, temperature_c: null },
        { sample_index: 1, timestamp: '2026-05-05T00:45:45', elapsed_sec: 1, distance_m: 2.4, latitude: 40.001, longitude: 116.001, altitude_m: 41, heart_rate: 101, cadence: 172, speed_mps: 2.5, pace_sec_per_km: 400, power_w: 242, temperature_c: null },
      ],
      laps: [
        { lap_index: 0, start_time: null, end_time: null, duration_sec: 423, distance_m: 1000, avg_hr: 140, max_hr: 156, min_hr: 91, avg_cadence: 174, max_cadence: 180, avg_speed_mps: 2.36, max_speed_mps: 3, avg_power_w: 247, elevation_gain_m: 0, elevation_loss_m: 4, calories: 79, avg_temperature_c: 31 },
      ],
      route_bounds: { min_latitude: 40, max_latitude: 40.001, min_longitude: 116, max_longitude: 116.001 },
      interpretation: {
        effort_distribution: 'Average heart rate 154 bpm.',
        pace_consistency: 'Pace variability is stable.',
        heart_rate_drift: 'Heart rate changed from first half to second half.',
        data_quality: 'Parsed 4092 samples, 4091 GPS points, and 11 laps from FIT source.',
      },
      returned_sample_count: 2,
    },
  }),
}))

import ActivityDetailPage from '@/app/activities/[id]/page'

describe('ActivityDetailPage', () => {
  it('renders GPS route, metrics, laps, interpretation, and FIT source', async () => {
    render(<ActivityDetailPage params={{ id: '145' }} />)
    expect(screen.getByText('Beijing run')).toBeInTheDocument()
    expect(screen.getByText('Route')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('route-map')).toBeInTheDocument())
    expect(screen.getByText('Heart rate')).toBeInTheDocument()
    expect(screen.getByText('Laps')).toBeInTheDocument()
    expect(screen.getByText(/Parsed 4092 samples/)).toBeInTheDocument()
    expect(screen.getByText(/File: FIT/)).toBeInTheDocument()
  })

  it('renders a map container when GPS samples are present', async () => {
    render(<ActivityDetailPage params={{ id: '145' }} />)
    await waitFor(() => {
      expect(screen.getByTestId('route-map')).toBeInTheDocument()
    })
  })
})
