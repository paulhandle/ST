'use client'

import Script from 'next/script'
import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { clearAthleteId, getStoredAthleteId, saveAthleteId, saveToken, getToken } from '@/lib/auth'
import BrandLogo from '@/components/BrandLogo'
import LanguageToggle from '@/components/LanguageToggle'
import { DIALING_REGIONS, dialingRegionFor } from '@/lib/i18n/countryCodes'
import { useI18n } from '@/lib/i18n/I18nProvider'

type Step = 'phone' | 'otp'
type LoginMode = 'primary' | 'sms'
type AuthResponse = {
  access_token: string
  is_new_user?: boolean
  has_athlete?: boolean
  athlete_id?: number | null
}
type GoogleCredentialResponse = { credential?: string }
type GoogleIdentityApi = {
  initialize: (config: {
    client_id: string
    callback: (response: GoogleCredentialResponse) => void
    ux_mode?: 'popup' | 'redirect'
  }) => void
  renderButton: (parent: HTMLElement, options: Record<string, string | number | boolean>) => void
}

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: GoogleIdentityApi
      }
    }
  }
}

const COPY = {
  en: {
    tagline: 'Endurance performance system',
    google: 'Continue with Google',
    passkey: 'Sign in with passkey',
    smsFallback: 'Use phone code instead',
    primaryError: 'This sign-in method is not configured yet.',
    googleError: 'Google sign-in is unavailable. Use phone code for now.',
    googleLoading: 'Google sign-in is still loading.',
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
    googleError: 'Google 登录暂时不可用，请先使用短信验证码。',
    googleLoading: 'Google 登录还在加载中。',
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
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? ''
  const smsLoginEnabled = process.env.NEXT_PUBLIC_SMS_LOGIN_ENABLED !== 'false'
  const googleButtonRef = useRef<HTMLDivElement | null>(null)
  const [step, setStep] = useState<Step>('phone')
  const [mode, setMode] = useState<LoginMode>('primary')
  const [countryCode, setCountryCode] = useState('+86')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleReady, setGoogleReady] = useState(false)
  const [googleScriptFailed, setGoogleScriptFailed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const loginInFlightRef = useRef(false)
  const selectedRegion = dialingRegionFor(countryCode)
  const canSend = phone.replace(/\D/g, '').length >= selectedRegion.minNationalDigits

  // Migrate pre-cookie sessions: if localStorage already has a valid token,
  // saveToken re-syncs it to the cookie and we skip the login flow entirely.
  useEffect(() => {
    const existing = getToken()
    if (existing) {
      saveToken(existing)
      router.replace(getStoredAthleteId() ? '/dashboard' : '/onboarding')
    }
  }, [router])

  const completeLogin = useCallback((data: AuthResponse) => {
    saveToken(data.access_token)
    if (data.has_athlete && data.athlete_id && data.athlete_id > 0) {
      saveAthleteId(data.athlete_id)
      router.replace('/dashboard')
      return
    }
    clearAthleteId()
    router.replace('/onboarding')
  }, [router])

  const handleGoogleCredential = useCallback(async (response: GoogleCredentialResponse) => {
    if (loginInFlightRef.current) {
      return
    }
    if (!response.credential) {
      setError(t.googleError)
      return
    }
    loginInFlightRef.current = true
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      })
      if (!res.ok) {
        setError(t.googleError)
        return
      }
      const data = await res.json()
      completeLogin(data)
    } finally {
      loginInFlightRef.current = false
      setLoading(false)
    }
  }, [completeLogin, t.googleError])

  const initializeGoogle = useCallback(() => {
    const googleId = window.google?.accounts?.id
    if (!googleClientId || !googleId || !googleButtonRef.current) {
      setGoogleReady(false)
      return
    }

    googleId.initialize({
      client_id: googleClientId,
      callback: handleGoogleCredential,
      ux_mode: 'popup',
    })
    const buttonWidth = Math.round(Math.min(380, Math.max(240, googleButtonRef.current.getBoundingClientRect().width || 380)))
    googleButtonRef.current.innerHTML = ''
    googleId.renderButton(googleButtonRef.current, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'rectangular',
      text: 'continue_with',
      logo_alignment: 'left',
      width: buttonWidth,
      locale: language === 'zh' ? 'zh_CN' : 'en',
    })
    setGoogleReady(true)
    setGoogleScriptFailed(false)
  }, [googleClientId, handleGoogleCredential, language])

  useEffect(() => {
    initializeGoogle()
  }, [initializeGoogle])

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
      completeLogin(data)
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
      {googleClientId && (
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="afterInteractive"
          onLoad={initializeGoogle}
          onError={() => {
            setGoogleReady(false)
            setGoogleScriptFailed(true)
          }}
        />
      )}
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
            {googleClientId ? (
              <>
                <div
                  ref={googleButtonRef}
                  aria-label={t.google}
                  style={{
                    ...googleButtonContainerStyle,
                    display: googleReady ? 'block' : 'none',
                  }}
                />
                {!googleReady && (
                  <button
                    onClick={() => setError(googleScriptFailed ? t.googleError : t.googleLoading)}
                    style={secondaryButtonStyle}
                  >
                    {t.google}
                  </button>
                )}
              </>
            ) : (
              <button onClick={unavailablePrimaryMethod} style={secondaryButtonStyle}>
                {t.google}
              </button>
            )}
            <button onClick={passkeyLogin} disabled={loading} style={secondaryButtonStyle}>
              {t.passkey}
            </button>
            {smsLoginEnabled && (
              <div style={fallbackLineStyle}>
                <button
                  onClick={() => { setMode('sms'); setError(null) }}
                  style={textLinkButtonStyle}
                  data-variant="text-link"
                >
                  {t.smsFallback}
                </button>
              </div>
            )}
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

const googleButtonContainerStyle: React.CSSProperties = {
  width: '100%',
  minHeight: 44,
  overflow: 'hidden',
}

const fallbackLineStyle: React.CSSProperties = {
  marginTop: 8,
  textAlign: 'center',
  fontSize: 13,
  lineHeight: 1.5,
}

const textLinkButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  padding: 0,
  color: 'var(--ink-faint)',
  cursor: 'pointer',
  fontFamily: 'var(--font-hand)',
  fontSize: 13,
  textDecoration: 'underline',
  textUnderlineOffset: 3,
}
