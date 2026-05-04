import Link from 'next/link'

type BrandLogoProps = {
  href?: string
  compact?: boolean
  className?: string
}

export default function BrandLogo({ href, compact = false, className }: BrandLogoProps) {
  const content = (
    <span className={`brand-logo${compact ? ' brand-logo--compact' : ''}${className ? ` ${className}` : ''}`}>
      <span>Performance</span>
      <span>Protocol</span>
    </span>
  )

  if (href) {
    return (
      <Link href={href} style={{ color: 'inherit', textDecoration: 'none' }}>
        {content}
      </Link>
    )
  }

  return content
}
