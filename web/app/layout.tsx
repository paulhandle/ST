import type { Metadata, Viewport } from 'next'
import { Kalam, Caveat } from 'next/font/google'
import './globals.css'

const kalam = Kalam({
  weight: ['300', '400', '700'],
  subsets: ['latin'],
  variable: '--font-hand',
  display: 'swap',
})

const caveat = Caveat({
  weight: ['400', '500', '700'],
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
    <html lang="zh-CN" className={`${kalam.variable} ${caveat.variable}`}>
      <body>{children}</body>
    </html>
  )
}
