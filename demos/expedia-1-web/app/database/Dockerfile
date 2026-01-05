# app/database/Dockerfile
FROM postgres:15-alpine

# Copy init scripts
COPY init/ /docker-entrypoint-initdb.d/

# Healthcheck
HEALTHCHECK --interval=5s --timeout=3s --retries=20 \
  CMD pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" || exit 1
