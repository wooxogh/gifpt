"""cherrypick_run.py — single-shot codegen + render for the cherry-pick workflow.

Used by `scripts/cherrypick_attention.md`. Reads a prompt from a slot directory,
calls the LLM (same SYSTEM_PROMPT and post-processing as production), saves the
generated code, then renders it. On failure, prints stderr so you can iterate.

Usage:
    python -m scripts.cherrypick_run cherrypick/attention/01_self_attention/v01
    python -m scripts.cherrypick_run cherrypick/attention/01_self_attention/v05 --no-llm

Slot directory layout:
    <slot>/prompt.txt   — the user message you wrote (required unless --no-llm)
    <slot>/scene.py     — generated (or hand-edited) Manim code
    <slot>/media/...    — manim render output (auto-cleaned each run)
    <slot>/video.mp4    — final symlink/copy of the rendered video
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


def run(slot_dir: Path, no_llm: bool) -> int:
    slot_dir = slot_dir.resolve()
    slot_dir.mkdir(parents=True, exist_ok=True)
    scene_path = slot_dir / "scene.py"
    prompt_path = slot_dir / "prompt.txt"

    # Wipe previous render artifacts in this slot so the new run is unambiguous.
    media_dir = slot_dir / "media"
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)
    final_link = slot_dir / "video.mp4"
    if final_link.exists() or final_link.is_symlink():
        final_link.unlink()

    if not no_llm:
        if not prompt_path.exists():
            print(f"[cherrypick] missing {prompt_path}", file=sys.stderr)
            print("[cherrypick] write your user prompt to that file, then re-run.", file=sys.stderr)
            return 2

        prompt = prompt_path.read_text().strip()
        if not prompt:
            print(f"[cherrypick] {prompt_path} is empty", file=sys.stderr)
            return 2

        print(f"[cherrypick] calling LLM ({slot_dir.name}) ...")
        from openai import OpenAI
        from studio.ai.llm_codegen import (
            SYSTEM_PROMPT,
            post_process_manim_code,
            MODEL_PRIMARY,
        )

        client = OpenAI()
        t0 = time.monotonic()
        resp = client.chat.completions.create(
            model=MODEL_PRIMARY,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            timeout=120,
        )
        raw = resp.choices[0].message.content or ""
        code = post_process_manim_code(raw)
        scene_path.write_text(code)
        gen_dt = time.monotonic() - t0
        print(f"[cherrypick] code saved → {scene_path} ({gen_dt:.1f}s, {len(code)} chars)")

    if not scene_path.exists():
        print(
            f"[cherrypick] missing {scene_path} — run without --no-llm, or paste code there manually.",
            file=sys.stderr,
        )
        return 2

    code = scene_path.read_text()

    print(f"[cherrypick] rendering {slot_dir.name} ...")
    from studio.video_render import run_manim_code, ManimRenderError, classify_runtime_error

    t0 = time.monotonic()
    try:
        video = run_manim_code(code, slot_dir, "video.mp4")
    except ManimRenderError as e:
        dt = time.monotonic() - t0
        err = classify_runtime_error(e.stderr_snippet)
        print(f"[cherrypick] RENDER FAIL ({dt:.1f}s)")
        print(f"[cherrypick] error_type: {err['error_type']}")
        print(f"[cherrypick] message: {err['message']}")

        # Save full stderr to file for debugging
        stderr_path = slot_dir / "error.log"
        stderr_path.write_text(e.stderr_snippet)
        print(f"[cherrypick] full stderr saved → {stderr_path}")

        # Print last 800 chars for quick glance
        print("--- stderr (last 800 chars) ---")
        print(e.stderr_snippet[-800:])
        print("--- end stderr ---")
        return 1
    except Exception:
        traceback.print_exc()
        return 1

    dt = time.monotonic() - t0

    # Make the final video easy to find: symlink at <slot>/video.mp4
    try:
        final_link.symlink_to(video)
    except OSError:
        shutil.copy2(video, final_link)

    print(f"[cherrypick] OK ({dt:.1f}s)")
    print(f"[cherrypick] VIDEO: {video}")
    print(f"[cherrypick] open with: open '{final_link}'")
    return 0


def main():
    p = argparse.ArgumentParser(
        description="cherry-pick single iteration: codegen + render"
    )
    p.add_argument("slot_dir", type=Path, help="slot directory (e.g. cherrypick/attention/01_self_attention/v01)")
    p.add_argument("--no-llm", action="store_true", help="skip LLM, render existing scene.py as-is")
    args = p.parse_args()
    sys.exit(run(args.slot_dir, args.no_llm))


if __name__ == "__main__":
    main()
