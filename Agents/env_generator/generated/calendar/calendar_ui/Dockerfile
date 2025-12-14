FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies based on lockfiles if present for better caching
COPY calendar_ui/package.json calendar_ui/package-lock.json* calendar_ui/yarn.lock* calendar_ui/pnpm-lock.yaml* ./

RUN \
  if [ -f package-lock.json ]; then npm ci; \
  elif [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
  elif [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install --frozen-lockfile; \
  else npm install; \
  fi

# Copy the rest of the frontend source
COPY calendar_ui/ .

# Build the production assets
RUN \
  if [ -f package.json ]; then \
    if npm run | grep -q "build"; then npm run build; \
    elif command -v yarn >/dev/null 2>&1 && yarn run | grep -q "build"; then yarn build; \
    else echo "No build script found in package.json" && exit 1; \
    fi; \
  else \
    echo "package.json not found in calendar_ui" && exit 1; \
  fi

# Runtime stage
FROM nginx:alpine

# Copy built assets from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Default nginx config can serve a SPA; override if custom routing is needed
# Optionally, you can add a custom nginx.conf here if required by the app.
# For now, rely on the default config which serves /usr/share/nginx/html on port 80.

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]