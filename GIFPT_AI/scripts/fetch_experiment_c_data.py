"""One-shot fetch of Experiment C (Week 4 Day 4) results from LangSmith.

Pulls every run under the experiment session, joins feedback scores
across the 5 evaluators, extracts qa_result.score + latency + token
counts, and dumps the aggregate to stdout as JSON. The Day 5 snapshot
doc copies from this JSON rather than re-querying LangSmith.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_GIFPT_AI = _HERE.parents[1]
if str(_GIFPT_AI) not in sys.path:
    sys.path.insert(0, str(_GIFPT_AI))

try:
    from dotenv import load_dotenv
    load_dotenv(_GIFPT_AI / ".env")
except ImportError:
    pass

from langsmith import Client

SESSION_ID = "07daebea-b9c1-4c5e-89a7-443eaae22a43"
EDGE_KEYS = (
    "pseudo_anim_preservation",
    "anim_codegen_preservation",
    "codegen_render_preservation",
    "render_qa_preservation",
    "intent_preservation_preservation",
)


def main() -> int:
    if not os.getenv("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY missing", file=sys.stderr)
        return 1
    client = Client()

    runs = list(
        client.list_runs(
            project_id=SESSION_ID,
            is_root=True,
        )
    )

    per_case = []
    for run in runs:
        outputs = run.outputs or {}
        qa = outputs.get("qa_result") or {}
        render = outputs.get("render_result") or {}
        stage_errors = outputs.get("stage_errors") or {}
        intent = outputs.get("intent") or {}
        intent_loss = outputs.get("intent_loss") or {}

        feedback_list = list(client.list_feedback(run_ids=[run.id]))
        scores: dict[str, float] = {}
        intent_extra = None
        for fb in feedback_list:
            if fb.key in EDGE_KEYS:
                scores[fb.key] = float(fb.score) if fb.score is not None else None
                if fb.key == "intent_preservation_preservation":
                    val = fb.value if isinstance(fb.value, dict) else {}
                    intent_extra = {
                        "overall_rate": val.get("overall_rate"),
                        "stages_checked": val.get("stages_checked"),
                        "per_stage_rate": val.get("per_stage_rate"),
                        "missing_count": len(val.get("missing") or []),
                    }

        inputs = run.inputs or {}
        # total_tokens + latency from run
        duration_s = None
        if run.end_time and run.start_time:
            duration_s = (run.end_time - run.start_time).total_seconds()

        per_case.append({
            "run_id": str(run.id),
            "name": run.name,
            "example_id": str(run.reference_example_id) if run.reference_example_id else None,
            "description": (inputs.get("description") or inputs.get("algorithm") or "")[:120],
            "duration_s": duration_s,
            "total_tokens": (run.total_tokens if hasattr(run, "total_tokens") else None),
            "total_cost": float(run.total_cost) if getattr(run, "total_cost", None) is not None else None,
            "render_success": bool(render.get("success")),
            "render_error_type": render.get("error_type"),
            "render_duration_s": render.get("duration_s"),
            "qa_score": qa.get("score"),
            "qa_passed": qa.get("passed"),
            "stage_errors": list(stage_errors.keys()),
            "intent_entity_count": len(intent.get("entities") or []),
            "intent_operation_count": len(intent.get("operations") or []),
            "intent_stages_present": list(intent_loss.keys()),
            "scores": scores,
            "intent_extra": intent_extra,
        })

    summary = {
        "session_id": SESSION_ID,
        "run_count": len(per_case),
        "render_success_rate": sum(1 for c in per_case if c["render_success"]) / len(per_case) if per_case else 0,
        "qa_pass_rate": sum(1 for c in per_case if c.get("qa_passed")) / len(per_case) if per_case else 0,
        "mean_qa_score_success_only": (
            sum(c["qa_score"] for c in per_case if c.get("qa_score") is not None)
            / sum(1 for c in per_case if c.get("qa_score") is not None)
        ) if any(c.get("qa_score") is not None for c in per_case) else None,
        "edge_pass_rates": {
            key: sum(1 for c in per_case if c["scores"].get(key) == 1.0) / len(per_case) if per_case else 0
            for key in EDGE_KEYS
        },
        "total_duration_s": sum(c["duration_s"] for c in per_case if c["duration_s"]),
        "total_tokens": sum(c["total_tokens"] or 0 for c in per_case),
        "total_cost": sum(c["total_cost"] or 0 for c in per_case),
        "per_case": per_case,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
