"""Edge evaluator: pseudo_ir → anim_ir.

Entity preservation: every pseudo_ir entity id must appear in the anim_ir layout.
Operation preservation: every pseudo_ir operation must have an anim_ir action
whose target references the operation's subject entity.

A single missing item drops the edge score to 0; the missing list carries
the diagnostic so run-diff can explain *what* was lost, not just "fail".
"""
from __future__ import annotations

from typing import Any

from studio.evaluators.base import EdgeEvalResult


def _get_list(d: Any, key: str) -> list[dict]:
    if not isinstance(d, dict):
        return []
    value = d.get(key)
    return value if isinstance(value, list) else []


def _entity_ids(pseudo_ir: dict) -> set[str]:
    return {
        e.get("id")
        for e in _get_list(pseudo_ir, "entities")
        if isinstance(e, dict) and isinstance(e.get("id"), str) and e.get("id")
    }


def _layout_ids(anim_ir: dict) -> set[str]:
    return {
        item.get("id")
        for item in _get_list(anim_ir, "layout")
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id")
    }


def _action_targets(anim_ir: dict) -> set[str]:
    targets: set[str] = set()
    for act in _get_list(anim_ir, "actions"):
        if not isinstance(act, dict):
            continue
        target = act.get("target")
        if isinstance(target, str) and target:
            targets.add(target)
    return targets


def pseudo_anim_preservation(pseudo_ir: dict, anim_ir: dict) -> EdgeEvalResult:
    """Score the pseudo_ir → anim_ir handoff.

    Returns score=1 when every pseudo entity id appears in anim layout AND
    every pseudo operation's subject is the target of at least one anim action.
    """
    missing: list[str] = []

    pseudo_entities = _entity_ids(pseudo_ir)
    anim_entities = _layout_ids(anim_ir)

    for ent_id in sorted(pseudo_entities):
        if ent_id not in anim_entities:
            missing.append(f"entity:{ent_id}")

    anim_targets = _action_targets(anim_ir)
    operations = _get_list(pseudo_ir, "operations")

    pseudo_subjects_seen: list[str] = []
    for op in operations:
        if not isinstance(op, dict):
            continue
        subject = op.get("subject")
        if not isinstance(subject, str) or not subject:
            continue
        pseudo_subjects_seen.append(subject)
        if subject not in anim_targets:
            action = op.get("action") or "?"
            missing.append(f"operation:{subject}/{action}")

    extra = {
        "pseudo_entity_count": len(pseudo_entities),
        "anim_layout_count": len(anim_entities),
        "pseudo_operation_count": len(pseudo_subjects_seen),
        "anim_action_count": len(_get_list(anim_ir, "actions")),
    }

    score = 1 if not missing and pseudo_entities and operations else 0
    if not pseudo_entities:
        missing.append("pseudo_ir:no_entities")
    if not operations:
        missing.append("pseudo_ir:no_operations")

    return EdgeEvalResult(edge="pseudo_anim", score=score, missing=missing, extra=extra)
