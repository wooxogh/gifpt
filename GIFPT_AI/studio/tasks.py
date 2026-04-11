# GIFPT_AI/studio/tasks.py

import hashlib
import os
import logging
import requests
import json
from pathlib import Path
import time

import boto3
from celery import shared_task
from studio.video_render import render_video_from_instructions, run_manim_code, RESULT_DIR
from studio.s3_utils import S3_BUCKET, S3_REGION

logger = logging.getLogger(__name__)

SPRING_CALLBACK_BASE = os.environ.get("SPRING_CALLBACK_BASE", "http://spring:8080")
CALLBACK_SECRET = os.environ.get("GIFPT_CALLBACK_SECRET", "")
RESULT_DIR = os.environ.get("GIFPT_RESULT_DIR", "/data/results")
DEAD_LETTER_TTL_SECONDS = int(os.environ.get("GIFPT_CALLBACK_DEAD_LETTER_TTL_SECONDS", "86400"))


# ---------------------------------------------------------------------------
# animate_algorithm — direct algorithm-name → video pipeline (no PDF required)
# ---------------------------------------------------------------------------

def _s3_key_for_slug(slug: str) -> str:
    """Deterministic S3 key: animations/SHA256(slug).mp4  (must match Java s3KeyForSlug)"""
    digest = hashlib.sha256(slug.encode()).hexdigest()
    return f"animations/{digest}.mp4"


def _s3_object_exists(key: str) -> bool:
    s3 = boto3.client("s3", region_name=S3_REGION)
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except s3.exceptions.ClientError:
        return False
    except Exception:
        return False


def _upload_to_s3_with_key(file_path: str, key: str) -> str:
    s3 = boto3.client("s3", region_name=S3_REGION)
    s3.upload_file(
        file_path,
        S3_BUCKET,
        key,
        ExtraArgs={"ContentType": "video/mp4"},
    )
    return f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"


@shared_task(name="studio.animate_algorithm")
def animate_algorithm(job_id: int, algorithm: str, prompt: str = None):
    """Generate a Manim animation for a named algorithm or custom logic description.

    When prompt is provided (custom description / pseudocode), uses the rich
    render_video_from_instructions pipeline (pseudocode IR → anim IR → codegen).
    When only algorithm name is given, uses the fast few-shot codegen path.

    Flow (name only):
        normalize_slug → domain classify → ExampleLibrary → few-shot codegen
        → run_manim_code → S3 (hash key) → Spring callback

    Flow (with prompt):
        render_video_from_instructions(prompt) → S3 (UUID key) → Spring callback
    """
    import openai
    import uuid
    from django.core.cache import cache  # Django Redis cache backend
    from studio.ai.example_library import normalize_slug, get_library
    from studio.ai.llm_domain import call_llm_detect_domain
    from studio.ai.patterns import DOMAIN_TO_PATTERN, PatternType
    from studio.ai.llm_codegen import call_llm_codegen_for_algorithm

    task_start = time.time()
    logger.info("animate_algorithm started job_id=%s algorithm=%r prompt=%s",
                job_id, algorithm, "provided" if prompt else "none")

    slug = normalize_slug(algorithm)
    callback_body: dict = {}

    try:
        # ── Path A: Custom prompt → rich pipeline ──
        if prompt:
            logger.info("animate_algorithm using rich pipeline for prompt job_id=%s", job_id)
            video_local_path = render_video_from_instructions(prompt)
            s3_key = f"animations/{uuid.uuid4().hex}.mp4"
            video_url = _upload_to_s3_with_key(video_local_path, s3_key)
            callback_body = {
                "status": "SUCCESS",
                "resultUrl": video_url,
                "summary": f"Custom visualization: {algorithm}",
                "errorMessage": None,
            }

        else:
            # ── Path B: Algorithm name → few-shot codegen ──
            s3_key = _s3_key_for_slug(slug)

            # 1) Cache check — return immediately if video already exists
            if _s3_object_exists(s3_key):
                video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
                logger.info("animate_algorithm cache HIT slug=%s", slug)
                callback_body = {
                    "status": "SUCCESS",
                    "resultUrl": video_url,
                    "summary": f"Algorithm visualization: {algorithm}",
                    "errorMessage": None,
                }
            else:
                # 2) Domain classify → PatternType (5s timeout; fallback to all examples)
                domain = None
                pattern_type = None
                try:
                    domain, is_3d = call_llm_detect_domain(slug.replace("_", " "))
                    pattern_type = DOMAIN_TO_PATTERN.get(domain)
                except Exception as exc:
                    logger.warning("animate_algorithm domain classify failed (%s) — using all examples", exc)

                # 3) Retrieve few-shot examples
                library = get_library()
                examples = library.get_examples(pattern_type, top_k=3, is_3d=is_3d)
                logger.info(
                    "animate_algorithm slug=%s domain=%s pattern=%s examples=%s",
                    slug, domain, pattern_type,
                    [e.get("tag") for e in examples],
                )

                # 4) Codegen + Render with self-healing
                from studio.ai.llm_codegen import call_llm_codegen_fix
                from studio.video_render import ManimRenderError, render_fallback

                manim_code = None
                video_local_path = None
                output_dir = Path(RESULT_DIR) / "animations"
                output_name = f"{slug}.mp4"
                render_start = time.perf_counter()
                last_error_type = ""
                last_stderr = ""
                attempt_history: list[dict] = []

                for attempt in range(1, 4):
                    # Generate code (initial or self-heal)
                    if attempt == 1:
                        for rate_try in range(1, 4):
                            try:
                                manim_code = call_llm_codegen_for_algorithm(algorithm, examples)
                                break
                            except openai.RateLimitError:
                                wait = 2 ** rate_try
                                logger.warning("RateLimitError, retrying in %ds (attempt %d/3)", wait, rate_try)
                                time.sleep(wait)
                        if manim_code is None:
                            raise RuntimeError("Codegen failed after 3 rate-limit retries")
                    else:
                        manim_code = call_llm_codegen_fix(
                            manim_code, last_error_type, last_stderr,
                            algorithm_name=algorithm,
                            attempt_history=attempt_history,
                        )

                    # Try rendering
                    try:
                        video_local_path = run_manim_code(manim_code, output_dir, output_name)
                        logger.info("[animate_algorithm] render success on attempt %d", attempt)
                        break
                    except ManimRenderError as e:
                        last_error_type = e.error_type
                        last_stderr = e.stderr_snippet
                        attempt_history.append({
                            "attempt": attempt,
                            "error_type": e.error_type,
                            "stderr": e.stderr_snippet[-500:],
                        })
                        logger.warning(
                            "[animate_algorithm] render attempt %d/3 failed: %s — self-healing",
                            attempt, e.error_type,
                        )

                if video_local_path is None:
                    logger.warning("[animate_algorithm] all render attempts failed — using fallback")
                    video_local_path = render_fallback(output_dir, output_name, algorithm_name=algorithm)

                render_time = time.perf_counter() - render_start

                # 6) Upload to S3 with deterministic hash key
                video_url = _upload_to_s3_with_key(video_local_path, s3_key)
                logger.info(
                    "animate_algorithm",
                    extra={
                        "algorithm": slug,
                        "domain": domain,
                        "pattern_type": str(pattern_type),
                        "examples_used": [e.get("tag") for e in examples],
                        "cache": "MISS",
                        "render_time_s": round(render_time, 2),
                        "job_id": job_id,
                    },
                )

                callback_body = {
                    "status": "SUCCESS",
                    "resultUrl": video_url,
                    "summary": f"Algorithm visualization: {algorithm}",
                    "errorMessage": None,
                }

    except Exception as exc:
        logger.exception("animate_algorithm failed job_id=%s", job_id)
        callback_body = {
            "status": "FAILED",
            "resultUrl": None,
            "summary": "",
            "errorMessage": str(exc),
        }

    finally:
        elapsed = time.time() - task_start
        logger.info("animate_algorithm done job_id=%s elapsed=%.2fs", job_id, elapsed)

    # 7) Spring callback
    callback_url = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
    callback_headers = {"X-Callback-Secret": CALLBACK_SECRET} if CALLBACK_SECRET else {}
    try:
        resp = requests.post(callback_url, json=callback_body, headers=callback_headers, timeout=10)
        logger.info("[ANIMATE_CALLBACK] status=%s job_id=%s", resp.status_code, job_id)
    except requests.ConnectionError:
        dead_letter_key = f"gifpt:callback:dead:{job_id}"
        try:
            cache.set(dead_letter_key, json.dumps(callback_body), timeout=DEAD_LETTER_TTL_SECONDS)
            logger.error(
                "[ANIMATE_CALLBACK] Spring unreachable — pushed to dead-letter key=%s ttl=%ss",
                dead_letter_key, DEAD_LETTER_TTL_SECONDS,
            )
        except Exception:
            logger.exception("[ANIMATE_CALLBACK] failed to write dead-letter job_id=%s", job_id)
    except Exception:
        logger.exception("[ANIMATE_CALLBACK] unexpected error job_id=%s", job_id)


