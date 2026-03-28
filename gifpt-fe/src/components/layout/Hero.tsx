'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'
import { Link } from '@/i18n/navigation'
import { useAnimate } from '@/hooks/useAnimate'
import { useAuth } from '@/context/AuthContext'

type Mode = 'name' | 'describe'

const NAME_CHIPS = ['Binary Search', 'Quick Sort', 'A* Pathfinding']
const DESCRIBE_CHIPS = [
  {
    label: 'S3FIFO Cache Eviction',
    text: 'S3FIFO Cache Eviction\n\nThree FIFO queues: Small, Main, Ghost.\n1. New items enter Small queue\n2. On cache hit in Small → promote to Main\n3. On eviction from Small → if accessed, move to Main; else move to Ghost\n4. Ghost tracks recently evicted keys to filter one-hit wonders',
  },
  {
    label: 'Raft Leader Election',
    text: 'Raft Leader Election\n\nNodes start as Followers with random election timeout.\n1. Timeout expires → become Candidate, increment term, vote for self\n2. Send RequestVote RPC to all other nodes\n3. If majority votes received → become Leader\n4. Leader sends periodic heartbeats to maintain authority\n5. If higher term discovered → step down to Follower',
  },
  {
    label: 'LSM-Tree Compaction',
    text: 'LSM-Tree Compaction\n\n1. Writes go to in-memory MemTable\n2. When MemTable is full → flush to Level 0 SSTable on disk\n3. Level 0 SSTables may overlap → merge-sort into Level 1\n4. Each level has size limit (10x previous)\n5. When level exceeds limit → pick SSTable, merge with overlapping SSTables in next level\n6. Result: sorted, non-overlapping SSTables at each level',
  },
]

