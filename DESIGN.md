# GIFPT Design System

**Aesthetic:** Cinematic Dark — algorithm animations deserve a stage, not a whiteboard.
Every UI element recedes so the animation canvas commands full attention.

---

## Color Palette

| Role | Token | Hex | Usage |
|------|-------|-----|-------|
| Background | `bg-base` | `#0a0a0f` | Page background |
| Surface | `bg-surface` | `#13131a` | Cards, panels, nav |
| Surface elevated | `bg-elevated` | `#1c1c26` | Hover states, modals |
| Border | `border-subtle` | `#2a2a3a` | Dividers, input borders |
| Accent | `accent` | `#7c6af7` | Primary CTA, active states, highlights |
| Accent hover | `accent-hover` | `#9585f8` | Hover on accent elements |
| Accent glow | `accent-glow` | `rgba(124,106,247,0.15)` | Glow effects, focus rings |
| Text primary | `text-primary` | `#f0f0f5` | Headings, body copy |
| Text secondary | `text-secondary` | `#8888aa` | Labels, metadata, placeholders |
| Text muted | `text-muted` | `#555577` | Disabled states, timestamps |
| Success | `success` | `#4ade80` | GIF export complete, job success |
| Error | `error` | `#f87171` | Job failed, error states |
| Warning | `warning` | `#fbbf24` | Rate limit warning, cache miss |

---

## Typography

**Font family:** Geist (system UI quality, but designed for screens)
**Monospace:** Geist Mono (algorithm names, code snippets, job IDs)

Install: `next/font/google` with `Geist` and `Geist_Mono`

| Scale | Size | Weight | Line height | Use |
|-------|------|--------|-------------|-----|
| `text-hero` | 3rem / 48px | 700 | 1.1 | Hero headline |
| `text-heading` | 1.5rem / 24px | 600 | 1.3 | Section headings |
| `text-subheading` | 1.125rem / 18px | 500 | 1.4 | Card titles, nav items |
| `text-body` | 1rem / 16px | 400 | 1.6 | Body copy |
| `text-small` | 0.875rem / 14px | 400 | 1.5 | Labels, badges, metadata |
| `text-mono` | 0.875rem / 14px | 400 | 1.5 | Algorithm names, IDs |

---

## Spacing System

Base unit: `4px`. Use Tailwind scale directly.

Key values: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128 / 160`

---

## Components

### Input (Algorithm Name Entry)
- Background: `bg-surface`
- Border: `border-subtle` → `accent` on focus
- Focus ring: `accent-glow` shadow (4px spread)
- Font: Geist Mono for the input value
- Border radius: `12px`
- Height: `56px` (desktop), `48px` (mobile)
- Send button: `accent` background, same height as input

### Canvas
- Background: `bg-surface`
- Border radius: `16px`
- Aspect ratio: `16:9`
- Max width: `900px`
- Border: `1px solid border-subtle`
- Loading state: pulsing `accent-glow` border animation

### Timeline Controls
- Scrubber track: `bg-elevated`
- Scrubber fill: `accent`
- Control icons: `text-secondary` → `text-primary` on hover
- Play/pause: icon button, `40px` touch target

### Buttons

| Variant | Background | Text | Border | Use |
|---------|-----------|------|--------|-----|
| Primary | `accent` | `white` | — | Generate, Export GIF |
| Secondary | `bg-elevated` | `text-primary` | `border-subtle` | Secondary actions |
| Ghost | transparent | `text-secondary` | — | Nav links, tertiary |
| Danger | `#7f1d1d` | `#fca5a5` | — | Delete, destructive |

Border radius: `8px`. Height: `40px` standard, `48px` large.

### Badges

```
Status badges — pill shape (border-radius: 9999px), 6px vertical padding
- processing: accent bg at 20% opacity, accent text
- done: success bg at 20% opacity, success text
- failed: error bg at 20% opacity, error text
- cached: border-subtle bg, text-secondary
```

### Cards (Gallery)
- Background: `bg-surface`
- Border: `1px solid border-subtle`
- Border radius: `12px`
- Hover: lift + `border-subtle` → `accent` at 40% opacity
- Thumbnail: `16:9` ratio, `bg-elevated` placeholder
- Padding: `12px`

### GIF Export Moment
- Full-screen overlay: `rgba(0,0,0,0.85)` backdrop blur
- Card: `bg-surface` with `accent-glow` border glow
- Confetti effect or `accent` particle burst
- Download button: Large Primary variant
- Share button: Secondary variant

---

## Motion Principles

**Philosophy:** Motion serves function. Never animate for decoration.

