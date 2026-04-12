"""Tests for anim_ir → manim_code edge preservation evaluator."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

from studio.evaluators.anim_codegen_preservation import anim_codegen_preservation  # noqa: E402


ANIM_IR = {
    "metadata": {"domain": "sorting"},
    "layout": [
        {"id": "input_matrix", "shape": "matrix", "position": [-4, 0], "label": "Input"},
        {"id": "kernel", "shape": "matrix", "position": [0, 0], "label": "Kernel"},
    ],
    "actions": [
        {"step": 1, "target": "input_matrix", "animation": "fade_in"},
        {"step": 2, "target": "kernel", "animation": "fade_in"},
    ],
}

CODE_GOOD = (
    "from manim import *\n\n"
    "class AlgorithmScene(Scene):\n"
    "    def construct(self):\n"
    "        input_matrix_label = Text('Input matrix')\n"
    "        kernel_label = Text('Kernel')\n"
    "        self.play(FadeIn(input_matrix_label), FadeIn(kernel_label))\n"
    "        self.wait(1)\n"
)

CODE_HALLUCINATED_HELPER = (
    "from manim import *\n\n"
    "class AlgorithmScene(Scene):\n"
    "    def construct(self):\n"
    "        input_matrix = Text('Input matrix')\n"
    "        kernel = Text('Kernel')\n"
    "        self.play(FadeIn(input_matrix))\n"
    "        Highlight(kernel)\n"  # hallucinated
    "        self.wait(1)\n"
)


def test_known_good_case_scores_one():
    result = anim_codegen_preservation(
        ANIM_IR,
        CODE_GOOD,
        unknown_helpers={"Highlight", "Focus", "Emphasize"},
        forbidden_names={"Matrix", "DashedLine"},
    )
    assert result.score == 1, f"expected pass, got missing={result.missing}"
    assert result.edge == "anim_codegen"
    assert result.extra["hallucinated"] == []


def test_hallucinated_helper_fails():
    result = anim_codegen_preservation(
        ANIM_IR,
        CODE_HALLUCINATED_HELPER,
        unknown_helpers={"Highlight", "Focus", "Emphasize"},
        forbidden_names=set(),
    )
    assert result.score == 0
    assert "hallucinated:Highlight" in result.missing
    assert result.extra["hallucinated"] == ["Highlight"]


def test_missing_layout_id_fails():
    partial_code = (
        "from manim import *\n"
        "class AlgorithmScene(Scene):\n"
        "    def construct(self):\n"
        "        only_one = Text('Input matrix')\n"
        "        self.wait(1)\n"
    )
    result = anim_codegen_preservation(
        ANIM_IR,
        partial_code,
        unknown_helpers=set(),
        forbidden_names=set(),
    )
    assert result.score == 0
    assert "layout_id:kernel" in result.missing


def test_empty_code_fails():
    result = anim_codegen_preservation(ANIM_IR, "", unknown_helpers=set(), forbidden_names=set())
    assert result.score == 0
    assert "manim_code:empty" in result.missing


def test_syntax_error_flagged():
    broken = "def wrong(\n"
    result = anim_codegen_preservation(
        ANIM_IR, broken, unknown_helpers=set(), forbidden_names=set()
    )
    assert result.score == 0
    assert any(m.startswith("syntax:") for m in result.missing)