export default function Hero() {
  const t = useTranslations('hero')
  const te = useTranslations('errors')
  const { auth } = useAuth()
  const [mode, setMode] = useState<Mode>('name')
  const [nameInput, setNameInput] = useState('')
  const [describeInput, setDescribeInput] = useState('')
  const token = auth.status === 'authenticated' ? auth.token : null
  const { state, animate, reset } = useAnimate(token)

  const isSubmitting =
    state.phase === 'loading' ||
    state.phase === 'pending' ||
    state.phase === 'running'

  function submitAnimation() {
    if (mode === 'name') {
      const trimmed = nameInput.trim()
      if (!trimmed) return
      animate(trimmed)
    } else {
      const trimmed = describeInput.trim()
      if (!trimmed) return
      const firstLine = trimmed.split('\n')[0].trim()
      animate(firstLine || trimmed.slice(0, 64), trimmed)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    submitAnimation()
  }

  function handleDescribeKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Ctrl/Cmd+Enter to submit in describe mode
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !isSubmitting) {
      e.preventDefault()
      submitAnimation()
    }
  }

  function handleNameKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !isSubmitting) {
      e.preventDefault()
      submitAnimation()
    }
  }

  function switchMode(m: Mode) {
    if (state.phase !== 'idle' && state.phase !== 'error' && state.phase !== 'login_required') return
    setMode(m)
  }

  return (
    <>
      {/* ── Hero section ── */}
      <section className="relative min-h-screen pt-20 flex flex-col items-center justify-center overflow-hidden">
        {/* Background elements */}
        <div className="absolute inset-0 pointer-events-none">
          <div
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: 'radial-gradient(#464554 1px, transparent 1px)',
              backgroundSize: '40px 40px',
            }}
          />
          <svg className="absolute top-0 left-0 w-full h-full opacity-10" preserveAspectRatio="none" viewBox="0 0 1000 1000">
            <path d="M0,500 Q250,400 500,500 T1000,500" fill="transparent" stroke="var(--primary)" strokeWidth="0.5" />
            <path d="M0,300 Q250,600 500,300 T1000,300" fill="transparent" stroke="var(--secondary)" strokeWidth="0.5" />
          </svg>
        </div>

        {/* Hero content */}
        <div className="relative z-10 w-full max-w-4xl px-8 text-center">
          {/* Badge */}
          <div
            className="inline-flex items-center space-x-2 px-3 py-1 rounded-full mb-8"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid rgba(70,69,84,0.15)',
            }}
          >
            <span
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ background: 'var(--secondary)' }}
            />
            <span
              className="text-xs uppercase tracking-widest"
              style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--text-secondary)' }}
            >
              Celestial Workshop v2.0
            </span>
          </div>

          {/* Headline */}
          <h1
            className="hero-text-gradient font-black text-5xl md:text-7xl lg:text-8xl tracking-tighter mb-8 leading-tight"
            style={{ fontFamily: 'var(--font-manrope)' }}
          >
            {t('title')}
          </h1>

          {/* Subtitle */}
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto mb-12 leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}
          >
            {mode === 'name' ? t('subtitle') : t('subtitle_describe')}
          </p>

          {/* Input area */}
          <div className="relative w-full max-w-2xl mx-auto group">
            {/* Glow effect */}
            <div
              className="absolute -inset-1 rounded-xl blur-xl opacity-0 group-focus-within:opacity-100 transition duration-500"
              style={{ background: mode === 'name'
                ? 'linear-gradient(to right, rgba(192,193,255,0.2), rgba(221,183,255,0.2))'
                : 'linear-gradient(to right, rgba(221,183,255,0.25), rgba(192,193,255,0.15))'
              }}
            />

            <div
              className="relative rounded-xl shadow-2xl overflow-hidden"
              style={{
                background: 'var(--bg-lowest)',
                border: '1px solid rgba(70,69,84,0.15)',
              }}
            >
              {/* ── Mode tabs ── */}
              <div className="flex border-b" style={{ borderColor: 'rgba(70,69,84,0.15)' }}>
                <button
                  type="button"
                  onClick={() => switchMode('name')}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-all duration-200"
                  style={{
                    fontFamily: 'var(--font-space-grotesk)',
                    color: mode === 'name' ? 'var(--primary)' : 'var(--text-muted)',
                    background: mode === 'name' ? 'rgba(128,131,255,0.06)' : 'transparent',
                    borderBottom: mode === 'name' ? '2px solid var(--primary)' : '2px solid transparent',
                  }}
                >
                  <span className="material-symbols-outlined text-lg">search</span>
                  {t('tab_name')}
                </button>
                <button
                  type="button"
                  onClick={() => switchMode('describe')}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-all duration-200"
                  style={{
                    fontFamily: 'var(--font-space-grotesk)',
                    color: mode === 'describe' ? 'var(--secondary)' : 'var(--text-muted)',
                    background: mode === 'describe' ? 'rgba(221,183,255,0.06)' : 'transparent',
                    borderBottom: mode === 'describe' ? '2px solid var(--secondary)' : '2px solid transparent',
                  }}
                >
                  <span className="material-symbols-outlined text-lg">code</span>
                  {t('tab_describe')}
                </button>
              </div>

              {/* ── Input body ── */}
              <form onSubmit={handleSubmit} className="flex flex-col">
                {mode === 'name' ? (
                  /* Name mode: single-line input */
                  <div className="flex items-center gap-3 px-5 py-4">
                    <input
                      type="text"
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                      onKeyDown={handleNameKeyDown}
                      placeholder={t('placeholder_name')}
                      disabled={isSubmitting}
                      className="flex-1 bg-transparent border-none outline-none text-base"
                      style={{
                        color: 'var(--text-primary)',
                        fontFamily: 'var(--font-inter)',
                      }}
                    />
                    <button
                      type="submit"
                      disabled={isSubmitting || !nameInput.trim()}
                      className="action-gradient font-black px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all duration-300 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{
                        fontFamily: 'var(--font-manrope)',
                        color: 'var(--on-primary)',
                        boxShadow: isSubmitting ? 'none' : '0 0 24px rgba(128,131,255,0.2)',
                      }}
                    >
                      <span>{isSubmitting ? t('animating') : t('cta')}</span>
                      <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>bolt</span>
                    </button>
                  </div>
                ) : (
                  /* Describe mode: textarea + submit */
                  <>
                    <textarea
                      value={describeInput}
                      onChange={(e) => setDescribeInput(e.target.value)}
                      onKeyDown={handleDescribeKeyDown}
                      placeholder={t('placeholder_describe')}
                      disabled={isSubmitting}
                      rows={6}
                      className="w-full bg-transparent border-none outline-none px-5 py-4 text-sm resize-none"
                      style={{
                        color: 'var(--text-primary)',
                        fontFamily: 'var(--font-jetbrains-mono)',
                        lineHeight: '1.7',
                      }}
                    />
                    <div
                      className="flex items-center justify-between px-5 py-3 border-t"
                      style={{ borderColor: 'rgba(70,69,84,0.1)' }}
                    >
                      <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-inter)' }}>
                        {t('describe_hint')}
                      </span>
                      <button
                        type="submit"
                        disabled={isSubmitting || !describeInput.trim()}
                        className="font-black px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all duration-300 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                          fontFamily: 'var(--font-manrope)',
                          background: 'var(--secondary)',
                          color: 'var(--on-primary)',
                          boxShadow: isSubmitting ? 'none' : '0 0 24px rgba(221,183,255,0.2)',
                        }}
                      >
                        <span>{isSubmitting ? t('animating') : t('cta')}</span>
                        <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
                      </button>
                    </div>
                  </>
                )}
              </form>
            </div>
          </div>

          {/* Chips — change based on mode */}
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {mode === 'name' ? (
              <>
                <span
                  className="text-xs uppercase tracking-wider self-center mr-2"
                  style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--text-muted)' }}
                >
                  {t('quick_start')}
                </span>
                {NAME_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => setNameInput(chip)}
                    className="px-4 py-1.5 rounded-full text-sm transition-colors"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid rgba(70,69,84,0.1)',
                      color: 'var(--text-secondary)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--primary)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
                  >
                    {chip}
                  </button>
                ))}
              </>
            ) : (
              <>
                <span
                  className="text-xs uppercase tracking-wider self-center mr-2"
                  style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--secondary)' }}
                >
                  {t('examples')}
                </span>
                {DESCRIBE_CHIPS.map((chip) => (
                  <button
                    key={chip.label}
                    onClick={() => setDescribeInput(chip.text)}
                    className="px-4 py-1.5 rounded-full text-sm transition-colors"
                    style={{
                      background: 'rgba(221,183,255,0.06)',
                      border: '1px solid rgba(221,183,255,0.15)',
                      color: 'var(--text-secondary)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--secondary)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
                  >
                    {chip.label}
                  </button>
                ))}
              </>
            )}
          </div>

          {/* Status / result area */}
          {(state.phase === 'loading' || state.phase === 'pending' || state.phase === 'running') && (
            <p className="mt-8 text-sm animate-pulse" style={{ color: mode === 'name' ? 'var(--primary)' : 'var(--secondary)' }}>
              {state.phase === 'loading' && t('status_loading')}
              {state.phase === 'pending' && t('status_pending')}
              {state.phase === 'running' && t('status_running')}
            </p>
          )}

          {state.phase === 'success' && (
            <div className="mt-10 w-full flex flex-col items-center gap-4">
              {state.cached && (
                <span
                  className="text-xs font-mono px-3 py-1 rounded-full"
                  style={{ background: 'var(--bg-surface)', border: '1px solid rgba(70,69,84,0.3)', color: 'var(--text-muted)' }}
                >
                  cached
                </span>
              )}
              <video
                src={state.videoUrl}
                controls autoPlay loop
                className="w-full rounded-2xl"
                style={{ background: 'var(--bg-surface)', maxHeight: '420px', border: '1px solid rgba(70,69,84,0.3)' }}
              />
              <button onClick={reset} className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {t('try_another')}
              </button>
            </div>
          )}

          {state.phase === 'login_required' && (
            <div
              className="mt-8 inline-flex flex-col items-center gap-4 px-6 py-5 rounded-2xl"
              style={{ background: 'var(--bg-surface)', border: '1px solid rgba(70,69,84,0.3)' }}
            >
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{te('login_required')}</p>
              <div className="flex gap-2">
                <Link
                  href="/login"
                  className="h-10 px-5 flex items-center text-sm rounded-xl font-bold"
                  style={{ background: 'var(--primary)', color: '#0d0096' }}
                >
                  {t('login')}
                </Link>
                <button
                  onClick={reset}
                  className="h-10 px-5 text-sm rounded-xl"
                  style={{ border: '1px solid rgba(70,69,84,0.3)', color: 'var(--text-secondary)' }}
                >
                  {t('cancel')}
                </button>
              </div>
            </div>
          )}

          {state.phase === 'error' && (
            <div className="mt-8 flex flex-col items-center gap-3">
              <p className="text-sm" style={{ color: 'var(--error)' }}>
                {state.message === 'timeout' ? te('timeout') : te('generation_failed')}
              </p>
              <button onClick={reset} className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {t('try_again')}
              </button>
            </div>
          )}
        </div>
      </section>

      {/* ── Bento grid ── */}
      <section className="w-full max-w-screen-2xl mx-auto px-8 mt-8 mb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 — Sorting Visualizer (col-span-2) */}
          <div
            className="md:col-span-2 relative overflow-hidden rounded-xl p-8 group"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
          >
            <span className="text-xs uppercase tracking-widest" style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--primary)' }}>
              Featured
            </span>
            <h3 className="text-3xl font-bold mt-4 mb-2" style={{ fontFamily: 'var(--font-manrope)' }}>
              Sorting Visualizer
            </h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '28rem' }}>
              Experience the rhythmic dance of data as it finds its place in the cosmic order.
            </p>

            {/* Algorithm bar chart visual */}
            <div
              className="mt-8 h-48 w-full rounded-lg overflow-hidden flex items-end justify-center gap-1.5 px-8 pb-6 transition-all duration-700"
              style={{ background: 'linear-gradient(160deg, #0d0d1e 0%, #111128 60%, #0f0f24 100%)' }}
            >
              {[38, 62, 28, 88, 52, 74, 24, 82, 44, 58, 70, 36, 92, 48].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t-sm transition-all duration-300"
                  style={{
                    height: `${h}%`,
                    background: i === 7 ? 'var(--primary)' : i === 3 ? 'var(--secondary)' : 'rgba(192,193,255,0.2)',
                  }}
                />
              ))}
            </div>
          </div>

          {/* Card 2 — AI Render Engine */}
          <div
            className="rounded-xl p-8 flex flex-col justify-between group"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
          >
            <div>
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center mb-6"
                style={{ background: 'rgba(221,183,255,0.1)' }}
              >
                <span className="material-symbols-outlined" style={{ color: 'var(--secondary)' }}>auto_awesome</span>
              </div>
              <h3 className="text-xl font-bold mb-2" style={{ fontFamily: 'var(--font-manrope)' }}>
                AI Render Engine
              </h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Generates Manim code from natural language prompts instantly.
              </p>
            </div>
            <div
              className="mt-8 pt-8 flex items-center justify-between"
              style={{ borderTop: '1px solid rgba(70,69,84,0.1)' }}
            >
              <span className="text-xs uppercase tracking-widest" style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--secondary)' }}>
                Learn More
              </span>
              <span className="material-symbols-outlined text-sm transition-transform group-hover:translate-x-1" style={{ color: 'var(--text-muted)' }}>
                arrow_forward
              </span>
            </div>
          </div>

          {/* Card 3 — Live Debugger */}
          <div
            className="rounded-xl p-8 flex flex-col justify-between group"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
          >
            <div>
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center mb-6"
                style={{ background: 'rgba(192,193,255,0.1)' }}
              >
                <span className="material-symbols-outlined" style={{ color: 'var(--primary)' }}>terminal</span>
              </div>
              <h3 className="text-xl font-bold mb-2" style={{ fontFamily: 'var(--font-manrope)' }}>
                Live Debugger
              </h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Step through your algorithm frame-by-frame with cinematic precision.
              </p>
            </div>
            <div
              className="mt-8 pt-8 flex items-center justify-between"
              style={{ borderTop: '1px solid rgba(70,69,84,0.1)' }}
            >
              <span className="text-xs uppercase tracking-widest" style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--primary)' }}>
                View Docs
              </span>
              <span className="material-symbols-outlined text-sm transition-transform group-hover:translate-x-1" style={{ color: 'var(--text-muted)' }}>
                arrow_forward
              </span>
            </div>
          </div>

          {/* Card 4 — Export to Cinematic 4K (col-span-2) */}
          <div
            className="md:col-span-2 rounded-xl overflow-hidden relative group"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
          >
            <div className="flex flex-col md:flex-row h-full">
              <div className="p-8 flex flex-col justify-center flex-1">
                <h3 className="text-2xl font-bold mb-4" style={{ fontFamily: 'var(--font-manrope)' }}>
                  Export to Cinematic 4K
                </h3>
                <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
                  High-fidelity exports for presentations, social media, or educational content. Professional quality, zero setup.
                </p>
                <div className="flex space-x-4">
                  {['H.264/HEVC', 'Transparent BG'].map((feat) => (
                    <div key={feat} className="flex items-center space-x-1">
                      <span className="material-symbols-outlined text-lg" style={{ color: 'var(--primary)', fontSize: '18px' }}>check_circle</span>
                      <span className="text-xs uppercase tracking-tighter" style={{ fontFamily: 'var(--font-space-grotesk)', color: 'var(--text-secondary)' }}>
                        {feat}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              {/* Cinematic gradient panel */}
              <div
                className="flex-1 min-h-48 relative overflow-hidden"
                style={{ background: 'var(--bg-elevated)' }}
              >
                <div
                  className="absolute inset-0 opacity-60 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background: 'linear-gradient(135deg, rgba(111,0,190,0.3) 0%, rgba(128,131,255,0.2) 40%, rgba(221,183,255,0.1) 100%)',
                  }}
                />
                <div
                  className="absolute inset-0"
                  style={{
                    backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 40px, rgba(192,193,255,0.03) 40px, rgba(192,193,255,0.03) 41px)',
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
