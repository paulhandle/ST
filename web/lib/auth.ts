const TOKEN_KEY = 'st_token'
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30 // 30 days, matches JWT TTL

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  const token = localStorage.getItem(TOKEN_KEY)
  // Migrate pre-cookie sessions: if localStorage has a token but no cookie, sync it
  if (token && !document.cookie.split('; ').find(p => p.startsWith(`${TOKEN_KEY}=`))) {
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
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`
}

export function isAuthenticated(): boolean {
  const t = getToken()
  return !!t && t.length > 0
}
