# Multi-agent web animation pipeline (PoC for "갈래 2")

Replaces the Manim render layer with a multi-agent + web-stack approach inspired
by Google Research's [PaperVizAgent](https://github.com/google-research/papervizagent),
adapted for *animated* output instead of static figures.

## What it does

```
paper.md
   │
   ▼ ┌─────────────┐
     │   Planner   │ → scene_plan.json    (5–8 step animation skeleton)
     └─────────────┘
   │
   ▼ ┌─────────────┐
     │   Stylist   │ → styled_plan.json   (color semantics, layout, motion, typography)
     └─────────────┘
   │
   ▼ ┌─────────────┐
     │ Visualizer  │ → animation.html     (single file: SVG + GSAP via CDN)
     └─────────────┘
   │
   ▼ ┌─────────────────────────┐
     │  Render + self-heal     │ → video.webm + frame_0..4.png
     │  (Playwright, ≤3 retry) │
     └─────────────────────────┘
   │
   ▼ ┌─────────────┐
     │   Critic    │ → critic_N.json   (multimodal: looks at keyframes)
     └─────────────┘
   │
   ▼ ┌─────────────┐
     │   Revisor   │ → animation_vN.html
     └─────────────┘
   │
   └── loop until verdict=acceptable or --max-critic exhausted
```

Each stage is a separate LLM call with its own system prompt. The **Critic** is
multimodal — it receives N keyframe screenshots from the latest render and emits
structured feedback (severity / category / suggested_fix). The **Revisor** is the
Visualizer agent on a revision round, taking the current HTML + Critic feedback
and emitting a corrected HTML.

The self-heal loop captures Playwright `console.error` and `pageerror` events
during render, sends them back to a Healer LLM call, and retries — analogous to
how `scripts/cherrypick_run.py` self-heals Manim render failures. JS-fatal errors
trigger heal; timeout-only (animation played but didn't signal completion) is
treated as a *degraded success* and passed to Critic anyway.

## Why this exists

- **Pipeline A** (existing) — `paper.md` → LLM → Manim Python code → render → mp4
- **Pipeline B** (this)     — `paper.md` → multi-agent LLMs → SVG+GSAP HTML → headless Chromium → webm

Same input, isolated substrate variable. The user judges side-by-side videos
and decides whether the web stack + multi-agent orchestration produces higher-
quality educational animations than auto-generated Manim.

## Provider / model selection

`pipeline.py` supports both Google Gemini and OpenAI. Both have multimodal
support (Gemini Vision and OpenAI Vision via image_url parts), so the Critic
loop works across providers.

| `PIPELINE_B_MODEL` value | Provider | Required env | Notes |
|---|---|---|---|
| `gemini-2.5-pro` *(default)* | Google | `GOOGLE_API_KEY` | Requires Google Cloud billing (free tier limit is 0) |
| `gemini-2.5-flash` | Google | `GOOGLE_API_KEY` | Free tier 20 req/day |
| `gemini-2.5-flash-lite` | Google | `GOOGLE_API_KEY` | Free tier 20 req/day, weaker but JSON-stable |
| `gemini-3-pro-preview` | Google | `GOOGLE_API_KEY` | PaperVizAgent's published config |
| `gpt-4o` | OpenAI | `OPENAI_API_KEY` | Matches existing Manim pipeline's model — fairest A/B |

`pipeline.py` auto-loads `.env` from this directory first, then `GIFPT_AI/.env`,
without an external dotenv dependency.

## Run it

### One-time setup
```bash
cd GIFPT_AI/experiments/multi-agent-web-pipeline

# Python deps (openai + google-genai + json-repair)
pip install -r requirements.txt

# Node deps (Playwright)
npm install
npx playwright install chromium

# API key — pick whichever provider you'll use:
echo "GOOGLE_API_KEY=..."  >> .env       # for Gemini default
# or
echo "OPENAI_API_KEY=sk-..." >> .env     # if you'll set PIPELINE_B_MODEL=gpt-4o

# (Either key can also live in GIFPT_AI/.env — the loader checks both.)
```

### Generate a video
```bash
# Default: gemini-2.5-pro (needs Google Cloud billing)
python pipeline.py papers/speculative-decoding.md

# Free tier:
PIPELINE_B_MODEL=gemini-2.5-flash       python pipeline.py papers/speculative-decoding.md

# OpenAI (matches existing Manim pipeline):
PIPELINE_B_MODEL=gpt-4o                 python pipeline.py papers/speculative-decoding.md
```

Useful flags:
```bash
--max-critic 0       # single-shot, skip refinement loop
--skip-stylist       # raw Planner output → Visualizer (test what Stylist adds)
--skip-critic        # render once, no refinement
--no-render          # produce HTML only, skip Playwright
```

### Output

Each run lands in `runs/<timestamp>/`:
```
runs/20260506-1430/
├── speculative-decoding.md         # input copy
├── scene_plan.json                 # Planner output
├── styled_plan.json                # Stylist output
├── animation_v0.html               # initial Visualizer output
├── animation_v1.html               # after Critic round 1 + Revisor
├── animation_v2.html               # after Critic round 2 + Revisor
├── animation.html                  # latest (= last vN.html)
├── critic_1.json, critic_2.json    # structured feedback per round
├── frame_0.png .. frame_4.png      # keyframes used by Critic
├── video.webm                      # final render
├── heal_PHASE_N.html               # (if self-heal triggered)
└── console_errors_PHASE_N.json
```

Convert WebM → MP4 / GIF with ffmpeg:
```bash
RUN=runs/20260506-1430
ffmpeg -i $RUN/video.webm -c:v libx264 -pix_fmt yuv420p $RUN/video.mp4
ffmpeg -i $RUN/video.webm -vf "fps=15,scale=960:-1:flags=lanczos" $RUN/video.gif
```

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

- `pipeline.py` — orchestrator + agent prompts (Planner / Stylist / Visualizer / Critic / Revisor / Healer)
- `record.mjs` — Playwright capture; uses `pathToFileURL`, polls `__animationDone__`,
  snaps 5 keyframes at 4/14/24/34/44s, emits `console_errors.json`
- `papers/speculative-decoding.md` — first paper input
- `runs/` — gitignored output directory

## Status

- [x] Planner agent
- [x] **Stylist agent** (color semantics, layout, motion, typography)
- [x] Visualizer agent (initial + revision modes)
- [x] **Critic agent** (multimodal — keyframe analysis)
- [x] **Revisor loop** (Critic feedback → re-render, up to `--max-critic` rounds)
- [x] Self-heal loop (JS error → Healer LLM → retry)
- [x] Playwright recorder with keyframe capture
- [x] Multi-provider dispatcher (Gemini + OpenAI), both with multimodal
- [x] `json_repair` fallback for malformed JSON from weaker models
- [x] Transient 5xx retry with exponential backoff
- [x] First end-to-end run on speculative-decoding.md
- [ ] Pro-tier validation run (`gemini-2.5-pro` or `gemini-3-pro-preview`) —
      blocked on Google Cloud billing activation
- [ ] Side-by-side comparison vs Manim baseline (Pipeline A) at Pro tier
- [ ] Retriever agent (PaperVizAgent's 5th agent — would feed Planner with
      retrieved reference diagrams; out of scope for this PoC since we have
      no curated web-animation reference corpus)
