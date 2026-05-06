#!/usr/bin/env python3
"""
Multi-agent web animation pipeline (PoC for "갈래 2").

Pipeline:
    paper.md
        → [Planner] scene_plan.json
        → [Visualizer] animation.html (SVG + GSAP, single file)
        → [Renderer + Self-heal] video.webm

Compare against the existing Manim pipeline (`scripts/cherrypick_run.py`)
fed the same paper as a prompt — both produce video, user judges side-by-side.

Usage:
    export OPENAI_API_KEY=sk-...
    cd GIFPT_AI/experiments/multi-agent-web-pipeline
    npm install                       # one-time, for record.mjs
    npx playwright install chromium   # one-time
    pip install -r requirements.txt   # one-time
    python pipeline.py papers/speculative-decoding.md

Output:
    runs/<timestamp>/
        paper.md
        scene_plan.json
        animation.html
        video.webm
        (+ heal_N.html, console_errors_N.json on retries)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
MAX_HEAL_DEFAULT = 3


def _load_env_file(path: Path) -> None:
    """Lightweight .env loader (no external dep). Existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("'\"")
        os.environ.setdefault(k, v)


_load_env_file(ROOT / ".env")               # local override (highest precedence)
_load_env_file(ROOT.parent.parent / ".env")  # GIFPT_AI/.env (project default)

# Default model — Gemini 2.5 Pro for quality (requires billing on Google Cloud).
# Fallback to flash via env if billing not enabled:
#   PIPELINE_B_MODEL=gemini-2.5-flash python pipeline.py ...
MODEL = os.getenv("PIPELINE_B_MODEL", "gemini-2.5-pro")
MAX_CRITIC_DEFAULT = 2


# ---------------------------------------------------------------------------
# Agent prompts
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """\
You are the Planner agent for an educational paper-visualization pipeline.

Given a method description from a research paper, produce a JSON scene plan that
specifies how to animate the core concept in a 45-60 second video.

Output STRICT JSON with this schema:
{
  "title": str,
  "subtitle": str,
  "duration_s": int,
  "steps": [
    {
      "step_num": int,
      "label": str,
      "duration_s": float,
      "description": str,
      "elements": [str],
      "key_insight": str
    }
  ],
  "visual_motifs": [str]
}

Rules:
- 5-8 steps total. Don't try to cover everything; pick THREE most important moments
  and surround them with setup and payoff.
- Animations must show CHANGE, not static facts. Prefer "X transforms into Y" over
  "X is described".
- The viewer is a CS undergrad familiar with neural networks. Don't oversimplify;
  don't dump jargon either.
- Each step should be visually distinct from the prior step.
- Output ONLY the JSON object, no markdown fences, no commentary.
"""


STYLIST_SYSTEM = """\
You are the Stylist agent. Given a scene plan and paper context, enrich the plan
with concrete visual styling decisions that the Visualizer must follow PRECISELY.

The goal is to remove all ambiguity from the Visualizer's job: every color, every
position, every motion should be decided here, not improvised at codegen time.

Output STRICT JSON, identical schema to the input plan plus a top-level "style"
field:

{
  ...all input fields preserved...,
  "style": {
    "color_semantics": {
      "<entity name from plan elements>": "<hex>",
      ...
    },
    "stage": {
      "background": "<hex>",
      "background_motif": "<short css description>",
      "safe_area_px": [<top>, <right>, <bottom>, <left>]
    },
    "typography": {
      "title":      {"family": "Geist Mono", "size": 18, "weight": 600, "color": "<hex>"},
      "step_label": {"family": "Geist Mono", "size": 13, "weight": 500, "color": "<hex>"},
      "math":       {"family": "Geist Mono", "size": 14, "weight": 400, "color": "<hex>"},
      "annotation": {"family": "Geist",      "size": 12, "weight": 400, "color": "<hex>"}
    },
    "motion": {
      "entrance": "<easing> <duration_s>",
      "exit":     "<easing> <duration_s>",
      "highlight":"<easing> <duration_s>",
      "stagger_default_s": <float>
    },
    "step_styles": [
      {
        "step_num": <int>,
        "summary": "<one-line visual recipe>",
        "key_elements": [
          {
            "name": "<matches a plan element name>",
            "shape": "rounded-rect" | "circle" | "matrix" | "vector" | "text" | "arrow",
            "position": "<center | top-left | bottom-right | (x,y) tuple in viewBox 1280x720>",
            "size_px": [<w>, <h>],
            "fill_color_token": "<key from color_semantics>",
            "z_layer": <0..10>
          }
        ],
        "annotations": [
          {"text": "<short caption>", "position": "<location>"}
        ],
        "transition_in": "<verb describing how this step enters from prior>"
      }
    ]
  }
}

Rules:
- Pick a palette where SEMANTIC pairs are visually distinct (e.g., M_p vs M_q must
  read as "different things instantly"). Anchor on the GIFPT design tokens
  (--accent #7c6af7, --success #4ade80, --warning #fbbf24, --error #f87171) but
  invent supporting colors as needed (4-6 entity colors total).
- Place at most 8 key elements per step — no more. Avoid clutter.
- Coordinates must respect safe area (default [80, 120, 80, 120]) and avoid overlap.
- Output ONLY the JSON.
"""


