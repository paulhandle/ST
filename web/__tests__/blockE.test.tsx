import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ replace: vi.fn() }),
}))
vi.mock('next/link', () => ({
  default: ({ href, children, ...p }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    React.createElement('a', { href, ...p }, children),
}))
vi.mock('@/components/CoachButton', () => ({ default: () => null }))

import TabsLayout from '@/app/(tabs)/layout'

describe('Tab bar', () => {
  it('shows 运动 tab and no 今天 tab', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('运动')).toBeInTheDocument()
    expect(screen.queryByText('今天')).not.toBeInTheDocument()
  })

  it('shows 概览 本周 计划 tabs', () => {
    render(<TabsLayout><div /></TabsLayout>)
    expect(screen.getByText('概览')).toBeInTheDocument()
    expect(screen.getByText('本周')).toBeInTheDocument()
    expect(screen.getByText('计划')).toBeInTheDocument()
  })
})
