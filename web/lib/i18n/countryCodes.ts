import type { Language } from './languages'

export type DialingRegion = {
  code: string
  sample: string
  minNationalDigits: number
  label: Record<Language, string>
}

export const DIALING_REGIONS: DialingRegion[] = [
  { code: '+86', sample: '138 0013 8000', minNationalDigits: 11, label: { en: 'China mainland', zh: '中国大陆' } },
  { code: '+1', sample: '415 555 2671', minNationalDigits: 10, label: { en: 'United States', zh: '美国' } },
  { code: '+44', sample: '7400 123456', minNationalDigits: 9, label: { en: 'United Kingdom', zh: '英国' } },
  { code: '+65', sample: '8123 4567', minNationalDigits: 8, label: { en: 'Singapore', zh: '新加坡' } },
  { code: '+852', sample: '5123 4567', minNationalDigits: 8, label: { en: 'Hong Kong SAR', zh: '中国香港' } },
  { code: '+886', sample: '912 345 678', minNationalDigits: 9, label: { en: 'Taiwan, China', zh: '中国台湾' } },
  { code: '+81', sample: '90 1234 5678', minNationalDigits: 9, label: { en: 'Japan', zh: '日本' } },
  { code: '+61', sample: '412 345 678', minNationalDigits: 9, label: { en: 'Australia', zh: '澳大利亚' } },
]

export function dialingRegionFor(code: string) {
  return DIALING_REGIONS.find(region => region.code === code) ?? DIALING_REGIONS[0]
}