VISUALIZER_SYSTEM = """\
You are the Visualizer agent. Given a paper description and a fully styled scene
plan (Planner output enriched by the Stylist), output a complete single-file HTML
page that renders the animation using SVG + GSAP from CDN.

# Hard requirements

1. Output ONLY valid HTML. No markdown fences, no commentary, no surrounding text.
2. Single self-contained file. External resources allowed only via these CDNs:
   - GSAP: <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
   - Geist fonts: <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
3. Stage size: viewBox="0 0 1280 720", dark background.
4. Auto-play on load (after a 300ms delay so fonts settle).
5. **At the end of the timeline, set `window.__animationDone__ = true`.** The
   recorder polls this to know when capture is complete. This is mandatory.
6. Include a "↻ replay" button bottom-right that restarts the animation.
7. Use SVG <text> for all on-screen text (not HTML overlays) so capture is crisp.

# Follow the styled plan literally

The Stylist has already decided every color, position, easing, and stagger. Your
job is FAITHFUL TRANSLATION, not reinvention. Specifically:

- Use color_semantics: every element drawn for "M_p" must use the hex assigned to
  "M_p" in the styled plan's color_semantics. Same color across all steps for the
  same entity — color is identity.
- Use step_styles[i].key_elements: place those shapes at those positions with
  those sizes. Don't invent new shapes mid-step.
- Use motion: entrance/exit/highlight easings + stagger_default come from the
  styled plan. Don't override with your own preferences.
- Use typography: each text element uses one of the four typography roles
  (title / step_label / math / annotation) — pick the right role, don't mix.

If the styled plan is silent on a detail, default to the GIFPT cinematic dark
system (background #0a0a0f, surfaces #13131a/#1c1c26, accent #7c6af7,
success #4ade80, warning #fbbf24, error #f87171, text #f0f0f5/#8888aa/#555577).

# Visual motifs (defaults)

  - Radial gradient on stage background (top-bright → bottom-dark)
  - Cell fills via <linearGradient id="cellGrad">: #1c1c26 → #13131a
  - Active elements get filter: drop-shadow(0 0 8px rgba(124,106,247,0.4))
  - Arrows use <marker id="arrowhead"> with the styled palette
  - Step indicator top-left (mono, 13px, accent num + secondary label)
  - Title top-right (mono, 12px, muted, uppercase)

# Animation principles

- Each step: entrance (0.4-0.7s) → hold (0.5-1.5s) → exit before next phase
- Phases can replace prior content; don't keep everything visible forever
- Update the step indicator at the start of each step via gsap.call()
- Stagger element entrances so individual items register
- Numerical values rendered with .toFixed(2) for tidy display
- Minimum 24px breathing room between distinct visual groups

# Pacing (target durations)

Match the scene plan's per-step durations. Total animation: 45-60 seconds.
Add a final 1-2 second hold on the last frame before setting __animationDone__.

# Forbidden

- No <canvas>, no <video>, no WebGL — SVG and CSS only.
- No external scripts beyond the GSAP CDN listed above.
- No images (no <img> elements, no background-image).

Output ONLY the complete HTML, starting with <!DOCTYPE html>.
"""


HEAL_SYSTEM = """\
You are an HTML/JS code fixer. You receive a broken animation HTML file and the
runtime errors captured during a render attempt.

Fix ONLY the errors. Do not rewrite the entire scene. Return the COMPLETE updated
HTML, starting with <!DOCTYPE html>. Output no markdown fences and no commentary.

Common failure modes:
- gsap selector matches no element → check that the queried IDs/classes exist in DOM
- ReferenceError → variable referenced before declaration; check ordering
- SyntaxError → fix the specific line
- Animation never sets window.__animationDone__ → ensure the final tl call sets it
- Timeline plays but capture is empty → ensure auto-play actually fires (DOMContentLoaded handler)
- regex.match()[1] crashes when the match returns null → guard with `?.[1]` or check first
"""


