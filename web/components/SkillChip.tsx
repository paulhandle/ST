import Link from 'next/link'

interface Props {
  skill: { slug: string; name: string; version: string }
}

export default function SkillChip({ skill }: Props) {
  return (
    <Link href="/settings" className="skill-chip" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span className="skill-chip-avatar">赵</span>
      <span>{skill.name}</span>
      <span style={{ color: 'var(--ink-faint)', fontSize: 10, marginLeft: 2 }}>▾</span>
    </Link>
  )
}
