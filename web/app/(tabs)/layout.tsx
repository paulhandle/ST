'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import CoachButton from '@/components/CoachButton'
import BrandLogo from '@/components/BrandLogo'

const TABS = [
  { href: '/dashboard',  label: '概览', icon: TabIconDashboard },
  { href: '/activities', label: '运动', icon: TabIconActivities },
  { href: '/week',       label: '本周', icon: TabIconWeek },
  { href: '/plan',       label: '计划', icon: TabIconPlan },
]

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <>
      <div className="app-topbar">
        <BrandLogo href="/dashboard" compact />
        <Link href="/settings" className="app-topbar-link">Settings</Link>
      </div>

      <div className="page-shell">{children}</div>

      <nav className="tabbar">
        {TABS.map(({ href, label, icon: Icon }) => (
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

function TabIconWeek({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="2" y="5" width="18" height="15" rx="2" stroke={c} strokeWidth="1.5" />
      <line x1="2" y1="9" x2="20" y2="9" stroke={c} strokeWidth="1.2" />
      {[5, 8, 11, 14, 17].map((x) => (
        <line key={x} x1={x} y1="5" x2={x} y2="9" stroke={c} strokeWidth="1" />
      ))}
      <line x1="6" y1="2" x2="6" y2="6" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="16" y1="2" x2="16" y2="6" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
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
