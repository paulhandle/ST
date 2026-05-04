import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/link', () => ({
  default: ({ children, href }: any) => <a href={href}>{children}</a>,
}))

import PendingAdjustmentSection from '@/components/plan/PendingAdjustmentSection'
import EmptyPlanState from '@/components/EmptyPlanState'

describe('PendingAdjustmentSection', () => {
  it('renders adjustment headline', () => {
    render(
      <PendingAdjustmentSection
        adjustment={{ id: 42, reason_headline: '本周疲劳度偏高，建议减量' }}
      />
    )
    expect(screen.getByText(/本周疲劳度偏高/)).toBeInTheDocument()
  })

  it('links to /adjustments/{id}', () => {
    render(
      <PendingAdjustmentSection
        adjustment={{ id: 42, reason_headline: '建议调整' }}
      />
    )
    expect(screen.getByRole('link')).toHaveAttribute('href', '/adjustments/42')
  })

  it('shows a count badge', () => {
    render(
      <PendingAdjustmentSection
        adjustment={{ id: 1, reason_headline: '调整建议' }}
      />
    )
    expect(screen.getByText(/1|待处理/)).toBeInTheDocument()
  })
})

describe('EmptyPlanState', () => {
  it('renders a CTA to generate plan', () => {
    render(<EmptyPlanState />)
    expect(screen.getByRole('link', { name: /Generate plan/ })).toBeInTheDocument()
  })

  it('links to plan generate wizard', () => {
    render(<EmptyPlanState />)
    expect(screen.getByRole('link', { name: /Generate plan/ })).toHaveAttribute('href', '/plan/generate')
  })

  it('shows encouraging copy', () => {
    render(<EmptyPlanState />)
    expect(screen.getByText(/training cycle/i)).toBeInTheDocument()
  })
})
