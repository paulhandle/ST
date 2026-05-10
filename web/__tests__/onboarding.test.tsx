import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

const { replaceMock, saveAthleteIdMock } = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  saveAthleteIdMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
}))

vi.mock('@/lib/auth', () => ({
  getAthleteId: () => 1,
  getToken: () => 'mock-token',
  handleStaleSession: vi.fn(),
  readApiErrorDetail: vi.fn(async (res: Response) => {
    const payload = await res.json()
    return payload.detail ?? null
  }),
  saveAthleteId: saveAthleteIdMock,
}))

import { handleStaleSession } from '@/lib/auth'
import OnboardingPage from '@/app/onboarding/page'

describe('OnboardingPage', () => {
  beforeEach(() => {
    replaceMock.mockReset()
    saveAthleteIdMock.mockReset()
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

  it('can enter the app without generating a plan', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 11 }) })
    vi.stubGlobal('fetch', mockFetch)

    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Enter without a plan'))

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/dashboard')
    })
    expect(saveAthleteIdMock).toHaveBeenCalledWith(11)
    expect(mockFetch).toHaveBeenCalledWith('/api/athletes', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({ Authorization: 'Bearer mock-token' }),
    }))
    expect(mockFetch.mock.calls.some(([url]) => url === '/api/marathon/goals')).toBe(false)
    expect(mockFetch.mock.calls.some(([url]) => url === '/api/marathon/plans/generate')).toBe(false)
    expect(mockFetch.mock.calls.some(([url]) => String(url).includes('/confirm'))).toBe(false)
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
    const athleteCall = mockFetch.mock.calls.find(([url]) => url === '/api/athletes')
    expect(athleteCall?.[1]?.headers).toMatchObject({ Authorization: 'Bearer mock-token' })
    expect(generateCall).toBeTruthy()
    expect(JSON.parse(generateCall?.[1]?.body as string).skill_slug).toBe('running_beginner')
    expect(mockFetch).toHaveBeenCalledWith('/api/plans/21/confirm', expect.objectContaining({ method: 'POST' }))
  })

  it('generates a plan with default onboarding values without LLM', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 11 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 21 }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ plan_id: 21, confirmed: true, confirmed_workout_count: 48 }) })
    vi.stubGlobal('fetch', mockFetch)

    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText(/Start training/))

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/plan')
    })
    const generateCall = mockFetch.mock.calls.find(([url]) => url === '/api/marathon/plans/generate')
    expect(JSON.parse(generateCall?.[1]?.body as string)).toMatchObject({
      race_goal_id: null,
      target_time_sec: null,
      race_date: null,
      plan_weeks: 16,
      skill_slug: 'marathon_st_default',
      use_llm: false,
      availability: {
        weekly_training_days: 3,
        preferred_long_run_weekday: 6,
        unavailable_weekdays: [0, 2, 4, 5],
      },
    })
  })

  it('shows backend auth details when athlete creation fails', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: {
            code: 'auth_unauthorized',
            reason: 'missing_credentials',
            message: 'Missing bearer token',
          },
        }),
      })
    vi.stubGlobal('fetch', mockFetch)

    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText(/Start training/))

    expect(await screen.findByText(/Missing bearer token \(missing_credentials\)/)).toBeInTheDocument()
    expect(replaceMock).not.toHaveBeenCalled()
  })

  it('clears stale sessions when athlete creation reports a deleted token user', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: {
            code: 'auth_unauthorized',
            reason: 'user_not_found',
            message: 'Token user not found',
          },
        }),
      })
    vi.stubGlobal('fetch', mockFetch)

    render(<OnboardingPage />)
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText(/Start training/))

    expect(await screen.findByText(/Token user not found \(user_not_found\)/)).toBeInTheDocument()
    expect(handleStaleSession).toHaveBeenCalledWith({
      code: 'auth_unauthorized',
      reason: 'user_not_found',
      message: 'Token user not found',
    })
  })
})
