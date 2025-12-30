.PHONY: help up down logs ps build config health dev-up dev-down dev-logs

COMPOSE_PROD = docker compose -f docker/docker-compose.yml
COMPOSE_DEV  = docker compose -f docker/docker-compose.dev.yml

BACKEND_HOST_PORT ?= 8000

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-12s %s\n", $$1, $$2}'

build: ## Build production-like stack images
	$(COMPOSE_PROD) build

up: ## Start production-like stack (detached)
	$(COMPOSE_PROD) up -d

down: ## Stop production-like stack
	$(COMPOSE_PROD) down

logs: ## Tail production-like stack logs
	$(COMPOSE_PROD) logs -f

ps: ## Show production-like stack status
	$(COMPOSE_PROD) ps

config: ## Print resolved production-like compose config
	$(COMPOSE_PROD) config

health: ## Verify backend health endpoint
	curl -fsS http://localhost:$(BACKEND_HOST_PORT)/health

# Dev stack helpers

dev-up: ## Start dev stack (foreground)
	$(COMPOSE_DEV) up

dev-down: ## Stop dev stack
	$(COMPOSE_DEV) down

dev-logs: ## Tail dev stack logs
	$(COMPOSE_DEV) logs -f
