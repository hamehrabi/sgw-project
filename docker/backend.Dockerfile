# SGW Resilience Platform — backend image (ADR-008: Python / FastAPI).
#
# Build context is the repository root. The image carries the application, the
# migrations (raw SQL, re-asserting the decision-record triggers), and the demo-220
# sample dataset so "Use sample storm data" works with no files on the host.
# Configuration arrives ONLY from the environment (ADR-006) — compose supplies it.

FROM python:3.12-slim

WORKDIR /app

# Dependency layer first, so code edits do not re-install the world.
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
# The bundled demo dataset, loaded through the same parse path as a real upload.
COPY scenarios/demo-220 /app/sample-data/demo-220
COPY docker/entrypoint.py /app/entrypoint.py

ENV PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# The healthcheck uses the interpreter already in the image — no curl in slim.
HEALTHCHECK --interval=5s --timeout=3s --retries=24 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"

CMD ["python", "/app/entrypoint.py"]
