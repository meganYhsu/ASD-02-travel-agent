FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 3003
# --timeout is longer than the proxy's 450 s backend timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:3003", "--workers", "2", "--threads", "4", "--timeout", "480", "--access-logfile", "-", "app:app"]