CRITIC_SYSTEM = """\
You are the Critic agent. You receive:
- The paper context (what concept the animation must teach)
- The styled scene plan (what was supposed to render)
- N keyframe screenshots captured at evenly-spaced times during render

Examine the screenshots holistically. Be RUTHLESS — your job is to find quality
defects a senior frontend engineer would notice immediately.

Look for:
- Element overlap, clipping, off-screen rendering
- Text legibility (too small, low contrast, overflowing containers)
- Color encoding inconsistency (does M_p stay the same color across frames?)
- Information density (cramped or sparse)
- Pacing and progression (do frames show meaningful change between steps?)
- Pedagogical clarity (would the concept land for a CS undergrad?)
- Visual polish (typography hierarchy, alignment, spacing, motion quality)
- Adherence to the styled plan (did the visualizer follow color/layout rules?)
- "LLM slop" patterns (centered floating boxes with no purpose, generic icons,
  decorative arrows that don't carry meaning, default fonts)

Output STRICT JSON:
{
  "verdict": "acceptable" | "needs_revision",
  "overall_score": <integer 0-10>,
  "praise": "<what works — Visualizer must preserve these aspects>",
  "issues": [
    {
      "frame_indices": [<int>],
      "step_num": <int|null>,
      "severity": "major" | "minor",
      "category": "layout" | "typography" | "color" | "pacing" | "clarity" | "polish" | "slop",
      "description": "<what's wrong, specific>",
      "suggested_fix": "<concrete code-level change>"
    }
  ]
}

Scoring guide:
- 10: would impress a senior frontend engineer; ready to ship
- 7-9: minor polish issues; "acceptable" only if 9+
- 4-6: clear quality problems; "needs_revision"
- 0-3: broken or generic LLM slop; "needs_revision"

Reserve "acceptable" for genuinely polished work (score ≥ 9). Default to "needs_revision".
"""


VISUALIZER_REVISION_SYSTEM = """\
You are the Visualizer agent on a REVISION ROUND. You receive:
- The original paper + styled scene plan
- The current HTML you previously wrote (or a teammate wrote)
- Specific feedback from the Critic agent listing issues to fix and praise to preserve

Your job:
- Address EVERY major issue. Address minor issues if it doesn't risk regression.
- PRESERVE everything called out in the praise field — do not undo that work.
- Maintain the contracts: auto-play, window.__animationDone__ at end, replay button,
  SVG-based text, viewBox 1280x720.
- Output ONLY the complete revised HTML, starting with <!DOCTYPE html>. No
  markdown fences, no commentary.

Important: this is a SURGICAL revision. If the critic says "step 3 boxes overlap",
fix step 3's layout. Don't rewrite step 1 unless it has its own issue listed.
"""


# ---------------------------------------------------------------------------
# LLM calls — multi-provider dispatcher
# ---------------------------------------------------------------------------

_openai_client = None
_gemini_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _gemini_client


def _call_openai(*, system: str, user: str, model: str, json_mode: bool, temperature: float) -> str:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    rsp = _get_openai_client().chat.completions.create(**kwargs)
    return rsp.choices[0].message.content


