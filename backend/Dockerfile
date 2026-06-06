# Morocco Spatial Dashboard — backend API
# Multi-stage; run as non-root.

FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps -w /wheels -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONPATH=/app

# Non-root user
RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY app ./app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
