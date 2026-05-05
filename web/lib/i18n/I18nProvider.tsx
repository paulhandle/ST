'use client'

import { createContext, useContext, type ReactNode } from 'react'
import { useLanguage } from './useLanguage'
import type { Language } from './languages'
import { copy, type AppCopy } from './copy'

type I18nContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  t: AppCopy
}

const I18nContext = createContext<I18nContextValue | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const { language, setLanguage } = useLanguage()

  return (
    <I18nContext.Provider value={{ language, setLanguage, t: copy[language] }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const value = useContext(I18nContext)
  if (!value) {
    throw new Error('useI18n must be used inside I18nProvider')
  }
  return value
}
