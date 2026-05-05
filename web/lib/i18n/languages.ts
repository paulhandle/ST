export type Language = 'en' | 'zh'

export const LANGUAGES: Language[] = ['en', 'zh']

export function isLanguage(value: string | null | undefined): value is Language {
  return value === 'en' || value === 'zh'
}

export function languageFromBrowser(): Language {
  if (typeof navigator === 'undefined') return 'en'
  return navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en'
}
