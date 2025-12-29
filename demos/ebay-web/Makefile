.PHONY: verify build up down smoke health

# Acceptance-style verification:
# - builds docker images
# - starts docker-compose stack
# - checks backend health
# - runs frontend smoke HTTP checks
verify: build up health smoke

build:
	docker compose -f docker/docker-compose.yml build

up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down -v --remove-orphans

health:
	curl -fsS http://localhost:18000/health

smoke:
	node app/frontend/scripts/smoke-http.mjs
