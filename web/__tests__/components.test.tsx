import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}))

import PaceRangeBar from '@/components/today/PaceRangeBar'
import WorkoutSteps from '@/components/today/WorkoutSteps'
import SkillChip from '@/components/SkillChip'
import BrandLogo from '@/components/BrandLogo'
import type { WorkoutStepOut } from '@/lib/api/types'
import { formatPace } from '@/lib/api/types'

describe('PaceRangeBar', () => {
  it('renders target zone labels with formatted pace values', () => {
    // targetMin=330 (5:30), targetMax=360 (6:00)
    render(<PaceRangeBar targetMin={330} targetMax={360} actualPace={null} />)
    expect(screen.getByText(/5:30/)).toBeInTheDocument()
    expect(screen.getByText(/6:00/)).toBeInTheDocument()
  })

  it('shows in-range status when actualPace is within zone', () => {
    // Zone: 330-360, actualPace=345 → in zone
    render(<PaceRangeBar targetMin={330} targetMax={360} actualPace={345} />)
    expect(screen.getByText(/✓ in range/)).toBeInTheDocument()
  })

  it('shows out-of-range status when actualPace is outside zone', () => {
    // Zone: 330-360, actualPace=400 → out of zone
    render(<PaceRangeBar targetMin={330} targetMax={360} actualPace={400} />)
    expect(screen.getByText(/⚠ out of range/)).toBeInTheDocument()
  })
})

describe('WorkoutSteps', () => {
  it('renders the correct number of step rows', () => {
    const steps: WorkoutStepOut[] = [
      {
        step_type: 'warmup',
        duration_min: 10,
        distance_m: null,
        intensity_type: 'easy',
        target_min: null,
        target_max: null,
        rpe_min: null,
        rpe_max: null,
        description: null,
      },
      {
        step_type: 'work',
        duration_min: 20,
        distance_m: 5000,
        intensity_type: 'pace',
        target_min: 300,
        target_max: 330,
        rpe_min: null,
        rpe_max: null,
        description: null,
      },
      {
        step_type: 'cooldown',
        duration_min: 10,
        distance_m: null,
        intensity_type: 'easy',
        target_min: null,
        target_max: null,
        rpe_min: null,
        rpe_max: null,
        description: null,
      },
    ]
    render(<WorkoutSteps steps={steps} />)
    const minuteLabels = screen.getAllByText(/min/)
    expect(minuteLabels).toHaveLength(3)
  })
})

describe('SkillChip', () => {
  it('renders the skill name', () => {
    const skill = { slug: 'base-run', name: 'Base Running', version: '1.0.0' }
    render(<SkillChip skill={skill} />)
    expect(screen.getByText('Base Running')).toBeInTheDocument()
  })
})

describe('BrandLogo', () => {
  it('renders the full wordmark by default', () => {
    render(<BrandLogo />)
    expect(screen.getByText('Performance')).toBeInTheDocument()
    expect(screen.getByText('Protocol')).toBeInTheDocument()
  })

  it('renders compact P2 mark without the full wordmark', () => {
    render(<BrandLogo compact />)
    expect(screen.getByLabelText('PerformanceProtocol')).toBeInTheDocument()
    expect(screen.getByText('P')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.queryByText('Performance')).not.toBeInTheDocument()
    expect(screen.queryByText('Protocol')).not.toBeInTheDocument()
  })

  it('keeps href on compact linked mark', () => {
    render(<BrandLogo href="/dashboard" compact />)
    expect(screen.getByLabelText('PerformanceProtocol')).toHaveAttribute('href', '/dashboard')
  })
})
