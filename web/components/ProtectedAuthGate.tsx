'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { getToken, handleStaleSession, readApiErrorDetail, clearToken } from '@/lib/auth'

const PUBLIC_PATHS = ['/', '/login', '/api', '/icons']
const PUBLIC_FILE_PATTERN = /\.(ico|png|jpg|jpeg|svg|webp|json|txt|xml)$/

type AuthGateState = 'checking' | 'allowed'

export default function ProtectedAuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || '/'
  const isPublic = isPublicPath(pathname)
  const [state, setState] = useState<AuthGateState>(isPublic ? 'allowed' : 'checking')

  useEffect(() => {
    let active = true

    if (isPublic) {
      setState('allowed')
      return () => {
        active = false
      }
    }

    setState('checking')
    const token = getToken()
    if (!token) {
      redirectToLogin()
      return () => {
        active = false
      }
    }

    async function validateSession() {
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!active) return
        if (res.ok) {
          setState('allowed')
          return
        }

        const detail = await readApiErrorDetail(res)
        if (!handleStaleSession(detail)) {
          clearToken()
          redirectToLogin()
        }
      } catch {
        if (!active) return
        clearToken()
        redirectToLogin()
      }
    }

    validateSession()
    return () => {
      active = false
    }
  }, [isPublic, pathname])

  if (!isPublic && state !== 'allowed') return null
  return <>{children}</>
}

export function isPublicPath(pathname: string): boolean {
  if (pathname === '/') return true
  if (pathname.startsWith('/_next/')) return true
  if (PUBLIC_FILE_PATTERN.test(pathname)) return true
  return PUBLIC_PATHS.some(path => path !== '/' && pathname.startsWith(path))
}

function redirectToLogin(): void {
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}
