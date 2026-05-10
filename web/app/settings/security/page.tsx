'use client'

import { useState } from 'react'
import Link from 'next/link'
import { getToken } from '@/lib/auth'
import { DIALING_REGIONS, dialingRegionFor } from '@/lib/i18n/countryCodes'
import { useI18n } from '@/lib/i18n/I18nProvider'
import { ArrowLeft } from 'lucide-react'

export default function SecuritySettingsPage() {
  const { language, t } = useI18n()
  const [countryCode, setCountryCode] = useState('+86')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [sent, setSent] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const selectedRegion = dialingRegionFor(countryCode)
  const canSend = phone.replace(/\D/g, '').length >= selectedRegion.minNationalDigits
  const token = getToken()

  async function addPasskey() {
    setMessage(null)
    if (!window.PublicKeyCredential || !navigator.credentials) {
      setMessage('Passkeys are not available in this browser.')
      return
    }
    const res = await fetch('/api/auth/passkeys/register/options', {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    })
    if (!res.ok) {
      setMessage('Could not start passkey setup.')
      return
    }
    setMessage('Passkey setup is ready. Browser ceremony wiring comes next.')
  }

  async function sendPhoneCode() {
    setMessage(null)
    const res = await fetch('/api/auth/phone/link/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ country_code: countryCode, national_number: phone }),
    })
    if (!res.ok) {
      setMessage('Could not send phone code.')
      return
    }
    setSent(true)
  }

  async function verifyPhoneCode() {
    setMessage(null)
    const res = await fetch('/api/auth/phone/link/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ country_code: countryCode, national_number: phone, code: otp }),
    })
    setMessage(res.ok ? 'Phone fallback added.' : 'Could not verify phone code.')
  }

  return (
    <div>
      <div style={{
        padding: '16px',
        borderBottom: '1px solid var(--rule-soft)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <Link
          href="/settings"
          aria-label={t.common.back}
          className="settings-back-link"
          style={{
            color: 'var(--ink)',
          }}
        >
          <ArrowLeft size={16} aria-hidden="true" />
          <span>{t.common.back}</span>
        </Link>
        <div>
          <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>Account security</div>
          <div className="annot text-faint" style={{ fontSize: 12, marginTop: 4 }}>
            Manage passkeys and SMS fallback.
          </div>
        </div>
      </div>

      <section style={{ padding: 16, borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>Passkeys</div>
        <div className="annot text-faint" style={{ fontSize: 12, marginBottom: 12 }}>
          Use device biometrics or a security key for no-cost sign-in.
        </div>
        <button onClick={addPasskey} style={buttonStyle(true)}>Add passkey</button>
      </section>

      <section style={{ padding: 16 }}>
        <div className="hand" style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>Phone fallback</div>
        <div className="annot text-faint" style={{ fontSize: 12, marginBottom: 12 }}>
          SMS is protected by per-phone and per-IP rate limits.
        </div>

        <select value={countryCode} onChange={e => setCountryCode(e.target.value)} style={inputStyle}>
          {DIALING_REGIONS.map(region => (
            <option key={region.code} value={region.code}>
              {region.label[language]} ({region.code})
            </option>
          ))}
        </select>
        <input
          type="tel"
          placeholder={selectedRegion.sample}
          value={phone}
          onChange={e => setPhone(e.target.value)}
          style={{ ...inputStyle, marginTop: 10 }}
        />
        {sent && (
          <input
            type="text"
            inputMode="numeric"
            placeholder="123456"
            value={otp}
            onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
            style={{ ...inputStyle, marginTop: 10 }}
          />
        )}
        <button
          onClick={sent ? verifyPhoneCode : sendPhoneCode}
          disabled={sent ? otp.length < 6 : !canSend}
          style={{ ...buttonStyle(sent ? otp.length === 6 : canSend), marginTop: 10 }}
        >
          {sent ? 'Verify phone' : 'Send code'}
        </button>
      </section>

      {message && <div className="hand" style={{ padding: 16, color: 'var(--accent)', fontSize: 13 }}>{message}</div>}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  border: '1px solid var(--rule)',
  borderRadius: 'var(--radius)',
  background: 'var(--paper)',
  color: 'var(--ink)',
  fontFamily: 'var(--font-hand)',
  fontSize: 15,
}

function buttonStyle(active: boolean): React.CSSProperties {
  return {
    width: '100%',
    padding: '13px 14px',
    border: 'none',
    borderRadius: 'var(--radius)',
    background: active ? 'var(--accent)' : 'var(--rule)',
    color: '#050505',
    fontFamily: 'var(--font-hand)',
    fontSize: 15,
    cursor: active ? 'pointer' : 'default',
  }
}
