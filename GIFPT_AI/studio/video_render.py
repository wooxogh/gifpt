# video_render.py
import os
import time
import tempfile
import subprocess
import re
from pathlib import Path
import logging

from studio.ai.qa import validate_pseudocode_ir, validate_anim_ir, vision_qa

logger = logging.getLogger(__name__)

RESULT_DIR = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))

SEP = "=" * 80
SUBSEP = "-" * 80

UNKNOWN_HELPERS = [
    'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
    'DrawArrowBetween', 'ShowValueOnPlot'
]

def _sanitize_text(text: str) -> str:
    """main.py의 sanitize_text와 같은 역할 (간단한 공백/줄바꿈 정리)."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def validate_manim_code_basic(code: str):
    """LLM이 만든 Manim 코드에 대한 경량 검증"""
    issues = []

    if 'from manim import *' not in code:
        issues.append({"error_type": "syntax", "message": "missing 'from manim import *'"})

    if re.search(r'class\s+AlgorithmScene\s*\(Scene\)', code) is None:
        issues.append({"error_type": "class_name", "message": "AlgorithmScene(Scene) not defined"})

    if re.search(r'def\s+construct\s*\(self\)\s*:', code) is None:
        issues.append({"error_type": "syntax", "message": "construct(self) not found"})

    # hex colors
    if re.search(r'#[0-9A-Fa-f]{6}', code):
        issues.append({"error_type": "color", "message": "hex color literal detected"})

    # invented helpers
    for name in UNKNOWN_HELPERS:
        if re.search(rf'\b{name}\s*\(', code):
            issues.append({"error_type": "unknown_helper", "message": f"uses undefined helper {name}"})
            break

    # 매우 단순한 괄호 체크
    if code.count('(') < code.count(')') or code.count('[') < code.count(']'):
        issues.append({"error_type": "syntax", "message": "possible unmatched bracket"})

    return issues


class ManimRenderError(Exception):
    """Raised when Manim rendering fails after all retry attempts."""
    def __init__(self, error_type: str, stderr_snippet: str, code: str):
        self.error_type = error_type
        self.stderr_snippet = stderr_snippet
        self.code = code
        super().__init__(f"Manim render failed: {error_type}")


def classify_runtime_error(stderr: str):
    if 'NameError' in stderr:
        m = re.search(r"NameError: name '([^']+)' is not defined", stderr)
        name = m.group(1) if m else "<unknown>"
        return {"error_type": "runtime_name", "message": f"undefined name: {name}"}
    if 'ImportError' in stderr or 'ModuleNotFoundError' in stderr:
        m = re.search(r"(?:ImportError|ModuleNotFoundError): ([^\n]+)", stderr)
        detail = m.group(1) if m else "import error"
        return {"error_type": "runtime_env", "message": detail}
    if 'AttributeError' in stderr:
        m = re.search(r"AttributeError: ([^\n]+)", stderr)
        detail = m.group(1) if m else "attribute error"
        return {"error_type": "runtime_attr", "message": detail}
    if 'TypeError' in stderr:
        m = re.search(r"TypeError: ([^\n]+)", stderr)
        detail = m.group(1) if m else "type error"
        return {"error_type": "runtime_type", "message": detail}
    if 'ValueError' in stderr:
        m = re.search(r"ValueError: ([^\n]+)", stderr)
        detail = m.group(1) if m else "value error"
        return {"error_type": "runtime_value", "message": detail}
    if 'IndexError' in stderr:
        m = re.search(r"IndexError: ([^\n]+)", stderr)
        detail = m.group(1) if m else "index error"
        return {"error_type": "runtime_index", "message": detail}
    if 'KeyError' in stderr:
        m = re.search(r"KeyError: ([^\n]+)", stderr)
        detail = m.group(1) if m else "key error"
        return {"error_type": "runtime_key", "message": detail}
    if 'ZeroDivisionError' in stderr:
        return {"error_type": "runtime_zerodiv", "message": "division by zero"}
    if 'MemoryError' in stderr:
        return {"error_type": "resource", "message": "out of memory"}
    if 'Timeout' in stderr or 'timed out' in stderr:
        return {"error_type": "timeout", "message": "render timeout"}
    # fallback: extract the last Exception line
    m = re.search(r"(\w+Error): ([^\n]+)", stderr)
    if m:
        return {"error_type": "runtime", "message": f"{m.group(1)}: {m.group(2)}"}
    return {"error_type": "runtime", "message": "unknown runtime error"}



def _render_manim_once(code: str, output_dir: Path, output_name: str, timeout: int = 180) -> str | None:
    """Run manim on *code* and return the video path, or None on failure."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        subprocess.run(
            ["manim", "-ql", tmp_path, "AlgorithmScene", "--format", "mp4", "-o", output_name],
            cwd=output_dir, check=True, capture_output=True, text=True, timeout=timeout,
        )

        tmp_name = Path(tmp_path).stem
        candidate = output_dir / "media" / "videos" / tmp_name / "480p15" / output_name
        if candidate.exists():
            return str(candidate.resolve())
        matches = list(output_dir.rglob(output_name))
        if matches:
            return str(matches[0].resolve())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    return None


