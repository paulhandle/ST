import { describe, expect, it } from 'vitest'
import manifest from '@/public/manifest.json'

describe('web app manifest', () => {
  it('uses the compact P squared icon', () => {
    expect(manifest.icons).toContainEqual({
      src: '/icons/pp-icon.svg',
      sizes: 'any',
      type: 'image/svg+xml',
      purpose: 'any maskable',
    })
    expect(manifest.theme_color).toBe('#070707')
  })
})
