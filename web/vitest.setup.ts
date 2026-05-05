import '@testing-library/jest-dom'
import React from 'react'
import { vi } from 'vitest'

vi.mock('@testing-library/react', async () => {
  const actual = await vi.importActual<typeof import('@testing-library/react')>('@testing-library/react')
  const { I18nProvider } = await import('./lib/i18n/I18nProvider')

  return {
    ...actual,
    render: (ui: React.ReactElement, options?: Parameters<typeof actual.render>[1]) =>
      actual.render(React.createElement(I18nProvider, null, ui), options),
  }
})
