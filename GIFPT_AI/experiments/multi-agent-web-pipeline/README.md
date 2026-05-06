# Multi-agent web animation pipeline (PoC for "갈래 2")

Replaces the Manim render layer with a multi-agent + web-stack approach inspired
by Google Research's [PaperVizAgent](https://github.com/google-research/papervizagent),
adapted for *animated* output instead of static figures.

## What it does

```
paper.md
   │
   ▼ ┌─────────────┐
     │   Planner   │ → scene_plan.json   (5–8 step animation skeleton)
     └─────────────┘
   │
   ▼ ┌─────────────┐
     │ Visualizer  │ → animation.html    (single file: SVG + GSAP via CDN)
     └─────────────┘
   │
   ▼ ┌─────────────────────────┐
     │  Render + self-heal     │ → video.webm
     │  (Playwright, ≤3 retry) │
     └─────────────────────────┘
```

Each agent is a `gpt-4o` call with its own system prompt. The Visualizer is the
expensive one (long output); Planner is a JSON-mode call that constrains structure.

The self-heal loop captures Playwright `console.error` and `pageerror` events
during render, sends them back to a fixer LLM call, and retries — analogous to
how `scripts/cherrypick_run.py` self-heals Manim render failures.

## Why this exists

Pipeline A (existing) — `paper.md` → gpt-4o → Manim Python code → render → mp4.
Pipeline B (this)   — `paper.md` → gpt-4o (×2 agents) → SVG+GSAP HTML → headless Chromium → webm.

Same input, same model. **Only the substrate differs.** That's the comparison
the user asked for: which substrate produces a higher-quality educational
animation when both are auto-generated end-to-end.

## Run it

### One-time setup
```bash
cd GIFPT_AI/experiments/multi-agent-web-pipeline

# Python deps
pip install -r requirements.txt

# Node deps (for record.mjs)
npm install
npx playwright install chromium

# API key — pipeline.py auto-loads `.env` from this directory at startup.
# Either create one here:
echo "OPENAI_API_KEY=sk-..." > .env
# …or symlink the existing project .env:
ln -s ../../.env .env
# …or just export it before running:
export OPENAI_API_KEY=sk-...
```

### Generate a video

```bash
python pipeline.py papers/speculative-decoding.md
```

Output ends up at `runs/<timestamp>/`:

```
runs/20260506-1430/
├── speculative-decoding.md       # input copy
├── scene_plan.json               # Planner output
├── animation.html                # Visualizer output
├── video.webm                    # final render
├── heal_1.html                   # (if self-heal triggered)
└── console_errors_1.json         # (errors that triggered the heal)
```

Convert WebM → MP4 / GIF with ffmpeg:
```bash
RUN=runs/20260506-1430
ffmpeg -i $RUN/video.webm -c:v libx264 -pix_fmt yuv420p $RUN/video.mp4
ffmpeg -i $RUN/video.webm -vf "fps=15,scale=960:-1:flags=lanczos" $RUN/video.gif
```

### Switch model (later, when revisiting Gemini)
```bash
PIPELINE_B_MODEL=gemini-3-pro-preview python pipeline.py papers/speculative-decoding.md
```
(Currently the OpenAI client path is the only one wired up; Gemini wiring is a
follow-up if/when we want to mirror PaperVizAgent's stack faithfully.)

## Run the Manim baseline on the same paper

To get a side-by-side, feed the same paper to the existing Manim path:

```bash
cd GIFPT_AI
SLOT=cherrypick/spec-decoding/v01
mkdir -p $SLOT
cp experiments/multi-agent-web-pipeline/papers/speculative-decoding.md $SLOT/prompt.txt
# (optionally tweak prompt.txt to match the cherry-pick prompt style)
python -m scripts.cherrypick_run $SLOT
# → $SLOT/video.mp4
```

Open both videos and judge:

| Dimension | Look for |
|-----------|----------|
| Pedagogical clarity | Does each step make the math/intuition obvious? |
| Layout discipline | No overlaps, consistent spacing |
| Visual polish | Typography, color, motion easing |
| Pacing | Each beat lands but doesn't drag |
| Failure mode | Anything broken / off-screen / mistimed |
| Render reliability | How many self-heal rounds did each pipeline need? |

## Files

- `pipeline.py` — orchestrator (Planner → Visualizer → render → heal loop)
- `record.mjs` — Playwright capture, exposes `__animationDone__` polling contract
- `papers/speculative-decoding.md` — first paper input
- `runs/` — gitignored output directory

## Status

- [x] Planner agent
- [x] Visualizer agent
- [x] Self-heal loop
- [x] Playwright recorder
- [ ] First end-to-end run on speculative-decoding.md
- [ ] Side-by-side comparison vs Manim baseline
- [ ] Gemini provider adapter (deferred)
- [ ] Stylist + Critic agents (deferred — current PoC is Planner+Visualizer only)
