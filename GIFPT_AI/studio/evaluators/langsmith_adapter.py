"""LangSmith adapter layer for the 4 edge-preservation evaluators.

LangSmith's `evaluate()` calls evaluators with the signature
`(run, example) -> dict` where `run.outputs` is whatever the target
function returned for the example's inputs. Our target function
returns the flat capture dict from `pipeline_capture.run_pipeline_capture`.

Each adapter reads the 2 stage outputs it needs out of that dict and
delegates to the corresponding pure-function evaluator.
"""
from __future__ import annotations

from typing import Any

from studio.evaluators.anim_codegen_preservation import anim_codegen_preservation
from studio.evaluators.codegen_render_preservation import codegen_render_preservation
from studio.evaluators.pseudo_anim_preservation import pseudo_anim_preservation
from studio.evaluators.render_qa_preservation import render_qa_preservation


def _outputs(run: Any) -> dict:
    raw = getattr(run, "outputs", None) if run is not None else None
    return raw if isinstance(raw, dict) else {}


def pseudo_anim_evaluator(run, example=None) -> dict:  # noqa: ARG001
    outputs = _outputs(run)
    result = pseudo_anim_preservation(
        outputs.get("pseudo_ir", {}),
        outputs.get("anim_ir", {}),
    )
    return result.as_feedback()


def anim_codegen_evaluator(run, example=None) -> dict:  # noqa: ARG001
    outputs = _outputs(run)
    result = anim_codegen_preservation(
        outputs.get("anim_ir", {}),
        outputs.get("manim_code", ""),
    )
    return result.as_feedback()


def codegen_render_evaluator(run, example=None) -> dict:  # noqa: ARG001
    outputs = _outputs(run)
    result = codegen_render_preservation(
        outputs.get("manim_code", ""),
        outputs.get("render_result", {}),
    )
    return result.as_feedback()


def render_qa_evaluator(run, example=None) -> dict:  # noqa: ARG001
    outputs = _outputs(run)
    anim_ir = outputs.get("anim_ir", {})
    domain = None
    if isinstance(anim_ir, dict):
        meta = anim_ir.get("metadata")
        if isinstance(meta, dict):
            domain = meta.get("domain")
    result = render_qa_preservation(outputs.get("qa_result", {}), domain=domain)
    return result.as_feedback()


ALL_EVALUATORS: tuple = (
    pseudo_anim_evaluator,
    anim_codegen_evaluator,
    codegen_render_evaluator,
    render_qa_evaluator,
)


def build_target_fn(*, render: bool = True, run_qa: bool = True):
    """Construct a LangSmith `target` callable from pipeline_capture.

    The returned function takes the example's `inputs` dict (which
    `upload_goldset.py` defines as `{description, algorithm}`) and
    returns the full stage-capture dict.
    """
    from studio.evaluators.pipeline_capture import run_pipeline_capture

    def target(inputs: dict) -> dict:
        description = (inputs or {}).get("description") or (inputs or {}).get("algorithm") or ""
        return run_pipeline_capture(description, render=render, run_qa=run_qa)

    return target
