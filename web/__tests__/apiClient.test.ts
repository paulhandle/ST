import { beforeEach, describe, expect, it, vi } from 'vitest'

const store: Record<string, string> = {}

vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
})

import { fetcher } from '@/lib/api/client'
import { saveAthleteId, saveToken } from '@/lib/auth'

function getCookieValue(name: string): string | null {
  const match = document.cookie.split('; ').find(p => p.startsWith(`${name}=`))
  return match ? match.split('=')[1] : null
}

beforeEach(() => {
  Object.keys(store).forEach(k => delete store[k])
  document.cookie = 'st_token=; max-age=0; path=/'
  vi.restoreAllMocks()
})

describe('api client auth failures', () => {
  it('clears stale reset sessions when the backend reports user_not_found', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { pathname: '/dashboard', assign })
    saveToken('deleted.user.token')
    saveAthleteId(42)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: {
        code: 'auth_unauthorized',
        reason: 'user_not_found',
        message: 'Token user not found',
      },
    }), { status: 401 })))

    await expect(fetcher('/api/athletes/42/dashboard')).rejects.toThrow('401')

    expect(store.st_token).toBeUndefined()
    expect(store.pp_athlete_id).toBeUndefined()
    expect(getCookieValue('st_token')).toBeNull()
    expect(assign).toHaveBeenCalledWith('/login')
  })
})
