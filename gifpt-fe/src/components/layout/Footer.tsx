'use client'

export default function Footer() {
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
          © 2024 GIFPT Celestial Workshop. All rights reserved.
        </div>
        <div
          className="flex items-center space-x-8 text-xs uppercase tracking-widest"
          style={{ fontFamily: 'var(--font-inter)' }}
        >
          {['Docs', 'Github', 'Discord'].map((link) => (
            <a
              key={link}
              href="#"
              className="transition-colors duration-200"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--secondary)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)' }}
            >
              {link}
            </a>
          ))}
        </div>
      </div>
    </footer>
  )
}
