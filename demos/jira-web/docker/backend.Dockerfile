# Backend Dockerfile (production-like)
#
# IMPORTANT: This image intentionally installs production dependencies only.
# The backend `start` script MUST NOT rely on devDependencies (nodemon/ts-node/etc.).
FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8000

# Install runtime deps first (better caching)
COPY app/backend/package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Copy source
COPY app/backend ./

EXPOSE 8000

# Healthcheck - verify app responds
# Use Node itself (available in node:20-alpine) instead of wget/curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
  CMD node -e "fetch('http://localhost:8000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npm","start"]
