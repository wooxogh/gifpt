"""5th evaluator: canonical intent preservation across all stages.

Unlike the 4 pairwise edge evaluators (pseudo→anim, anim→codegen,
codegen→render, render→qa), this one does NOT compare two adjacent
stage artifacts. It anchors to a canonical intent extracted from the
raw user text (`IntentTracker.extract_intent`, Week 4 Day 1) and
measures how much of that intent survives into each of pseudo_ir,
anim_ir, and codegen.

The new signal this adds, which the 4 edge evaluators cannot see:
    user_text → pseudo_ir loss.

If the very first LLM stage already dropped an entity the user asked
for, the pairwise evaluators start counting from an already-diminished
baseline and never flag the initial loss. IntentTracker closes that gap.

Binary scoring rule (consistent with the other evaluators):
    score = 1  iff all stages reported full preservation (no lost items)
    score = 0  otherwise

Per-stage preservation rates and lost phrase lists are attached to the
`extra` dict so LangSmith run-diff can explain *where* the loss happened,
not just that it did.
"""
from __future__ import annotations

from typing import Any

from studio.evaluators.base import EdgeEvalResult

# Stages the intent tracker checks against, in pipeline order.
INTENT_CHECK_STAGES: tuple[str, ...] = ("pseudo_ir", "anim_ir", "codegen")


def intent_preservation(
    intent: dict | None,
    intent_loss: dict | None,
    *,
    stage_errors: dict | None = None,
) -> EdgeEvalResult:
    """Score whether every canonical intent phrase survived every stage.

    Args:
        intent: `capture["intent"]` — `{"entities": [...], "operations": [...]}`.
            If None or empty, the edge is treated as fully preserved (no
            signal either way) rather than penalized.
        intent_loss: `capture["intent_loss"]` — `{stage: {...IntentLoss dict...}}`.
        stage_errors: Optional `capture["stage_errors"]`. If the intent
            extract step itself errored, we flag it in missing and return 0.

    Returns:
        EdgeEvalResult with edge="intent_preservation".
    """
    if stage_errors and "intent_extract" in stage_errors:
        return EdgeEvalResult(
            edge="intent_preservation",
            score=0,
            missing=[f"intent_extract:{stage_errors['intent_extract']}"],
            extra={"reason": "extract_failed"},
        )

    intent_dict = intent if isinstance(intent, dict) else {}
    entities = intent_dict.get("entities") or []
    operations = intent_dict.get("operations") or []
    intent_count = len(entities) + len(operations)

    # No canonical intent to anchor against → no signal. Return "preserved"
    # rather than punishing the case; the 4 existing edge evaluators still
    # cover pairwise handoffs. Zero-intent cases show up in extra for audit.
    if intent_count == 0:
        return EdgeEvalResult(
            edge="intent_preservation",
            score=1,
            missing=[],
            extra={
                "reason": "empty_intent",
                "entity_count": 0,
                "operation_count": 0,
                "stages_checked": 0,
            },
        )

    loss_dict = intent_loss if isinstance(intent_loss, dict) else {}

    missing: list[str] = []
    per_stage_rates: dict[str, float] = {}
    per_stage_lost: dict[str, list[str]] = {}
    stages_checked = 0

    for stage in INTENT_CHECK_STAGES:
        record = loss_dict.get(stage)
        if not isinstance(record, dict):
            # Stage wasn't reached (upstream stage crashed). Record as a
            # non-check rather than a loss — missing stage info is not
            # the same signal as "intent dropped at this stage".
            continue
        stages_checked += 1
        rate = record.get("preservation_rate")
        if isinstance(rate, (int, float)):
            per_stage_rates[stage] = float(rate)

        lost_here: list[str] = []
        for phrase in record.get("lost_entities") or []:
            lost_here.append(f"entity:{phrase}")
            missing.append(f"{stage}:entity:{phrase}")
        for phrase in record.get("lost_operations") or []:
            lost_here.append(f"operation:{phrase}")
            missing.append(f"{stage}:operation:{phrase}")
        per_stage_lost[stage] = lost_here

    if stages_checked == 0:
        # Intent existed but no stage ran far enough to be checked.
        # Upstream crash — not an intent-tracker failure. Mark as 0 with a
        # clear reason so diff reports don't silently flip it to "preserved".
        return EdgeEvalResult(
            edge="intent_preservation",
            score=0,
            missing=["intent_check:no_stages_reached"],
            extra={
                "reason": "upstream_crash",
                "entity_count": len(entities),
                "operation_count": len(operations),
                "stages_checked": 0,
            },
        )

    # Final score: binary — any loss on any checked stage → 0
    final_score = 1 if not missing else 0

    # Aggregate preservation = mean of per-stage rates over the stages
    # that ran. This is the single scalar that feeds the 5-dim vector.
    if per_stage_rates:
        overall_rate = sum(per_stage_rates.values()) / len(per_stage_rates)
    else:
        overall_rate = 1.0 if not missing else 0.0

    extra: dict[str, Any] = {
        "entity_count": len(entities),
        "operation_count": len(operations),
        "stages_checked": stages_checked,
        "per_stage_rate": per_stage_rates,
        "per_stage_lost": per_stage_lost,
        "overall_rate": round(overall_rate, 4),
    }

    return EdgeEvalResult(
        edge="intent_preservation",
        score=final_score,
        missing=missing,
        extra=extra,
    )
