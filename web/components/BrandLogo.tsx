import Link from 'next/link'

type BrandLogoProps = {
  href?: string
  compact?: boolean
  className?: string
}

export default function BrandLogo({ href, compact = false, className }: BrandLogoProps) {
  const content = (
    <span
      className={`brand-logo${compact ? ' brand-logo--compact' : ''}${className ? ` ${className}` : ''}`}
      aria-hidden={href ? true : undefined}
      aria-label={href ? undefined : 'PerformanceProtocol'}
    >
      {compact ? (
        <>
          <span className="brand-logo__p">P</span>
          <sup className="brand-logo__sup">2</sup>
        </>
      ) : (
        <>
          <span>Performance</span>
          <span>Protocol</span>
        </>
      )}
    </span>
  )

  if (href) {
    return (
      <Link href={href} aria-label="PerformanceProtocol" style={{ color: 'inherit', textDecoration: 'none' }}>
        {content}
      </Link>
    )
  }

  return content
}