# ---------------------------------------------------------------------------
# Dead-letter retry — runs via Celery beat every 5 minutes
# ---------------------------------------------------------------------------

@shared_task(name="studio.retry_dead_letter_callbacks")
def retry_dead_letter_callbacks():
    """Scan Redis for dead-letter callbacks and retry sending them to Spring."""
    import redis as _redis

    redis_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
    r = _redis.from_url(redis_url)

    # Django CACHES KEY_PREFIX is "gifpt", so keys become "gifpt:gifpt:callback:dead:*"
    # Try both patterns to be robust
    keys = list(r.keys("gifpt:gifpt:callback:dead:*")) or list(r.keys("gifpt:callback:dead:*"))

    if not keys:
        return

    retried = 0
    for key in keys:
        key_str = key.decode() if isinstance(key, bytes) else key
        job_id = key_str.rsplit(":", 1)[-1]

        raw = r.get(key)
        if not raw:
            continue

        try:
            callback_body = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("[DEAD_LETTER_RETRY] invalid JSON for key=%s — deleting", key_str)
            r.delete(key)
            continue

        callback_url = f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete"
        callback_headers = {"X-Callback-Secret": CALLBACK_SECRET} if CALLBACK_SECRET else {}

        try:
            resp = requests.post(callback_url, json=callback_body, headers=callback_headers, timeout=10)
            if resp.status_code < 500:
                r.delete(key)
                retried += 1
                logger.info("[DEAD_LETTER_RETRY] success job_id=%s status=%s", job_id, resp.status_code)
            else:
                logger.warning("[DEAD_LETTER_RETRY] server error job_id=%s status=%s", job_id, resp.status_code)
        except requests.ConnectionError:
            logger.warning("[DEAD_LETTER_RETRY] still unreachable job_id=%s", job_id)
        except Exception:
            logger.exception("[DEAD_LETTER_RETRY] unexpected error job_id=%s", job_id)

    logger.info("[DEAD_LETTER_RETRY] completed: retried=%d total_keys=%d", retried, len(keys))
