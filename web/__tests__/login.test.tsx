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
  it('renders phone input', () => {
    render(<LoginPage />)
    expect(screen.getByPlaceholderText(/手机号/)).toBeInTheDocument()
  })

  it('renders send OTP button', () => {
    render(<LoginPage />)
    expect(screen.getByText(/获取验证码/)).toBeInTheDocument()
  })

  it('OTP input is hidden initially', () => {
    render(<LoginPage />)
    expect(screen.queryByPlaceholderText(/验证码/)).not.toBeInTheDocument()
  })

  it('shows OTP input after send-otp success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: '已发送', otp_code: 123456 }),
    })

    render(<LoginPage />)
    const phoneInput = screen.getByPlaceholderText(/手机号/)
    fireEvent.change(phoneInput, { target: { value: '13800138000' } })
    fireEvent.click(screen.getByText(/获取验证码/))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/验证码/)).toBeInTheDocument()
    })
  })

  it('shows error when send-otp fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      text: async () => '手机号格式错误',
    })

    render(<LoginPage />)
    // Use 11-digit phone so the button is enabled
    fireEvent.change(screen.getByPlaceholderText(/手机号/), {
      target: { value: '13800138999' },
    })
    fireEvent.click(screen.getByText(/获取验证码/))

    await waitFor(() => {
      expect(screen.getByText(/发送失败/i)).toBeInTheDocument()
    })
  })
})
