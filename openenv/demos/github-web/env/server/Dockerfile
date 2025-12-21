FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY env/server/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN python -m playwright install chromium

# Copy application code
COPY . /app/

# Make start script executable
RUN chmod +x /app/env/server/start.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV VIEWPORT_WIDTH=1280
ENV VIEWPORT_HEIGHT=720
ENV TIMEOUT=10000
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/env/server/start.sh"]