def _call_gemini(*, system: str, user: str, model: str, json_mode: bool, temperature: float,
                 image_paths: list[Path] | None = None) -> str:
    from google.genai import types as gtypes

    parts: list[Any] = [gtypes.Part.from_text(text=user)]
    if image_paths:
        for p in image_paths:
            with open(p, "rb") as f:
                parts.append(gtypes.Part.from_bytes(data=f.read(), mime_type="image/png"))

    config_kwargs: dict[str, Any] = {
        "system_instruction": system,
        "temperature": temperature,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    rsp = _get_gemini_client().models.generate_content(
        model=model,
        contents=[gtypes.Content(role="user", parts=parts)],
        config=gtypes.GenerateContentConfig(**config_kwargs),
    )
    return rsp.text


def _is_transient(exc: Exception) -> bool:
    """5xx-style transient errors should be retried; 4xx (quota/auth) should not."""
    name = type(exc).__name__
    msg = str(exc)
    return name == "ServerError" or " 503 " in msg or "UNAVAILABLE" in msg or " 502 " in msg or " 504 " in msg


def call_llm(*, system: str, user: str, json_mode: bool = False, temperature: float = 0.7,
             image_paths: list[Path] | None = None) -> str:
    """Unified LLM call with retry on transient errors. Multimodal via image_paths (Gemini only)."""
    last_exc: Exception | None = None
    max_attempts = 7  # 5s, 10s, 20s, 40s, 50s, 50s waits → up to ~3 minutes
    for attempt in range(max_attempts):
        try:
            if MODEL.startswith("gemini"):
                return _call_gemini(system=system, user=user, model=MODEL, json_mode=json_mode,
                                    temperature=temperature, image_paths=image_paths)
            if image_paths:
                raise NotImplementedError(
                    f"Multimodal not implemented for non-Gemini models (got MODEL={MODEL})"
                )
            return _call_openai(system=system, user=user, model=MODEL, json_mode=json_mode, temperature=temperature)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts - 1 or not _is_transient(exc):
                raise
            wait = min(50, 5 * (2 ** attempt))  # 5, 10, 20, 40, 50, 50s
            print(f"[llm] transient {type(exc).__name__} (attempt {attempt + 1}/{max_attempts}), "
                  f"retrying in {wait}s — {str(exc)[:120]}")
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def _parse_json_lenient(raw: str, agent_name: str) -> dict[str, Any]:
    """Parse LLM JSON output. On failure, repair via json_repair (PaperVizAgent uses the same trick)."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[{agent_name}] JSON parse failed ({e.msg} at char {e.pos}); repairing…")
        import json_repair
        repaired = json_repair.loads(raw)
        if not isinstance(repaired, dict):
            raise ValueError(f"{agent_name} output is not a JSON object after repair") from e
        return repaired


def call_planner(paper_text: str) -> dict[str, Any]:
    raw = call_llm(system=PLANNER_SYSTEM, user=paper_text, json_mode=True, temperature=0.7)
    return _parse_json_lenient(raw, "planner")


def call_stylist(scene_plan: dict, paper_text: str) -> dict[str, Any]:
    user_msg = (
        "## Paper\n\n" + paper_text +
        "\n\n## Scene plan from Planner\n\n```json\n" + json.dumps(scene_plan, indent=2) + "\n```"
    )
    raw = call_llm(system=STYLIST_SYSTEM, user=user_msg, json_mode=True, temperature=0.5)
    return _parse_json_lenient(raw, "stylist")


def call_visualizer(styled_plan: dict, paper_text: str) -> str:
    user_msg = (
        "## Paper\n\n" + paper_text +
        "\n\n## Styled scene plan\n\n```json\n" + json.dumps(styled_plan, indent=2) + "\n```"
    )
    raw = call_llm(system=VISUALIZER_SYSTEM, user=user_msg, temperature=0.5)
    return _strip_markdown(raw)


def call_healer(broken_html: str, errors: list[str]) -> str:
    user_msg = (
        "## Errors\n\n" + "\n".join(f"- {e}" for e in errors) +
        "\n\n## Current HTML\n\n" + broken_html
    )
    raw = call_llm(system=HEAL_SYSTEM, user=user_msg, temperature=0.2)
    return _strip_markdown(raw)


def call_critic(paper_text: str, styled_plan: dict, frame_paths: list[Path]) -> dict[str, Any]:
    user_msg = (
        "## Paper\n\n" + paper_text +
        "\n\n## Styled scene plan\n\n```json\n" + json.dumps(styled_plan, indent=2) + "\n```" +
        f"\n\n## Frames\n\nN={len(frame_paths)} keyframes follow as image attachments, "
        f"in chronological order (frame 0 = earliest)."
    )
    raw = call_llm(
        system=CRITIC_SYSTEM,
        user=user_msg,
        json_mode=True,
        temperature=0.3,
        image_paths=frame_paths,
    )
    return _parse_json_lenient(raw, "critic")


def call_revisor(current_html: str, styled_plan: dict, paper_text: str, critic_feedback: dict) -> str:
    user_msg = (
        "## Paper\n\n" + paper_text +
        "\n\n## Styled scene plan\n\n```json\n" + json.dumps(styled_plan, indent=2) + "\n```" +
        "\n\n## Critic feedback\n\n```json\n" + json.dumps(critic_feedback, indent=2) + "\n```" +
        "\n\n## Current HTML to revise\n\n" + current_html
    )
    raw = call_llm(system=VISUALIZER_REVISION_SYSTEM, user=user_msg, temperature=0.4)
    return _strip_markdown(raw)


def _strip_markdown(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # Drop ```lang and trailing ```
        first_newline = s.find("\n")
        s = s[first_newline + 1:] if first_newline != -1 else s
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_and_capture(html_path: Path, out_dir: Path) -> tuple[Path | None, list[str], list[Path]]:
    """Run record.mjs subprocess. Returns (video_path or None, console_errors, frame_paths)."""
    record_js = ROOT / "record.mjs"

    # Wipe stale frames from prior render in same out_dir
    for stale in out_dir.glob("frame_*.png"):
        stale.unlink()

    proc = subprocess.run(
        ["node", str(record_js), str(html_path), str(out_dir)],
        capture_output=True,
        text=True,
        timeout=360,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)

    errors_path = out_dir / "console_errors.json"
    errors: list[str] = []
    if errors_path.exists():
        errors = json.loads(errors_path.read_text())

    frame_paths = sorted(out_dir.glob("frame_*.png"))

    video_path = out_dir / "video.webm"
    if video_path.exists() and video_path.stat().st_size > 0:
        return video_path, errors, frame_paths
    return (None,
            errors or [f"recorder exited {proc.returncode}: {proc.stderr[:500]}"],
            frame_paths)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _has_fatal_errors(errors: list[str]) -> bool:
    """JS errors are fatal (animation broken). Timeout alone means it played but didn't signal done — degraded but viewable."""
    for e in errors:
        if e.startswith("[pageerror]") or e.startswith("[console.error]") or e.startswith("[requestfailed]"):
            return True
    return False


def render_with_heal(html_path: Path, run_dir: Path, max_heal: int, html: str,
                     phase_label: str) -> tuple[Path | None, list[Path], str]:
    """Render the current HTML; on console errors, run heal loop. Returns (video, frames, final_html).

    Distinguishes fatal JS errors (heal-worthy) from timeout-only (degraded success — animation
    played but didn't signal completion; pass to Critic anyway).
    """
    best_video: Path | None = None
    best_frames: list[Path] = []
    best_html: str = html

    for attempt in range(max_heal + 1):
        print(f"\n[render:{phase_label}] attempt {attempt + 1} of {max_heal + 1}…")
        video, errors, frames = render_and_capture(html_path, run_dir)

        if video and not errors:
            print(f"[render:{phase_label}] CLEAN OK → {video} ({len(frames)} frames)")
            return video, frames, html

        # Track best degraded render (most frames captured)
        if video and len(frames) > len(best_frames):
            best_video, best_frames, best_html = video, frames, html

        if not _has_fatal_errors(errors) and video and len(frames) >= 3:
            # Only non-fatal warnings (e.g., __animationDone__ timeout) — animation
            # played far enough to capture useful frames. Accept and move on.
            print(f"[render:{phase_label}] DEGRADED OK (no fatal errors, {len(frames)} frames) — "
                  f"passing to Critic")
            return video, frames, html

        if attempt < max_heal:
            print(f"[heal:{phase_label}] {len(errors)} error(s), patching…")
            for e in errors[:3]:
                print(f"  - {e[:180]}")
            (run_dir / f"console_errors_{phase_label}_{attempt + 1}.json").write_text(
                json.dumps(errors, indent=2)
            )
            html = call_healer(html, errors)
            (run_dir / f"heal_{phase_label}_{attempt + 1}.html").write_text(html)
            html_path.write_text(html)
        else:
            print(f"[heal:{phase_label}] heal exhausted; falling back to best degraded render")
            if best_video:
                # Restore the html that produced the best render
                html_path.write_text(best_html)
                return best_video, best_frames, best_html
            return None, frames, html
    return None, [], html


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-agent web animation PoC")
    parser.add_argument("paper", type=Path, help="Path to paper markdown")
    parser.add_argument("--max-heal", type=int, default=MAX_HEAL_DEFAULT,
                        help="Self-heal rounds for console errors (default: 3)")
    parser.add_argument("--max-critic", type=int, default=MAX_CRITIC_DEFAULT,
                        help="Critic refinement rounds after first successful render (default: 2)")
    parser.add_argument("--no-render", action="store_true",
                        help="Skip Playwright render (just produce HTML)")
    parser.add_argument("--skip-stylist", action="store_true",
                        help="Skip Stylist agent (Visualizer gets raw plan)")
    parser.add_argument("--skip-critic", action="store_true",
                        help="Skip Critic loop (single-shot render)")
    args = parser.parse_args()

    # API key check
    if MODEL.startswith("gemini") and not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
        return 1
    if not MODEL.startswith("gemini") and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 1

    if not args.paper.exists():
        print(f"ERROR: paper not found: {args.paper}", file=sys.stderr)
        return 1

    paper_text = args.paper.read_text()
    run_dir = ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.paper, run_dir / args.paper.name)
    print(f"[run-dir] {run_dir}")
    print(f"[model]   {MODEL}")

    # ---- Planner ----
    print(f"\n[planner] calling {MODEL}…")
    t0 = time.time()
    plan = call_planner(paper_text)
    (run_dir / "scene_plan.json").write_text(json.dumps(plan, indent=2))
    print(f"[planner] OK ({time.time() - t0:.1f}s) — {len(plan.get('steps', []))} steps, "
          f"target {plan.get('duration_s', '?')}s")
    print(f"[planner] title: {plan.get('title')}")

    # ---- Stylist ----
    if args.skip_stylist:
        styled_plan = plan
        print("\n[stylist] skipped (--skip-stylist)")
    else:
        print(f"\n[stylist] calling {MODEL}…")
        t0 = time.time()
        styled_plan = call_stylist(plan, paper_text)
        (run_dir / "styled_plan.json").write_text(json.dumps(styled_plan, indent=2))
        n_colors = len(styled_plan.get("style", {}).get("color_semantics", {}))
        n_step_styles = len(styled_plan.get("style", {}).get("step_styles", []))
        print(f"[stylist] OK ({time.time() - t0:.1f}s) — {n_colors} entity colors, "
              f"{n_step_styles} step layouts")

    # ---- Visualizer (initial) ----
    print(f"\n[visualizer] calling {MODEL}…")
    t0 = time.time()
    html = call_visualizer(styled_plan, paper_text)
    html_path = run_dir / "animation.html"
    html_path.write_text(html)
    (run_dir / "animation_v0.html").write_text(html)
    print(f"[visualizer] OK ({time.time() - t0:.1f}s) — {len(html):,} chars")

    if args.no_render:
        print(f"\n[done] HTML at {html_path} (rendering skipped)")
        return 0

    # ---- Render + heal (initial) ----
    video, frames, html = render_with_heal(html_path, run_dir, args.max_heal, html, "initial")
    if video is None:
        print("[render] FAILED — could not produce a working render")
        return 2

    # ---- Critic refinement loop ----
    if args.skip_critic or args.max_critic <= 0:
        print(f"\n[done] critic skipped → {video}")
        print(f"\nrun directory: {run_dir}")
        return 0

    for crit_round in range(1, args.max_critic + 1):
        if not frames:
            print(f"\n[critic] round {crit_round}: no frames captured, aborting refinement")
            break

        print(f"\n[critic] round {crit_round}/{args.max_critic} — analyzing {len(frames)} frames…")
        t0 = time.time()
        feedback = call_critic(paper_text, styled_plan, frames)
        (run_dir / f"critic_{crit_round}.json").write_text(json.dumps(feedback, indent=2))
        verdict = feedback.get("verdict", "?")
        score = feedback.get("overall_score", "?")
        n_issues = len(feedback.get("issues", []))
        print(f"[critic] OK ({time.time() - t0:.1f}s) — verdict={verdict} score={score} "
              f"issues={n_issues}")

        if verdict == "acceptable":
            print(f"[critic] accepted at round {crit_round}, stopping refinement early")
            break

        # ---- Revisor ----
        print(f"\n[revisor] round {crit_round} — calling Visualizer with feedback…")
        t0 = time.time()
        html = call_revisor(html, styled_plan, paper_text, feedback)
        (run_dir / f"animation_v{crit_round}.html").write_text(html)
        html_path.write_text(html)
        print(f"[revisor] OK ({time.time() - t0:.1f}s) — {len(html):,} chars")

        # ---- Re-render + heal ----
        video, frames, html = render_with_heal(
            html_path, run_dir, args.max_heal, html, f"crit{crit_round}"
        )
        if video is None:
            print(f"[render] revision round {crit_round} could not be rendered, "
                  f"reverting to last good")
            # Restore previous good html
            prev_path = run_dir / (
                f"animation_v{crit_round - 1}.html" if crit_round > 1 else "animation_v0.html"
            )
            html = prev_path.read_text()
            html_path.write_text(html)
            video, _, _ = render_and_capture(html_path, run_dir)[:3]
            break

    print(f"\n[done] final video → {video}")
    print(f"run directory: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
