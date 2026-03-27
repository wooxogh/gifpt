'use client'

import { useState } from 'react'
import Nav from '@/components/layout/Nav'
import Footer from '@/components/layout/Footer'

const FILTERS = ['Trending', 'New', 'Most Viewed'] as const
type Filter = (typeof FILTERS)[number]

const MOCK_CARDS = [
  { id: 1, title: 'Bubble Sort Visualization', views: '12.4K', duration: '2:34', gradient: 'linear-gradient(135deg, #1a1a3e 0%, #3d1a78 50%, #6f00be 100%)' },
  { id: 2, title: 'Dijkstra\'s Algorithm', views: '8.7K', duration: '3:12', gradient: 'linear-gradient(135deg, #0d2137 0%, #0a4f7a 50%, #0083ff 100%)' },
  { id: 3, title: 'Merge Sort in Action', views: '6.2K', duration: '1:58', gradient: 'linear-gradient(135deg, #1a2e1a 0%, #1a5c2e 50%, #00be6f 100%)' },
  { id: 4, title: 'A* Pathfinding', views: '15.1K', duration: '4:05', gradient: 'linear-gradient(135deg, #2e1a1a 0%, #7a1a0a 50%, #ff5500 100%)' },
  { id: 5, title: 'Binary Search Tree', views: '5.3K', duration: '2:47', gradient: 'linear-gradient(135deg, #1a1a2e 0%, #4a1a7a 50%, #c0c1ff 100%)' },
  { id: 6, title: 'Heap Sort Breakdown', views: '3.8K', duration: '3:29', gradient: 'linear-gradient(135deg, #2e2a1a 0%, #7a6a0a 50%, #ffd700 100%)' },
  { id: 7, title: 'BFS & DFS Compared', views: '9.9K', duration: '5:01', gradient: 'linear-gradient(135deg, #1a2e2e 0%, #0a5a7a 50%, #00d4ff 100%)' },
  { id: 8, title: 'Quick Sort Deep Dive', views: '11.2K', duration: '3:55', gradient: 'linear-gradient(135deg, #2e1a2e 0%, #6a0a7a 50%, #dd00ff 100%)' },
]

