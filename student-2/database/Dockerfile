FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5402
ENV DATABASE_PATH=/data/traveler_preferences.db
EXPOSE 5402
CMD ["python", "app.py"]
