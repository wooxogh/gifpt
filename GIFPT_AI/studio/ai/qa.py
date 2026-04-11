# studio/ai/qa.py
"""QA module for Manim animation pipeline.

Three layers:
1. IR validation  — cheap structural checks on pseudocode/anim IR before codegen.
2. Deep IR validation — Pydantic models + cross-reference checks (entity↔operation consistency).
3. Vision QA      — after render, extract frames and ask GPT-4o to evaluate quality.
"""

import base64
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from openai import OpenAI

logger = logging.getLogger(__name__)

try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as exc:
    logger.error("Failed to initialize OpenAI client at import time; Vision QA may be unavailable: %s", exc)
    client = None


# ── 1. IR Validation ─────────────────────────────────────────────────────────

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


# ── 1b. Deep IR Validation (Pydantic + cross-reference) ─────────────────────

# Manim scene coordinate bounds
SCENE_X_MIN, SCENE_X_MAX = -7.1, 7.1
SCENE_Y_MIN, SCENE_Y_MAX = -4.0, 4.0


class PseudocodeEntity(BaseModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    attributes: dict = Field(default_factory=dict)


class PseudocodeOperation(BaseModel):
    step: int | None = None
    subject: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: str | None = None
    description: str | None = None


class PseudocodeIR(BaseModel):
    metadata: dict = Field(default_factory=dict)
    entities: list[PseudocodeEntity] = Field(min_length=1)
    operations: list[PseudocodeOperation] = Field(min_length=2)

    @model_validator(mode="after")
    def check_entity_references(self):
        """Verify every operation.subject references a defined entity ID."""
        entity_ids = {e.id for e in self.entities}
        for i, op in enumerate(self.operations):
            if op.subject not in entity_ids:
                raise ValueError(
                    f"operations[{i}].subject='{op.subject}' not in entity IDs: {entity_ids}"
                )
            if op.target and op.target not in entity_ids:
                raise ValueError(
                    f"operations[{i}].target='{op.target}' not in entity IDs: {entity_ids}"
                )
        return self


class AnimLayoutItem(BaseModel):
    id: str = Field(min_length=1)
    shape: str = Field(min_length=1)
    position: list[float] = Field(min_length=2, max_length=3)
    color: str | None = None
    label: str | None = None
    data: list | None = None
    dimensions: str | None = None

    @field_validator("position")
    @classmethod
    def position_in_bounds(cls, v: list[float]) -> list[float]:
        x, y = v[0], v[1]
        if not (SCENE_X_MIN <= x <= SCENE_X_MAX):
            raise ValueError(f"x={x} out of scene bounds [{SCENE_X_MIN}, {SCENE_X_MAX}]")
        if not (SCENE_Y_MIN <= y <= SCENE_Y_MAX):
            raise ValueError(f"y={y} out of scene bounds [{SCENE_Y_MIN}, {SCENE_Y_MAX}]")
        return v


class AnimAction(BaseModel):
    step: int | None = None
    target: str | None = None
    animation: str = Field(min_length=1)
    description: str | None = None


class AnimIR(BaseModel):
    metadata: dict = Field(default_factory=dict)
    layout: list[AnimLayoutItem] = Field(min_length=1)
    actions: list[AnimAction] = Field(min_length=2)

    @model_validator(mode="after")
    def check_action_targets(self):
        """Verify action targets reference defined layout IDs."""
        layout_ids = {item.id for item in self.layout}
        for i, act in enumerate(self.actions):
            if act.target and act.target not in layout_ids:
                raise ValueError(
                    f"actions[{i}].target='{act.target}' not in layout IDs: {layout_ids}"
                )
        return self

    @model_validator(mode="after")
    def check_no_duplicate_layout_ids(self):
        ids = [item.id for item in self.layout]
        seen = set()
        for lid in ids:
            if lid in seen:
                raise ValueError(f"Duplicate layout id: '{lid}'")
            seen.add(lid)
        return self


def validate_pseudocode_ir_deep(ir: dict) -> list[str]:
    """Pydantic-based deep validation of pseudocode IR.

    Returns list of issues (empty = pass). Catches:
    - Missing/invalid fields with type enforcement
    - Entity ID ↔ operation subject/target reference integrity
    """
    try:
        PseudocodeIR.model_validate(ir)
        return []
    except (ValidationError, TypeError, ValueError) as e:
        # Flatten Pydantic validation errors into human-readable strings
        issues = []
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = " → ".join(str(l) for l in err["loc"])
                issues.append(f"{loc}: {err['msg']}")
        else:
            issues.append(str(e))
        return issues
    except Exception as e:
        logger.exception("Unexpected error in validate_pseudocode_ir_deep")
        return [f"Internal validator error: {type(e).__name__}: {e}"]


def validate_anim_ir_deep(ir: dict) -> list[str]:
    """Pydantic-based deep validation of animation IR.

    Returns list of issues (empty = pass). Catches:
    - Missing/invalid fields with type enforcement
    - Position coordinates outside Manim scene bounds
    - Action target ↔ layout ID reference integrity
    - Duplicate layout IDs
    """
    try:
        AnimIR.model_validate(ir)
        return []
    except (ValidationError, TypeError, ValueError) as e:
        issues = []
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = " → ".join(str(l) for l in err["loc"])
                issues.append(f"{loc}: {err['msg']}")
        else:
            issues.append(str(e))
        return issues
    except Exception as e:
        logger.exception("Unexpected error in validate_anim_ir_deep")
        return [f"Internal validator error: {type(e).__name__}: {e}"]


# ── 2. Vision QA ──────────────────────────────────────────────────────────────

# ── Domain-specific QA config ─────────────────────────────────────────────────

# Base criteria weights (sum to 1.0)
DEFAULT_WEIGHTS = {
    "correctness": 0.35,
    "clarity": 0.25,
    "completeness": 0.25,
    "readability": 0.15,
}

# Domain-specific required checks: if these fail, score is penalized
# Each check has: key (for JSON), description (for prompt), penalty (subtracted from final score)
DOMAIN_QA_CONFIG = {
    "sorting": {
        "threshold": 5.0,
        "weights": {"correctness": 0.30, "clarity": 0.20, "completeness": 0.35, "readability": 0.15},
        "required_checks": [
            {"key": "elements_visible", "desc": "Array elements are visible as distinct cells with numeric values", "penalty": 2.0},
            {"key": "comparison_shown", "desc": "Comparison or swap operations are animated step by step", "penalty": 2.5},
            {"key": "sorted_progression", "desc": "Progression from unsorted to sorted state is visible", "penalty": 1.5},
            {"key": "state_highlighting", "desc": "Active/compared/swapped elements are highlighted with color", "penalty": 1.0},
        ],
    },
    "graph_traversal": {
        "threshold": 5.0,
        "weights": {"correctness": 0.35, "clarity": 0.25, "completeness": 0.25, "readability": 0.15},
        "required_checks": [
            {"key": "nodes_visible", "desc": "Nodes are visible as distinct shapes with labels", "penalty": 2.5},
            {"key": "edges_drawn", "desc": "Edges/connections between nodes are drawn", "penalty": 2.0},
            {"key": "traversal_order", "desc": "Traversal order is visible (visited nodes change color)", "penalty": 2.0},
            {"key": "frontier_shown", "desc": "Queue/stack/frontier state is shown if applicable", "penalty": 1.0},
        ],
    },
    "cnn_param": {
        "threshold": 5.0,
        "weights": {"correctness": 0.30, "clarity": 0.30, "completeness": 0.25, "readability": 0.15},
        "required_checks": [
            {"key": "layers_visible", "desc": "Layers (input, convolution, output) are distinguishable", "penalty": 2.5},
            {"key": "kernel_animated", "desc": "Kernel/filter operations are animated (sliding window)", "penalty": 2.0},
            {"key": "dimensions_shown", "desc": "Dimensions/shapes are annotated on layers", "penalty": 1.0},
            {"key": "data_flow_clear", "desc": "Data flow direction is clear (left to right or similar)", "penalty": 1.5},
        ],
    },
    "dynamic_programming": {
        "threshold": 5.0,
        "weights": {"correctness": 0.35, "clarity": 0.20, "completeness": 0.30, "readability": 0.15},
        "required_checks": [
            {"key": "table_visible", "desc": "Table/grid structure is visible showing subproblem results", "penalty": 2.5},
            {"key": "fill_animated", "desc": "Cell fill-ins are animated in correct order", "penalty": 2.0},
            {"key": "dependencies_shown", "desc": "Dependencies between cells are shown (arrows or highlights)", "penalty": 1.5},
        ],
    },
    "cache": {
        "threshold": 5.0,
        "weights": DEFAULT_WEIGHTS,
        "required_checks": [
            {"key": "slots_visible", "desc": "Cache slots/queue structures are visible", "penalty": 2.5},
            {"key": "hit_miss_indicated", "desc": "Hit/miss events are clearly indicated", "penalty": 2.0},
            {"key": "eviction_animated", "desc": "Eviction process is animated", "penalty": 1.5},
        ],
    },
    "transformer": {
        "threshold": 5.0,
        "weights": {"correctness": 0.30, "clarity": 0.30, "completeness": 0.25, "readability": 0.15},
        "required_checks": [
            {"key": "blocks_visible", "desc": "Encoder/decoder blocks are distinguishable", "penalty": 2.0},
            {"key": "attention_shown", "desc": "Attention mechanism is visually represented", "penalty": 2.5},
            {"key": "data_flow_sequential", "desc": "Data flow through layers is shown sequentially", "penalty": 1.5},
        ],
    },
    "hash_table": {
        "threshold": 5.0,
        "weights": DEFAULT_WEIGHTS,
        "required_checks": [
            {"key": "buckets_visible", "desc": "Hash table buckets/slots are visible", "penalty": 2.0},
            {"key": "hash_operation_shown", "desc": "Hash function computation is shown", "penalty": 1.5},
            {"key": "collision_handled", "desc": "Collision handling (chaining/probing) is animated", "penalty": 2.0},
        ],
    },
}


def _build_domain_checks_prompt(domain: str) -> str:
    """Build the domain-specific checks section for the Vision QA prompt."""
    config = DOMAIN_QA_CONFIG.get(domain)
    if not config:
        return ""

    checks = config["required_checks"]
    lines = [f"\nDOMAIN-SPECIFIC REQUIRED CHECKS for {domain.upper()} visualization:"]
    lines.append("For each check, respond with true/false in the 'domain_checks' field:")
    for chk in checks:
        lines.append(f'  - "{chk["key"]}": {chk["desc"]}')
    return "\n".join(lines)


def compute_domain_adjusted_score(
    base_scores: dict[str, float],
    domain_checks: dict[str, bool],
    domain: str | None,
) -> tuple[float, list[str]]:
    """Compute a weighted score with domain-specific penalties.

    Args:
        base_scores: {"correctness": 1-10, "clarity": 1-10, "completeness": 1-10, "readability": 1-10}
        domain_checks: {"check_key": True/False, ...}
        domain: The domain string or None

    Returns:
        (final_score, penalty_reasons): final score 0-10, list of penalty reasons
    """
    config = DOMAIN_QA_CONFIG.get(domain) if domain else None
    weights = (config or {}).get("weights", DEFAULT_WEIGHTS)

    # Weighted base score
    weighted = 0.0
    total_weight = 0.0
    for criterion, weight in weights.items():
        val = base_scores.get(criterion, 5.0)
        # Clamp to 1-10
        val = max(1.0, min(10.0, float(val)))
        weighted += val * weight
        total_weight += weight

    base_score = weighted / total_weight if total_weight > 0 else 5.0

    # Apply domain-specific penalties
    penalty_reasons: list[str] = []
    total_penalty = 0.0

    reported_checks = domain_checks or {}
    if config:
        for chk in config["required_checks"]:
            key = chk["key"]
            if key not in reported_checks:
                total_penalty += chk["penalty"]
                penalty_reasons.append(f"{chk['desc']} — MISSING (penalty: -{chk['penalty']})")
                continue
            passed = reported_checks[key]
            if not passed:
                total_penalty += chk["penalty"]
                penalty_reasons.append(f"{chk['desc']} — FAILED (penalty: -{chk['penalty']})")

    final_score = max(0.0, base_score - total_penalty)
    return round(final_score, 1), penalty_reasons


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
    domain: str | None = None,
) -> dict:
    """Run vision QA on rendered video with domain-aware weighted scoring.

    When a domain is provided and has a config in DOMAIN_QA_CONFIG, the scoring
    uses per-criterion weights and applies penalties for failed required checks.
    This reduces false positives (pretty but educationally wrong) and false
    negatives (visually simple but correct).

    Returns:
        {
            "score": float (-1 to 10; -1 means vision QA was unavailable
                      because the OpenAI client was not initialized or an error occurred),
            "passed": bool (True when score >= threshold, or when vision QA is
                       unavailable and the check is skipped),
            "issues": list[str],
            "summary": str,
            "base_scores": dict (per-criterion scores, if available),
            "domain_checks": dict (domain check results, if available),
            "penalties": list[str] (penalty reasons, if any),
        }
    """
    if not client:
        return {
            "score": -1,
            "passed": True,
            "issues": ["OpenAI client not initialized"],
            "summary": "Vision QA unavailable",
            "base_scores": {},
            "domain_checks": {},
            "penalties": [],
        }

    frames = extract_frames(video_path, num_frames)

    if not frames:
        return {
            "score": 0,
            "passed": False,
            "issues": ["Could not extract frames from video"],
            "summary": "Frame extraction failed",
            "base_scores": {},
            "domain_checks": {},
            "penalties": [],
        }

    # Build domain-specific prompt section
    domain_checks_prompt = _build_domain_checks_prompt(domain) if domain else ""
    has_domain_checks = bool(domain and domain in DOMAIN_QA_CONFIG)

    # Build structured JSON schema for response
    if has_domain_checks:
        check_keys = [c["key"] for c in DOMAIN_QA_CONFIG[domain]["required_checks"]]
        domain_checks_schema = ", ".join(f'"{k}": <true/false>' for k in check_keys)
        response_schema = (
            '{"base_scores": {"correctness": <1-10>, "clarity": <1-10>, '
            '"completeness": <1-10>, "readability": <1-10>}, '
            f'"domain_checks": {{{domain_checks_schema}}}, '
            '"issues": [<string list>], "summary": "<1 sentence>"}'
        )
    else:
        response_schema = (
            '{"base_scores": {"correctness": <1-10>, "clarity": <1-10>, '
            '"completeness": <1-10>, "readability": <1-10>}, '
            '"issues": [<string list>], "summary": "<1 sentence>"}'
        )

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"You are a QA reviewer for algorithm visualization videos.\n"
                f"The video is supposed to visualize: \"{algorithm_description}\"\n\n"
                f"Below are {len(frames)} evenly-spaced frames from the rendered video.\n\n"
                f"Score each criterion from 1 to 10:\n"
                f"1. CORRECTNESS: Does it accurately represent the described algorithm/logic?\n"
                f"2. CLARITY: Are elements visible, not overlapping, properly labeled?\n"
                f"3. COMPLETENESS: Does it show the key steps, not just a static image?\n"
                f"4. READABILITY: Is text readable? Are colors distinguishable?\n"
                f"{domain_checks_prompt}\n\n"
                f"Respond with ONLY JSON:\n{response_schema}"
            ),
        }
    ]

    for frame_b64 in frames:
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
            max_tokens=500,
            timeout=30,
        )
        result = json.loads(resp.choices[0].message.content)

        # Extract structured scores
        base_scores = result.get("base_scores", {})
        domain_checks = result.get("domain_checks", {})
        issues = result.get("issues", [])
        summary = result.get("summary", "")

        # Backward compat: if LLM returns flat "score" instead of base_scores
        if not base_scores and "score" in result:
            flat_score = float(result["score"])
            base_scores = {
                "correctness": flat_score,
                "clarity": flat_score,
                "completeness": flat_score,
                "readability": flat_score,
            }

        # Compute domain-adjusted score
        final_score, penalties = compute_domain_adjusted_score(
            base_scores, domain_checks, domain
        )

        # Use domain-specific threshold if available
        config = DOMAIN_QA_CONFIG.get(domain) if domain else None
        effective_threshold = (config or {}).get("threshold", threshold)

        if penalties:
            if not isinstance(issues, list):
                issues = [issues] if issues else []
            issues = issues + penalties

        logger.info(
            "vision_qa domain=%s score=%.1f (base=%s) penalties=%d passed=%s summary=%s",
            domain, final_score, base_scores, len(penalties),
            final_score >= effective_threshold, summary,
        )

        return {
            "score": final_score,
            "passed": final_score >= effective_threshold,
            "issues": issues,
            "summary": summary,
            "base_scores": base_scores,
            "domain_checks": domain_checks,
            "penalties": penalties,
        }

    except Exception as e:
        logger.warning("vision_qa failed: %s — passing by default", e)
        return {
            "score": -1,
            "passed": True,
            "issues": [f"QA evaluation failed: {e}"],
            "summary": "QA skipped due to error",
            "base_scores": {},
            "domain_checks": {},
            "penalties": [],
        }
