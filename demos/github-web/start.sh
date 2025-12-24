#!/bin/bash

# GitHub Clone - Start All Services (No Docker)

set -e

echo "🚀 Starting GitHub Clone..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check PostgreSQL
echo -e "${BLUE}Checking PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL not found. Please install it first.${NC}"
    exit 1
fi

# Check if database exists
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw github_web_db; then
    echo -e "${BLUE}Creating database...${NC}"
    sudo -u postgres psql -c "CREATE DATABASE github_web_db;"

    echo -e "${BLUE}Running schema and seed data...${NC}"
    sudo -u postgres psql -d github_web_db -f app/database/init/01_schema.sql
    sudo -u postgres psql -d github_web_db -f app/database/init/02_seed.sql
    echo -e "${GREEN}✓ Database setup complete${NC}"
else
    echo -e "${GREEN}✓ Database already exists${NC}"
fi

# Backend
echo ""
echo -e "${BLUE}Setting up Backend...${NC}"
cd app/backend

if [ ! -d "node_modules" ]; then
    echo "Installing backend dependencies..."
    npm install
fi

# Create .env if not exists
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
NODE_ENV=development
PORT=5000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=github_web_db
DB_USER=postgres
DB_PASSWORD=postgres
EOF
    echo -e "${GREEN}✓ Backend .env created${NC}"
fi

echo -e "${BLUE}Starting Backend on port 5000...${NC}"
npm start &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

cd ../..

# Frontend
echo ""
echo -e "${BLUE}Setting up Frontend...${NC}"
cd app/frontend

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Create .env if not exists
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
VITE_API_URL=http://localhost:5000
EOF
    echo -e "${GREEN}✓ Frontend .env created${NC}"
fi

echo -e "${BLUE}Starting Frontend on port 3000...${NC}"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

cd ../..

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ All services started!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "Backend:  ${BLUE}http://localhost:5000${NC}"
echo -e "Database: ${BLUE}localhost:5432${NC}"
echo ""
echo "Test accounts:"
echo "  octocat@github.com / github123"
echo "  linus@kernel.org / linux123"
echo "  guido@python.org / python123"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running and handle Ctrl+C
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Wait for processes
wait