| Interaction | Duration | Easing | Notes |
|-------------|----------|--------|-------|
| Button hover | 150ms | ease-out | Scale 1.0→1.02, bg shift |
| Page transitions | 200ms | ease-in-out | Fade only |
| Canvas loading | — | — | Pulsing border glow, not spinner |
| Job status poll | 500ms | — | Smooth status badge transition |
| GIF export | 300ms | ease-out | Card appears with scale 0.95→1.0 |
| Gallery items | 100ms stagger | ease-out | Load from bottom on mount |

**Avoid:** bounce, elastic, overshoot on functional elements. Reserve expressive motion for the GIF export moment only.

---

## Layout

**Nav:** Fixed top, `bg-surface` with bottom `border-subtle`. Height `64px`.
Left: GIFPT wordmark (Geist Mono, `text-subheading`, accent color).
Right: Login button (Ghost), Generate button (Primary, hidden when already on home).

**Home:**
- Centered column, max-width `640px` for input
- Below input: recent public animations (horizontal scroll on mobile)

**Animation Page:**
- Two-column on desktop: canvas (70%) + sidebar (30%)
- Single column on mobile: canvas top, controls below
- Sidebar: job status, parameter summary, share/export actions

**Gallery:**
- Grid: 3 columns desktop, 2 tablet, 1 mobile
- Filter bar: algorithm domain chips (Sorting, Graph, DP, etc.)

---

## Tailwind Config

```js
// tailwind.config.ts — extend with:
theme: {
  extend: {
    colors: {
      base: '#0a0a0f',
      surface: '#13131a',
      elevated: '#1c1c26',
      subtle: '#2a2a3a',
      accent: {
        DEFAULT: '#7c6af7',
        hover: '#9585f8',
        glow: 'rgba(124,106,247,0.15)',
      },
    },
    fontFamily: {
      sans: ['var(--font-geist-sans)'],
      mono: ['var(--font-geist-mono)'],
    },
    borderRadius: {
      card: '12px',
      canvas: '16px',
      input: '12px',
    },
  }
}
```

---

## Accessibility

- Color contrast: `text-primary` on `bg-base` = 14:1. `text-secondary` on `bg-base` = 4.8:1 (WCAG AA).
- `accent` on `bg-base` = 4.6:1 (WCAG AA for large text / UI components).
- All interactive elements: visible focus ring using `accent-glow` shadow.
- Canvas: `role="img"` with `aria-label` describing the algorithm being animated.
- Keyboard: Space/K = play/pause, Left/Right = scrub 5s, F = fullscreen.

---

## File Organization (gifpt-fe)

```
src/
  app/                     # Next.js App Router pages
  components/
    ui/                    # Primitives: Button, Badge, Input, Card
    canvas/                # AnimationCanvas, Timeline, Controls
    gallery/               # GalleryGrid, GalleryCard
    layout/                # Nav, Footer
  lib/
    api.ts                 # Spring Boot API client
    hooks/                 # useJob, useGallery
  styles/
    globals.css            # CSS variables + Tailwind base
```

---

---

## Internationalization (i18n)

**Default language:** English (`en`)
**Supported languages:** English (`en`), Korean (`ko`)
**Library:** `next-intl`

### Language Switcher
- Location: Nav, right side — before login button
- UI: `EN | KO` text toggle (Ghost button style, `text-secondary` inactive, `text-primary` active)
- Persists via cookie (`NEXT_LOCALE`) — survives page refresh
- URL strategy: prefix routing (`/en/...`, `/ko/...`), default locale (`en`) has no prefix

### Message File Structure
```
gifpt-fe/
  messages/
    en.json    # English (default)
    ko.json    # Korean
```

### Key Namespaces
```json
{
  "nav": { "generate": "Generate", "gallery": "Gallery", "login": "Login" },
  "hero": {
    "title": "Animate any algorithm",
    "subtitle": "Type an algorithm name. Get a Manim animation in under 60 seconds.",
    "placeholder": "e.g. bubble sort, dijkstra, binary search tree...",
    "cta": "Animate"
  },
  "canvas": {
    "loading": "Rendering your animation...",
    "export": "Export GIF",
    "share": "Copy link"
  },
  "status": {
    "processing": "Processing",
    "done": "Done",
    "failed": "Failed",
    "cached": "Cached"
  },
  "errors": {
    "login_required": "Log in to generate new animations",
    "rate_limited": "Too many requests — try again in an hour"
  }
}
```

Korean (`ko.json`) mirrors the same structure with Korean values.

### Usage in Components
```tsx
import { useTranslations } from 'next-intl'

export function Hero() {
  const t = useTranslations('hero')
  return <h1>{t('title')}</h1>  // "Animate any algorithm" or "알고리즘을 애니메이션으로"
}
```

---

*Design system version 1.0 — established 2026-03-27*
*Consult this file before writing any new UI components.*
