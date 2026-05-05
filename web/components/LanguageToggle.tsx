'use client'

import type { Language } from '@/lib/i18n/languages'

export default function LanguageToggle({
  language,
  onChange,
  className,
  compact = false,
}: {
  language: Language
  onChange: (language: Language) => void
  className?: string
  compact?: boolean
}) {
  return (
    <div className={`language-toggle${compact ? ' language-toggle--compact' : ''}${className ? ` ${className}` : ''}`} aria-label="Language">
      <button
        type="button"
        className={language === 'en' ? 'active' : ''}
        onClick={() => onChange('en')}
      >
        EN
      </button>
      <button
        type="button"
        className={language === 'zh' ? 'active' : ''}
        onClick={() => onChange('zh')}
      >
        中文
      </button>
    </div>
  )
}
