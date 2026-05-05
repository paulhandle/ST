import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

vi.mock('next/link', () => ({
  default: ({ children, href }: any) => <a href={href}>{children}</a>,
}))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useParams: () => ({ id: '1', slug: 'running_beginner' }),
}))

import SkillList from '@/components/skills/SkillList'
import SwitchSkillDialog from '@/components/skills/SwitchSkillDialog'
import AffectedWorkoutRow from '@/components/adjustments/AffectedWorkoutRow'
import ActivityRow from '@/components/activities/ActivityRow'
import type { SkillManifestOut, AffectedWorkout, AthleteActivityOut } from '@/lib/api/types'

/* ── SkillList ───────────────────────────────────────────────────── */

const SKILLS: SkillManifestOut[] = [
  {
    slug: 'marathon_st_default', name: 'PerformanceProtocol Marathon Plan', version: '1.0',
    sport: 'marathon', author: 'PerformanceProtocol', tags: ['marathon'],
    description: '通用全马计划', is_active: true,
  },
  {
    slug: 'running_beginner', name: 'Beginner Runner Plan', version: '1.0',
    sport: 'marathon', author: 'PerformanceProtocol', tags: ['beginner'],
    description: '零基础入门', is_active: false,
  },
]

describe('SkillList', () => {
  it('renders all skills', () => {
    render(<SkillList skills={SKILLS} onSwitch={() => {}} />)
    expect(screen.getByText('PerformanceProtocol Marathon Plan')).toBeInTheDocument()
    expect(screen.getByText('Beginner Runner Plan')).toBeInTheDocument()
  })

  it('marks active skill', () => {
    render(<SkillList skills={SKILLS} onSwitch={() => {}} />)
    expect(screen.getByText('Current')).toBeInTheDocument()
  })

  it('shows switch button for inactive skill', () => {
    render(<SkillList skills={SKILLS} onSwitch={() => {}} />)
    expect(screen.getByText('Switch')).toBeInTheDocument()
  })

  it('calls onSwitch with slug when switch clicked', () => {
    const onSwitch = vi.fn()
    render(<SkillList skills={SKILLS} onSwitch={onSwitch} />)
    fireEvent.click(screen.getByText('Switch'))
    expect(onSwitch).toHaveBeenCalledWith('running_beginner')
  })
})

/* ── SwitchSkillDialog ───────────────────────────────────────────── */

describe('SwitchSkillDialog', () => {
  const preview = {
    frozen_completed: 3,
    frozen_missed: 1,
    regenerated_count: 10,
    weeks_affected: 5,
    applicable: true,
    applicability_reason: '',
  }

  it('renders preview counts', () => {
    render(
      <SwitchSkillDialog
        skillName="Beginner Runner Plan"
        preview={preview}
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText(/10/)).toBeInTheDocument()  // regenerated_count
    expect(screen.getByText(/5/)).toBeInTheDocument()   // weeks_affected
  })

  it('shows confirm button when applicable', () => {
    render(
      <SwitchSkillDialog
        skillName="Beginner Runner Plan"
        preview={preview}
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText(/Confirm switch/)).toBeInTheDocument()
  })

  it('shows reason and disables confirm when not applicable', () => {
    render(
      <SwitchSkillDialog
        skillName="Beginner Runner Plan"
        preview={{ ...preview, applicable: false, applicability_reason: '周跑量过高' }}
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText(/周跑量过高/)).toBeInTheDocument()
    expect(screen.getByText(/Confirm switch/).closest('button')).toBeDisabled()
  })

  it('calls onConfirm when button clicked', () => {
    const onConfirm = vi.fn()
    render(
      <SwitchSkillDialog
        skillName="Beginner Runner Plan"
        preview={preview}
        onConfirm={onConfirm}
        onCancel={() => {}}
      />
    )
    fireEvent.click(screen.getByText(/Confirm switch/))
    expect(onConfirm).toHaveBeenCalled()
  })
})

/* ── AffectedWorkoutRow ──────────────────────────────────────────── */

const WORKOUT: AffectedWorkout = {
  workout_id: 1,
  date: '2026-05-10',
  title: '轻松跑 40 分钟',
  change_summary: '距离减少 20%',
  before: { distance_m: 8000 },
  after: { distance_m: 6400 },
}

describe('AffectedWorkoutRow', () => {
  it('renders workout title', () => {
    render(<AffectedWorkoutRow workout={WORKOUT} />)
    expect(screen.getByText('轻松跑 40 分钟')).toBeInTheDocument()
  })

  it('renders change summary', () => {
    render(<AffectedWorkoutRow workout={WORKOUT} />)
    expect(screen.getByText(/距离减少 20%/)).toBeInTheDocument()
  })

  it('renders workout date', () => {
    render(<AffectedWorkoutRow workout={WORKOUT} />)
    // Date rendered in some locale format containing "10" (the day)
    expect(screen.getByText(/10/)).toBeInTheDocument()
  })
})

/* ── ActivityRow ─────────────────────────────────────────────────── */

const ACTIVITY: AthleteActivityOut = {
  id: 1,
  started_at: '2026-05-01T07:00:00Z',
  title: '轻松跑',
  distance_km: 8.2,
  duration_min: 48,
  avg_pace_sec_per_km: 351,
  avg_hr: 142,
  matched_workout_title: '轻松跑 40 分钟',
  matched_workout_planned_distance_m: 8000,
  match_status: 'completed',
  delta_summary: '配速 +5s/km',
}

describe('ActivityRow', () => {
  it('renders activity title and distance', () => {
    render(<ActivityRow activity={ACTIVITY} />)
    expect(screen.getByText('轻松跑')).toBeInTheDocument()
    expect(screen.getByText(/8\.2/)).toBeInTheDocument()
  })

  it('renders match status dot', () => {
    const { container } = render(<ActivityRow activity={ACTIVITY} />)
    expect(container.querySelector('.status-dot')).toBeInTheDocument()
  })

  it('renders delta summary', () => {
    render(<ActivityRow activity={ACTIVITY} />)
    expect(screen.getByText(/配速 \+5s\/km/)).toBeInTheDocument()
  })

  it('renders miss status correctly', () => {
    render(<ActivityRow activity={{ ...ACTIVITY, match_status: 'miss', delta_summary: null }} />)
    const dot = document.querySelector('.status-dot')
    expect(dot?.className).toContain('miss')
  })
})
