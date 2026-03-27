import Nav from '@/components/layout/Nav'
import Hero from '@/components/layout/Hero'
import Footer from '@/components/layout/Footer'

export default function Home() {
  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col">
        <Hero />
      </main>
      <Footer />
    </>
  )
}
