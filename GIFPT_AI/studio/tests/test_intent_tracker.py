"""Tests for intent_tracker.extract_intent + IntentSchema parsing.

Run from GIFPT_AI/: python3 -m pytest studio/tests/test_intent_tracker.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Project root on path
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Mock external packages BEFORE importing intent_tracker
_mock_openai = MagicMock()
_mock_client = MagicMock()
_mock_openai.OpenAI = MagicMock(return_value=_mock_client)
sys.modules.setdefault("openai", _mock_openai)
sys.modules.setdefault("dotenv", MagicMock())

from studio.ai import intent_tracker  # noqa: E402
from studio.ai.intent_tracker import (  # noqa: E402
    IntentLoss,
    IntentSchema,
    _parse_intent_response,
    _serialize_anim_ir,
    _serialize_codegen,
    _serialize_pseudo_ir,
    _tokenize,
    build_intent_prompt,
    check_intent_loss,
    extract_intent,
)


def _make_response(content: str, usage: dict | None = None) -> MagicMock:
    """Build a fake OpenAI chat.completions.create() return value."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    if usage is not None:
        usage_obj = MagicMock()
        usage_obj.prompt_tokens = usage.get("prompt_tokens")
        usage_obj.completion_tokens = usage.get("completion_tokens")
        usage_obj.total_tokens = usage.get("total_tokens")
        resp.usage = usage_obj
    else:
        resp.usage = None
    return resp


# ---------- pure parsing tests (no LLM) ----------


def test_parse_intent_response_happy_path():
    raw = json.dumps(
        {
            "entities": ["input matrix", "kernel"],
            "operations": ["slide kernel right", "compute dot product"],
        }
    )
    result = _parse_intent_response(raw)
    assert isinstance(result, IntentSchema)
    assert result.entities == ["input matrix", "kernel"]
    assert result.operations == ["slide kernel right", "compute dot product"]
    assert not result.is_empty()


def test_parse_intent_response_strips_whitespace_and_empties():
    raw = json.dumps(
        {
            "entities": ["  array  ", "", "pivot"],
            "operations": ["swap elements", "   "],
        }
    )
    result = _parse_intent_response(raw)
    assert result.entities == ["array", "pivot"]
    assert result.operations == ["swap elements"]


def test_parse_intent_response_tolerates_missing_keys():
    raw = json.dumps({"entities": ["node"]})  # operations missing
    result = _parse_intent_response(raw)
    assert result.entities == ["node"]
    assert result.operations == []


def test_parse_intent_response_tolerates_wrong_types():
    # Schema drift: operations arrives as a string instead of list
    raw = json.dumps({"entities": ["a"], "operations": "not a list"})
    result = _parse_intent_response(raw)
    assert result.entities == ["a"]
    assert result.operations == []


def test_parse_intent_response_rejects_non_json():
    import pytest

    with pytest.raises(ValueError, match="invalid JSON"):
        _parse_intent_response("not json at all {")


def test_parse_intent_response_rejects_non_dict():
    import pytest

    with pytest.raises(ValueError, match="expected dict"):
        _parse_intent_response(json.dumps(["a", "b"]))


def test_intent_schema_is_empty():
    assert IntentSchema(entities=[], operations=[]).is_empty()
    assert not IntentSchema(entities=["a"], operations=[]).is_empty()
    assert not IntentSchema(entities=[], operations=["b"]).is_empty()


# ---------- build_intent_prompt ----------


def test_build_intent_prompt_includes_user_text():
    text = "5-node BFS from node 0"
    prompt = build_intent_prompt(text)
    assert "5-node BFS from node 0" in prompt
    assert "JSON" in prompt


def test_build_intent_prompt_strips_surrounding_whitespace():
    prompt = build_intent_prompt("   hello   \n")
    assert "hello" in prompt
    # Leading whitespace should be stripped before insertion
    assert "   hello" not in prompt


# ---------- extract_intent with mocked LLM ----------


