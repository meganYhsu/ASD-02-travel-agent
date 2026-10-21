FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUDGET_DB_PATH=/app/data/budget.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Run as a non-root user; only the data directory is writable.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown appuser /app/data
USER appuser
EXPOSE 6003
# One worker: SQLite has a single writer. --preload creates the schema once.
CMD ["gunicorn", "--bind", "0.0.0.0:6003", "--workers", "1", "--threads", "8", "--preload", "--access-logfile", "-", "wsgi:app"]
