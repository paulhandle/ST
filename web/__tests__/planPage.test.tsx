import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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
})
