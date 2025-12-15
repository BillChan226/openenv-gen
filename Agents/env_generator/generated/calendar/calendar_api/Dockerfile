FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (if needed in the future)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY calendar_api/requirements.txt ./calendar_api/requirements.txt
RUN pip install --no-cache-dir -r calendar_api/requirements.txt

# Copy application code
COPY calendar_api ./calendar_api

# Expose the application port
EXPOSE 8000

# Default command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "calendar_api.main:app", "--host", "0.0.0.0", "--port", "8000"]