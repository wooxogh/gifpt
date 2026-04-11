"""Tests for llm_codegen utility functions and input normalization.

Run from GIFPT_AI/: python3 -m pytest studio/tests/test_llm_codegen.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Project root on path
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Mock external packages BEFORE importing llm_codegen
_mock_openai = MagicMock()
_mock_client = MagicMock()
_mock_openai.OpenAI = MagicMock(return_value=_mock_client)
sys.modules.setdefault("openai", _mock_openai)
sys.modules.setdefault("dotenv", MagicMock())

from studio.ai.llm_codegen import (  # noqa: E402
    _build_few_shot_system_prompt,
    _build_intent_context,
    _build_attempt_history_context,
    call_llm_codegen_fix,
    call_llm_codegen_with_qa_feedback,
    SYSTEM_PROMPT,
    PEDAGOGICAL_RULES_FULL,
    PEDAGOGICAL_RULES_CONDENSED,
    MODEL_PRIMARY,
    MODEL_FAST,
    MAX_QA_ISSUES,
)


def _setup_mock_response():
    """Configure the mock client to return valid Manim code."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = (
        "from manim import *\n\nclass AlgorithmScene(Scene):\n"
        "    def construct(self):\n        self.wait(1)\n"
    )
    mock_resp.usage = None
    _mock_client.chat.completions.create.return_value = mock_resp
    return _mock_client