def test_extract_intent_calls_llm_and_parses():
    intent_tracker.client.chat.completions.create = MagicMock(
        return_value=_make_response(
            json.dumps(
                {
                    "entities": ["stack", "top pointer"],
                    "operations": ["push element", "pop element"],
                }
            )
        )
    )
    result = extract_intent("A stack with push and pop")
    assert result.entities == ["stack", "top pointer"]
    assert result.operations == ["push element", "pop element"]

    # Verify the LLM was called with gpt-4o (uniform-model principle)
    call_kwargs = intent_tracker.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_extract_intent_with_usage_returns_usage_dict():
    intent_tracker.client.chat.completions.create = MagicMock(
        return_value=_make_response(
            json.dumps({"entities": ["x"], "operations": ["y"]}),
            usage={"prompt_tokens": 42, "completion_tokens": 8, "total_tokens": 50},
        )
    )
    intent, usage = intent_tracker.extract_intent_with_usage("anything")
    assert intent.entities == ["x"]
    assert usage == {"prompt_tokens": 42, "completion_tokens": 8, "total_tokens": 50}


# ---------- realistic fixture ----------


# ---------- Day 2: tokenization + serialization ----------


def test_tokenize_basic():
    tokens = _tokenize("A 4x4 input grid with a kernel.")
    assert "4x4" in tokens
    assert "input" in tokens
    assert "grid" in tokens
    assert "kernel" in tokens
    # stopwords dropped
    assert "the" not in tokens
    assert "a" not in tokens
    assert "with" not in tokens


def test_tokenize_splits_snake_case_and_camel():
    tokens = _tokenize("input_matrix kernel_3x3 MergeSort")
    assert "input" in tokens
    assert "matrix" in tokens
    assert "kernel" in tokens
    assert "3x3" in tokens
    # camelcase falls into a single token — consistent with our lenient policy
    assert "mergesort" in tokens


def test_tokenize_drops_short_tokens():
    tokens = _tokenize("a b cd xyz")
    assert "xyz" in tokens
    assert "b" not in tokens
    assert "cd" not in tokens


def test_serialize_pseudo_ir_flattens_entities_and_operations():
    pseudo_ir = {
        "metadata": {"title": "CNN Forward"},
        "entities": [
            {"id": "input_matrix", "type": "matrix", "attributes": {"padding": 1}},
            {"id": "kernel", "type": "filter"},
        ],
        "operations": [
            {
                "step": 1,
                "subject": "kernel",
                "action": "slide_over",
                "target": "input_matrix",
                "description": "slide kernel right to compute dot product",
            }
        ],
    }
    text = _serialize_pseudo_ir(pseudo_ir)
    assert "input_matrix" in text
    assert "kernel" in text
    assert "slide" in text
    assert "dot product" in text


def test_serialize_anim_ir_flattens_layout_and_actions():
    anim_ir = {
        "metadata": {"title": "BFS", "domain": "graph_traversal"},
        "layout": [
            {"id": "node_0", "shape": "Circle", "label": "start", "dimensions": "r=0.5"},
        ],
        "actions": [
            {"target": "node_0", "animation": "highlight", "description": "turn yellow"},
        ],
    }
    text = _serialize_anim_ir(anim_ir)
    assert "node_0" in text
    assert "Circle" in text
    assert "highlight" in text
    assert "yellow" in text


def test_serialize_codegen_passthrough():
    code = "class Scene: def construct(self): self.play(Write(...))"
    assert _serialize_codegen(code) == code
    assert _serialize_codegen("") == ""


# ---------- Day 2: check_intent_loss ----------


def test_check_intent_loss_all_preserved():
    intent = IntentSchema(
        entities=["input matrix", "kernel"],
        operations=["slide kernel right"],
    )
    pseudo_ir = {
        "entities": [
            {"id": "input_matrix", "type": "matrix"},
            {"id": "kernel", "type": "filter"},
        ],
        "operations": [
            {"subject": "kernel", "action": "slide", "description": "slide kernel right over input"},
        ],
    }
    loss = check_intent_loss(intent, pseudo_ir, "pseudo_ir")
    assert loss.stage == "pseudo_ir"
    assert loss.lost_entities == []
    assert loss.lost_operations == []
    assert loss.preserved_entities == 2
    assert loss.preserved_operations == 1
    assert loss.preservation_rate == 1.0


