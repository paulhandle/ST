import type { Metadata, Viewport } from 'next'
import { Inter, Space_Grotesk } from 'next/font/google'
import { I18nProvider } from '@/lib/i18n/I18nProvider'
import './globals.css'

const inter = Inter({
  weight: ['400', '500', '600', '700', '800', '900'],
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const spaceGrotesk = Space_Grotesk({
  weight: ['500', '600', '700'],
  subsets: ['latin'],
  variable: '--font-data',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'PerformanceProtocol',
  description: 'Endurance training plans, execution tracking, device sync, and adaptive feedback for serious athletes.',
  manifest: '/manifest.json',
  icons: {
    icon: '/icons/pp-icon.svg',
    shortcut: '/icons/pp-icon.svg',
    apple: '/icons/pp-icon.svg',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#0a0a0a',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body>
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  )
}
