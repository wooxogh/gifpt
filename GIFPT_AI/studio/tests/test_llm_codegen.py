"""Tests for llm_codegen utility functions and input normalization.

Mocks openai and dotenv so no env vars or packages needed.
Run from GIFPT_AI/: python3 -m unittest studio.tests.test_llm_codegen
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

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


class TestQAFeedbackNormalization(unittest.TestCase):
    """call_llm_codegen_with_qa_feedback input normalization."""

    def _call(self, qa_issues):
        _setup_mock_response()
        return call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, qa_issues
        )

    def test_none_issues(self):
        result = self._call(None)
        self.assertIn("AlgorithmScene", result)

    def test_empty_string(self):
        result = self._call("")
        self.assertIn("AlgorithmScene", result)

    def test_single_string(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, "overlapping elements"
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        self.assertIn("overlapping elements", user_msg)

    def test_list_of_strings(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, ["overlap", "unreadable text"]
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        self.assertIn("- overlap", user_msg)
        self.assertIn("- unreadable text", user_msg)

    def test_whitespace_only_filtered(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, ["  ", "", "real issue"]
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        self.assertIn("- real issue", user_msg)

    def test_truncation_at_max(self):
        mock = _setup_mock_response()
        issues = [f"issue {i}" for i in range(30)]
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, issues
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        self.assertIn(f"issue {MAX_QA_ISSUES - 1}", user_msg)
        self.assertNotIn(f"issue {MAX_QA_ISSUES + 5}", user_msg)

    def test_non_iterable_fallback(self):
        result = self._call(42)
        self.assertIn("AlgorithmScene", result)

    def test_empty_list_falls_back_to_standard(self):
        mock = _setup_mock_response()
        call_llm_codegen_with_qa_feedback(
            {"entities": [], "actions": []}, []
        )
        call_args = mock.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][-1]["content"]
        # Empty list should not include QA feedback section
        self.assertNotIn("quality issues detected by Vision QA", user_msg)


class TestBuildFewShotSystemPrompt(unittest.TestCase):
    """_build_few_shot_system_prompt edge cases."""

    def test_empty_examples(self):
        result = _build_few_shot_system_prompt([])
        self.assertIn("PEDAGOGICAL RULES", result)
        self.assertIn("AlgorithmScene", result)

    def test_example_with_none_code(self):
        # code=None should not crash
        result = _build_few_shot_system_prompt([
            {"tag": "test", "pattern_type": "SEQ", "quality_score": 5, "code": None}
        ])
        self.assertIn("example_1", result)

    def test_example_with_missing_keys(self):
        result = _build_few_shot_system_prompt([{}])
        self.assertIn("example_1", result)


class TestSharedConstants(unittest.TestCase):
    """Verify shared constants are used in prompts."""

    def test_system_prompt_contains_pedagogical_rules(self):
        self.assertIn("CAUSE BEFORE EFFECT", SYSTEM_PROMPT)

    def test_few_shot_prompt_contains_pedagogical_rules(self):
        prompt = _build_few_shot_system_prompt([])
        self.assertIn("CAUSE BEFORE EFFECT", prompt)

    def test_pedagogical_constants_not_empty(self):
        self.assertGreater(len(PEDAGOGICAL_RULES_FULL), 100)
        self.assertGreater(len(PEDAGOGICAL_RULES_CONDENSED), 100)

    def test_model_constants(self):
        self.assertTrue(MODEL_PRIMARY)
        self.assertTrue(MODEL_FAST)
        self.assertNotEqual(MODEL_PRIMARY, MODEL_FAST)


if __name__ == "__main__":
    unittest.main()
