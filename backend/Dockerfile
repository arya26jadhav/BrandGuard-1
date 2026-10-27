FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY wheels ./wheels
RUN pip install --no-cache-dir --no-index --find-links=wheels -r requirements.txt

COPY app ./app

EXPOSE 8000
    CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]