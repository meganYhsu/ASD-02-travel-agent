FROM python:3.12-slim
# FLASK_HOST: if the command is overridden with `python db_api.py` (as
# deployment/aws/compose.yaml does), it must still listen on the container
# network, not only on the container's own loopback.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/preferences.db \
    FLASK_HOST=0.0.0.0
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Run as a non-root user; only the data directories are writable.
# /data is the volume path used by deployment/aws/compose.yaml: a new named
# volume copies this directory's owner, so appuser can write to it. Its
# sqlite-entrypoint.py helper links /app/preferences.db to /data; creating
# that link here means the helper never needs write access to /app.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /data \
    && chown appuser /app/data /data \
    && ln -s /data/preferences.db /app/preferences.db
USER appuser
EXPOSE 6001
# One worker: SQLite has a single writer. --preload creates the schema once.
CMD ["gunicorn", "--bind", "0.0.0.0:6001", "--workers", "1", "--threads", "8", "--preload", "--access-logfile", "-", "wsgi:app"]
