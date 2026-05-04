import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock localStorage
const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
})

import { getToken, saveToken, clearToken, isAuthenticated } from '@/lib/auth'

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
