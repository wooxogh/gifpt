FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir celery==5.3.6 redis==5.0.1 requests==2.32.3
RUN mkdir -p /app/studio && touch /app/studio/__init__.py
COPY mock_tasks.py /app/studio/tasks.py
ENV PYTHONPATH=/app
CMD ["celery", "-A", "studio.tasks", "worker", "-l", "info", "-Q", "gifpt.default", "--concurrency=4"]
