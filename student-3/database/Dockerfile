FROM python:3.12-slim
# BUDGET_DB_PATH: the SQLite file lives in /data, the volume path used by
# deployment/aws/compose.yaml. FLASK_HOST: that compose file overrides the
# command with `python db_api.py`, which must still listen on the container
# network, not only on the container's own loopback.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUDGET_DB_PATH=/data/budget.db \
    FLASK_HOST=0.0.0.0
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Run as a non-root user; only /data is writable. A new named volume copies
# this directory's owner, so appuser can write to it. The AWS compose file's
# sqlite-entrypoint.py links /app/budget.db to /data/budget.db; creating that
# link here means the helper never needs write access to /app.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown appuser /data \
    && ln -s /data/budget.db /app/budget.db
USER appuser
EXPOSE 6003
# One worker: SQLite has a single writer. --preload creates the schema once.
CMD ["gunicorn", "--bind", "0.0.0.0:6003", "--workers", "1", "--threads", "8", "--preload", "--access-logfile", "-", "wsgi:app"]