class TestQAFeedbackNormalization:
    """call_llm_codegen_with_qa_feedback input normalization."""

    def _call(self, qa_issues):
        _setup_mock_response()
        return call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, qa_issues
        )

    def test_none_issues(self):
        result = self._call(None)
        assert "AlgorithmScene" in result

    def test_empty_string(self):
        result = self._call("")
        assert "AlgorithmScene" in result

    def test_single_string(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, "overlapping elements"
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert "overlapping elements" in user_msg

    def test_list_of_strings(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, ["overlap", "unreadable text"]
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert "- overlap" in user_msg
        assert "- unreadable text" in user_msg

    def test_whitespace_only_filtered(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, ["  ", "", "real issue"]
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert "- real issue" in user_msg

    def test_truncation_at_max(self):
        mock = _setup_mock_response()
        issues = [f"issue {i}" for i in range(30)]
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, issues
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert f"issue {MAX_QA_ISSUES - 1}" in user_msg
        assert f"issue {MAX_QA_ISSUES + 5}" not in user_msg

    def test_non_iterable_fallback(self):
        result = self._call(42)
        assert "AlgorithmScene" in result

    def test_empty_list_falls_back_to_standard(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, []
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        # Empty list should not include QA feedback section
        assert "quality issues detected by Vision QA" not in user_msg


class TestBuildFewShotSystemPrompt:
    """_build_few_shot_system_prompt edge cases."""

    def test_empty_examples(self):
        result = _build_few_shot_system_prompt([])
        assert "PEDAGOGICAL RULES" in result
        assert "AlgorithmScene" in result

    def test_example_with_none_code(self):
        # code=None should not crash
        result = _build_few_shot_system_prompt([
            {"tag": "test", "pattern_type": "SEQ", "quality_score": 5, "code": None}
        ])
        assert "example_1" in result

    def test_example_with_missing_keys(self):
        result = _build_few_shot_system_prompt([{}])
        assert "example_1" in result


class TestBuildIntentContext:
    """_build_intent_context helper for self-healing fix prompts."""

    def test_none_inputs(self):
        assert _build_intent_context(None, None) == ""

    def test_algorithm_name_only(self):
        result = _build_intent_context("bubble sort", None)
        assert "Algorithm: bubble sort" in result

    def test_anim_ir_with_metadata(self):
        ir = {
            "metadata": {"title": "Merge Sort", "domain": "sorting"},
            "layout": [
                {"shape": "array", "id": "arr"},
                {"shape": "rectangle", "id": "ptr"},
            ],
            "actions": [
                {"animation": "fade_in"},
                {"animation": "highlight"},
                {"animation": "swap"},
            ],
        }
        result = _build_intent_context(None, ir)
        assert "Topic: Merge Sort" in result
        assert "Layout: 2 elements" in result
        assert "Actions: 3 steps" in result

    def test_both_params(self):
        result = _build_intent_context("dijkstra", {"metadata": {"domain": "graph"}})
        assert "Algorithm: dijkstra" in result
        assert "Topic: graph" in result

    def test_empty_ir(self):
        result = _build_intent_context(None, {})
        assert result == ""

    def test_layout_as_string_ignored(self):
        """Non-list layout should be silently ignored, not produce 'Layout: 10 elements'."""
        result = _build_intent_context(None, {"layout": "not a list"})
        assert "Layout" not in result

    def test_actions_as_dict_ignored(self):
        result = _build_intent_context(None, {"actions": {"step": 1}})
        assert "Actions" not in result

    def test_layout_with_non_dict_items(self):
        """Layout items that aren't dicts should not appear in shape preview."""
        ir = {"layout": [{"shape": "array"}, "bad_item", 42]}
        result = _build_intent_context(None, ir)
        assert "Layout: 3 elements" in result
        assert "array" in result


class TestBuildAttemptHistoryContext:
    """_build_attempt_history_context helper for self-healing fix prompts."""

    def test_none_history(self):
        assert _build_attempt_history_context(None) == ""

    def test_empty_history(self):
        assert _build_attempt_history_context([]) == ""

    def test_single_attempt(self):
        history = [{"attempt": 1, "error_type": "runtime_name", "stderr": "NameError: name 'x' is not defined"}]
        result = _build_attempt_history_context(history)
        assert "Attempt 1" in result
        assert "runtime_name" in result
        assert "NameError" in result

    def test_caps_at_three_entries(self):
        history = [{"attempt": i, "error_type": f"err_{i}", "stderr": f"Error {i}"} for i in range(5)]
        result = _build_attempt_history_context(history)
        # Should only include the last 3
        assert "Attempt 2" in result
        assert "Attempt 4" in result
        assert "Attempt 0" not in result


class TestCodegenFixWithContext:
    """call_llm_codegen_fix with enhanced context parameters."""

    def test_fix_includes_algorithm_name(self):
        mock = _setup_mock_response()
        call_llm_codegen_fix(
            "from manim import *\nbroken code",
            "runtime_name",
            "NameError: name 'x' is not defined",
            algorithm_name="quicksort",
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert "Algorithm: quicksort" in user_msg
        assert "ORIGINAL INTENT" in user_msg

    def test_fix_includes_anim_ir(self):
        mock = _setup_mock_response()
        ir = {"metadata": {"title": "BFS"}, "layout": [{"shape": "graph", "id": "g"}], "actions": [{"animation": "highlight"}]}
        call_llm_codegen_fix(
            "from manim import *\nbroken",
            "runtime_attr",
            "AttributeError: no attr",
            anim_ir=ir,
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert "Topic: BFS" in user_msg
        assert "Layout: 1 elements" in user_msg

    def test_fix_includes_attempt_history(self):
        mock = _setup_mock_response()
        history = [
            {"attempt": 1, "error_type": "runtime_name", "stderr": "NameError: name 'highlight_rect'"},
            {"attempt": 2, "error_type": "runtime_attr", "stderr": "AttributeError: 'VGroup' object"},
        ]
        call_llm_codegen_fix(
            "from manim import *\ncode",
            "runtime_type",
            "TypeError: unsupported",
            attempt_history=history,
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        assert "Previous failed attempts" in user_msg
        assert "Attempt 1" in user_msg
        assert "Attempt 2" in user_msg

    def test_fix_backward_compatible(self):
        """Calling without new params still works (backward compat)."""
        _setup_mock_response()
        result = call_llm_codegen_fix("from manim import *\ncode", "runtime", "some error")
        assert "AlgorithmScene" in result


class TestSharedConstants:
    """Verify shared constants are used in prompts."""

    def test_system_prompt_contains_pedagogical_rules(self):
        assert "CAUSE BEFORE EFFECT" in SYSTEM_PROMPT

    def test_few_shot_prompt_contains_pedagogical_rules(self):
        prompt = _build_few_shot_system_prompt([])
        assert "CAUSE BEFORE EFFECT" in prompt

    def test_pedagogical_constants_not_empty(self):
        assert len(PEDAGOGICAL_RULES_FULL) > 100
        assert len(PEDAGOGICAL_RULES_CONDENSED) > 100

    def test_model_constants(self):
        assert MODEL_PRIMARY
        assert MODEL_FAST
        assert MODEL_PRIMARY != MODEL_FAST