def run_manim_code(code: str, output_dir: Path, output_name: str | None = None) -> str:
    """Render Manim code — returns video path on success, raises ManimRenderError on failure.

    Unlike the previous version this does NOT include a fallback scene;
    the caller is responsible for deciding what to do on failure (e.g. self-heal or fallback).
    """
    import time as _time

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_name is None:
        output_name = f"video_{int(_time.time())}.mp4"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        subprocess.run(
            ["manim", "-ql", tmp_path, "AlgorithmScene", "--format", "mp4", "-o", output_name],
            cwd=output_dir, check=True, capture_output=True, text=True, timeout=180,
        )

        tmp_name = Path(tmp_path).stem
        candidate = output_dir / "media" / "videos" / tmp_name / "480p15" / output_name
        if candidate.exists():
            return str(candidate.resolve())
        matches = list(output_dir.rglob(output_name))
        if matches:
            return str(matches[0].resolve())

    except subprocess.CalledProcessError as e:
        last_stderr = e.stderr or ""
        err = classify_runtime_error(last_stderr)
        logger.warning("run_manim_code failed: %s", err)
        raise ManimRenderError(err["error_type"], last_stderr[-2000:], code)

    except subprocess.TimeoutExpired:
        logger.warning("run_manim_code timed out")
        raise ManimRenderError("timeout", "render timed out after 180s", code)

    raise ManimRenderError("runtime", "render produced no video file", code)


