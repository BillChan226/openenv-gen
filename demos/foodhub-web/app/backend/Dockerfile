FROM node:20-alpine

WORKDIR /app

# Native modules build deps (bcrypt)
RUN apk add --no-cache python3 make g++

COPY package.json package-lock.json* ./
RUN npm install --omit=dev --legacy-peer-deps

COPY . .

ENV NODE_ENV=production
# Backend listens on PORT (docker-compose sets 8083)
EXPOSE 8083

CMD ["npm", "start"]
