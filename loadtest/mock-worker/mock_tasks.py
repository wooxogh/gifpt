"""Mock Celery task that replaces studio.animate_algorithm for load testing.

Skips OpenAI/Manim/S3. Sleeps to mimic prod render time, then hits the Spring
callback with SUCCESS + a fixture URL.
"""
import os
import random
import time
import logging

import requests
from celery import Celery

logger = logging.getLogger(__name__)

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
SPRING_CALLBACK_BASE = os.environ.get("SPRING_CALLBACK_BASE", "http://spring:8080")
CALLBACK_SECRET = os.environ.get("GIFPT_CALLBACK_SECRET", "")
MIN_SLEEP = float(os.environ.get("MOCK_MIN_SLEEP_SECONDS", "8"))
MAX_SLEEP = float(os.environ.get("MOCK_MAX_SLEEP_SECONDS", "20"))
FIXTURE_URL = os.environ.get(
    "MOCK_RESULT_URL",
    "https://gifpt-demo.s3.ap-northeast-1.amazonaws.com/fixtures/loadtest.mp4",
)

app = Celery("studio", broker=BROKER_URL, backend=BACKEND_URL)
app.conf.task_default_queue = "gifpt.default"


@app.task(name="studio.animate_algorithm")
def animate_algorithm(job_id: int, algorithm: str, prompt: str = None):
    delay = random.uniform(MIN_SLEEP, MAX_SLEEP)
    logger.info("mock animate_algorithm job_id=%s sleeping %.1fs", job_id, delay)
    time.sleep(delay)
    r = requests.post(
        f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete",
        json={
            "status": "SUCCESS",
            "resultUrl": FIXTURE_URL,
            "summary": "",
            "errorMessage": "",
        },
        headers={"X-Callback-Secret": CALLBACK_SECRET},
        timeout=10,
    )
    r.raise_for_status()
    logger.info("mock callback ok job_id=%s status=%s", job_id, r.status_code)
    return {"job_id": job_id, "status": "SUCCESS"}
