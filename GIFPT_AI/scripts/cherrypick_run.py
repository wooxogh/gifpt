"""cherrypick_run.py — codegen + render + self-heal for the cherry-pick workflow.

Reads a prompt from a slot directory, calls the LLM (same SYSTEM_PROMPT and
post-processing as production), saves the generated code, then renders it.
On render failure, sends the error back to the LLM to fix the code and retries
(up to --max-heal attempts).

Usage:
    python -m scripts.cherrypick_run cherrypick/attention/01_self_attention/v01
    python -m scripts.cherrypick_run cherrypick/attention/01_self_attention/v05 --no-llm
    python -m scripts.cherrypick_run cherrypick/attention/01_self_attention/v07 --max-heal 5

Slot directory layout:
    <slot>/prompt.txt   — the user message you wrote (required unless --no-llm)
    <slot>/scene.py     — generated (or hand-edited) Manim code
    <slot>/media/...    — manim render output (auto-cleaned each run)
    <slot>/video.mp4    — final symlink/copy of the rendered video
    <slot>/error.log    — last render error stderr (if failed)
    <slot>/heal_N.py    — code from self-heal attempt N (for debugging)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

# Make `studio` importable
GIFPT_AI_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GIFPT_AI_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GIFPT_AI.settings")

MAX_HEAL_DEFAULT = 3

HEAL_SYSTEM_PROMPT = """You are a Manim code fixer. You receive broken Manim Python code
and the error message from the render attempt. Fix ONLY the error — do not rewrite
the entire scene. Return the complete fixed Python code.

Common Manim CE 0.19.0 fixes:
- .deepcopy() does not exist → use .copy()
- .set_text() does not exist on Text → create new Text + Transform
- Line/Arrow start/end must be coordinate arrays (e.g., obj.get_center()), NOT Mobject objects
- SurroundingRectangle expects Mobject(s), not a list/slice → wrap in VGroup()
- self.play() must receive at least 1 animation, never an empty list
- run_time must be > 0, use max(value, 0.1)
- No DashedLine, DashedArrow, CurvedArrow — use Line or Arrow instead
- Trailing non-code text after the class → remove it

Output ONLY the fixed Python code, no markdown, no explanation."""


def generate_code(client, prompt: str, system_prompt: str, model: str, post_process) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        timeout=120,
    )
    raw = resp.choices[0].message.content or ""
    return post_process(raw)


def _extract_error_line(code: str, stderr: str) -> str:
    """Try to find which line in the original code caused the error."""
    import re
    # Look for line numbers referencing the temp file
    matches = re.findall(r'line (\d+)', stderr)
    if not matches:
        return ""
    lines = code.split("\n")
    context_parts = []
    for m in matches[-3:]:  # last 3 line refs
        lineno = int(m) - 1
        if 0 <= lineno < len(lines):
            start = max(0, lineno - 2)
            end = min(len(lines), lineno + 3)
            snippet = "\n".join(f"  {'>>>' if i == lineno else '   '} {i+1}: {lines[i]}" for i in range(start, end))
            context_parts.append(snippet)
    if context_parts:
        return "\n\nRELEVANT CODE LINES:\n" + "\n---\n".join(context_parts)
    return ""


def heal_code(client, code: str, error_msg: str, model: str, post_process) -> str:
    """Send broken code + error to LLM, get fixed code back."""
    code_context = _extract_error_line(code, error_msg)
    heal_prompt = f"""The following Manim code failed to render.

ERROR:
{error_msg[-1500:]}
{code_context}

BROKEN CODE:
```python
{code}
```

