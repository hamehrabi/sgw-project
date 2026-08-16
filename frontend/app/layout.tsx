import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

import './globals.css'

// Self-hosted at build by next/font — an offline internal tool makes no runtime font
// request to anyone. One family, per the brief: the personality is carried by how Inter
// is set (weight, size, tabular numerals), not by a second face.
const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' })

export const metadata: Metadata = {
  title: 'SGW Resilience Platform',
  description: 'Ranks assets by risk and records decisions. It recommends; people decide.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  )
}
