import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

import OnboardingPage from '@/app/onboarding/page'

describe('OnboardingPage', () => {
  it('renders step 1 heading', () => {
    render(<OnboardingPage />)
    expect(screen.getByText('Connect COROS')).toBeInTheDocument()
  })

  it('shows step indicator', () => {
    render(<OnboardingPage />)
    expect(screen.getByText('1 / 4')).toBeInTheDocument()
  })

  it('can navigate to step 2', () => {
    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText('Set Goal')).toBeInTheDocument()
  })
})