export default function GalleryPage() {
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState<Filter>('Trending')
  const [hoveredCard, setHoveredCard] = useState<number | null>(null)

  const filtered = MOCK_CARDS.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <>
      <Nav />
      <main className="flex flex-1 flex-col pt-20">
        {/* ── Header ── */}
        <section className="relative pt-20 pb-16 px-8 text-center overflow-hidden">
          {/* Background glow */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse at 50% 0%, rgba(128, 131, 255, 0.12) 0%, transparent 70%)',
            }}
          />
          <div className="relative max-w-screen-2xl mx-auto">
            <div
              className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs uppercase tracking-widest mb-8"
              style={{
                background: 'rgba(128,131,255,0.08)',
                border: '1px solid rgba(128,131,255,0.2)',
                color: 'var(--primary)',
                fontFamily: 'var(--font-space-grotesk)',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: 'var(--primary)', boxShadow: '0 0 6px var(--primary)' }}
              />
              <span>Community Gallery</span>
            </div>

            <h1
              className="text-5xl md:text-7xl font-black tracking-tighter mb-6"
              style={{ fontFamily: 'var(--font-manrope)' }}
            >
              Algorithm{' '}
              <span className="hero-text-gradient">Artistry</span>
            </h1>
            <p
              className="text-lg max-w-xl mx-auto mb-12"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
            >
              Browse algorithm visualizations created by the community. Watch, learn, and get inspired.
            </p>

            {/* Search */}
            <div className="flex justify-center mb-8">
              <div
                className="relative w-full max-w-md"
                style={{
                  background: 'rgba(28,27,27,0.8)',
                  border: '1px solid rgba(70,69,84,0.3)',
                  borderRadius: '0.75rem',
                }}
              >
                <span
                  className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-xl select-none"
                  style={{ color: 'var(--text-muted)' }}
                >
                  search
                </span>
                <input
                  type="text"
                  placeholder="Search algorithms..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-transparent pl-11 pr-4 py-3 text-sm outline-none"
                  style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-inter)' }}
                />
              </div>
            </div>

            {/* Filter pills */}
            <div className="flex justify-center space-x-3">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  onClick={() => setActiveFilter(f)}
                  className="px-5 py-2 rounded-full text-sm font-medium transition-all duration-200"
                  style={
                    activeFilter === f
                      ? {
                          background: 'var(--primary)',
                          color: '#0d0096',
                          fontFamily: 'var(--font-space-grotesk)',
                        }
                      : {
                          background: 'rgba(28,27,27,0.8)',
                          border: '1px solid rgba(70,69,84,0.3)',
                          color: 'var(--text-muted)',
                          fontFamily: 'var(--font-space-grotesk)',
                        }
                  }
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* ── Grid ── */}
        <section className="px-8 pb-24 max-w-screen-2xl mx-auto w-full">
          {filtered.length === 0 ? (
            <p
              className="text-center py-24"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
            >
              No results for &ldquo;{search}&rdquo;
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {filtered.map((card) => (
                <div
                  key={card.id}
                  className="group cursor-pointer"
                  onMouseEnter={() => setHoveredCard(card.id)}
                  onMouseLeave={() => setHoveredCard(null)}
                >
                  {/* Thumbnail */}
                  <div
                    className="relative aspect-video rounded-xl overflow-hidden mb-3"
                    style={{
                      background: card.gradient,
                      border: '1px solid rgba(70,69,84,0.15)',
                    }}
                  >
                    {/* Decorative grid overlay */}
                    <div
                      className="absolute inset-0 opacity-10"
                      style={{
                        backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)',
                        backgroundSize: '20px 20px',
                      }}
                    />
                    {/* Play button */}
                    <div
                      className="absolute inset-0 flex items-center justify-center transition-opacity duration-200"
                      style={{ opacity: hoveredCard === card.id ? 1 : 0 }}
                    >
                      <div
                        className="flex items-center justify-center w-12 h-12 rounded-full"
                        style={{
                          background: 'rgba(192,193,255,0.15)',
                          backdropFilter: 'blur(8px)',
                          border: '1px solid rgba(192,193,255,0.3)',
                        }}
                      >
                        <span
                          className="material-symbols-outlined text-2xl"
                          style={{ color: 'var(--primary)', fontVariationSettings: "'FILL' 1" }}
                        >
                          play_arrow
                        </span>
                      </div>
                    </div>
                    {/* Duration badge */}
                    <div
                      className="absolute bottom-2 right-2 px-2 py-0.5 rounded text-xs font-medium"
                      style={{
                        background: 'rgba(14,14,14,0.8)',
                        color: 'var(--text-primary)',
                        fontFamily: 'var(--font-jetbrains-mono)',
                        backdropFilter: 'blur(4px)',
                      }}
                    >
                      {card.duration}
                    </div>
                  </div>
                  {/* Card info */}
                  <h3
                    className="text-sm font-semibold mb-1 transition-colors duration-200"
                    style={{
                      color: hoveredCard === card.id ? 'var(--primary)' : 'var(--text-primary)',
                      fontFamily: 'var(--font-manrope)',
                    }}
                  >
                    {card.title}
                  </h3>
                  <p
                    className="text-xs"
                    style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}
                  >
                    {card.views} views
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Load more */}
          {filtered.length > 0 && (
            <div className="flex justify-center mt-14">
              <button
                className="px-8 py-3 rounded-xl text-sm font-semibold transition-all duration-200 active:scale-95"
                style={{
                  background: 'rgba(28,27,27,0.8)',
                  border: '1px solid rgba(70,69,84,0.3)',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-space-grotesk)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(192,193,255,0.3)'
                  e.currentTarget.style.color = 'var(--primary)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(70,69,84,0.3)'
                  e.currentTarget.style.color = 'var(--text-secondary)'
                }}
              >
                View More Animations
              </button>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  )
}
