"""One-shot pipeline runner that captures all stage outputs for evaluators.

Unlike `render_video_from_instructions`, this runner deliberately
**skips retry/self-healing** — we want to measure edge preservation on
the FIRST try, which is the true baseline. Retry masking would hide
the edge loss we're trying to quantify.

Returned dict:
    {
      "intent": {"entities": [...], "operations": [...]},  # may be empty if extract failed
      "intent_loss": {
          "pseudo_ir": {...IntentLoss...},
          "anim_ir":   {...IntentLoss...},
          "codegen":   {...IntentLoss...},
      },
      "pseudo_ir": dict,        # may be {} if stage crashed
      "anim_ir": dict,
      "manim_code": str,
      "render_result": {
          "success": bool,
          "duration_s": float,
          "error_type": str | None,
          "error_message": str | None,
          "video_path": str | None,
      },
      "qa_result": dict,        # empty if not reached
      "stage_errors": {stage_name: str} for any stage that raised
    }

Week 4 (Day 2): added Stage 0 IntentTracker.extract + per-stage
check_intent_loss. Intent handling is non-blocking — downstream stages
always run regardless of intent failures. Two new keys may appear in
`stage_errors`:
  - `intent_extract`: the Stage 0 extract call itself raised. `intent`
    stays empty and per-stage loss checks are skipped for the rest of
    the run.
  - `intent_check_<stage>`: extract succeeded, but the deterministic
    loss check against that stage's artifact raised (e.g. malformed
    artifact). The affected stage is absent from `intent_loss`, but
    adjacent stages still get checked.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_pipeline_capture(
    description: str,
    *,
    render: bool = True,
    run_qa: bool = True,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the GIFPT v1 pipeline once and capture every stage output.

    Args:
        description: Natural-language algorithm description.
        render: If False, skip the Manim render step (and QA). Useful
            for cheap runs that only measure the 2 LLM edges.
        run_qa: If False, skip Vision QA even when render succeeds.
        output_dir: Required when `render=True`. Caller owns the
            lifecycle of this directory — in LangSmith batch runs the
            wrapper in `langsmith_adapter.build_target_fn` creates and
            cleans up a TemporaryDirectory per example so rendered mp4s
            don't leak across long baseline runs. When render=False,
            this argument is ignored.
    """
    from studio.ai.llm_pseudocode import call_llm_pseudocode_ir_with_usage
    from studio.ai.llm_anim_ir import call_llm_anim_ir_with_usage
    from studio.ai.llm_codegen import call_llm_codegen_with_usage
    from studio.ai.intent_tracker import (
        IntentSchema,
        check_intent_loss,
        extract_intent_with_usage,
    )

    capture: dict[str, Any] = {
        "description": description,
        "intent": {"entities": [], "operations": []},
        "intent_loss": {},
        "pseudo_ir": {},
        "anim_ir": {},
        "manim_code": "",
        "render_result": {
            "success": False,
            "duration_s": None,
            "error_type": None,
            "error_message": None,
            "video_path": None,
        },
        "qa_result": {},
        "stage_errors": {},
        "usage": {},
    }

    # Stage 0: intent extraction (non-blocking — a failure here leaves
    # intent_loss empty but does not abort the rest of the pipeline)
    intent: IntentSchema | None = None
    try:
        intent, usage_intent = extract_intent_with_usage(description)
        capture["intent"] = {
            "entities": list(intent.entities),
            "operations": list(intent.operations),
        }
        capture["usage"]["intent"] = usage_intent
    except Exception as exc:
        capture["stage_errors"]["intent_extract"] = f"{type(exc).__name__}: {exc}"
        logger.warning("intent_extract stage failed: %s", exc)

    def _record_intent_loss(stage_name: str, artifact: Any) -> None:
        if intent is None or intent.is_empty():
            return
        try:
            loss = check_intent_loss(intent, artifact, stage_name)
            capture["intent_loss"][stage_name] = {
                "stage": loss.stage,
                "lost_entities": loss.lost_entities,
                "lost_operations": loss.lost_operations,
                "preserved_entities": loss.preserved_entities,
                "preserved_operations": loss.preserved_operations,
                "preservation_rate": loss.preservation_rate,
            }
        except Exception as exc:
            capture["stage_errors"][f"intent_check_{stage_name}"] = (
                f"{type(exc).__name__}: {exc}"
            )
            logger.warning("intent_check[%s] failed: %s", stage_name, exc)

    # Stage 1: pseudo_ir
    try:
        pseudo_ir, usage_pseudo = call_llm_pseudocode_ir_with_usage(description)
        capture["pseudo_ir"] = pseudo_ir or {}
        capture["usage"]["pseudo_ir"] = usage_pseudo
    except Exception as exc:
        capture["stage_errors"]["pseudo_ir"] = f"{type(exc).__name__}: {exc}"
        logger.warning("pseudo_ir stage failed: %s", exc)
        return capture
    _record_intent_loss("pseudo_ir", capture["pseudo_ir"])

    # Stage 2: anim_ir
    try:
        anim_ir, usage_anim = call_llm_anim_ir_with_usage(capture["pseudo_ir"])
        capture["anim_ir"] = anim_ir or {}
        capture["usage"]["anim_ir"] = usage_anim
    except Exception as exc:
        capture["stage_errors"]["anim_ir"] = f"{type(exc).__name__}: {exc}"
        logger.warning("anim_ir stage failed: %s", exc)
        return capture
    _record_intent_loss("anim_ir", capture["anim_ir"])

    # Stage 3: codegen
    try:
        result = call_llm_codegen_with_usage(capture["anim_ir"])
        if isinstance(result, tuple) and len(result) == 2:
            manim_code, usage_codegen = result
        else:
            manim_code = result
            usage_codegen = None
        capture["manim_code"] = manim_code or ""
        capture["usage"]["codegen"] = usage_codegen
    except Exception as exc:
        capture["stage_errors"]["codegen"] = f"{type(exc).__name__}: {exc}"
        logger.warning("codegen stage failed: %s", exc)
        return capture
    _record_intent_loss("codegen", capture["manim_code"])

    if not render:
        return capture

    # Stage 4: render
    from studio.video_render import run_manim_code, ManimRenderError, classify_runtime_error

    if output_dir is None:
        capture["stage_errors"]["render"] = "output_dir_required"
        capture["render_result"]["error_type"] = "output_dir_required"
        return capture
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = f"capture_{int(time.time() * 1000)}.mp4"

    t0 = time.perf_counter()
    try:
        video_path = run_manim_code(capture["manim_code"], output_dir, output_name)
        capture["render_result"] = {
            "success": True,
            "duration_s": time.perf_counter() - t0,
            "error_type": None,
            "error_message": None,
            "video_path": video_path,
        }
    except ManimRenderError as exc:
        capture["render_result"] = {
            "success": False,
            "duration_s": time.perf_counter() - t0,
            "error_type": exc.error_type,
            "error_message": exc.stderr_snippet[-500:] if exc.stderr_snippet else None,
            "video_path": None,
        }
        capture["stage_errors"]["render"] = exc.error_type
        return capture
    except Exception as exc:
        classified = classify_runtime_error(str(exc))
        capture["render_result"] = {
            "success": False,
            "duration_s": time.perf_counter() - t0,
            "error_type": classified.get("error_type", "unknown"),
            "error_message": str(exc)[-500:],
            "video_path": None,
        }
        capture["stage_errors"]["render"] = capture["render_result"]["error_type"]
        return capture

    if not run_qa:
        return capture

    # Stage 5: Vision QA
    try:
        from studio.ai.qa import vision_qa
        qa_domain = (
            capture["anim_ir"].get("metadata", {}).get("domain")
            if isinstance(capture["anim_ir"], dict)
            else None
        )
        qa_result = vision_qa(
            capture["render_result"]["video_path"],
            description,
            num_frames=4,
            threshold=5.0,
            domain=qa_domain,
        )
        capture["qa_result"] = qa_result or {}
    except Exception as exc:
        capture["stage_errors"]["qa"] = f"{type(exc).__name__}: {exc}"
        logger.warning("qa stage failed: %s", exc)

    return capture
