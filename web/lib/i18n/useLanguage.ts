'use client'

import { useEffect, useState } from 'react'
import { isLanguage, languageFromBrowser, type Language } from './languages'

const STORAGE_KEY = 'pp_language'
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365

function initialLanguage(): Language {
  if (typeof window === 'undefined') return 'en'
  const stored = typeof window.localStorage?.getItem === 'function'
    ? window.localStorage.getItem(STORAGE_KEY)
    : null
  if (isLanguage(stored)) return stored
  return languageFromBrowser()
}

export function useLanguage() {
  const [language, setLanguageState] = useState<Language>('en')

  useEffect(() => {
    setLanguageState(initialLanguage())
  }, [])

  function setLanguage(next: Language) {
    setLanguageState(next)
    if (typeof window === 'undefined') return
    if (typeof window.localStorage?.setItem === 'function') {
      window.localStorage.setItem(STORAGE_KEY, next)
    }
    document.cookie = `${STORAGE_KEY}=${next}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
  }

  return { language, setLanguage }
}
