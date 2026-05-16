import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
}))

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => routerMocks,
}))

// Mock fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock localStorage
const store: Record<string, string> = {}
let assignedPath = ''
vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
})

import LoginPage from '@/app/login/page'

beforeEach(() => {
  vi.clearAllMocks()
  routerMocks.push.mockClear()
  routerMocks.replace.mockClear()
  Object.keys(store).forEach(k => delete store[k])
  document.cookie = 'st_token=; path=/; max-age=0; SameSite=Lax'
  assignedPath = ''
  delete process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
  delete process.env.NEXT_PUBLIC_SMS_LOGIN_ENABLED
  vi.unstubAllGlobals()
  vi.stubGlobal('fetch', mockFetch)
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v },
    removeItem: (k: string) => { delete store[k] },
  })
  vi.stubGlobal('location', {
    ...window.location,
    assign: vi.fn((path: string) => { assignedPath = path }),
  })
})

describe('LoginPage', () => {
  function openSmsFallback() {
    fireEvent.click(screen.getByText(/Use phone code instead/))
  }

  function stubPasskeySupport(credential: PublicKeyCredential) {
    vi.stubGlobal('PublicKeyCredential', class MockPublicKeyCredential {})
    Object.setPrototypeOf(credential, window.PublicKeyCredential.prototype)
    vi.stubGlobal('navigator', {
      ...window.navigator,
      language: 'en-US',
      credentials: {
        get: vi.fn(async () => credential),
      },
    })
    vi.stubGlobal('AuthenticatorAssertionResponse', class MockAuthenticatorAssertionResponse {})
    Object.setPrototypeOf(credential.response, window.AuthenticatorAssertionResponse.prototype)
  }

  it('shows a loading skeleton when google client id is set but GIS has not initialised', () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'test-google-client-id'
    // Do NOT stub window.google — GIS script hasn't loaded yet
    render(<LoginPage />)
    // Should NOT show a clickable "Continue with Google" button
    expect(screen.queryByRole('button', { name: /Continue with Google/i })).toBeNull()
    // Should show the loading skeleton container
    const skeletons = screen.getAllByLabelText(/Continue with Google/i)
    const busySkeleton = skeletons.find(el => el.getAttribute('aria-busy') === 'true')
    expect(busySkeleton).toBeInTheDocument()
    expect(busySkeleton!.getAttribute('aria-busy')).toBe('true')
  })

  it('prioritizes Google and passkey sign-in', () => {
    render(<LoginPage />)
    expect(screen.getByText(/Continue with Google/)).toBeInTheDocument()
    expect(screen.getByText(/Sign in with passkey/)).toBeInTheDocument()
    expect(screen.getByText(/after adding a passkey in account security/i)).toBeInTheDocument()
    expect(screen.getByText(/Use phone code instead/).closest('button')).toHaveAttribute('data-variant', 'text-link')
    expect(screen.queryByPlaceholderText(/138 0013 8000/)).not.toBeInTheDocument()
  })

  it('posts Google credential token and follows the existing auth redirect', async () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'test-google-client-id'
    let googleCallback: ((response: { credential?: string }) => void) | undefined
    const initialize = vi.fn((config: { client_id: string; callback: (response: { credential?: string }) => void }) => {
      googleCallback = config.callback
    })
    const renderButton = vi.fn((parent: HTMLElement) => {
      const button = document.createElement('button')
      button.textContent = 'Continue with Google'
      button.addEventListener('click', () => googleCallback?.({ credential: 'google-id-token' }))
      parent.appendChild(button)
    })
    vi.stubGlobal('google', {
      accounts: {
        id: { initialize, renderButton },
      },
    })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'google-app-token',
        token_type: 'bearer',
        user_id: 1,
        is_new_user: false,
        has_athlete: false,
        athlete_id: null,
      }),
    })

    render(<LoginPage />)

    await waitFor(() => {
      expect(initialize).toHaveBeenCalledWith(expect.objectContaining({ client_id: 'test-google-client-id' }))
      expect(renderButton).toHaveBeenCalledWith(expect.any(HTMLElement), expect.objectContaining({ theme: 'filled_black' }))
    })
    fireEvent.click(screen.getByRole('button', { name: /Continue with Google/ }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/auth/google', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ id_token: 'google-id-token' }),
      }))
      expect(store.st_token).toBe('google-app-token')
      expect(store.pp_athlete_id).toBeUndefined()
      expect(window.location.assign).toHaveBeenCalledWith('/onboarding')
      expect(assignedPath).toBe('/onboarding')
    })
  })

  it('ignores duplicate Google callbacks while login is already in progress', async () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'test-google-client-id'
    let googleCallback: ((response: { credential?: string }) => void) | undefined
    vi.stubGlobal('google', {
      accounts: {
        id: {
          initialize: vi.fn((config: { callback: (response: { credential?: string }) => void }) => {
            googleCallback = config.callback
          }),
          renderButton: vi.fn((parent: HTMLElement) => {
            const button = document.createElement('button')
            button.textContent = 'Continue with Google'
            button.addEventListener('click', () => {
              googleCallback?.({ credential: 'google-id-token' })
              googleCallback?.({ credential: 'google-id-token' })
            })
            parent.appendChild(button)
          }),
        },
      },
    })
    mockFetch.mockImplementationOnce(() => new Promise(resolve => {
      setTimeout(() => {
        resolve({
          ok: true,
          json: async () => ({
            access_token: 'google-app-token',
            token_type: 'bearer',
            user_id: 1,
            is_new_user: false,
            has_athlete: false,
            athlete_id: null,
          }),
        })
      }, 10)
    }))

    render(<LoginPage />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Continue with Google/ })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /Continue with Google/ }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1)
      expect(window.location.assign).toHaveBeenCalledWith('/onboarding')
    })
  })

  it('routes returning Google users with an athlete to dashboard and stores athlete id', async () => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'test-google-client-id'
    let googleCallback: ((response: { credential?: string }) => void) | undefined
    vi.stubGlobal('google', {
      accounts: {
        id: {
          initialize: vi.fn((config: { callback: (response: { credential?: string }) => void }) => {
            googleCallback = config.callback
          }),
          renderButton: vi.fn((parent: HTMLElement) => {
            const button = document.createElement('button')
            button.textContent = 'Continue with Google'
            button.addEventListener('click', () => googleCallback?.({ credential: 'google-id-token' }))
            parent.appendChild(button)
          }),
        },
      },
    })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'google-app-token',
        token_type: 'bearer',
        user_id: 1,
        is_new_user: false,
        has_athlete: true,
        athlete_id: 42,
      }),
    })

    render(<LoginPage />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Continue with Google/ })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /Continue with Google/ }))

    await waitFor(() => {
      expect(store.pp_athlete_id).toBe('42')
      expect(window.location.assign).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('completes passkey sign-in and follows the existing auth redirect', async () => {
    const credential = {
      id: 'credential-id',
      rawId: new Uint8Array([1, 2, 3]).buffer,
      type: 'public-key',
      response: {
        clientDataJSON: new Uint8Array([4]).buffer,
        authenticatorData: new Uint8Array([5]).buffer,
        signature: new Uint8Array([6]).buffer,
        userHandle: new Uint8Array([7]).buffer,
      },
    } as unknown as PublicKeyCredential
    stubPasskeySupport(credential)
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          options: {
            challenge: 'AQID',
            rpId: 'localhost',
            allowCredentials: [{ id: 'BAU', type: 'public-key' }],
            userVerification: 'preferred',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'passkey-token',
          token_type: 'bearer',
          user_id: 1,
          is_new_user: false,
          has_athlete: true,
          athlete_id: 42,
        }),
      })

    render(<LoginPage />)
    fireEvent.click(screen.getByText(/Sign in with passkey/))

    await waitFor(() => {
      expect(navigator.credentials.get).toHaveBeenCalled()
      expect(mockFetch).toHaveBeenCalledWith('/api/auth/passkeys/login/verify', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          credential: {
            id: 'credential-id',
            rawId: 'AQID',
            type: 'public-key',
            response: {
              clientDataJSON: 'BA',
              authenticatorData: 'BQ',
              signature: 'Bg',
              userHandle: 'Bw',
            },
          },
        }),
      }))
      expect(store.st_token).toBe('passkey-token')
      expect(window.location.assign).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('guides users without a registered passkey back to Google first', async () => {
    delete store.st_token
    const credential = {
      id: 'credential-id',
      rawId: new Uint8Array([1]).buffer,
      type: 'public-key',
      response: {
        clientDataJSON: new Uint8Array([2]).buffer,
        authenticatorData: new Uint8Array([3]).buffer,
        signature: new Uint8Array([4]).buffer,
        userHandle: null,
      },
    } as unknown as PublicKeyCredential
    stubPasskeySupport(credential)
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          options: {
            challenge: 'AQID',
            rpId: 'localhost',
            allowCredentials: [],
            userVerification: 'preferred',
          },
        }),
      })
      .mockResolvedValueOnce({ ok: false })

    render(<LoginPage />)
    fireEvent.click(screen.getByText(/Sign in with passkey/))

    await waitFor(() => {
      expect(screen.getByText(/Sign in with Google first/i)).toBeInTheDocument()
      expect(store.st_token).toBeUndefined()
    })
  })

  it('routes an existing token without stored athlete id back to onboarding', async () => {
    store.st_token = 'existing-token'

    render(<LoginPage />)

    await waitFor(() => {
      expect(window.location.assign).toHaveBeenCalledWith('/onboarding')
    })
  })

  it('routes an existing token with stored athlete id to dashboard', async () => {
    store.st_token = 'existing-token'
    store.pp_athlete_id = '42'

    render(<LoginPage />)

    await waitFor(() => {
      expect(window.location.assign).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('keeps SMS fallback available when Google is not configured', () => {
    render(<LoginPage />)
    fireEvent.click(screen.getByText(/Continue with Google/))
    expect(screen.getByText(/This sign-in method is not configured yet/i)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Use phone code instead/))
    expect(screen.getByPlaceholderText(/138 0013 8000/)).toBeInTheDocument()
  })

  it('hides SMS fallback when it is disabled for production', () => {
    process.env.NEXT_PUBLIC_SMS_LOGIN_ENABLED = 'false'
    render(<LoginPage />)
    expect(screen.queryByText(/Use phone code instead/)).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/138 0013 8000/)).not.toBeInTheDocument()
  })

  it('renders phone input after choosing SMS fallback', () => {
    render(<LoginPage />)
    openSmsFallback()
    expect(screen.getByPlaceholderText(/138 0013 8000/)).toBeInTheDocument()
  })

  it('renders dialing-code selector with Taiwan, China wording', () => {
    render(<LoginPage />)
    openSmsFallback()
    expect(screen.getByLabelText(/Country\/region code/i)).toHaveValue('+86')
    expect(screen.getByRole('option', { name: /Taiwan, China \(\+886\)/ })).toBeInTheDocument()
  })

  it('renders send OTP button', () => {
    render(<LoginPage />)
    openSmsFallback()
    expect(screen.getByText(/Send code/)).toBeInTheDocument()
  })

  it('OTP input is hidden initially', () => {
    render(<LoginPage />)
    openSmsFallback()
    expect(screen.queryByLabelText(/Verification code/)).not.toBeInTheDocument()
  })

  it('shows OTP input after send-otp success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: '已发送', otp_code: 123456 }),
    })

    render(<LoginPage />)
    openSmsFallback()
    const phoneInput = screen.getByPlaceholderText(/138 0013 8000/)
    fireEvent.change(phoneInput, { target: { value: '13800138000' } })
    fireEvent.click(screen.getByText(/Send code/))

    await waitFor(() => {
      expect(screen.getByLabelText(/Verification code/)).toBeInTheDocument()
    })
  })

  it('shows error when send-otp fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      text: async () => '手机号格式错误',
    })

    render(<LoginPage />)
    openSmsFallback()
    // Use 11-digit phone so the button is enabled
    fireEvent.change(screen.getByPlaceholderText(/138 0013 8000/), {
      target: { value: '13800138999' },
    })
    fireEvent.click(screen.getByText(/Send code/))

    await waitFor(() => {
      expect(screen.getByText(/Unable to send code/i)).toBeInTheDocument()
    })
  })

  it('sends country code and national number to send-otp', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'sent', otp_code: 123456 }),
    })

    render(<LoginPage />)
    openSmsFallback()
    fireEvent.change(screen.getByPlaceholderText(/138 0013 8000/), {
      target: { value: '138 0013 8000' },
    })
    fireEvent.click(screen.getByText(/Send code/))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/auth/send-otp', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ country_code: '+86', national_number: '138 0013 8000' }),
      }))
    })
  })

  it('sends selected dialing code for US numbers', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'sent', otp_code: 123456 }),
    })

    render(<LoginPage />)
    openSmsFallback()
    fireEvent.change(screen.getByLabelText(/Country\/region code/i), {
      target: { value: '+1' },
    })
    fireEvent.change(screen.getByPlaceholderText(/415 555 2671/), {
      target: { value: '4155552671' },
    })
    fireEvent.click(screen.getByText(/Send code/))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/auth/send-otp', expect.objectContaining({
        body: JSON.stringify({ country_code: '+1', national_number: '4155552671' }),
      }))
    })
  })

  it('sends country fields when verifying OTP', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ message: 'sent', otp_code: 123456 }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'token',
          token_type: 'bearer',
          user_id: 1,
          is_new_user: false,
          has_athlete: false,
          athlete_id: null,
        }),
      })

    render(<LoginPage />)
    openSmsFallback()
    fireEvent.change(screen.getByPlaceholderText(/138 0013 8000/), {
      target: { value: '13800138000' },
    })
    fireEvent.click(screen.getByText(/Send code/))

    await waitFor(() => expect(screen.getByLabelText(/Verification code/)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/Verification code/), {
      target: { value: '123456' },
    })
    fireEvent.click(screen.getByText(/Sign in/))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenLastCalledWith('/api/auth/verify-otp', expect.objectContaining({
        body: JSON.stringify({ country_code: '+86', national_number: '13800138000', code: '123456' }),
      }))
      expect(window.location.assign).toHaveBeenCalledWith('/onboarding')
    })
  })

  it('switches login copy to Chinese', () => {
    render(<LoginPage />)
    fireEvent.click(screen.getByRole('button', { name: '中文' }))
    fireEvent.click(screen.getByText('使用短信验证码'))
    expect(screen.getByText('手机号')).toBeInTheDocument()
    expect(screen.getByText('发送验证码')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /中国台湾 \(\+886\)/ })).toBeInTheDocument()
  })
})
