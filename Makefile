.PHONY: help dev down build test lint migrate logs clean

# ── Colors ──
GREEN  := \033[0;32m
YELLOW := \033[1;33m
NC     := \033[0m

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-18s$(NC) %s\n", $$1, $$2}'

# ── Docker Compose ────────────────────────────────────────────────────────────
dev: ## Start all services (hot-reload)
	@echo "$(YELLOW)Starting NEUROTWIN OS dev stack…$(NC)"
	docker compose up --build

down: ## Stop all services
	docker compose down

build: ## Build all Docker images
	docker compose build --parallel

logs: ## Tail all service logs
	docker compose logs -f

logs-api: ## Tail API logs only
	docker compose logs -f api

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run backend tests
	@echo "$(YELLOW)Running backend tests…$(NC)"
	cd services/api && pytest tests/ -v --cov=app --cov-report=term-missing

test-watch: ## Run tests in watch mode
	cd services/api && ptw tests/

test-web: ## Run frontend type check + lint
	cd web && npm run type-check && npm run lint

# ── Linting ───────────────────────────────────────────────────────────────────
lint: ## Lint Python (ruff) + TypeScript (eslint)
	cd services/api && ruff check app/ && mypy app/ --ignore-missing-imports
	cd web && npm run lint

format: ## Auto-format Python (ruff) + TypeScript (prettier)
	cd services/api && ruff format app/
	cd web && npx prettier --write .

# ── Database ──────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	cd services/api && alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="add_users")
	cd services/api && alembic revision --autogenerate -m "$(MSG)"

db-shell: ## Open psql shell
	docker compose exec postgres psql -U neurotwin -d neurotwin_db

redis-shell: ## Open Redis CLI
	docker compose exec redis redis-cli

# ── Web ───────────────────────────────────────────────────────────────────────
web-install: ## Install web deps
	cd web && npm install

web-dev: ## Run Next.js dev server
	cd web && npm run dev

web-build: ## Build web for production
	cd web && npm run build

# ── K8s ───────────────────────────────────────────────────────────────────────
k8s-apply: ## Apply K8s manifests
	kubectl apply -f infra/k8s/manifests.yaml

k8s-status: ## Check deployment status
	kubectl get all -n neurotwin

k8s-logs: ## Tail API pod logs
	kubectl logs -f -l app=neurotwin-api -n neurotwin

# ── Utilities ─────────────────────────────────────────────────────────────────
clean: ## Remove __pycache__, .next, etc.
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf web/.next web/node_modules services/api/.mypy_cache

setup: ## First-time setup: copy .env, install deps
	cp .env.example .env
	cd web && npm install
	cd services/api && pip install -r requirements.txt
	@echo "$(GREEN)✅ Setup complete. Edit .env and run: make dev$(NC)"
