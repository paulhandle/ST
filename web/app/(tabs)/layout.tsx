'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import CoachButton from '@/components/CoachButton'
import BrandLogo from '@/components/BrandLogo'
import LanguageToggle from '@/components/LanguageToggle'
import { useI18n } from '@/lib/i18n/I18nProvider'

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { language, setLanguage, t } = useI18n()
  const tabs = [
    { href: '/dashboard', label: t.nav.dashboard, icon: TabIconDashboard },
    { href: '/activities', label: t.nav.activities, icon: TabIconActivities },
    { href: '/plan', label: t.nav.plan, icon: TabIconPlan },
    { href: '/me', label: t.nav.me, icon: TabIconMe },
  ]

  return (
    <>
      <div className="app-topbar">
        <BrandLogo href="/dashboard" compact />
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <LanguageToggle language={language} onChange={setLanguage} compact />
        </div>
      </div>

      <div className="page-shell">{children}</div>

      <nav className="tabbar">
        {tabs.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`tabbar-item ${pathname === href ? 'active' : ''}`}
          >
            <span className="tabbar-icon">
              <Icon active={pathname === href} />
            </span>
            <span>{label}</span>
          </Link>
        ))}
      </nav>

      <CoachButton />
    </>
  )
}

/* ── Tab icons (simple SVG, sketch feel) ───────────────────────────── */

function TabIconDashboard({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="2" y="2" width="8" height="8" rx="2" stroke={c} strokeWidth="1.5" />
      <rect x="12" y="2" width="8" height="8" rx="2" stroke={c} strokeWidth="1.5" />
      <rect x="2" y="12" width="8" height="8" rx="2" stroke={c} strokeWidth="1.5" />
      <rect x="12" y="12" width="8" height="8" rx="2" stroke={c} strokeWidth="1.5" />
    </svg>
  )
}

function TabIconActivities({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="6" r="2.5" stroke={c} strokeWidth="1.5" />
      <path d="M7 11l2 2 4-4" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 19l2-4h8l2 4" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function TabIconMe({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="7" r="4" stroke={c} strokeWidth="1.5" />
      <path d="M4 20c1.4-4 4-6 7-6s5.6 2 7 6" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function TabIconPlan({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="3" y="2" width="16" height="18" rx="2" stroke={c} strokeWidth="1.5" />
      <line x1="7" y1="7"  x2="15" y2="7"  stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="7" y1="11" x2="15" y2="11" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="7" y1="15" x2="11" y2="15" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
