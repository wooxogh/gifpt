# studio/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
import json
import logging

from .tasks import animate_algorithm
from GIFPT_AI.celery import app as celery_app

logger = logging.getLogger(__name__)


@api_view(['POST'])
def animate(request):
    """Receive animate_algorithm dispatch from Spring Boot.

    Expected body: {"job_id": <int>, "algorithm": "<str>"}
    """
    data = getattr(request, "data", {}) or {}
    if not data and request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return Response(
                {"error": "invalid_json", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not data.get("job_id") or not data.get("algorithm"):
        missing = [f for f in ("job_id", "algorithm") if not data.get(f)]
        return Response(
            {"error": "missing_fields", "missing": missing},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        job_id = int(data["job_id"])
    except (ValueError, TypeError):
        return Response({"error": "invalid_job_id"}, status=status.HTTP_400_BAD_REQUEST)

    algorithm = str(data["algorithm"])[:256]
    prompt = str(data["prompt"])[:4000] if data.get("prompt") else None
    task = animate_algorithm.delay(job_id=job_id, algorithm=algorithm, prompt=prompt)
    return Response({"task_id": task.id, "status": "QUEUED"}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
def task_status(request, task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    payload = {"task_id": task_id, "state": res.state}
    if res.state == "SUCCESS":
        payload["result"] = res.result
    elif res.state == "FAILURE":
        payload["error"] = str(res.result)
    return Response(payload)
