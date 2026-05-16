import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { I18nProvider } from '@/lib/i18n/I18nProvider'

const swrMock = vi.hoisted(() => vi.fn())

vi.mock('swr', () => ({
  default: swrMock,
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Cell: () => null,
}))

vi.mock('@/lib/hooks/useDashboard', () => ({
  useDashboard: () => ({
    dashboard: {
      today: { plan_id: 7 },
      this_week: { week_index: 1 },
      pending_adjustment: null,
    },
  }),
}))

vi.mock('@/components/plan/PendingAdjustmentSection', () => ({
  default: () => null,
}))

vi.mock('@/components/EmptyPlanState', () => ({
  default: () => <div>Empty plan</div>,
}))

vi.mock('@/lib/auth', () => ({
  getToken: () => 'mock-token',
  getAthleteId: () => 1,
}))

import PlanPage from '@/app/(tabs)/plan/page'

function renderPlanPage() {
  render(
    <I18nProvider>
      <PlanPage />
    </I18nProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  swrMock.mockImplementation((key: string | null) => {
    if (key === '/api/marathon/plans/7') {
      return {
        data: {
          id: 7,
          title: 'Marathon Plan',
          total_weeks: 2,
          start_date: '2026-05-04',
          race_date: '2026-06-14',
          is_confirmed: true,
          goal_description: null,
        },
      }
    }
    if (key === '/api/plans/7/volume-curve') {
      return {
        data: {
          plan_id: 7,
          weeks: [
            { week_index: 1, week_label: 'W1', executed_km: 5, planned_km: 20, phase: 'base', is_recovery: false },
            { week_index: 2, week_label: 'W2', executed_km: 0, planned_km: 24, phase: 'base', is_recovery: false },
          ],
          peak_planned_km: 24,
          peak_executed_km: 5,
        },
      }
    }
    return { data: undefined }
  })
})

describe('PlanPage', () => {
  it('renders volume curve weeks from the backend wrapper object', () => {
    renderPlanPage()
    expect(screen.getByText('Marathon Plan')).toBeInTheDocument()
    expect(screen.getByText('W1')).toBeInTheDocument()
    expect(screen.getByText('W2')).toBeInTheDocument()
  })

  it('shows revoke plan button and calls revoke endpoint on confirmation', async () => {
    const mockFetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 7, status: 'draft', is_confirmed: false, title: 'Marathon Plan',
        weeks: 16, start_date: null, race_date: null, target_time_sec: null,
        athlete_id: 1, race_goal_id: null, sport: 'marathon', goal: 'finish',
        mode: 'structured', created_at: '2026-05-01T00:00:00Z', updated_at: '2026-05-16T00:00:00Z',
        structured_workouts: [],
      }),
    })
    vi.stubGlobal('fetch', mockFetch)

    renderPlanPage()
    await waitFor(() => expect(screen.getByText(/Revoke plan/i)).toBeInTheDocument())

    vi.stubGlobal('confirm', () => true)
    fireEvent.click(screen.getByText(/Revoke plan/i))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/marathon\/plans\/\d+\/revoke/),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })
})
