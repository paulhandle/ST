import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => '/settings',
}))

vi.mock('@/lib/auth', () => ({
  clearToken: vi.fn(),
  getToken: () => 'mock-token',
}))

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

import SettingsPage from '@/app/settings/page'
import SecuritySettingsPage from '@/app/settings/security/page'

describe('SettingsPage', () => {
  it('has an explicit back link to Me', () => {
    render(<SettingsPage />)
    expect(screen.getByRole('link', { name: 'Back' })).toHaveAttribute('href', '/me')
  })

  it('links to account security for passkeys and phone fallback', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Account security')).toBeInTheDocument()
    expect(screen.getByText('Passkeys and phone fallback')).toBeInTheDocument()
    expect(screen.getByText('Account security').closest('a')).toHaveAttribute('href', '/settings/security')
  })
})

describe('SecuritySettingsPage', () => {
  it('has an explicit back link to Settings', () => {
    render(<SecuritySettingsPage />)
    expect(screen.getByRole('link', { name: 'Back' })).toHaveAttribute('href', '/settings')
  })
})
