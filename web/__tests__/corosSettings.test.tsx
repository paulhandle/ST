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
  it('loads status, connects COROS, and imports history', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          athlete_id: 1,
          connected: false,
          auth_status: 'disconnected',
          username: null,
          last_login_at: null,
          last_import_at: null,
          last_sync_at: null,
          last_error: null,
        }),
      })
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          athlete_id: 1,
          connected: true,
          auth_status: 'connected',
          username: 'runner@example.com',
          last_login_at: '2026-05-05T04:00:00Z',
          last_import_at: null,
          last_sync_at: null,
          last_error: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          athlete_id: 1,
          provider: 'coros',
          imported_count: 4,
          updated_count: 1,
          metric_count: 3,
          message: 'ok',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          athlete_id: 1,
          connected: true,
          auth_status: 'connected',
          username: 'runner@example.com',
          last_login_at: '2026-05-05T04:00:00Z',
          last_import_at: '2026-05-05T04:02:00Z',
          last_sync_at: null,
          last_error: null,
        }),
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

    fireEvent.click(screen.getByText('Import history now'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/coros/import?athlete_id=1', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ device_type: 'coros' }),
      }))
    })
    expect(await screen.findByText('History import completed.')).toBeInTheDocument()
    expect(screen.getByText(/Imported 4/)).toBeInTheDocument()
  })
})
