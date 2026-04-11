"""Tests for AST-based Manim code validation.

Run from GIFPT_AI/: python3 -m pytest studio/tests/test_ast_validation.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

# Mock external packages before importing video_render
sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

from studio.video_render import validate_manim_code_ast  # noqa: E402


class TestSyntaxErrors:
    def test_valid_code_no_issues(self):
        code = (
            "from manim import *\n\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        self.play(FadeIn(Circle()))\n"
            "        self.wait(1)\n"
        )
        assert validate_manim_code_ast(code) == []

    def test_syntax_error_detected(self):
        code = "def broken(\n"
        issues = validate_manim_code_ast(code)
        assert len(issues) == 1
        assert issues[0]["error_type"] == "syntax"
        assert "SyntaxError" in issues[0]["message"]

    def test_syntax_error_returns_early(self):
        """On SyntaxError, should not attempt AST walk."""
        code = "class Foo(:\n    pass"
        issues = validate_manim_code_ast(code)
        assert len(issues) == 1
        assert issues[0]["error_type"] == "syntax"


class TestForbiddenNames:
    def test_matrix_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        m = Matrix([[1,2],[3,4]])\n"
        )
        issues = validate_manim_code_ast(code)
        assert any(i["error_type"] == "forbidden_api" and "Matrix" in i["message"] for i in issues)

    def test_dashed_line_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        line = DashedLine(LEFT, RIGHT)\n"
        )
        issues = validate_manim_code_ast(code)
        assert any("DashedLine" in i["message"] for i in issues)

    def test_mathtex_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        t = MathTex(r'\\frac{1}{2}')\n"
        )
        issues = validate_manim_code_ast(code)
        assert any("MathTex" in i["message"] for i in issues)

    def test_hallucinated_helper_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        AddPointToGraph(self, 1, 2)\n"
        )
        issues = validate_manim_code_ast(code)
        assert any("AddPointToGraph" in i["message"] for i in issues)

    def test_qualified_matrix_detected(self):
        """manim.Matrix(...) should be caught too."""
        code = (
            "import manim\n"
            "class AlgorithmScene(manim.Scene):\n"
            "    def construct(self):\n"
            "        m = manim.Matrix([[1,2]])\n"
        )
        issues = validate_manim_code_ast(code)
        assert any(i["error_type"] == "forbidden_api" and "Matrix" in i["message"] for i in issues)

    def test_aliased_module_detected(self):
        """mn.DashedLine(...) should be caught."""
        code = (
            "import manim as mn\n"
            "class AlgorithmScene(mn.Scene):\n"
            "    def construct(self):\n"
            "        line = mn.DashedLine(mn.LEFT, mn.RIGHT)\n"
        )
        issues = validate_manim_code_ast(code)
        assert any("DashedLine" in i["message"] for i in issues)

    def test_valid_classes_not_flagged(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        c = Circle()\n"
            "        r = Rectangle(width=2, height=1)\n"
            "        t = Text('hello')\n"
            "        a = Arrow(LEFT, RIGHT)\n"
        )
        assert validate_manim_code_ast(code) == []


class TestForbiddenAttrs:
    def test_deepcopy_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        c = Circle()\n"
            "        d = c.deepcopy()\n"
        )
        issues = validate_manim_code_ast(code)
        assert any(i["error_type"] == "forbidden_method" and "deepcopy" in i["message"] for i in issues)

    def test_set_text_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        t = Text('hello')\n"
            "        t.set_text('world')\n"
        )
        issues = validate_manim_code_ast(code)
        assert any("set_text" in i["message"] for i in issues)

    def test_copy_not_flagged(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        c = Circle()\n"
            "        d = c.copy()\n"
        )
        assert validate_manim_code_ast(code) == []

    def test_bare_deepcopy_attr_not_flagged(self):
        """Referencing .deepcopy without calling it should not flag."""
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        method_ref = Circle.deepcopy\n"
        )
        issues = validate_manim_code_ast(code)
        assert not any(i["error_type"] == "forbidden_method" for i in issues)


class TestCameraFrame:
    def test_camera_frame_detected(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        self.camera.frame.set(width=20)\n"
        )
        issues = validate_manim_code_ast(code)
        assert any("camera.frame" in i["message"] for i in issues)

    def test_non_self_camera_not_flagged(self):
        """cam.camera.frame access (not self.) should not be flagged."""
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        cam = SomeObject()\n"
            "        val = cam.camera.frame\n"
        )
        issues = validate_manim_code_ast(code)
        assert not any("camera.frame" in i.get("message", "") for i in issues)


class TestMultipleIssues:
    def test_multiple_issues_reported(self):
        code = (
            "from manim import *\n"
            "class AlgorithmScene(Scene):\n"
            "    def construct(self):\n"
            "        m = Matrix([[1,2]])\n"
            "        d = m.deepcopy()\n"
            "        line = DashedLine(LEFT, RIGHT)\n"
            "        self.camera.frame.set(width=20)\n"
        )
        issues = validate_manim_code_ast(code)
        error_types = {i["error_type"] for i in issues}
        assert "forbidden_api" in error_types
        assert "forbidden_method" in error_types
        # At least 3 issues: Matrix, deepcopy, DashedLine, camera.frame
        assert len(issues) >= 3
