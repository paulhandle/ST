import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

import HomePage from '@/app/page'

const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value },
  removeItem: (key: string) => { delete store[key] },
})

beforeEach(() => {
  Object.keys(store).forEach(key => delete store[key])
  document.cookie = 'pp_language=; max-age=0; path=/'
})

describe('HomePage i18n', () => {
  it('renders English homepage copy by default', () => {
    render(<HomePage />)
    expect(screen.getAllByText('Start Training').length).toBeGreaterThan(0)
    expect(screen.getByText('Workflow')).toBeInTheDocument()
  })

  it('switches homepage copy to Chinese', () => {
    render(<HomePage />)
    fireEvent.click(screen.getByRole('button', { name: '中文' }))

    expect(screen.getAllByText('开始训练').length).toBeGreaterThan(0)
    expect(screen.getByText('流程')).toBeInTheDocument()
  })
})
