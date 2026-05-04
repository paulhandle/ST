import Link from 'next/link'

export default function EmptyPlanState() {
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center' }}>
      <div style={{ fontSize: 52, marginBottom: 16 }}>🏃</div>

      <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        Build your next training cycle
      </div>

      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
        Set a goal and generate a structured plan,
        <br />
        then track execution day by day.
      </div>

      <Link
        href="/plan/generate"
        style={{
          display: 'inline-block',
          padding: '14px 32px',
          background: 'var(--ink)',
          color: 'var(--paper)',
          borderRadius: 8,
          fontFamily: 'var(--font-hand)',
          fontSize: 16,
          textDecoration: 'none',
        }}
      >
        Generate plan →
      </Link>
    </div>
  )
}
