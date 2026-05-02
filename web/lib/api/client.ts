const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url.startsWith('/api') ? url.slice(4) : url}`)
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${err}`)
  }
  return res.json()
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url.startsWith('/api') ? url.slice(4) : url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${err}`)
  }
  return res.json()
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${err}`)
  }
  return res.json()
}
