FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5405
ENV DATABASE_PATH=/data/travel_docs.db
EXPOSE 5405
CMD ["python", "app.py"]
