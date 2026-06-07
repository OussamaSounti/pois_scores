# Morocco Spatial Dashboard — backend API / pipeline
# Multi-stage; run as non-root.
#
# Build API image (default):
#   docker build -t backend-api ./backend
# Build pipeline image (includes Prefect):
#   docker build --build-arg INSTALL_TARGET=pipeline -t backend-pipeline ./backend

FROM python:3.12-slim AS builder

ARG INSTALL_TARGET=api

WORKDIR /build

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt requirements-pipeline.txt ./
RUN if [ "$INSTALL_TARGET" = "pipeline" ]; then \
      pip install --no-cache-dir -r requirements-pipeline.txt; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONPATH=/app

RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app ./app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
