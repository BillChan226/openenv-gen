# syntax=docker/dockerfile:1

FROM postgres:16-alpine

# The official postgres image automatically runs any *.sql/*.sql.gz files
# found in /docker-entrypoint-initdb.d on first container startup.
#
# We copy the init scripts into the image to satisfy the required project
# structure (app/database/Dockerfile) and to make DB initialization work
# even without bind-mounts.
COPY init/*.sql /docker-entrypoint-initdb.d/

ENV LANG=C.UTF-8
