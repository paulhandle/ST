import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = ['/', '/login', '/api']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths through
  if (pathname === '/' || PUBLIC_PATHS.some(p => p !== '/' && pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // Check for JWT in cookie or Authorization header
  const token =
    request.cookies.get('st_token')?.value ||
    request.headers.get('authorization')?.replace('Bearer ', '')

  if (!token) {
    const loginUrl = new URL('/login', request.url)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|manifest.json).*)'],
}
