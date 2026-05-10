import { getToken, handleStaleSession, readApiErrorDetail } from '@/lib/auth'

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

function _stripApiPrefix(url: string): string {
  return url.startsWith('/api') ? url.slice(4) : url
}

function _authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${_stripApiPrefix(url)}`, {
    headers: _authHeaders(),
  })
  if (!res.ok) {
    await handleApiAuthFailure(res)
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${err}`)
  }
  return res.json()
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${_stripApiPrefix(url)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._authHeaders() },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    await handleApiAuthFailure(res)
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${err}`)
  }
  return res.json()
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ..._authHeaders(), ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    await handleApiAuthFailure(res)
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${err}`)
  }
  return res.json()
}

async function handleApiAuthFailure(res: Response): Promise<void> {
  if (res.status !== 401) return
  handleStaleSession(await readApiErrorDetail(res))
}
