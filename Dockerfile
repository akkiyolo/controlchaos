FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend /app/backend
COPY frontend /app/frontend
COPY scripts /app/scripts
COPY .env.example /app/.env.example

# Install python dependencies
RUN pip install --no-cache-dir -e "/app/backend"

EXPOSE 8000

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
