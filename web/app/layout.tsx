import type { Metadata, Viewport } from 'next'
import { Barlow_Condensed, Barlow } from 'next/font/google'
import './globals.css'

const barlowCondensed = Barlow_Condensed({
  weight: ['400', '600', '700'],
  subsets: ['latin'],
  variable: '--font-hand',
  display: 'swap',
})

const barlow = Barlow({
  weight: ['400', '500', '600'],
  subsets: ['latin'],
  variable: '--font-annot',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'ST · 跑步训练',
  description: '智能马拉松训练平台',
  manifest: '/manifest.json',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#fafaf6',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`${barlowCondensed.variable} ${barlow.variable}`}>
      <body>{children}</body>
    </html>
  )
}
