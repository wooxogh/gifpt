# Web Animation PoC — vs. Manim baseline

**Question being tested:** Can an LLM-generated web animation (SVG + GSAP, rendered via headless Chromium) produce higher-quality educational animations than auto-generated Manim — for the *same* concept, with the *same* prompt?

If yes → this is the path forward for `GIFPT_AI`'s render layer (replacing Manim with web stack + multi-agent orchestration à la PaperVizAgent).

If no → re-evaluate. Maybe img2vid (Veo / SVD) on PaperVizAgent stills is the better path.

---

## What's here

```
01_self_attention/
├── index.html          # 30s SVG + GSAP animation (single file, CDN deps)
├── record.mjs          # Playwright headless capture → WebM
├── package.json
└── .gitignore
```

The concept is **slot 01** from `scripts/cherrypick_attention.md`:
> Self-attention on 3 input tokens "the", "cat", "sat". Show tokens → embeddings → Q/K/V → Q·Kᵀ → softmax → ×V → output. ~30s.

This is a *hand-crafted* animation written by Claude in one pass, given the same problem statement that the cherry-pick Manim prompt targets. It is **not** the multi-agent pipeline yet — it's a "ceiling probe" to see whether the web stack can produce something visually credible. If a single-shot is already competitive with cherry-picked Manim v05, the multi-agent pipeline (Planner → Stylist → Visualizer → Critic) on top should comfortably exceed Manim auto-gen quality.

---

## Run it

### Preview in browser (instant)
```bash
open index.html
```
Animation auto-plays on load. Click `↻ replay` bottom-right to re-run.

### Record as video (for side-by-side comparison)
```bash
cd GIFPT_AI/experiments/web-anim-poc/01_self_attention
npm install
npx playwright install chromium
node record.mjs
# → output/self_attention.webm
```

Convert to MP4 / GIF (requires `ffmpeg`):
```bash
ffmpeg -i output/self_attention.webm -c:v libx264 -pix_fmt yuv420p output/self_attention.mp4
ffmpeg -i output/self_attention.webm -vf "fps=15,scale=960:-1:flags=lanczos" output/self_attention.gif
```

---

## How to evaluate

Open the produced video next to a Manim cherry-pick output (any of `cherrypick/attention/01_self_attention/v0?/video.mp4` once that workflow has been run). Score on:

| Dimension | What to look for |
|-----------|------------------|
| **Pedagogical clarity** | Does each step (1→6) make the underlying math obvious? |
| **Layout discipline** | No overlaps, consistent spacing, no chaotic re-layouts |
| **Visual polish** | Typography, color use, motion easing, glow/depth |
| **Pacing** | Each step has time to land but doesn't drag |
| **Information density** | Is the right amount on screen at each moment? |
| **Failure modes** | Does anything render broken / off-screen / mistimed? |

The honest verdict matters — if the web version isn't visibly better, the substrate change isn't worth doing.

---

## Why this stack

- **SVG** → crisp at any resolution, element-level access (perfect for Critic agent screenshots → diff)
- **GSAP** → declarative timeline, vastly more LLM training data than Manim API
- **Headless Chromium** → deterministic frame capture, well-supported in Python via Playwright (drops cleanly into existing Celery worker)
- **Single file** → portable, fast to iterate, easy to embed in `GIFPT_AI/studio/video_render.py` later

---

## Next steps if PoC succeeds

1. Define **scene JSON schema** — what does the Planner emit that Visualizer consumes?
2. Refactor one Visualizer agent prompt — JSON scene → React/SVG/GSAP code
3. Build a **Next.js renderer page** (`/render/[jobId]`) that takes scene JSON, animates, exposes `window.__animationDone__` for capture
4. Replace `GIFPT_AI/studio/video_render.py`'s Manim invocation with a Playwright call against the renderer page
5. Add Critic loop — render → screenshot → LLM eval → patch JSON → re-render
