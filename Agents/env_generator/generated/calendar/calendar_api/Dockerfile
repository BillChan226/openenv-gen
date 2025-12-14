FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies only if needed; keep minimal for now
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY openenv_adapter/requirements.txt ./openenv_adapter/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r openenv_adapter/requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

# Adjust the module path and app object if they differ in main.py
CMD ["uvicorn", "openenv_adapter.server.main:app", "--host", "0.0.0.0", "--port", "8000"]