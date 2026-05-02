import { describe, it, expect } from 'vitest'
import { formatPace, formatTime, formatKm } from '@/lib/api/types'

describe('formatPace', () => {
  it('formats 360 sec/km as "6:00"', () => {
    expect(formatPace(360)).toBe('6:00')
  })

  it('returns "--" for null', () => {
    expect(formatPace(null)).toBe('--')
  })
})

describe('formatTime', () => {
  it('formats 3661 seconds as "1:01:01"', () => {
    expect(formatTime(3661)).toBe('1:01:01')
  })
})

describe('formatKm', () => {
  it('converts 10000 meters to "10.0"', () => {
    expect(formatKm(10000)).toBe('10.0')
  })

  it('returns "--" for null', () => {
    expect(formatKm(null)).toBe('--')
  })
})
