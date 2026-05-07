'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { saveToken, getToken } from '@/lib/auth'
import BrandLogo from '@/components/BrandLogo'
import LanguageToggle from '@/components/LanguageToggle'
import { DIALING_REGIONS, dialingRegionFor } from '@/lib/i18n/countryCodes'
import { useI18n } from '@/lib/i18n/I18nProvider'

type Step = 'phone' | 'otp'
type LoginMode = 'primary' | 'sms'

const COPY = {
  en: {
    tagline: 'Endurance performance system',
    google: 'Continue with Google',
    passkey: 'Sign in with passkey',
    smsFallback: 'Use phone code instead',
    primaryError: 'This sign-in method is not configured yet.',
    countryCode: 'Country/region code',
    phone: 'Phone number',
    otp: 'Verification code',
    send: 'Send code',
    sending: 'Sending...',
    signIn: 'Sign in',
  verifying: 'Verifying...',
    resend: 'Resend code',
    sendError: 'Unable to send code',
    verifyError: 'The verification code is invalid or expired.',
  },
  zh: {
    tagline: '耐力表现系统',
    google: '使用 Google 登录',
    passkey: '使用 Passkey 登录',
    smsFallback: '使用短信验证码',
    primaryError: '这个登录方式还没有配置。',
    countryCode: '国家/地区区号',
    phone: '手机号',
    otp: '验证码',
    send: '发送验证码',
    sending: '发送中...',
    signIn: '登录',
    verifying: '验证中...',
    resend: '重新发送',
    sendError: '无法发送验证码',
    verifyError: '验证码无效或已过期。',
  },
}

export default function LoginPage() {
  const router = useRouter()
  const { language, setLanguage } = useI18n()
  const t = COPY[language]
  const [step, setStep] = useState<Step>('phone')
  const [mode, setMode] = useState<LoginMode>('primary')
  const [countryCode, setCountryCode] = useState('+86')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const selectedRegion = dialingRegionFor(countryCode)
  const canSend = phone.replace(/\D/g, '').length >= selectedRegion.minNationalDigits

  // Migrate pre-cookie sessions: if localStorage already has a valid token,
  // saveToken re-syncs it to the cookie and we skip the login flow entirely.
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
        body: JSON.stringify({ country_code: countryCode, national_number: phone }),
      })
      if (!res.ok) {
        const msg = await res.text().catch(() => t.sendError)
        setError(`${t.sendError}: ${msg}`)
        return
      }
      setStep('otp')
    } finally {
      setLoading(false)
    }
  }

  function unavailablePrimaryMethod() {
    setError(t.primaryError)
  }

  async function passkeyLogin() {
    setError(null)
    setLoading(true)
    try {
      if (!window.PublicKeyCredential || !navigator.credentials) {
        setError(t.primaryError)
        return
      }
      const res = await fetch('/api/auth/passkeys/login/options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) {
        setError(t.primaryError)
        return
      }
      setError(t.primaryError)
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
        body: JSON.stringify({ country_code: countryCode, national_number: phone, code: otp }),
      })
      if (!res.ok) {
        setError(t.verifyError)
        return
      }
      const data = await res.json()
      saveToken(data.access_token)
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
      <div style={{ position: 'absolute', top: 20, right: 20 }}>
        <LanguageToggle language={language} onChange={setLanguage} />
      </div>

      <BrandLogo href="/" />
      <div className="annot text-faint" style={{ fontSize: 14, marginBottom: 48 }}>{t.tagline}</div>

      <div style={{ width: '100%', maxWidth: 380 }}>
        {error && mode === 'primary' && (
          <div className="hand" style={{ color: 'var(--accent)', fontSize: 13, marginBottom: 12 }}>
            {error}
          </div>
        )}
        {mode === 'primary' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button onClick={unavailablePrimaryMethod} style={secondaryButtonStyle}>
              {t.google}
            </button>
            <button onClick={passkeyLogin} disabled={loading} style={secondaryButtonStyle}>
              {t.passkey}
            </button>
            <button
              onClick={() => { setMode('sms'); setError(null) }}
              style={{ ...secondaryButtonStyle, borderStyle: 'dashed', color: 'var(--ink-faint)' }}
            >
              {t.smsFallback}
            </button>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <label htmlFor="country-code" className="hand" style={labelStyle}>
                {t.countryCode}
              </label>
              <select
                id="country-code"
                value={countryCode}
                onChange={e => setCountryCode(e.target.value)}
                disabled={step === 'otp'}
                className="hand"
                style={{
                  ...inputStyle,
                  opacity: step === 'otp' ? 0.6 : 1,
                }}
              >
                {DIALING_REGIONS.map(region => (
                  <option key={region.code} value={region.code}>
                    {region.label[language]} ({region.code})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label htmlFor="phone" className="hand" style={labelStyle}>
                {t.phone}
              </label>
              <input
                id="phone"
                type="tel"
                placeholder={selectedRegion.sample}
                value={phone}
                onChange={e => setPhone(e.target.value)}
                disabled={step === 'otp'}
                className="hand"
                style={{
                  ...inputStyle,
                  opacity: step === 'otp' ? 0.6 : 1,
                }}
              />
            </div>

            {step === 'otp' && (
              <div style={{ marginBottom: 16 }}>
                <label htmlFor="otp" className="hand" style={labelStyle}>
                  {t.otp}
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
                    ...inputStyle,
                    border: '1px solid var(--accent)',
                    fontSize: 20,
                    letterSpacing: 6,
                  }}
                />
              </div>
            )}

            {error && (
              <div className="hand" style={{ color: 'var(--accent)', fontSize: 13, marginBottom: 12 }}>
                {error}
              </div>
            )}

            {step === 'phone' ? (
              <button
                onClick={sendOtp}
                disabled={!canSend || loading}
                style={primaryButtonStyle(canSend)}
              >
                {loading ? t.sending : t.send}
              </button>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <button
                  onClick={verifyOtp}
                  disabled={otp.length < 6 || loading}
                  style={primaryButtonStyle(otp.length === 6)}
                >
                  {loading ? t.verifying : t.signIn}
                </button>
                <button
                  onClick={() => { setStep('phone'); setOtp(''); setError(null) }}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontFamily: 'var(--font-hand)',
                    fontSize: 13,
                    color: 'var(--ink-faint)',
                    cursor: 'pointer',
                  }}
                >
                  {t.resend}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  fontSize: 13,
  color: 'var(--ink-faint)',
  display: 'block',
  marginBottom: 6,
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  fontSize: 16,
  background: 'var(--paper)',
  color: 'var(--ink)',
  fontFamily: 'var(--font-hand)',
  outline: 'none',
}

function primaryButtonStyle(active: boolean): React.CSSProperties {
  return {
    width: '100%',
    padding: '14px',
    background: active ? 'var(--accent)' : 'var(--rule)',
    color: '#050505',
    border: 'none',
    borderRadius: 'var(--radius)',
    fontFamily: 'var(--font-hand)',
    fontSize: 16,
    cursor: active ? 'pointer' : 'default',
    transition: 'background 0.15s',
  }
}

const secondaryButtonStyle: React.CSSProperties = {
  width: '100%',
  padding: '14px',
  background: 'var(--paper)',
  color: 'var(--ink)',
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  fontFamily: 'var(--font-hand)',
  fontSize: 16,
  cursor: 'pointer',
}
