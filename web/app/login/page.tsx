'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { saveToken } from '@/lib/auth'

type Step = 'phone' | 'otp'

export default function LoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('phone')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
        const msg = await res.text().catch(() => '发送失败')
        setError(`发送失败：${msg}`)
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
        setError('验证码错误或已过期')
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
      {/* Logo */}
      <div className="hand" style={{ fontSize: 48, fontWeight: 700, marginBottom: 8 }}>ST</div>
      <div className="annot text-faint" style={{ fontSize: 14, marginBottom: 48 }}>智能马拉松训练</div>

      <div style={{ width: '100%', maxWidth: 360 }}>
        {/* Phone input */}
        <div style={{ marginBottom: 16 }}>
          <label className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)', display: 'block', marginBottom: 6 }}>
            手机号
          </label>
          <input
            type="tel"
            placeholder="手机号"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            disabled={step === 'otp'}
            className="hand"
            style={{
              width: '100%',
              padding: '12px 14px',
              border: '1.5px solid var(--rule)',
              borderRadius: 8,
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
            <label className="hand" style={{ fontSize: 13, color: 'var(--ink-faint)', display: 'block', marginBottom: 6 }}>
              验证码
            </label>
            <input
              type="text"
              inputMode="numeric"
              placeholder="验证码"
              value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              maxLength={6}
              autoFocus
              className="hand"
              style={{
                width: '100%',
                padding: '12px 14px',
                border: '1.5px solid var(--ink)',
                borderRadius: 8,
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
              background: phone.length >= 11 ? 'var(--ink)' : 'var(--rule)',
              color: 'var(--paper)',
              border: 'none',
              borderRadius: 8,
              fontFamily: 'var(--font-hand)',
              fontSize: 16,
              cursor: phone.length >= 11 ? 'pointer' : 'default',
              transition: 'background 0.15s',
            }}
          >
            {loading ? '发送中…' : '获取验证码'}
          </button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button
              onClick={verifyOtp}
              disabled={otp.length < 6 || loading}
              style={{
                width: '100%',
                padding: '14px',
                background: otp.length === 6 ? 'var(--ink)' : 'var(--rule)',
                color: 'var(--paper)',
                border: 'none',
                borderRadius: 8,
                fontFamily: 'var(--font-hand)',
                fontSize: 16,
                cursor: otp.length === 6 ? 'pointer' : 'default',
              }}
            >
              {loading ? '验证中…' : '登录'}
            </button>
            <button
              onClick={() => { setStep('phone'); setOtp(''); setError(null) }}
              style={{
                background: 'none', border: 'none',
                fontFamily: 'var(--font-hand)', fontSize: 13,
                color: 'var(--ink-faint)', cursor: 'pointer',
              }}
            >
              重新发送
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
