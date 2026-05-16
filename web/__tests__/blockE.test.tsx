import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ replace: vi.fn(), back: vi.fn() }),
}))
vi.mock('next/link', () => ({
  default: ({ href, children, ...p }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    React.createElement('a', { href, ...p }, children),
}))
vi.mock('@/components/CoachButton', () => ({ default: () => null }))

import TabsLayout from '@/app/(tabs)/layout'

describe('Tab bar', () => {
  it('shows Activities tab and no Today tab', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('Activities')).toBeInTheDocument()
    expect(screen.queryByText('Today')).not.toBeInTheDocument()
  })

  it('uses compact P2 mark in the app topbar', () => {
    render(<TabsLayout><div /></TabsLayout>)
    const topbarMark = screen.getByLabelText('PerformanceProtocol')
    expect(topbarMark).toHaveAttribute('href', '/dashboard')
    expect(screen.queryByText('Performance')).not.toBeInTheDocument()
    expect(screen.queryByText('Protocol')).not.toBeInTheDocument()
  })

  it('shows Overview, Plan, and Me tabs without the Week tab', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Plan')).toBeInTheDocument()
    expect(screen.getByText('Me')).toBeInTheDocument()
    expect(screen.queryByText('This Week')).not.toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
  })
})

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
    expect(screen.getByText(/Rest day/)).toBeInTheDocument()
  })
})

vi.mock('@/lib/auth', () => ({
  getToken: () => 'mock-token',
  getAthleteId: () => 1,
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
    expect(screen.getByText(/Analyzing/)).toBeInTheDocument()
  })

  it('lets the user continue when assessment fails', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({ ok: false, text: async () => 'not connected' })
      .mockResolvedValueOnce({ ok: false, text: async () => 'no history' })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ([{
          slug: 'marathon_st_default',
          name: 'PerformanceProtocol Marathon Plan',
          version: '1.0.0',
          sport: 'marathon',
          author: null,
          tags: [],
          description: 'Default plan',
          is_active: true,
        }]),
      })
    vi.stubGlobal('fetch', mockFetch)

    const { default: PlanGeneratePage } = await import('@/app/plan/generate/page')
    render(<PlanGeneratePage />)

    await waitFor(() => {
      expect(screen.getAllByText(/Assessment failed/).length).toBeGreaterThan(0)
    })
    expect(screen.queryByText(/Analyzing/)).not.toBeInTheDocument()
    expect(screen.getByText(/Based on 0 history activities/)).toBeInTheDocument()

    fireEvent.click(screen.getByText(/Set goal/))
    expect(screen.getByText('Training weeks')).toBeInTheDocument()
  })

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

    const mockFetch = vi.fn()
      .mockResolvedValueOnce({ ok: false })
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

    vi.stubGlobal('fetch', mockFetch)

    const { default: PlanGeneratePage } = await import('@/app/plan/generate/page')
    render(<PlanGeneratePage />)

    await waitFor(() => expect(screen.getByText(/Set goal/i)).toBeInTheDocument())
    fireEvent.click(screen.getByText(/Set goal/i))

    await waitFor(() => expect(screen.getByText(/Generate plan/i)).toBeInTheDocument())
    fireEvent.click(screen.getByText(/Generate plan/i))

    await waitFor(() => {
      expect(screen.getByText(/Plan Overview/i)).toBeInTheDocument()
      expect(screen.getByText(/48/)).toBeInTheDocument()
    })
  })
})

vi.mock('@/lib/hooks/useCalendar', () => ({
  useCalendar: () => ({
    days: [
      { date: '2026-05-04', status: 'completed', title: '跑步 8.0km', sport: 'run',
        workout_type: 'easy_run', activity_id: 1, workout_id: 10,
        distance_km: 8.0, duration_min: 48 },
      { date: '2026-05-06', status: 'partial', title: 'Tempo partial', sport: 'run',
        workout_type: 'tempo', activity_id: 2, workout_id: 11,
        distance_km: 6.2, duration_min: 39 },
      { date: '2026-05-07', status: 'unmatched', title: 'Free ride', sport: 'cycle',
        workout_type: null, activity_id: 3, workout_id: null,
        distance_km: 24.4, duration_min: 58 },
      { date: '2026-05-08', status: 'miss', title: 'Missed intervals', sport: 'run',
        workout_type: 'intervals', activity_id: null, workout_id: 12,
        distance_km: 9.0, duration_min: 52 },
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
    render(<MonthStrip days={[]} selectedDate={null} onSelectDate={vi.fn()} />)
    expect(screen.getAllByText(today).length).toBeGreaterThan(0)
  })

  it('calls onSelectDate when a day is clicked', () => {
    const onSelect = vi.fn()
    render(<MonthStrip days={[]} selectedDate={null} onSelectDate={onSelect} />)
    screen.getAllByRole('button')[0].click()
    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})

import ActivitiesPage from '@/app/(tabs)/activities/page'

describe('ActivitiesPage', () => {
  it('uses timeline as the default review view', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('Timeline')).toBeInTheDocument()
    expect(screen.getByText('Calendar')).toBeInTheDocument()
    expect(screen.getByText('Jump to month')).toBeInTheDocument()
  })

  it('renders filter chips', () => {
    render(<ActivitiesPage />)
    expect(screen.getByRole('button', { name: 'Sport filter: All' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sport filter: Run' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sport filter: Ride' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sport filter: Strength' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Status filter: Done' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Status filter: Partial' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Status filter: Free' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Status filter: Missed' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Status filter: Planned' })).toBeInTheDocument()
  })

  it('renders list items from calendar data', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('跑步 8.0km')).toBeInTheDocument()
    expect(screen.getByText('Tempo partial')).toBeInTheDocument()
    expect(screen.getByText('Free ride')).toBeInTheDocument()
    expect(screen.getByText('Missed intervals')).toBeInTheDocument()
    expect(screen.getByText('Long Run')).toBeInTheDocument()
  })

  it('links real activities to detail and planned rows to workouts', () => {
    render(<ActivitiesPage />)
    expect(screen.getByText('跑步 8.0km').closest('a')).toHaveAttribute('href', '/activities/1')
    expect(screen.getByText('Free ride').closest('a')).toHaveAttribute('href', '/activities/3')
    expect(screen.getByText('Missed intervals').closest('a')).toHaveAttribute('href', '/workouts/2026-05-08')
    expect(screen.getByText('Long Run').closest('a')).toHaveAttribute('href', '/workouts/2026-05-10')
  })

  it('shows a legend and status-specific row classes', () => {
    const { container } = render(<ActivitiesPage />)
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(container.querySelector('[data-status="completed"]')).toHaveClass('activity-row--completed')
    expect(container.querySelector('[data-status="partial"]')).toHaveClass('activity-row--partial')
    expect(container.querySelector('[data-status="unmatched"]')).toHaveClass('activity-row--unmatched')
    expect(container.querySelector('[data-status="miss"]')).toHaveClass('activity-row--miss')
    expect(container.querySelector('[data-status="planned"]')).toHaveClass('activity-row--planned')
  })

  it('shows MonthStrip only in Calendar view', () => {
    const { container } = render(<ActivitiesPage />)
    expect(container.querySelector('[data-date]')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Calendar'))
    expect(container.querySelector('[data-date]')).toBeInTheDocument()
  })

  it('filters by status', () => {
    render(<ActivitiesPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Status filter: Done' }))
    expect(screen.getByText('跑步 8.0km')).toBeInTheDocument()
    expect(screen.queryByText('Tempo partial')).not.toBeInTheDocument()
    expect(screen.queryByText('Long Run')).not.toBeInTheDocument()
  })
})
