const TOKEN_KEY = 'st_token'
const ATHLETE_ID_KEY = 'pp_athlete_id'
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30 // 30 days, matches JWT TTL
const STALE_SESSION_REASON = 'user_not_found'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  const localToken = getLocalStorageToken()
  const cookieToken = getCookieToken()
  const token = cookieToken ?? localToken

  if (!token) return null

  if (cookieToken && localToken !== cookieToken) {
    localStorage.setItem(TOKEN_KEY, cookieToken)
  }

  // Migrate pre-cookie sessions: if localStorage has a token but no cookie, sync it.
  if (!cookieToken) {
    document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
  }

  return token
}

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
  // Also set as cookie so Next.js middleware can read it for SSR route protection
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ATHLETE_ID_KEY)
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`
}

export type ApiErrorDetail = {
  code?: string
  reason?: string
  message?: string
}

export function parseApiErrorDetail(payload: unknown): ApiErrorDetail | null {
  if (!payload || typeof payload !== 'object') return null
  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string') return { message: detail }
  if (!detail || typeof detail !== 'object') return null
  const value = detail as Record<string, unknown>
  return {
    code: typeof value.code === 'string' ? value.code : undefined,
    reason: typeof value.reason === 'string' ? value.reason : undefined,
    message: typeof value.message === 'string' ? value.message : undefined,
  }
}

export async function readApiErrorDetail(res: Response): Promise<ApiErrorDetail | null> {
  try {
    return parseApiErrorDetail(await res.clone().json())
  } catch {
    return null
  }
}

export function isStaleSessionError(detail: ApiErrorDetail | null): boolean {
  return detail?.code === 'auth_unauthorized' && detail.reason === STALE_SESSION_REASON
}

export function handleStaleSession(detail: ApiErrorDetail | null): boolean {
  if (!isStaleSessionError(detail)) return false
  clearToken()
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
  return true
}

export function isAuthenticated(): boolean {
  const t = getToken()
  return !!t && t.length > 0
}

export function saveAthleteId(athleteId: number): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(ATHLETE_ID_KEY, String(athleteId))
}

export function clearAthleteId(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(ATHLETE_ID_KEY)
}

export function getStoredAthleteId(): number | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem(ATHLETE_ID_KEY)
  const parsed = raw ? Number(raw) : NaN
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

export function getAthleteId(): number {
  if (typeof window === 'undefined') return 1
  return getStoredAthleteId() ?? 1
}

function getLocalStorageToken(): string | null {
  if (typeof window.localStorage?.getItem !== 'function') return null
  return localStorage.getItem(TOKEN_KEY)
}

function getCookieToken(): string | null {
  const part = document.cookie.split('; ').find(p => p.startsWith(`${TOKEN_KEY}=`))
  if (!part) return null
  const value = part.slice(TOKEN_KEY.length + 1)
  return value || null
}
