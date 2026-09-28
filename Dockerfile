FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

ENV PORT=5001

EXPOSE 5001

CMD ["sh", "-c", "python ensure_cloud_data.py && exec gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-5001} app:app"]
