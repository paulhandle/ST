import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'

const navigationMocks = vi.hoisted(() => ({
  pathname: '/dashboard',
}))

vi.mock('next/navigation', () => ({
  usePathname: () => navigationMocks.pathname,
}))

const store: Record<string, string> = {}

vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
})

import ProtectedAuthGate, { isPublicPath } from '@/components/ProtectedAuthGate'
import { saveAthleteId, saveToken } from '@/lib/auth'

function getCookieValue(name: string): string | null {
  const match = document.cookie.split('; ').find(p => p.startsWith(`${name}=`))
  return match ? match.split('=')[1] : null
}

beforeEach(() => {
  Object.keys(store).forEach(k => delete store[k])
  document.cookie = 'st_token=; max-age=0; path=/'
  navigationMocks.pathname = '/dashboard'
  vi.restoreAllMocks()
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v },
    removeItem: (k: string) => { delete store[k] },
  })
  vi.stubGlobal('location', { pathname: navigationMocks.pathname, assign: vi.fn() })
})

describe('isPublicPath', () => {
  it('treats public routes and assets as public', () => {
    expect(isPublicPath('/')).toBe(true)
    expect(isPublicPath('/login')).toBe(true)
    expect(isPublicPath('/icons/pp-icon.svg')).toBe(true)
    expect(isPublicPath('/manifest.json')).toBe(true)
  })

  it('treats app routes as protected', () => {
    expect(isPublicPath('/dashboard')).toBe(false)
    expect(isPublicPath('/onboarding')).toBe(false)
    expect(isPublicPath('/settings/coros')).toBe(false)
  })
})

describe('ProtectedAuthGate', () => {
  it('renders public route children without validating auth', () => {
    navigationMocks.pathname = '/login'
    vi.stubGlobal('location', { pathname: '/login', assign: vi.fn() })
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<ProtectedAuthGate><div>Login content</div></ProtectedAuthGate>)

    expect(screen.getByText('Login content')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('validates protected routes before rendering children', async () => {
    saveToken('valid.token')
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 1 }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    render(<ProtectedAuthGate><div>Protected content</div></ProtectedAuthGate>)

    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Protected content')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me', {
      headers: { Authorization: 'Bearer valid.token' },
    })
  })

  it('clears deleted-user sessions before protected children render', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { pathname: '/onboarding', assign })
    navigationMocks.pathname = '/onboarding'
    saveToken('deleted.user.token')
    saveAthleteId(42)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: {
        code: 'auth_unauthorized',
        reason: 'user_not_found',
        message: 'Token user not found',
      },
    }), { status: 401 })))

    render(<ProtectedAuthGate><div>Onboarding content</div></ProtectedAuthGate>)

    expect(screen.queryByText('Onboarding content')).not.toBeInTheDocument()
    await waitFor(() => expect(assign).toHaveBeenCalledWith('/login'))
    expect(screen.queryByText('Onboarding content')).not.toBeInTheDocument()
    expect(store.st_token).toBeUndefined()
    expect(store.pp_athlete_id).toBeUndefined()
    expect(getCookieValue('st_token')).toBeNull()
  })
})
