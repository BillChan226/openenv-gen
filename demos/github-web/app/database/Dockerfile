FROM postgres:15-alpine

# Copy initialization scripts
COPY init/ /docker-entrypoint-initdb.d/

EXPOSE 5432
