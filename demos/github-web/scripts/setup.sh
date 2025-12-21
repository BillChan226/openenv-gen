#!/usr/bin/env bash
# Setup script for {{ENV_NAME}} environment
set -euo pipefail

echo "Setting up {{ENV_NAME}} environment..."

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd app/frontend && npm install && cd ../..

# Install backend dependencies
echo "Installing backend dependencies..."
cd app/backend && npm install && cd ../..

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r env/server/requirements.txt

# Install Playwright
echo "Installing Playwright browsers..."
python -m playwright install chromium

# Copy environment file
if [ ! -f docker/.env ]; then
    cp docker/.env.example docker/.env
    echo "Created docker/.env from template"
fi

echo "Setup complete!"
echo ""
echo "To start the environment:"
echo "  cd docker && docker-compose up --build"
echo ""
echo "To run in development mode:"
echo "  cd docker && docker-compose -f docker-compose.yml -f docker-compose.dev.yml up"
