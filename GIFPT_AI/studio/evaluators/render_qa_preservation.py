"""Edge evaluator: rendered mp4 → Vision QA verdict.

The QA edge is where *intent that survived codegen* must be *visible*
to the vision model. Missing a domain-required check (e.g. sorting
without `comparison_shown`) means the video rendered successfully but
the upstream intent was still lost — just at the presentation layer.
"""
from __future__ import annotations

from typing import Any

from studio.evaluators.base import EdgeEvalResult


def render_qa_preservation(
    qa_result: dict,
    *,
    domain: str | None = None,
    domain_qa_config: dict | None = None,
) -> EdgeEvalResult:
    """Score the render → qa handoff.

    Args:
        qa_result: Vision QA output dict. Expected shape:
            {
              "score": float,
              "passed": bool,
              "threshold": float,
              "domain_checks": {"comparison_shown": true, ...},
              "issues": list[str]
            }
        domain: Domain name carried from anim_ir metadata. Used to look
            up required checks from DOMAIN_QA_CONFIG when passed.
        domain_qa_config: Override for DOMAIN_QA_CONFIG (tests inject a
            minimal fixture here to avoid importing studio.ai.qa).
    """
    missing: list[str] = []

    if not isinstance(qa_result, dict):
        return EdgeEvalResult(
            edge="render_qa",
            score=0,
            missing=["qa_result:not_a_dict"],
            extra={},
        )

    score_val = qa_result.get("score")
    passed = qa_result.get("passed")
    threshold = qa_result.get("threshold")

    if passed is False:
        missing.append(f"qa_score:{score_val}<{threshold}")
    elif passed is None:
        missing.append("qa_result:no_passed_field")

    failed_checks: list[str] = []
    domain_checks = qa_result.get("domain_checks")

    if domain and isinstance(domain_checks, dict):
        if domain_qa_config is None:
            try:
                from studio.ai.qa import DOMAIN_QA_CONFIG
                domain_qa_config = DOMAIN_QA_CONFIG
            except Exception:
                domain_qa_config = {}

        config = (domain_qa_config or {}).get(domain)
        required = (config or {}).get("required_checks", []) if isinstance(config, dict) else []

        for check in required:
            if not isinstance(check, dict):
                continue
            key = check.get("key")
            if not isinstance(key, str) or not key:
                continue
            value = domain_checks.get(key)
            if value is False:
                failed_checks.append(key)
                missing.append(f"domain_check:{domain}.{key}")
            elif value is None:
                failed_checks.append(f"{key}(missing)")
                missing.append(f"domain_check:{domain}.{key}(missing)")

    extra: dict[str, Any] = {
        "score": score_val,
        "threshold": threshold,
        "passed": passed,
        "domain": domain,
        "failed_checks": failed_checks,
        "qa_issues": qa_result.get("issues", []),
    }

    final_score = 1 if not missing else 0
    return EdgeEvalResult(
        edge="render_qa", score=final_score, missing=missing, extra=extra
    )
