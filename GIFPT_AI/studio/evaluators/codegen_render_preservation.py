"""Edge evaluator: manim_code → rendered mp4.

Checks the last AST-level barriers that cause runtime crashes plus the
observable render outcome. A green result means the code was
statically clean (no FORBIDDEN AST), rendered within the timeout
budget, and produced an output file.

This is the edge where `failure-taxonomy.md` shows 37.5% of failures
(3/8) — all NameError/AttributeError/timeout on dijkstra.
"""
from __future__ import annotations

from typing import Any

from studio.evaluators.base import EdgeEvalResult

RENDER_TIMEOUT_BUDGET_S = 180.0


def codegen_render_preservation(
    manim_code: str,
    render_result: dict,
    *,
    timeout_budget_s: float = RENDER_TIMEOUT_BUDGET_S,
) -> EdgeEvalResult:
    """Score the manim_code → render handoff.

    Args:
        manim_code: The Python source that was executed by Manim.
        render_result: Dict describing the render outcome. Expected keys:
            - success (bool) — True if mp4 was produced
            - duration_s (float) — wall-clock render time
            - error_type (str | None) — classification from
              `classify_runtime_error` (e.g. "runtime_name", "timeout")
            - error_message (str, optional) — stderr snippet
            - video_path (str | None) — path to produced file
        timeout_budget_s: Override for the soft latency budget.
    """
    missing: list[str] = []

    # AST-level barriers first — these map 1:1 to production failures.
    # If the validator itself fails to load or run, we CANNOT grant a green
    # score: the AST safety gate never actually executed, so there's no
    # evidence the code is clean. Record the evaluator failure in `missing`
    # so the edge score is forced to 0.
    try:
        from studio.video_render import validate_manim_code_ast
        ast_issues = validate_manim_code_ast(manim_code or "")
        validator_available = True
    except Exception as exc:
        ast_issues = [{"error_type": "evaluator_error", "message": str(exc)}]
        validator_available = False
        missing.append("ast:evaluator_error")

    forbidden_ast: list[str] = []
    for issue in ast_issues:
        if not isinstance(issue, dict):
            continue
        if issue.get("error_type") in {"forbidden_api", "forbidden_method", "syntax"}:
            forbidden_ast.append(
                f"{issue.get('error_type')}:{issue.get('message', '?')}"
            )
            missing.append(f"ast:{issue.get('error_type')}")

    if not isinstance(render_result, dict):
        render_result = {}

    success = bool(render_result.get("success"))
    duration_s = render_result.get("duration_s")
    error_type = render_result.get("error_type")
    video_path = render_result.get("video_path")

    if not success:
        missing.append(f"render:{error_type or 'unknown_error'}")
    elif not video_path:
        missing.append("render:no_output_path")

    budget_ok = True
    if isinstance(duration_s, (int, float)):
        if duration_s > timeout_budget_s:
            budget_ok = False
            missing.append(f"timeout:{duration_s:.0f}s>{timeout_budget_s:.0f}s")

    extra: dict[str, Any] = {
        "forbidden_ast": forbidden_ast,
        "render_success": success,
        "duration_s": duration_s,
        "error_type": error_type,
        "budget_ok": budget_ok,
        "validator_available": validator_available,
    }

    score = 1 if not missing else 0
    return EdgeEvalResult(
        edge="codegen_render", score=score, missing=missing, extra=extra
    )
