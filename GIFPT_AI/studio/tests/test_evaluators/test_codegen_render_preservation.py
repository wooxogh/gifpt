"""Tests for manim_code → render edge preservation evaluator."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

from studio.evaluators.codegen_render_preservation import codegen_render_preservation  # noqa: E402


CODE_CLEAN = (
    "from manim import *\n\n"
    "class AlgorithmScene(Scene):\n"
    "    def construct(self):\n"
    "        self.play(FadeIn(Circle()))\n"
    "        self.wait(1)\n"
)

CODE_FORBIDDEN_API = (
    "from manim import *\n\n"
    "class AlgorithmScene(Scene):\n"
    "    def construct(self):\n"
    "        t = Matrix([[1, 2], [3, 4]])\n"  # Matrix is forbidden
    "        self.add(t)\n"
)


def test_successful_render_scores_one():
    render_result = {
        "success": True,
        "duration_s": 12.5,
        "error_type": None,
        "video_path": "/tmp/foo.mp4",
    }
    result = codegen_render_preservation(CODE_CLEAN, render_result)
    assert result.score == 1, f"expected pass, got missing={result.missing}"
    assert result.edge == "codegen_render"
    assert result.extra["forbidden_ast"] == []


def test_render_failure_scores_zero():
    render_result = {
        "success": False,
        "duration_s": 2.1,
        "error_type": "runtime_name",
        "error_message": "NameError: Graph not defined",
        "video_path": None,
    }
    result = codegen_render_preservation(CODE_CLEAN, render_result)
    assert result.score == 0
    assert "render:runtime_name" in result.missing


def test_forbidden_ast_scores_zero():
    render_result = {"success": True, "duration_s": 5.0, "video_path": "/tmp/x.mp4"}
    result = codegen_render_preservation(CODE_FORBIDDEN_API, render_result)
    assert result.score == 0
    assert any(m.startswith("ast:forbidden_api") for m in result.missing)
    assert len(result.extra["forbidden_ast"]) >= 1


def test_timeout_budget_violation():
    render_result = {
        "success": True,
        "duration_s": 250.0,
        "error_type": None,
        "video_path": "/tmp/slow.mp4",
    }
    result = codegen_render_preservation(
        CODE_CLEAN, render_result, timeout_budget_s=180.0
    )
    assert result.score == 0
    assert any("timeout:" in m for m in result.missing)
    assert result.extra["budget_ok"] is False


def test_missing_video_path_fails():
    render_result = {"success": True, "duration_s": 5.0}
    result = codegen_render_preservation(CODE_CLEAN, render_result)
    assert result.score == 0
    assert "render:no_output_path" in result.missing
