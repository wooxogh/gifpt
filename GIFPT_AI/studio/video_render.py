# video_render.py
import os
import time
import tempfile
import subprocess
import re
from pathlib import Path
import logging

from studio.ai.llm_domain import call_llm_detect_domain
from studio.ai.llm import call_llm_domain_ir
from studio.ai.render_cnn_matrix import render_cnn_matrix
from studio.ai.render_sorting import render_sorting
from studio.ai.llm_domain import build_sorting_trace_ir
from studio.ai.qa import validate_pseudocode_ir, validate_anim_ir, vision_qa, IRValidationError

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
    if 'ImportError' in stderr:
        return {"error_type": "runtime_env", "message": "import error"}
    if 'MemoryError' in stderr:
        return {"error_type": "resource", "message": "out of memory"}
    if 'Timeout' in stderr or 'timed out' in stderr:
        return {"error_type": "timeout", "message": "render timeout"}
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

    last_stderr = ""

    for attempt in range(1, 4):
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
            logger.warning("run_manim_code attempt %d/3 failed: %s", attempt, err)

        except subprocess.TimeoutExpired:
            last_stderr = "render timed out after 180s"
            logger.warning("run_manim_code attempt %d/3 timed out", attempt)

    # All attempts exhausted — raise with error details for self-healing
    err = classify_runtime_error(last_stderr)
    raise ManimRenderError(err["error_type"], last_stderr[-2000:], code)


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
    PDF 분석 파이프라인에서 전달된 'video instructions' 텍스트를 받아
    main.py의 /generate 로직과 동일한 파이프라인으로 영상을 생성한다.

    - cnn_param  → call_llm_domain_ir + render_cnn_matrix
    - sorting    → call_llm_sort_trace + render_sorting
    - 기타       → pseudocode_ir → anim_ir → manim_code → manim 실행
    """
    user_text = _sanitize_text(instructions)

    # 1) 도메인 결정
    domain, is_3d = call_llm_detect_domain(user_text)
    logger.info("🎯 detected domain for video_render: %s (is_3d=%s)", domain, is_3d)

    # 2) 도메인별 처리 -----------------------------

    # (1) CNN 파라미터 전용
    if domain == "cnn_param":
        ir = call_llm_domain_ir("cnn_param", user_text)
        params = ir["ir"]["params"]

        video_path = render_cnn_matrix(params)
        logger.info("🎬 CNN video rendered at %s", video_path)
        return video_path

    # (2) 정렬 전용 파이프라인 (trace → render_sorting)
    if domain == "sorting":
        sort_trace = build_sorting_trace_ir(user_text)
        video_path = render_sorting(sort_trace)
        logger.info("🎬 sorting video rendered at %s", video_path)
        return video_path

        # 3) 일반 알고리즘/모델 시각화 (pseudocode → anim_ir → manim 코드)
    #    QA: IR 검증 실패 시 해당 단계 재생성, Vision QA 실패 시 전체 재생성

    from studio.ai.llm_pseudocode import call_llm_pseudocode_ir_with_usage
    from studio.ai.llm_anim_ir import call_llm_anim_ir_with_usage
    from studio.ai.llm_codegen import call_llm_codegen_with_usage

    MAX_PIPELINE_ATTEMPTS = 2  # 전체 파이프라인 재시도 (Vision QA 실패 시)
    MAX_IR_RETRIES = 2         # 각 IR 단계 재시도

    for pipeline_attempt in range(1, MAX_PIPELINE_ATTEMPTS + 1):
        logger.info("[Pipeline] attempt %d/%d domain=%s", pipeline_attempt, MAX_PIPELINE_ATTEMPTS, domain)

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
        from studio.ai.llm_codegen import call_llm_codegen_fix

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
                code_try, usage_codegen = call_llm_codegen_with_usage(anim_ir)
            elif last_error_type is not None:
                # Self-heal: feed the render error back to LLM for correction
                code_try = call_llm_codegen_fix(manim_code, last_error_type, last_stderr)
            else:
                # Previous attempt failed static validation (no render error) — retry codegen
                code_try, usage_codegen = call_llm_codegen_with_usage(anim_ir)

            issues = validate_manim_code_basic(code_try)
            dur = time.perf_counter() - start

            if issues:
                logger.warning("[CodeGen] attempt %d/%d static issues (%d) %.2fs",
                               attempt, max_codegen_attempts, len(issues), dur)
                manim_code = code_try
                if attempt < max_codegen_attempts:
                    continue  # retry codegen without rendering
            else:
                manim_code = code_try
                logger.info("[CodeGen] attempt %d passed %.2fs", attempt, dur)

            # Debug: save generated code
            debug_dir = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))
            debug_path = debug_dir / f"debug_generated_code_{domain}.py"
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
                    video_path = render_fallback(output_dir, output_name, algorithm_name=domain)

        if video_path is None:
            video_path = render_fallback(output_dir, output_name, algorithm_name=domain)

        logger.info("[Render] video at %s", video_path)

        # ── Step 5: Vision QA ──
        qa_result = vision_qa(video_path, user_text, num_frames=4, threshold=5.0, domain=domain)
        logger.info("[Vision QA] score=%.1f passed=%s summary=%s",
                    qa_result["score"], qa_result["passed"], qa_result["summary"])

        if qa_result["passed"]:
            if qa_result["score"] > 0:
                logger.info("[Vision QA] PASSED (score=%.1f) — returning video", qa_result["score"])
            return video_path

        # QA failed — retry entire pipeline if attempts remain
        if pipeline_attempt < MAX_PIPELINE_ATTEMPTS:
            logger.warning("[Vision QA] FAILED (score=%.1f) — retrying pipeline. Issues: %s",
                           qa_result["score"], qa_result["issues"])
        else:
            logger.warning("[Vision QA] FAILED (score=%.1f) — no retries left, returning best effort. Issues: %s",
                           qa_result["score"], qa_result["issues"])
            return video_path

    # Should not reach here, but just in case
    return video_path
