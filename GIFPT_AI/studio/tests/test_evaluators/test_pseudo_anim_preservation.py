"""Tests for pseudo_ir → anim_ir edge preservation evaluator.

Run from GIFPT_AI/: python3 -m pytest studio/tests/test_evaluators/ -v
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from studio.evaluators.pseudo_anim_preservation import pseudo_anim_preservation  # noqa: E402


PSEUDO_IR_GOOD = {
    "metadata": {"title": "Bubble Sort"},
    "entities": [
        {"id": "array", "type": "array"},
        {"id": "pointer_i", "type": "pointer"},
    ],
    "operations": [
        {"step": 1, "subject": "array", "action": "create"},
        {"step": 2, "subject": "pointer_i", "action": "move", "target": "array"},
        {"step": 3, "subject": "array", "action": "swap"},
    ],
}

ANIM_IR_GOOD = {
    "metadata": {"domain": "sorting", "title": "Bubble Sort"},
    "layout": [
        {"id": "array", "shape": "array", "position": [0, 0]},
        {"id": "pointer_i", "shape": "Arrow", "position": [0, -1]},
    ],
    "actions": [
        {"step": 1, "target": "array", "animation": "fade_in"},
        {"step": 2, "target": "pointer_i", "animation": "move"},
        {"step": 3, "target": "array", "animation": "swap"},
    ],
}


def test_known_good_case_scores_one():
    result = pseudo_anim_preservation(PSEUDO_IR_GOOD, ANIM_IR_GOOD)
    assert result.score == 1, f"expected pass, got missing={result.missing}"
    assert result.edge == "pseudo_anim"
    assert result.missing == []
    assert result.extra["pseudo_entity_count"] == 2
    assert result.extra["anim_layout_count"] == 2


def test_missing_entity_in_anim_layout_fails():
    bad_anim = dict(ANIM_IR_GOOD)
    bad_anim["layout"] = [{"id": "array", "shape": "array", "position": [0, 0]}]
    result = pseudo_anim_preservation(PSEUDO_IR_GOOD, bad_anim)
    assert result.score == 0
    assert "entity:pointer_i" in result.missing


def test_missing_operation_subject_fails():
    bad_pseudo = {
        "entities": [{"id": "array", "type": "array"}],
        "operations": [
            {"step": 1, "subject": "array", "action": "create"},
            {"step": 2, "subject": "ghost_entity", "action": "poof"},
        ],
    }
    result = pseudo_anim_preservation(bad_pseudo, ANIM_IR_GOOD)
    assert result.score == 0
    assert any("ghost_entity" in m for m in result.missing)


def test_empty_pseudo_ir_fails():
    result = pseudo_anim_preservation({}, ANIM_IR_GOOD)
    assert result.score == 0
    assert "pseudo_ir:no_entities" in result.missing
    assert "pseudo_ir:no_operations" in result.missing


def test_feedback_payload_shape():
    result = pseudo_anim_preservation(PSEUDO_IR_GOOD, ANIM_IR_GOOD)
    fb = result.as_feedback()
    assert fb["key"] == "pseudo_anim_preservation"
    assert fb["score"] == 1.0
    assert fb["value"]["edge"] == "pseudo_anim"
    assert fb["value"]["missing"] == []
