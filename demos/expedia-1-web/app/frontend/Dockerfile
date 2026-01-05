# Development/Preview stage with Vite dev server
# This allows the proxy to work for API calls
FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm install --no-audit --no-fund

# Copy source code
COPY . .

# Expose the port (default 3001, can be overridden via VITE_PORT)
EXPOSE 3001

# Start the dev server - binds to 0.0.0.0 for Docker access
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
