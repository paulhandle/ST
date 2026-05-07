import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

// Mock fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock localStorage
const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
})

import LoginPage from '@/app/login/page'

beforeEach(() => {
  vi.clearAllMocks()
  Object.keys(store).forEach(k => delete store[k])
})

describe('LoginPage', () => {
  function openSmsFallback() {
    fireEvent.click(screen.getByText(/Use phone code instead/))
  }

  it('prioritizes Google and passkey sign-in', () => {
    render(<LoginPage />)
    expect(screen.getByText(/Continue with Google/)).toBeInTheDocument()
    expect(screen.getByText(/Sign in with passkey/)).toBeInTheDocument()
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
        json: async () => ({ access_token: 'token', token_type: 'bearer', user_id: 1, is_new_user: false }),
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
