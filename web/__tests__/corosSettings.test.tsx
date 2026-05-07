import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ back: vi.fn(), replace: vi.fn(), push: vi.fn() }),
}))

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

vi.mock('@/lib/auth', () => ({
  getAthleteId: () => 1,
  getToken: () => 'mock-token',
}))

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value },
  removeItem: (key: string) => { delete store[key] },
})

import EmptyPlanState from '@/components/EmptyPlanState'
import CorosSettingsPage from '@/app/settings/coros/page'

beforeEach(() => {
  vi.clearAllMocks()
  Object.keys(store).forEach(key => delete store[key])
  document.cookie = 'pp_language=; max-age=0; path=/'
})

describe('Plan empty state i18n', () => {
  it('switches empty-plan copy to Chinese', async () => {
    window.localStorage.setItem('pp_language', 'zh')
    render(<EmptyPlanState />)

    await waitFor(() => {
      expect(screen.getByText('建立你的下一个训练周期')).toBeInTheDocument()
    })
    expect(screen.getByText('生成计划', { exact: false })).toBeInTheDocument()
  })
})

describe('CorosSettingsPage', () => {
  it('loads status, connects COROS, and starts full sync with progress', async () => {
    let connected = false
    mockFetch.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url === '/api/coros/status?athlete_id=1') {
        return {
          ok: true,
          json: async () => ({
            athlete_id: 1,
            connected,
            auth_status: connected ? 'connected' : 'disconnected',
            automation_mode: 'real',
            username: connected ? 'runner@example.com' : null,
            last_login_at: connected ? '2026-05-05T04:00:00Z' : null,
            last_import_at: connected ? '2026-05-05T04:02:00Z' : null,
            last_sync_at: null,
            last_error: null,
          }),
        }
      }
      if (url === '/api/coros/connect') {
        connected = true
        return {
          ok: true,
          json: async () => ({
            id: 7,
            athlete_id: 1,
            device_type: 'coros',
            external_user_id: 'runner@example.com',
            username: 'runner@example.com',
            auth_status: 'connected',
            last_login_at: '2026-05-05T04:00:00Z',
            last_import_at: null,
            last_sync_at: null,
            last_error: null,
            created_at: '2026-05-05T04:00:00Z',
          }),
        }
      }
      if (url === '/api/coros/sync/start') {
        return {
          ok: true,
          json: async () => ({
            provider: 'coros',
            id: 11,
            athlete_id: 1,
            status: 'running',
            phase: 'activity_details',
            message: 'Reading COROS activity details',
            total_count: 10,
            processed_count: 4,
            imported_count: 4,
            updated_count: 1,
            metric_count: 3,
            failed_count: 0,
            raw_record_count: 8,
            started_at: '2026-05-05T04:01:00Z',
            completed_at: null,
            error_message: null,
            created_at: '2026-05-05T04:01:00Z',
            updated_at: '2026-05-05T04:02:00Z',
          }),
        }
      }
      if (url === '/api/coros/sync/jobs/11') {
        return {
          ok: true,
          json: async () => ({
            provider: 'coros',
            id: 11,
            athlete_id: 1,
            status: 'succeeded',
            phase: 'complete',
            message: 'COROS full sync completed',
            total_count: 10,
            processed_count: 10,
            imported_count: 4,
            updated_count: 1,
            metric_count: 3,
            failed_count: 0,
            raw_record_count: 8,
            started_at: '2026-05-05T04:01:00Z',
            completed_at: '2026-05-05T04:03:00Z',
            error_message: null,
            created_at: '2026-05-05T04:01:00Z',
            updated_at: '2026-05-05T04:03:00Z',
          }),
        }
      }
      if (url === '/api/coros/sync/jobs/11/events?limit=8') {
        return {
          ok: true,
          json: async () => ([
            {
              id: 1,
              job_id: 11,
              level: 'info',
              phase: 'activity_list',
              message: 'Read COROS activity page 1 of 1',
              processed_count: 1,
              total_count: 1,
              created_at: '2026-05-05T04:02:00Z',
            },
          ]),
        }
      }
      throw new Error(`Unexpected request: ${url} ${init?.method ?? 'GET'}`)
    })

    render(<CorosSettingsPage />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/coros/status?athlete_id=1', expect.any(Object))
    })

    fireEvent.change(screen.getByLabelText('COROS account'), {
      target: { value: 'runner@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secret' },
    })
    fireEvent.click(screen.getByText('Connect COROS'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/coros/connect', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          athlete_id: 1,
          username: 'runner@example.com',
          password: 'secret',
        }),
      }))
    })

    await waitFor(() => {
      expect(screen.getByText('COROS connected.')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Start full sync'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/coros/sync/start', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ athlete_id: 1 }),
      }))
    })
    expect(await screen.findByText('Full sync started.')).toBeInTheDocument()
    expect(await screen.findByText('Sync complete')).toBeInTheDocument()
    expect(screen.getByText('raw records')).toBeInTheDocument()
  })
})
