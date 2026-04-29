FROM python:3.13-alpine AS builder

RUN apk add --no-cache gcc musl-dev libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

# Runtime only — no headers, no compiler
RUN apk add --no-cache libpq

WORKDIR $APP_HOME

# Copy pre-built packages from builder
COPY --from=builder /install /usr/local

# Copy app
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Non-root user
RUN addgroup -S appuser && adduser -S -G appuser -h /app appuser
RUN chown -R appuser:appuser $APP_HOME
ENV HOME=/app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "app.main:app", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "1", \
    "--preload", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "100", \
    "--timeout", "60", \
    "--graceful-timeout", "30", \
    "--forwarded-allow-ips=*"]