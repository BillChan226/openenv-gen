# Frontend Dockerfile
# - dev target: Vite dev server with /api proxy
# - prod target: build static assets and serve via nginx with /api reverse proxy

# -----------------
# Dev (Vite)
# -----------------
FROM node:20-alpine AS dev
WORKDIR /app

COPY app/frontend/package*.json ./
RUN npm ci

COPY app/frontend ./

EXPOSE 5173
CMD ["npm","run","dev","--","--host","0.0.0.0","--port","5173","--strictPort"]

# -----------------
# Build
# -----------------
FROM node:20-alpine AS build
WORKDIR /app

COPY app/frontend/package*.json ./
RUN npm ci

COPY app/frontend ./

# Build-time API base URL: use relative /api for same-origin in production.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# -----------------
# Prod (nginx)
# -----------------
FROM nginx:1.27-alpine AS prod

# Nginx config with /api reverse proxy to backend service
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Static assets
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1
