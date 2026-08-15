import type { Metadata } from 'next'

import './globals.css'

export const metadata: Metadata = {
  title: 'SGW Resilience Platform',
  description: 'Ranks assets by risk and records decisions. It recommends; people decide.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