def render_fallback(output_dir: Path, output_name: str, algorithm_name: str = "Algorithm") -> str:
    """Render a minimal placeholder scene showing the algorithm name.

    Returns the video path, or raises RuntimeError if even this fails.
    """
    safe_name = algorithm_name.replace("'", "\\'").replace('"', '\\"')[:60]
    fallback_code = (
        "from manim import *\n\n"
        "class AlgorithmScene(Scene):\n"
        "    def construct(self):\n"
        f"        title = Text('{safe_name}', font_size=36, color=WHITE)\n"
        "        msg = Text('Video generation failed — please retry', font_size=20, color=GRAY)\n"
        "        grp = VGroup(title, msg).arrange(DOWN, buff=0.5)\n"
        "        self.play(FadeIn(grp))\n"
        "        self.wait(2)\n"
        "        self.play(FadeOut(grp))\n"
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = _render_manim_once(fallback_code, output_dir, output_name, timeout=60)
    if path:
        return path
    raise RuntimeError("render_fallback: fallback scene also failed to render")


def render_video_from_instructions(instructions: str) -> str:
    """
    Custom prompt → generic pipeline (pseudocode IR → anim IR → codegen → render).

    Domain classification is intentionally skipped here. It caused misclassification
    crashes (e.g., LSM-Tree → sorting → empty trace → Manim crash). The generic
    pipeline handles all algorithm types through the IR abstraction.

    When Vision QA fails, the QA issues are fed back into codegen so the LLM
    can fix specific problems instead of blindly retrying.
    """
    from studio.ai.llm_pseudocode import call_llm_pseudocode_ir_with_usage
    from studio.ai.llm_anim_ir import call_llm_anim_ir_with_usage
    from studio.ai.llm_codegen import call_llm_codegen_with_usage, call_llm_codegen_fix, call_llm_codegen_with_qa_feedback

    user_text = _sanitize_text(instructions)

    MAX_PIPELINE_ATTEMPTS = 2  # Vision QA 실패 시 재시도
    MAX_IR_RETRIES = 2         # 각 IR 단계 재시도

    # Persistent state across pipeline attempts for QA feedback loop
    prev_qa_issues: list[str] = []

    for pipeline_attempt in range(1, MAX_PIPELINE_ATTEMPTS + 1):
        logger.info("[Pipeline] attempt %d/%d (generic)", pipeline_attempt, MAX_PIPELINE_ATTEMPTS)

        # ── Step 1: Pseudocode IR + validation ──
        pseudo_ir = None
        for ir_try in range(1, MAX_IR_RETRIES + 1):
            t0 = time.perf_counter()
            pseudo_ir, usage_pseudo = call_llm_pseudocode_ir_with_usage(user_text)
            t_pseudo = time.perf_counter() - t0
            logger.info("[Pseudocode IR] attempt %d/%d time=%.2fs", ir_try, MAX_IR_RETRIES, t_pseudo)

            ir_issues = validate_pseudocode_ir(pseudo_ir)
            if not ir_issues:
                logger.info("[Pseudocode IR] passed validation — entities=%d operations=%d",
                            len(pseudo_ir.get("entities", [])), len(pseudo_ir.get("operations", [])))
                break
            logger.warning("[Pseudocode IR] validation failed (%d issues): %s", len(ir_issues), ir_issues[:3])
            if ir_try == MAX_IR_RETRIES:
                logger.warning("[Pseudocode IR] proceeding with last attempt despite issues")

        # ── Step 2: Animation IR + validation ──
        anim_ir = None
        for ir_try in range(1, MAX_IR_RETRIES + 1):
            ta0 = time.perf_counter()
            anim_ir, usage_anim = call_llm_anim_ir_with_usage(pseudo_ir)
            t_anim = time.perf_counter() - ta0
            logger.info("[Anim IR] attempt %d/%d time=%.2fs", ir_try, MAX_IR_RETRIES, t_anim)

            ir_issues = validate_anim_ir(anim_ir)
            if not ir_issues:
                logger.info("[Anim IR] passed validation — layout=%d actions=%d",
                            len(anim_ir.get("layout", [])), len(anim_ir.get("actions", [])))
                break
            logger.warning("[Anim IR] validation failed (%d issues): %s", len(ir_issues), ir_issues[:3])
            if ir_try == MAX_IR_RETRIES:
                logger.warning("[Anim IR] proceeding with last attempt despite issues")

        # ── Step 3: Codegen + Render with self-healing ──
        manim_code = None
        video_path = None
        last_error_type = None
        last_stderr = None
        max_codegen_attempts = 3
        output_dir = RESULT_DIR / "videos"
        output_name = f"video_{int(time.time())}.mp4"

        for attempt in range(1, max_codegen_attempts + 1):
            start = time.perf_counter()

            if attempt == 1:
                if prev_qa_issues:
                    # QA feedback loop: use issues from previous pipeline attempt
                    logger.info("[CodeGen] using QA feedback from previous attempt: %s", prev_qa_issues[:3])
                    code_try = call_llm_codegen_with_qa_feedback(anim_ir, prev_qa_issues)
                else:
                    code_try, usage_codegen = call_llm_codegen_with_usage(anim_ir)
            elif last_error_type is not None:
                code_try = call_llm_codegen_fix(manim_code, last_error_type, last_stderr)
            else:
                code_try, usage_codegen = call_llm_codegen_with_usage(anim_ir)

            issues = validate_manim_code_basic(code_try)
            dur = time.perf_counter() - start

            if issues:
                logger.warning("[CodeGen] attempt %d/%d static issues (%d) %.2fs",
                               attempt, max_codegen_attempts, len(issues), dur)
                manim_code = code_try
                if attempt < max_codegen_attempts:
                    continue
            else:
                manim_code = code_try
                logger.info("[CodeGen] attempt %d passed %.2fs", attempt, dur)

            # Debug: save generated code
            debug_dir = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))
            debug_path = debug_dir / "debug_generated_code_generic.py"
            try:
                debug_dir.mkdir(parents=True, exist_ok=True)
                debug_path.write_text(manim_code or "", encoding="utf-8")
            except Exception:
                pass

            # Try rendering
            try:
                video_path = run_manim_code(manim_code, output_dir, output_name)
                logger.info("[Render] success on attempt %d — %s", attempt, video_path)
                break
            except ManimRenderError as e:
                last_error_type = e.error_type
                last_stderr = e.stderr_snippet
                logger.warning("[Render] attempt %d/%d failed: %s — feeding error back to LLM",
                               attempt, max_codegen_attempts, e.error_type)
                if attempt == max_codegen_attempts:
                    logger.warning("[Render] all attempts exhausted — rendering fallback")
                    video_path = render_fallback(output_dir, output_name, algorithm_name="Algorithm")

        if video_path is None:
            video_path = render_fallback(output_dir, output_name, algorithm_name="Algorithm")

        logger.info("[Render] video at %s", video_path)

        # ── Step 4: Vision QA ──
        qa_domain = anim_ir.get("metadata", {}).get("domain") if isinstance(anim_ir, dict) else None
        qa_result = vision_qa(video_path, user_text, num_frames=4, threshold=5.0, domain=qa_domain)
        logger.info("[Vision QA] score=%.1f passed=%s summary=%s",
                    qa_result["score"], qa_result["passed"], qa_result["summary"])

        if qa_result["passed"]:
            if qa_result["score"] > 0:
                logger.info("[Vision QA] PASSED (score=%.1f) — returning video", qa_result["score"])
            return video_path

        # QA failed — normalize issues for stable QA feedback loop
        raw_issues = qa_result.get("issues", [])
        if isinstance(raw_issues, list):
            prev_qa_issues = [str(issue).strip() for issue in raw_issues if str(issue).strip()]
        elif isinstance(raw_issues, str):
            normalized = raw_issues.strip()
            prev_qa_issues = [normalized] if normalized else []
        else:
            prev_qa_issues = []

        if pipeline_attempt < MAX_PIPELINE_ATTEMPTS:
            logger.warning("[Vision QA] FAILED (score=%.1f) — retrying with QA feedback. Issues: %s",
                           qa_result["score"], prev_qa_issues)
        else:
            logger.warning("[Vision QA] FAILED (score=%.1f) — no retries left, returning best effort. Issues: %s",
                           qa_result["score"], prev_qa_issues)
            return video_path

    return video_path