def test_check_intent_loss_partial_loss():
    intent = IntentSchema(
        entities=["input matrix", "output grid"],
        operations=["slide kernel right", "highlight compared pair"],
    )
    pseudo_ir = {
        "entities": [{"id": "input_matrix", "type": "matrix"}],  # "output grid" missing
        "operations": [
            {"subject": "kernel", "action": "slide", "description": "slide kernel right"},
            # "highlight compared pair" missing
        ],
    }
    loss = check_intent_loss(intent, pseudo_ir, "pseudo_ir")
    assert "output grid" in loss.lost_entities
    assert loss.preserved_entities == 1
    assert "highlight compared pair" in loss.lost_operations
    assert loss.preserved_operations == 1
    assert loss.total_lost == 2
    assert loss.total_checked == 4
    assert loss.preservation_rate == 0.5


def test_check_intent_loss_conservative_false_negative():
    """Day 2 matcher is conservative: a single missing content token
    marks the phrase lost even if a synonym appears. Document this."""
    intent = IntentSchema(entities=["input grid"], operations=[])
    pseudo_ir = {
        "entities": [{"id": "input_matrix", "type": "matrix"}],  # "grid" vs "matrix"
    }
    loss = check_intent_loss(intent, pseudo_ir, "pseudo_ir")
    # "grid" token not present → phrase flagged lost even though semantically preserved
    assert loss.lost_entities == ["input grid"]


def test_check_intent_loss_empty_intent_is_fully_preserved():
    intent = IntentSchema(entities=[], operations=[])
    loss = check_intent_loss(intent, {}, "pseudo_ir")
    assert loss.preservation_rate == 1.0
    assert loss.total_checked == 0


def test_check_intent_loss_anim_ir_stage():
    intent = IntentSchema(
        entities=["stack", "top pointer"],
        operations=["push element"],
    )
    anim_ir = {
        "layout": [
            {"id": "stack_container", "shape": "Rectangle", "label": "Stack"},
            {"id": "top_arrow", "shape": "Arrow", "label": "top pointer"},
        ],
        "actions": [
            {"target": "stack_container", "animation": "fade_in", "description": "push element onto top"},
        ],
    }
    loss = check_intent_loss(intent, anim_ir, "anim_ir")
    assert loss.preserved_entities == 2  # "stack" in stack_container, "top pointer" in label
    assert loss.preserved_operations == 1
    assert loss.preservation_rate == 1.0


def test_check_intent_loss_codegen_stage():
    intent = IntentSchema(
        entities=["input matrix", "kernel"],
        operations=["slide kernel right"],
    )
    code = """
    class ConvScene(Scene):
        def construct(self):
            input_matrix = Matrix([[1,2],[3,4]])
            kernel = Square()
            self.play(kernel.animate.shift(RIGHT))  # slide kernel right
    """
    loss = check_intent_loss(intent, code, "codegen")
    assert loss.preserved_entities == 2
    assert loss.preserved_operations == 1


def test_check_intent_loss_unknown_stage_raises():
    import pytest

    intent = IntentSchema(entities=["x"], operations=[])
    with pytest.raises(ValueError, match="unknown stage"):
        check_intent_loss(intent, {}, "render")


def test_intent_loss_properties():
    loss = IntentLoss(
        stage="pseudo_ir",
        lost_entities=["a", "b"],
        lost_operations=["c"],
        preserved_entities=2,
        preserved_operations=1,
    )
    assert loss.total_lost == 3
    assert loss.total_checked == 6
    assert loss.preservation_rate == 0.5


# ---------- back to pre-existing extraction fixture ----------


def test_extract_intent_fixture_cnn_convolution():
    """A realistic goldset-style description. Verifies the full extract path
    with a mocked LLM response shaped like what gpt-4o actually returns."""
    intent_tracker.client.chat.completions.create = MagicMock(
        return_value=_make_response(
            json.dumps(
                {
                    "entities": ["4x4 input grid", "2x2 kernel", "output grid"],
                    "operations": [
                        "slide kernel over input",
                        "highlight current window",
                        "show output value per step",
                    ],
                }
            )
        )
    )
    result = extract_intent(
        "4x4 input grid + 2x2 kernel; yellow highlight slides over input window "
        "as kernel convolves. Show each output value as computed."
    )
    assert len(result.entities) == 3
    assert len(result.operations) == 3
    assert "kernel" in result.entities[1]
