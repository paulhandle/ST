'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { saveToken, getToken } from '@/lib/auth'
import BrandLogo from '@/components/BrandLogo'

type Step = 'phone' | 'otp'

export default function LoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('phone')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Migrate pre-cookie sessions: if localStorage already has a valid token,
  // saveToken re-syncs it to the cookie and we skip the login flow entirely
  useEffect(() => {
    const existing = getToken()
    if (existing) {
      saveToken(existing)
      router.replace('/dashboard')
    }
  }, [router])

  async function sendOtp() {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/auth/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone }),
      })
      if (!res.ok) {
        const msg = await res.text().catch(() => 'Unable to send code')
        setError(`Unable to send code: ${msg}`)
        return
      }
      setStep('otp')
    } finally {
      setLoading(false)
    }
  }

  async function verifyOtp() {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code: otp }),
      })
      if (!res.ok) {
        setError('The verification code is invalid or expired.')
        return
      }
      const data = await res.json()
      saveToken(data.access_token)
      // New user (no athlete yet) → onboarding; returning user → dashboard
      router.replace(data.is_new_user ? '/onboarding' : '/dashboard')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 24px',
      background: 'var(--paper)',
    }}>
      {/* Brand */}
      <BrandLogo href="/" />
      <div className="annot text-faint" style={{ fontSize: 14, marginBottom: 48 }}>Endurance performance system</div>

      <div style={{ width: '100%', maxWidth: 360 }}>
        {/* Phone input */}
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="phone" className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)', display: 'block', marginBottom: 6 }}>
            Phone number
          </label>
          <input
            id="phone"
            type="tel"
            placeholder="+86 138 0013 8000"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            disabled={step === 'otp'}
            className="hand"
            style={{
              width: '100%',
              padding: '12px 14px',
              border: '1px solid var(--rule)',
              borderRadius: 'var(--radius)',
              fontSize: 16,
              background: 'var(--paper)',
              color: 'var(--ink)',
              fontFamily: 'var(--font-hand)',
              outline: 'none',
              opacity: step === 'otp' ? 0.6 : 1,
            }}
          />
        </div>

        {/* OTP input — shown after send */}
        {step === 'otp' && (
          <div style={{ marginBottom: 16 }}>
            <label htmlFor="otp" className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)', display: 'block', marginBottom: 6 }}>
              Verification code
            </label>
            <input
              id="otp"
              type="text"
              inputMode="numeric"
              placeholder="123456"
              value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              maxLength={6}
              autoFocus
              className="hand"
              style={{
                width: '100%',
                padding: '12px 14px',
                border: '1px solid var(--accent)',
                borderRadius: 'var(--radius)',
                fontSize: 20,
                letterSpacing: 6,
                background: 'var(--paper)',
                color: 'var(--ink)',
                fontFamily: 'var(--font-hand)',
                outline: 'none',
              }}
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="hand" style={{ color: 'var(--accent)', fontSize: 13, marginBottom: 12 }}>
            {error}
          </div>
        )}

        {/* CTA button */}
        {step === 'phone' ? (
          <button
            onClick={sendOtp}
            disabled={phone.length < 11 || loading}
            style={{
              width: '100%',
              padding: '14px',
              background: phone.length >= 11 ? 'var(--accent)' : 'var(--rule)',
              color: '#050505',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontFamily: 'var(--font-hand)',
              fontSize: 16,
              cursor: phone.length >= 11 ? 'pointer' : 'default',
              transition: 'background 0.15s',
            }}
          >
            {loading ? 'Sending...' : 'Send code'}
          </button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button
              onClick={verifyOtp}
              disabled={otp.length < 6 || loading}
              style={{
                width: '100%',
                padding: '14px',
                background: otp.length === 6 ? 'var(--accent)' : 'var(--rule)',
                color: '#050505',
                border: 'none',
                borderRadius: 'var(--radius)',
                fontFamily: 'var(--font-hand)',
                fontSize: 16,
                cursor: otp.length === 6 ? 'pointer' : 'default',
              }}
            >
              {loading ? 'Verifying...' : 'Sign in'}
            </button>
            <button
              onClick={() => { setStep('phone'); setOtp(''); setError(null) }}
              style={{
                background: 'none', border: 'none',
                fontFamily: 'var(--font-hand)', fontSize: 13,
                color: 'var(--ink-faint)', cursor: 'pointer',
              }}
            >
              Resend code
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
