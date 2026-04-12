"""LangSmith edge-preservation evaluators for the GIFPT v1 pipeline.

Each evaluator targets one handoff edge in the 4-stage pipeline
(pseudo_ir → anim_ir → manim_code → render → qa) and returns an
EdgeEvalResult describing whether intent was preserved across that edge.

Entry points:
    from studio.evaluators import (
        EdgeEvalResult,
        pseudo_anim_preservation,
        anim_codegen_preservation,
        codegen_render_preservation,
        render_qa_preservation,
    )
"""
from studio.evaluators.base import EdgeEvalResult, EDGE_NAMES
from studio.evaluators.pseudo_anim_preservation import pseudo_anim_preservation
from studio.evaluators.anim_codegen_preservation import anim_codegen_preservation
from studio.evaluators.codegen_render_preservation import codegen_render_preservation
from studio.evaluators.render_qa_preservation import render_qa_preservation

__all__ = [
    "EdgeEvalResult",
    "EDGE_NAMES",
    "pseudo_anim_preservation",
    "anim_codegen_preservation",
    "codegen_render_preservation",
    "render_qa_preservation",
]
