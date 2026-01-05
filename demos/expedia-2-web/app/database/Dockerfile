# Use specific version - changing this breaks existing volumes!
FROM postgres:16-alpine

ENV POSTGRES_INITDB_ARGS="--encoding=UTF-8 --locale=C"

# Initialization scripts (executed in alphabetical order)
COPY init/ /docker-entrypoint-initdb.d/
