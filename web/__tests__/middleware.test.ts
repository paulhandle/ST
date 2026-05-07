import { describe, expect, it } from 'vitest'
import { NextRequest, NextResponse } from 'next/server'
import { middleware } from '@/middleware'

function request(pathname: string): NextRequest {
  return new NextRequest(new URL(pathname, 'http://localhost:3000'))
}

describe('middleware', () => {
  it('does not require auth for public icons', () => {
    const response = middleware(request('/icons/pp-icon.svg'))
    expect(response.headers.get('location')).toBeNull()
  })

  it('redirects protected routes without auth', () => {
    const response = middleware(request('/dashboard'))
    expect(response.headers.get('location')).toBe('http://localhost:3000/login')
  })

  it('matches the NextResponse pass-through shape for public routes', () => {
    const response = middleware(request('/icons/pp-icon.svg'))
    expect(response).toBeInstanceOf(NextResponse)
  })
})
