import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

const replaceMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
}))

vi.mock('@/lib/auth', () => ({
  getAthleteId: () => 1,
  getToken: () => 'mock-token',
  saveAthleteId: vi.fn(),
}))

import OnboardingPage from '@/app/onboarding/page'

describe('OnboardingPage', () => {
  beforeEach(() => {
    replaceMock.mockReset()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ([{
        slug: 'marathon_st_default',
        name: 'PerformanceProtocol Marathon Plan',
        version: '1.0.0',
        sport: 'marathon',
        author: null,
        tags: ['default'],
        description: 'Default plan',
        is_active: true,
      }]),
    }))
  })

  it('renders step 1 heading', () => {
    render(<OnboardingPage />)
    expect(screen.getByText('Build your training cycle')).toBeInTheDocument()
    expect(screen.getByText(/connect COROS after setup/i)).toBeInTheDocument()
    expect(screen.queryByText('Connect COROS')).not.toBeInTheDocument()
  })

  it('shows step indicator', () => {
    render(<OnboardingPage />)
    expect(screen.getByText('1 / 5')).toBeInTheDocument()
  })

  it('can navigate to step 2', () => {
    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText('Set Goal')).toBeInTheDocument()
  })

  it('selects a skill, generates a plan, confirms it, and routes to Plan', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ([
          {
            slug: 'marathon_st_default',
            name: 'PerformanceProtocol Marathon Plan',
            version: '1.0.0',
            sport: 'marathon',
            author: null,
            tags: ['default'],
            description: 'Default plan',
            is_active: true,
          },
          {
            slug: 'running_beginner',
            name: 'Running Beginner',
            version: '1.0.0',
            sport: 'marathon',
            author: null,
            tags: ['beginner'],
            description: 'Start with a conservative base.',
            is_active: false,
          },
        ]),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 11 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 21 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ plan_id: 21, confirmed: true, confirmed_workout_count: 48 }) })
    vi.stubGlobal('fetch', mockFetch)

    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(screen.getByText('Running Beginner')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Running Beginner'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText(/Start training/))

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/plan')
    })
    const generateCall = mockFetch.mock.calls.find(([url]) => url === '/api/marathon/plans/generate')
    expect(generateCall).toBeTruthy()
    expect(JSON.parse(generateCall?.[1]?.body as string).skill_slug).toBe('running_beginner')
    expect(mockFetch).toHaveBeenCalledWith('/api/plans/21/confirm', expect.objectContaining({ method: 'POST' }))
  })
})
