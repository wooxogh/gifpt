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



_FALLBACK_CODE = (
    "from manim import *\n\n"
    "class AlgorithmScene(Scene):\n"
    "    def construct(self):\n"
    "        txt = Text('Fallback', font_size=48, color=WHITE)\n"
    "        self.play(FadeIn(txt))\n"
    "        self.wait(1)\n"
    "        self.play(FadeOut(txt))\n"
    "        self.wait(1)\n"
)


def run_manim_code(code: str, output_dir: Path, output_name: str | None = None) -> str:
    """Render Manim code with retry and fallback.

    Args:
        code: Complete Manim Python source (must define AlgorithmScene).
        output_dir: Directory to use as Manim's working directory.
        output_name: Base filename for the output mp4 (default: auto-generated).

    Returns:
        Absolute path to the rendered mp4 file.

    Raises:
        RuntimeError: If both primary render and fallback render fail.
    """
    import time as _time

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_name is None:
        output_name = f"video_{int(_time.time())}.mp4"

    video_path = None
    max_render_attempts = 3

    for attempt in range(1, max_render_attempts + 1):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            subprocess.run(
                [
                    "manim", "-ql",
                    tmp_path,
                    "AlgorithmScene",
                    "--format", "mp4",
                    "-o", output_name,
                ],
                cwd=output_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )

            tmp_name = Path(tmp_path).stem
            candidate = output_dir / "media" / "videos" / tmp_name / "480p15" / output_name
            if candidate.exists():
                video_path = str(candidate.resolve())
                break

            matches = list(output_dir.rglob(output_name))
            if matches:
                video_path = str(matches[0].resolve())
                break

        except subprocess.CalledProcessError as e:
            err = classify_runtime_error(e.stderr or "")
            logger.warning("run_manim_code attempt %d/%d failed: %s", attempt, max_render_attempts, err)
            if attempt == max_render_attempts:
                break

        except subprocess.TimeoutExpired:
            logger.warning("run_manim_code attempt %d/%d timed out", attempt, max_render_attempts)
            if attempt == max_render_attempts:
                break

    if video_path:
        return video_path

    # Fallback: render a minimal placeholder scene
    logger.warning("run_manim_code: all attempts failed, rendering fallback")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_fb:
        tmp_fb.write(_FALLBACK_CODE)
        fb_path = tmp_fb.name
    try:
        subprocess.run(
            [
                "manim", "-ql",
                fb_path,
                "AlgorithmScene",
                "--format", "mp4",
                "-o", output_name,
            ],
            cwd=output_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        fb_name = Path(fb_path).stem
        fb_candidate = output_dir / "media" / "videos" / fb_name / "480p15" / output_name
        if fb_candidate.exists():
            return str(fb_candidate.resolve())
        matches = list(output_dir.rglob(output_name))
        if matches:
            return str(matches[0].resolve())
    except Exception as ee:
        raise RuntimeError(f"run_manim_code fallback failed: {ee}") from ee

    raise RuntimeError("run_manim_code: video file not found after fallback render")


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
    domain = call_llm_detect_domain(user_text)
    logger.info("🎯 detected domain for video_render: %s", domain)

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

        # ── Step 3: Codegen (with existing retry + post-check) ──
        manim_code = None
        max_codegen_attempts = 3

        for attempt in range(1, max_codegen_attempts + 1):
            start = time.perf_counter()
            code_try, usage_codegen = call_llm_codegen_with_usage(anim_ir)
            issues = validate_manim_code_basic(code_try)
            dur = time.perf_counter() - start

            if issues:
                logger.warning("[CodeGen] attempt %d/%d failed (%d issues) %.2fs",
                               attempt, max_codegen_attempts, len(issues), dur)
                if attempt == max_codegen_attempts:
                    manim_code = code_try
                continue
            else:
                manim_code = code_try
                logger.info("[CodeGen] attempt %d passed %.2fs", attempt, dur)
                break

        # Debug: save generated code
        debug_dir = Path(os.environ.get("GIFPT_RESULT_DIR", "/tmp/gifpt_results"))
        debug_path = debug_dir / f"debug_generated_code_{domain}.py"
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(manim_code or "", encoding="utf-8")
        except Exception:
            pass

        # ── Step 4: Render ──
        output_dir = RESULT_DIR / "videos"
        output_name = f"video_{int(time.time())}.mp4"
        video_path = run_manim_code(manim_code, output_dir, output_name)
        logger.info("[Render] video at %s", video_path)

        # ── Step 5: Vision QA ──
        qa_result = vision_qa(video_path, user_text, num_frames=4, threshold=5.0)
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
