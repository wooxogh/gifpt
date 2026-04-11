"""Tests for Pydantic-based deep IR validation.

Run from GIFPT_AI/: python3 -m pytest studio/tests/test_ir_deep_validation.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Mock external packages before importing qa
sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

from studio.ai.qa import (  # noqa: E402
    validate_pseudocode_ir_deep,
    validate_anim_ir_deep,
    PseudocodeIR,
    AnimIR,
)


# ── Pseudocode IR ────────────────────────────────────────────────────────────


class TestPseudocodeIRDeepValid:
    def test_valid_ir_passes(self):
        ir = {
            "metadata": {"title": "Bubble Sort"},
            "entities": [
                {"id": "arr", "type": "array", "attributes": {"size": 5}},
                {"id": "ptr", "type": "pointer"},
            ],
            "operations": [
                {"step": 1, "subject": "arr", "action": "create"},
                {"step": 2, "subject": "ptr", "action": "highlight", "target": "arr"},
            ],
        }
        assert validate_pseudocode_ir_deep(ir) == []

    def test_minimal_valid(self):
        ir = {
            "entities": [{"id": "a", "type": "x"}],
            "operations": [
                {"subject": "a", "action": "create"},
                {"subject": "a", "action": "highlight"},
            ],
        }
        assert validate_pseudocode_ir_deep(ir) == []


class TestPseudocodeIRDeepInvalid:
    def test_missing_entities(self):
        ir = {"operations": [{"subject": "x", "action": "y"}, {"subject": "x", "action": "z"}]}
        issues = validate_pseudocode_ir_deep(ir)
        assert len(issues) > 0

    def test_too_few_operations(self):
        ir = {
            "entities": [{"id": "a", "type": "x"}],
            "operations": [{"subject": "a", "action": "create"}],
        }
        issues = validate_pseudocode_ir_deep(ir)
        assert any("too_short" in i or "least 2" in i for i in issues)

    def test_entity_missing_id(self):
        ir = {
            "entities": [{"type": "array"}],
            "operations": [
                {"subject": "a", "action": "x"},
                {"subject": "a", "action": "y"},
            ],
        }
        issues = validate_pseudocode_ir_deep(ir)
        assert len(issues) > 0

    def test_operation_references_nonexistent_entity(self):
        ir = {
            "entities": [{"id": "arr", "type": "array"}],
            "operations": [
                {"subject": "arr", "action": "create"},
                {"subject": "nonexistent", "action": "highlight"},
            ],
        }
        issues = validate_pseudocode_ir_deep(ir)
        assert any("nonexistent" in i for i in issues)

    def test_operation_target_references_nonexistent_entity(self):
        ir = {
            "entities": [{"id": "arr", "type": "array"}],
            "operations": [
                {"subject": "arr", "action": "create"},
                {"subject": "arr", "action": "move", "target": "ghost"},
            ],
        }
        issues = validate_pseudocode_ir_deep(ir)
        assert any("ghost" in i for i in issues)

    def test_not_a_dict(self):
        issues = validate_pseudocode_ir_deep("not a dict")
        assert len(issues) > 0


# ── Animation IR ─────────────────────────────────────────────────────────────


class TestAnimIRDeepValid:
    def test_valid_ir_passes(self):
        ir = {
            "metadata": {"domain": "sorting"},
            "layout": [
                {"id": "arr", "shape": "array", "position": [0, 0]},
                {"id": "ptr", "shape": "circle", "position": [-3.0, 2.0]},
            ],
            "actions": [
                {"step": 1, "target": "arr", "animation": "fade_in"},
                {"step": 2, "target": "ptr", "animation": "highlight"},
            ],
        }
        assert validate_anim_ir_deep(ir) == []


class TestAnimIRDeepInvalid:
    def test_position_out_of_bounds_x(self):
        ir = {
            "layout": [{"id": "a", "shape": "rect", "position": [15.0, 0]}],
            "actions": [
                {"animation": "fade_in"},
                {"animation": "fade_out"},
            ],
        }
        issues = validate_anim_ir_deep(ir)
        assert any("out of scene bounds" in i for i in issues)

    def test_position_out_of_bounds_y(self):
        ir = {
            "layout": [{"id": "a", "shape": "rect", "position": [0, 10.0]}],
            "actions": [
                {"animation": "fade_in"},
                {"animation": "fade_out"},
            ],
        }
        issues = validate_anim_ir_deep(ir)
        assert any("out of scene bounds" in i for i in issues)

    def test_action_target_nonexistent(self):
        ir = {
            "layout": [{"id": "arr", "shape": "array", "position": [0, 0]}],
            "actions": [
                {"target": "arr", "animation": "fade_in"},
                {"target": "nonexistent", "animation": "highlight"},
            ],
        }
        issues = validate_anim_ir_deep(ir)
        assert any("nonexistent" in i for i in issues)

    def test_duplicate_layout_ids(self):
        ir = {
            "layout": [
                {"id": "arr", "shape": "array", "position": [0, 0]},
                {"id": "arr", "shape": "circle", "position": [1, 1]},
            ],
            "actions": [
                {"animation": "fade_in"},
                {"animation": "fade_out"},
            ],
        }
        issues = validate_anim_ir_deep(ir)
        assert any("Duplicate" in i or "duplicate" in i.lower() for i in issues)

    def test_missing_layout(self):
        ir = {"actions": [{"animation": "x"}, {"animation": "y"}]}
        issues = validate_anim_ir_deep(ir)
        assert len(issues) > 0

    def test_too_few_actions(self):
        ir = {
            "layout": [{"id": "a", "shape": "rect", "position": [0, 0]}],
            "actions": [{"animation": "fade_in"}],
        }
        issues = validate_anim_ir_deep(ir)
        assert any("least 2" in i or "too_short" in i for i in issues)

    def test_position_exactly_at_boundary(self):
        """Positions exactly at scene edge should pass."""
        ir = {
            "layout": [{"id": "a", "shape": "rect", "position": [-7.1, -4.0]}],
            "actions": [
                {"animation": "fade_in"},
                {"animation": "fade_out"},
            ],
        }
        assert validate_anim_ir_deep(ir) == []

    def test_action_with_no_target_passes(self):
        """Actions without target (e.g., global animations) should pass."""
        ir = {
            "layout": [{"id": "a", "shape": "rect", "position": [0, 0]}],
            "actions": [
                {"animation": "fade_in"},
                {"animation": "wait"},
            ],
        }
        assert validate_anim_ir_deep(ir) == []