Fix the error and return the complete corrected Python code."""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": HEAL_SYSTEM_PROMPT},
            {"role": "user", "content": heal_prompt},
        ],
        timeout=120,
    )
    raw = resp.choices[0].message.content or ""
    return post_process(raw)


def try_render(code: str, slot_dir: Path) -> tuple[str | None, str | None]:
    """Try to render code. Returns (video_path, None) on success or (None, error_detail) on failure."""
    from studio.video_render import run_manim_code, ManimRenderError

    # Clean media dir for fresh render
    media_dir = slot_dir / "media"
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)

    try:
        video = run_manim_code(code, slot_dir, "video.mp4")
        return video, None
    except ManimRenderError as e:
        error_detail = f"{e.error_type}: {e.stderr_snippet[-1500:]}"
        return None, error_detail


def run(slot_dir: Path, no_llm: bool, max_heal: int) -> int:
    slot_dir = slot_dir.resolve()
    slot_dir.mkdir(parents=True, exist_ok=True)
    scene_path = slot_dir / "scene.py"
    prompt_path = slot_dir / "prompt.txt"

    # Wipe previous render artifacts
    media_dir = slot_dir / "media"
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)
    final_link = slot_dir / "video.mp4"
    if final_link.exists() or final_link.is_symlink():
        final_link.unlink()

    client = None
    post_process = None
    model = None

    if not no_llm:
        if not prompt_path.exists():
            print(f"[cherrypick] missing {prompt_path}", file=sys.stderr)
            return 2

        prompt = prompt_path.read_text().strip()
        if not prompt:
            print(f"[cherrypick] {prompt_path} is empty", file=sys.stderr)
            return 2

        from openai import OpenAI
        from studio.ai.llm_codegen import SYSTEM_PROMPT, post_process_manim_code, MODEL_PRIMARY

        client = OpenAI()
        post_process = post_process_manim_code
        model = MODEL_PRIMARY

        print(f"[cherrypick] calling LLM ({slot_dir.name}) ...")
        t0 = time.monotonic()
        code = generate_code(client, prompt, SYSTEM_PROMPT, model, post_process)
        scene_path.write_text(code)
        gen_dt = time.monotonic() - t0
        print(f"[cherrypick] code saved → {scene_path} ({gen_dt:.1f}s, {len(code)} chars)")

    if not scene_path.exists():
        print(f"[cherrypick] missing {scene_path}", file=sys.stderr)
        return 2

    code = scene_path.read_text()

    # Render + self-heal loop
    print(f"[cherrypick] rendering {slot_dir.name} ...")
    t0 = time.monotonic()

    video, error_detail = try_render(code, slot_dir)

    if video:
        dt = time.monotonic() - t0
        _finish(video, final_link, dt)
        return 0

    # First render failed — start self-heal loop
    print(f"[cherrypick] render failed, starting self-heal (max {max_heal} attempts) ...")

    if client is None:
        # Need LLM for self-heal, lazy init
        from openai import OpenAI
        from studio.ai.llm_codegen import post_process_manim_code, MODEL_PRIMARY
        client = OpenAI()
        post_process = post_process_manim_code
        model = MODEL_PRIMARY

    for attempt in range(1, max_heal + 1):
        print(f"[cherrypick] self-heal {attempt}/{max_heal} ...")

        # Extract short error for display
        error_lines = (error_detail or "unknown error").split("\n")
        short_error = "\n".join(error_lines[-5:]) if len(error_lines) > 5 else error_detail
        print(f"[cherrypick]   error: {short_error[:200]}")

        t_heal = time.monotonic()
        try:
            code = heal_code(client, code, error_detail or "unknown error", model, post_process)
        except Exception as exc:
            print(f"[cherrypick]   heal LLM call failed: {exc}")
            break

        heal_dt = time.monotonic() - t_heal
        heal_path = slot_dir / f"heal_{attempt}.py"
        heal_path.write_text(code)
        scene_path.write_text(code)
        print(f"[cherrypick]   healed code saved → {heal_path} ({heal_dt:.1f}s, {len(code)} chars)")

        video, error_detail = try_render(code, slot_dir)

        if video:
            dt = time.monotonic() - t0
            print(f"[cherrypick] self-heal succeeded on attempt {attempt}!")
            _finish(video, final_link, dt)
            return 0

    # All heal attempts exhausted
    dt = time.monotonic() - t0
    print(f"[cherrypick] RENDER FAIL after {max_heal} self-heal attempts ({dt:.1f}s)")
    stderr_path = slot_dir / "error.log"
    stderr_path.write_text(error_detail or "unknown error")
    print(f"[cherrypick] last error saved → {stderr_path}")
    print("--- last error (last 800 chars) ---")
    print((error_detail or "")[-800:])
    print("--- end error ---")
    return 1


def _finish(video: str, final_link: Path, dt: float):
    """Symlink the video and print success."""
    try:
        final_link.symlink_to(video)
    except OSError:
        shutil.copy2(video, final_link)
    print(f"[cherrypick] OK ({dt:.1f}s)")
    print(f"[cherrypick] VIDEO: {video}")
    print(f"[cherrypick] open with: open '{final_link}'")


def main():
    p = argparse.ArgumentParser(description="cherry-pick: codegen + render + self-heal")
    p.add_argument("slot_dir", type=Path, help="slot directory")
    p.add_argument("--no-llm", action="store_true", help="skip initial LLM codegen and render existing scene.py (self-heal still uses LLM on failure)")
    p.add_argument("--max-heal", type=int, default=MAX_HEAL_DEFAULT,
                    help=f"max self-heal attempts (default: {MAX_HEAL_DEFAULT})")
    args = p.parse_args()
    sys.exit(run(args.slot_dir, args.no_llm, args.max_heal))


if __name__ == "__main__":
    main()
