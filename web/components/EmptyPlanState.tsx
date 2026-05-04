import Link from 'next/link'

export default function EmptyPlanState() {
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center' }}>
      <div style={{ fontSize: 52, marginBottom: 16 }}>🏃</div>

      <div className="hand" style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        开始你的马拉松训练
      </div>

      <div className="hand text-faint" style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
        设定目标，我们为你生成专属计划，
        <br />
        每天追踪训练进度。
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
        生成训练计划 →
      </Link>
    </div>
  )
}
