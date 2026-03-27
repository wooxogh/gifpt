import { Manrope, Inter, Space_Grotesk, JetBrains_Mono } from 'next/font/google'
import { getLocale } from 'next-intl/server'
import './globals.css'

const manrope = Manrope({ variable: '--font-manrope', subsets: ['latin'], display: 'swap' })
const inter = Inter({ variable: '--font-inter', subsets: ['latin'], display: 'swap' })
const spaceGrotesk = Space_Grotesk({ variable: '--font-space-grotesk', subsets: ['latin'], display: 'swap' })
const jetbrainsMono = JetBrains_Mono({ variable: '--font-jetbrains-mono', subsets: ['latin'], display: 'swap' })

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale()

  return (
    <html
      lang={locale}
      className={`${manrope.variable} ${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} h-full`}
    >
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
        />
      </head>
      <body className="min-h-full flex flex-col" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
        {children}
      </body>
    </html>
  )
}
