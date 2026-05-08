import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn() }),
}))

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

import SettingsPage from '@/app/settings/page'

describe('SettingsPage', () => {
  it('links to account security for passkeys and phone fallback', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Account security')).toBeInTheDocument()
    expect(screen.getByText('Passkeys and phone fallback')).toBeInTheDocument()
    expect(screen.getByText('Account security').closest('a')).toHaveAttribute('href', '/settings/security')
  })
})
