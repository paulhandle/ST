import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('completes passkey registration ceremony', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          options: {
            challenge: 'AQID',
            rp: { id: 'localhost', name: 'PerformanceProtocol' },
            user: { id: 'BAU', name: 'runner@example.com', displayName: 'Runner' },
            pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
            excludeCredentials: [{ id: 'Bgc', type: 'public-key' }],
          },
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ registered: true }) })
    vi.stubGlobal('fetch', mockFetch)
    vi.stubGlobal('PublicKeyCredential', class MockPublicKeyCredential {})
    vi.stubGlobal('AuthenticatorAttestationResponse', class MockAuthenticatorAttestationResponse {})
    const credential = {
      id: 'new-credential',
      rawId: new Uint8Array([1, 2, 3]).buffer,
      type: 'public-key',
      response: {
        clientDataJSON: new Uint8Array([4]).buffer,
        attestationObject: new Uint8Array([5]).buffer,
        getTransports: () => ['internal'],
      },
    } as unknown as PublicKeyCredential
    Object.setPrototypeOf(credential, window.PublicKeyCredential.prototype)
    Object.setPrototypeOf(credential.response, window.AuthenticatorAttestationResponse.prototype)
    vi.stubGlobal('navigator', {
      ...window.navigator,
      language: 'en-US',
      credentials: {
        create: vi.fn(async () => credential),
      },
    })

    render(<SecuritySettingsPage />)
    fireEvent.click(screen.getByText('Add passkey'))

    await waitFor(() => {
      expect(navigator.credentials.create).toHaveBeenCalled()
      expect(mockFetch).toHaveBeenCalledWith('/api/auth/passkeys/register/verify', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          credential: {
            id: 'new-credential',
            rawId: 'AQID',
            type: 'public-key',
            response: {
              clientDataJSON: 'BA',
              attestationObject: 'BQ',
              transports: ['internal'],
            },
          },
          name: 'Passkey',
        }),
      }))
      expect(screen.getByText('Passkey added.')).toBeInTheDocument()
    })
  })
})
