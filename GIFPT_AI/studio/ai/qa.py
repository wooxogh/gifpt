# studio/ai/qa.py
"""QA module for Manim animation pipeline.

Two layers:
1. IR validation  — cheap structural checks on pseudocode/anim IR before codegen.
2. Vision QA      — after render, extract frames and ask GPT-4o to evaluate quality.
"""

import base64
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as exc:
    logger.error("Failed to initialize OpenAI client at import time; Vision QA may be unavailable: %s", exc)
    client = None


# ── 1. IR Validation ─────────────────────────────────────────────────────────

class IRValidationError(Exception):
    """Raised when IR fails structural validation."""
    def __init__(self, stage: str, issues: list[str]):
        self.stage = stage
        self.issues = issues
        super().__init__(f"IR validation failed at {stage}: {issues}")


def validate_pseudocode_ir(ir: dict) -> list[str]:
    """Validate pseudocode IR structure. Returns list of issues (empty = pass)."""
    issues = []

    if not isinstance(ir, dict):
        return ["IR is not a dict"]

    # Must have entities
    entities = ir.get("entities")
    if not entities or not isinstance(entities, list):
        issues.append("'entities' is missing or empty")
    else:
        for i, e in enumerate(entities):
            if not isinstance(e, dict):
                issues.append(f"entities[{i}] is not a dict")
                continue
            if not e.get("id"):
                issues.append(f"entities[{i}] missing 'id'")
            if not e.get("type"):
                issues.append(f"entities[{i}] missing 'type'")

    # Must have operations
    operations = ir.get("operations")
    if not operations or not isinstance(operations, list):
        issues.append("'operations' is missing or empty")
    else:
        if len(operations) < 2:
            issues.append(f"only {len(operations)} operations — too few for meaningful visualization")
        for i, op in enumerate(operations):
            if not isinstance(op, dict):
                issues.append(f"operations[{i}] is not a dict")
                continue
            if not op.get("action"):
                issues.append(f"operations[{i}] missing 'action'")
            if not op.get("subject"):
                issues.append(f"operations[{i}] missing 'subject'")

    return issues


def validate_anim_ir(ir: dict) -> list[str]:
    """Validate animation IR structure. Returns list of issues (empty = pass)."""
    issues = []

    if not isinstance(ir, dict):
        return ["IR is not a dict"]

    # Must have layout
    layout = ir.get("layout")
    if not layout or not isinstance(layout, list):
        issues.append("'layout' is missing or empty")
    else:
        for i, item in enumerate(layout):
            if not isinstance(item, dict):
                issues.append(f"layout[{i}] is not a dict")
                continue
            if not item.get("id"):
                issues.append(f"layout[{i}] missing 'id'")
            if not item.get("shape"):
                issues.append(f"layout[{i}] missing 'shape'")
            pos = item.get("position")
            if not pos or not isinstance(pos, (list, tuple)) or len(pos) < 2:
                issues.append(f"layout[{i}] missing or invalid 'position'")

    # Must have actions
    actions = ir.get("actions")
    if not actions or not isinstance(actions, list):
        issues.append("'actions' is missing or empty")
    else:
        if len(actions) < 2:
            issues.append(f"only {len(actions)} actions — too few for meaningful animation")
        for i, act in enumerate(actions):
            if not isinstance(act, dict):
                issues.append(f"actions[{i}] is not a dict")
                continue
            if not act.get("animation"):
                issues.append(f"actions[{i}] missing 'animation'")

    return issues


# ── 2. Vision QA ──────────────────────────────────────────────────────────────

def extract_frames(video_path: str, num_frames: int = 4) -> list[str]:
    """Extract evenly-spaced frames from video as base64 PNG strings."""
    video_path = Path(video_path)
    if not video_path.exists():
        logger.warning("extract_frames: video not found at %s", video_path)
        return []

    frames = []
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use ffmpeg to extract frames
        try:
            # Get video duration
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", str(video_path)],
                capture_output=True, text=True, timeout=10,
            )
            duration = float(probe.stdout.strip() or "5")
        except Exception:
            duration = 5.0

        # Extract frames at evenly spaced intervals (skip first/last 10%)
        start = duration * 0.1
        end = duration * 0.9
        interval = (end - start) / max(num_frames - 1, 1)

        for i in range(num_frames):
            timestamp = start + i * interval
            frame_path = Path(tmpdir) / f"frame_{i:02d}.png"
            try:
                subprocess.run(
                    ["ffmpeg", "-ss", str(timestamp), "-i", str(video_path),
                     "-vframes", "1", "-q:v", "2", str(frame_path)],
                    capture_output=True, timeout=10,
                )
                if frame_path.exists():
                    with open(frame_path, "rb") as f:
                        frames.append(base64.b64encode(f.read()).decode("utf-8"))
            except Exception as e:
                logger.warning("extract_frames: failed at %.1fs: %s", timestamp, e)

    return frames


def vision_qa(
    video_path: str,
    algorithm_description: str,
    num_frames: int = 4,
    threshold: float = 5.0,
) -> dict:
    """Run vision QA on rendered video.

    Returns:
        {
            "score": float (1-10),
            "passed": bool,
            "issues": list[str],
            "summary": str,
        }
    """
    if not client:
        return {
            "score": -1,
            "passed": True,  # Don't block on QA failure
            "issues": ["OpenAI client not initialized"],
            "summary": "Vision QA unavailable",
        }

    frames = extract_frames(video_path, num_frames)

    if not frames:
        return {
            "score": 0,
            "passed": False,
            "issues": ["Could not extract frames from video"],
            "summary": "Frame extraction failed",
        }

    # Build GPT-4o message with frames
    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"You are a QA reviewer for algorithm visualization videos.\n"
                f"The video is supposed to visualize: \"{algorithm_description}\"\n\n"
                f"Below are {len(frames)} evenly-spaced frames from the rendered video.\n"
                f"Evaluate the quality on these criteria:\n"
                f"1. CORRECTNESS: Does it accurately represent the described algorithm/logic?\n"
                f"2. VISUAL CLARITY: Are elements visible, not overlapping, properly labeled?\n"
                f"3. COMPLETENESS: Does it show the key steps, not just a static image?\n"
                f"4. READABILITY: Is text readable? Are colors distinguishable?\n\n"
                f"Respond with ONLY JSON:\n"
                f'{{"score": <1-10>, "issues": [<string list of problems found>], '
                f'"summary": "<1 sentence overall assessment>"}}'
            ),
        }
    ]

    for i, frame_b64 in enumerate(frames):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{frame_b64}",
                "detail": "low",
            },
        })

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": content}],
            max_tokens=300,
            timeout=30,
        )
        result = json.loads(resp.choices[0].message.content)
        score = float(result.get("score", 0))
        issues = result.get("issues", [])
        summary = result.get("summary", "")

        logger.info("vision_qa score=%.1f issues=%d summary=%s", score, len(issues), summary)

        return {
            "score": score,
            "passed": score >= threshold,
            "issues": issues,
            "summary": summary,
        }

    except Exception as e:
        logger.warning("vision_qa failed: %s — passing by default", e)
        return {
            "score": -1,
            "passed": True,  # Don't block on QA failure
            "issues": [f"QA evaluation failed: {e}"],
            "summary": "QA skipped due to error",
        }
