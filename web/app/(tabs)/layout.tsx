'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import CoachButton from '@/components/CoachButton'

const TABS = [
  { href: '/dashboard', label: '概览', icon: TabIconDashboard },
  { href: '/today',     label: '今天', icon: TabIconToday },
  { href: '/week',      label: '本周', icon: TabIconWeek },
  { href: '/plan',      label: '计划', icon: TabIconPlan },
]

export default function TabsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <>
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

function TabIconToday({ active }: { active: boolean }) {
  const c = active ? 'var(--accent)' : 'var(--ink-faint)'
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect x="3" y="4" width="16" height="15" rx="2" stroke={c} strokeWidth="1.5" />
      <line x1="3" y1="8" x2="19" y2="8" stroke={c} strokeWidth="1.5" />
      <line x1="7" y1="2" x2="7" y2="6" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="15" y1="2" x2="15" y2="6" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="11" cy="14" r="2" fill={c} />
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
