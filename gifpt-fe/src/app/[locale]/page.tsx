import { useTranslations } from 'next-intl'
import Nav from '@/components/layout/Nav'
import Hero from '@/components/layout/Hero'

export default function Home() {
  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col">
        <Hero />
      </main>
    </>
  )
}
