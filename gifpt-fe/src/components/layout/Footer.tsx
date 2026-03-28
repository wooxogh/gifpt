'use client'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer
      className="w-full py-12"
      style={{
        background: 'var(--bg-lowest)',
        borderTop: '1px solid rgba(70,69,84,0.15)',
      }}
    >
      <div className="flex flex-col md:flex-row justify-between items-center px-8 w-full max-w-screen-2xl mx-auto space-y-4 md:space-y-0">
        <div
          className="text-xs uppercase tracking-widest"
          style={{ fontFamily: 'var(--font-inter)', color: 'var(--text-muted)' }}
        >
          © {year} GIFPT Celestial Workshop. All rights reserved.
        </div>
        <div
          className="flex items-center space-x-8 text-xs uppercase tracking-widest"
          style={{ fontFamily: 'var(--font-inter)' }}
        >
          <a
            href="https://github.com/wooxogh/gifpt"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors duration-200 hover:text-secondary focus-visible:text-secondary focus-visible:underline focus-visible:outline-none"
            style={{ color: 'var(--text-muted)' }}
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  )
}
