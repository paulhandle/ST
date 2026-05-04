'use client'

import Link from 'next/link'
import { clearToken } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface SettingRow {
  label: string
  sub?: string
  href?: string
  onPress?: () => void
  accent?: boolean
}

export default function SettingsPage() {
  const router = useRouter()

  function logout() {
    clearToken()
    router.replace('/login')
  }

  const sections: { title: string; rows: SettingRow[] }[] = [
    {
      title: '训练',
      rows: [
        { label: '训练方法论', sub: '查看并切换 Skill', href: '/skills' },
        { label: '历史活动', sub: '所有跑步记录与状态', href: '/activities' },
      ],
    },
    {
      title: '数据',
      rows: [
        { label: 'COROS 同步', sub: '管理设备连接', href: '/settings/coros' },
      ],
    },
    {
      title: '账号',
      rows: [
        { label: '退出登录', accent: true, onPress: logout },
      ],
    },
  ]

  return (
    <div>
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--rule-soft)' }}>
        <div className="hand" style={{ fontSize: 20, fontWeight: 700 }}>设置</div>
      </div>

      {sections.map((section) => (
        <div key={section.title} style={{ marginBottom: 8 }}>
          <div className="hand text-faint" style={{ fontSize: 12, padding: '12px 16px 6px', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            {section.title}
          </div>

          <div style={{ borderTop: '1px solid var(--rule-soft)', borderBottom: '1px solid var(--rule-soft)' }}>
            {section.rows.map((row, i) => {
              const inner = (
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '14px 16px',
                  borderBottom: i < section.rows.length - 1 ? '1px solid var(--rule-soft)' : 'none',
                  cursor: 'pointer',
                  background: 'var(--paper)',
                }}>
                  <div>
                    <div className="hand" style={{ fontSize: 15, color: row.accent ? 'var(--accent)' : 'var(--ink)' }}>
                      {row.label}
                    </div>
                    {row.sub && (
                      <div className="annot text-faint" style={{ fontSize: 12, marginTop: 2 }}>{row.sub}</div>
                    )}
                  </div>
                  {row.href && (
                    <span className="hand text-faint" style={{ fontSize: 18 }}>›</span>
                  )}
                </div>
              )

              if (row.href) {
                return <Link key={row.label} href={row.href} style={{ textDecoration: 'none', display: 'block' }}>{inner}</Link>
              }
              return <div key={row.label} onClick={row.onPress}>{inner}</div>
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
