"""Week 5 D1 — tests for intent injection into the pseudo_ir prompt.

Focus:
- `_format_intent_hint` renders entity/operation blocks deterministically
- `build_prompt_pseudocode` is unchanged when intent is None (control arm)
- `build_prompt_pseudocode` prepends the hint block when intent is present
- Empty intent (no entities + no operations) behaves like None — this
  matters because `IntentSchema.is_empty()` cases should not accidentally
  inject a malformed empty block.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Stub external deps so importing llm_pseudocode doesn't need openai.
_mock_openai = MagicMock()
_mock_client = MagicMock()
_mock_openai.OpenAI = MagicMock(return_value=_mock_client)
sys.modules.setdefault("openai", _mock_openai)

_mock_dotenv = MagicMock()
_mock_dotenv.load_dotenv = MagicMock()
sys.modules.setdefault("dotenv", _mock_dotenv)

from studio.ai.llm_pseudocode import (  # noqa: E402
    _format_intent_hint,
    build_prompt_pseudocode,
)


def test_format_intent_hint_none_returns_empty_string():
    assert _format_intent_hint(None) == ""


def test_format_intent_hint_empty_dict_returns_empty_string():
    assert _format_intent_hint({}) == ""


def test_format_intent_hint_empty_lists_returns_empty_string():
    assert _format_intent_hint({"entities": [], "operations": []}) == ""


def test_format_intent_hint_entities_only():
    hint = _format_intent_hint({"entities": ["array", "pointer"], "operations": []})
    assert "REQUIRED intent" in hint
    assert "* array" in hint
    assert "* pointer" in hint
    # No Operations block when operations list is empty
    assert "Operations that MUST" not in hint


def test_format_intent_hint_operations_only():
    hint = _format_intent_hint(
        {"entities": [], "operations": ["swap elements", "highlight pivot"]}
    )
    assert "REQUIRED intent" in hint
    assert "Entities that MUST" not in hint
    assert "* swap elements" in hint
    assert "* highlight pivot" in hint


def test_format_intent_hint_full_block():
    intent = {
        "entities": ["hash bucket", "key"],
        "operations": ["insert key into bucket"],
    }
    hint = _format_intent_hint(intent)
    assert "REQUIRED intent" in hint
    assert "Entities that MUST" in hint
    assert "Operations that MUST" in hint
    for token in ("hash bucket", "key", "insert key into bucket"):
        assert f"* {token}" in hint
    # The compliance rule about case-insensitive matching is still in there
    assert "case-insensitive" in hint


def test_build_prompt_pseudocode_control_arm_unchanged():
    """When intent is None (injection OFF), the prompt must match the
    exact pre-Week-5 behavior so the control arm stays comparable across
    Experiment C and Experiment B runs."""
    user_text = "Bubble sort 5 elements with comparison swaps"
    prompt_off = build_prompt_pseudocode(user_text)
    assert "REQUIRED intent" not in prompt_off
    assert "Text to convert:" in prompt_off
    assert user_text in prompt_off


def test_build_prompt_pseudocode_injection_prepends_hint():
    user_text = "BFS from node 0 in a 5-node graph"
    intent = {
        "entities": ["node", "edge", "visited set"],
        "operations": ["enqueue neighbor", "mark visited"],
    }
    prompt_on = build_prompt_pseudocode(user_text, intent=intent)

    # Hint block comes BEFORE the user text block so the LLM reads it first.
    idx_hint = prompt_on.index("REQUIRED intent")
    idx_text = prompt_on.index("Text to convert:")
    assert idx_hint < idx_text

    # Every canonical token shows up verbatim.
    for tok in ("node", "edge", "visited set", "enqueue neighbor", "mark visited"):
        assert f"* {tok}" in prompt_on


def test_build_prompt_pseudocode_empty_intent_matches_control():
    """Empty intent (None or empty lists) must produce the same prompt as
    injection OFF. Otherwise Stage 0 failures would contaminate the
    control arm with a phantom (empty) hint block."""
    user_text = "trivial example"
    control = build_prompt_pseudocode(user_text)
    with_none = build_prompt_pseudocode(user_text, intent=None)
    with_empty = build_prompt_pseudocode(
        user_text, intent={"entities": [], "operations": []}
    )
    assert control == with_none == with_empty
