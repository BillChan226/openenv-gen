FROM node:20-alpine AS builder
WORKDIR /app

# Ensure devDependencies are installed for the build (vite lives in devDependencies)
ENV NODE_ENV=development
ENV NPM_CONFIG_PRODUCTION=false

# Install dependencies first (better layer caching)
COPY package.json package-lock.json ./
RUN npm ci --include=dev

# Copy source and build
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# IMPORTANT: overwrite the default nginx site config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Container listens on 3000; docker-compose maps host port 8000 -> 3000
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
