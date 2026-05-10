import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock localStorage
const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
})

import {
  clearAthleteId,
  clearToken,
  getAthleteId,
  getStoredAthleteId,
  getToken,
  handleStaleSession,
  isAuthenticated,
  saveAthleteId,
  saveToken,
} from '@/lib/auth'

function getCookieValue(name: string): string | null {
  const match = document.cookie.split('; ').find(p => p.startsWith(`${name}=`))
  return match ? match.split('=')[1] : null
}

beforeEach(() => {
  Object.keys(store).forEach(k => delete store[k])
  // Clear the st_token cookie
  document.cookie = 'st_token=; max-age=0; path=/'
})

describe('getToken', () => {
  it('returns null when nothing stored', () => {
    expect(getToken()).toBeNull()
  })

  it('returns stored token', () => {
    store['st_token'] = 'abc.def.ghi'
    expect(getToken()).toBe('abc.def.ghi')
  })

  it('falls back to the auth cookie when localStorage has no token', () => {
    document.cookie = 'st_token=cookie.token.here; path=/'
    expect(getToken()).toBe('cookie.token.here')
  })

  it('prefers the auth cookie when localStorage has a stale token', () => {
    store['st_token'] = 'stale.local.token'
    document.cookie = 'st_token=current.cookie.token; path=/'

    expect(getToken()).toBe('current.cookie.token')
    expect(store['st_token']).toBe('current.cookie.token')
  })
})

describe('saveToken', () => {
  it('writes token to localStorage', () => {
    saveToken('tok.en.here')
    expect(store['st_token']).toBe('tok.en.here')
  })

  it('sets st_token cookie so Next.js middleware can authenticate SSR requests', () => {
    saveToken('tok.en.here')
    expect(getCookieValue('st_token')).toBe('tok.en.here')
  })
})

describe('clearToken', () => {
  it('removes token from localStorage', () => {
    store['st_token'] = 'some-token'
    clearToken()
    expect(store['st_token']).toBeUndefined()
  })

  it('clears st_token cookie', () => {
    saveToken('some-token')
    clearToken()
    expect(getCookieValue('st_token')).toBeNull()
  })

  it('removes stored athlete id', () => {
    store.pp_athlete_id = '42'
    clearToken()
    expect(store.pp_athlete_id).toBeUndefined()
  })
})

describe('handleStaleSession', () => {
  it('clears token state and redirects to login for deleted-user tokens', () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { pathname: '/onboarding', assign })
    saveToken('deleted.user.token')
    saveAthleteId(42)

    const handled = handleStaleSession({
      code: 'auth_unauthorized',
      reason: 'user_not_found',
      message: 'Token user not found',
    })

    expect(handled).toBe(true)
    expect(store.st_token).toBeUndefined()
    expect(store.pp_athlete_id).toBeUndefined()
    expect(getCookieValue('st_token')).toBeNull()
    expect(assign).toHaveBeenCalledWith('/login')
  })

  it('ignores other auth failures', () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { pathname: '/onboarding', assign })
    saveToken('expired.token')

    const handled = handleStaleSession({
      code: 'auth_unauthorized',
      reason: 'expired',
      message: 'Token expired',
    })

    expect(handled).toBe(false)
    expect(store.st_token).toBe('expired.token')
    expect(assign).not.toHaveBeenCalled()
  })
})

describe('isAuthenticated', () => {
  it('returns false when no token', () => {
    expect(isAuthenticated()).toBe(false)
  })

  it('returns true when token is present', () => {
    store['st_token'] = 'valid.token.here'
    expect(isAuthenticated()).toBe(true)
  })

  it('returns false when token is empty string', () => {
    store['st_token'] = ''
    expect(isAuthenticated()).toBe(false)
  })
})

describe('athlete id storage', () => {
  it('defaults to athlete 1 before onboarding stores an id', () => {
    expect(getAthleteId()).toBe(1)
  })

  it('returns null when no athlete id has been explicitly stored', () => {
    expect(getStoredAthleteId()).toBeNull()
  })

  it('saves and reads the current athlete id', () => {
    saveAthleteId(42)
    expect(getStoredAthleteId()).toBe(42)
    expect(getAthleteId()).toBe(42)
  })

  it('clears only the stored athlete id', () => {
    saveToken('tok.en.here')
    saveAthleteId(42)
    clearAthleteId()
    expect(getToken()).toBe('tok.en.here')
    expect(getStoredAthleteId()).toBeNull()
  })
})
