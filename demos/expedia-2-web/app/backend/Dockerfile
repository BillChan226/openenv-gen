FROM node:20-alpine

WORKDIR /app

# Native build deps for bcrypt
RUN apk add --no-cache python3 make g++

COPY package.json package-lock.json* ./
RUN npm install --omit=dev --legacy-peer-deps

COPY . .

ENV NODE_ENV=production
EXPOSE 3000

CMD ["node", "server.js"]
