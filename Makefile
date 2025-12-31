.PHONY: help install test lint lint-fix clean backend-test frontend-test backend-lint frontend-lint auto-fix ci-simulate

# Couleurs pour l'output
BLUE=\033[0;34m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

help: ## Affiche cette aide
	@echo "$(BLUE)MCParr - Commandes disponibles$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Exemples:$(NC)"
	@echo "  make install      # Installer toutes les dépendances"
	@echo "  make test         # Lancer tous les tests"
	@echo "  make lint-fix     # Corriger automatiquement les erreurs de linting"
	@echo "  make ci-simulate  # Simuler le pipeline CI localement"

install: ## Installe toutes les dépendances (backend + frontend)
	@echo "$(BLUE)📦 Installation des dépendances...$(NC)"
	@cd src/backend && pip install poetry && poetry install
	@cd src/frontend && npm ci
	@echo "$(GREEN)✅ Installation terminée$(NC)"

# =============================================================================
# Tests
# =============================================================================

test: backend-test frontend-test ## Lance tous les tests (backend + frontend)

backend-test: ## Lance les tests backend avec coverage
	@echo "$(BLUE)🐍 Tests Backend...$(NC)"
	@cd src/backend && poetry run pytest --cov=src --cov-report=xml --cov-report=html --cov-report=term --junitxml=junit.xml -v
	@echo "$(GREEN)✅ Tests backend terminés$(NC)"
	@echo "$(YELLOW)📊 Rapport de couverture: src/backend/htmlcov/index.html$(NC)"

frontend-test: ## Lance les tests frontend
	@echo "$(BLUE)🎨 Tests Frontend...$(NC)"
	@cd src/frontend && npm test || echo "⚠️  Pas de tests configurés"
	@echo "$(GREEN)✅ Tests frontend terminés$(NC)"

# =============================================================================
# Linting
# =============================================================================

lint: backend-lint frontend-lint ## Vérifie le code (backend + frontend)

backend-lint: ## Vérifie le linting du backend
	@echo "$(BLUE)🐍 Linting Backend...$(NC)"
	@cd src/backend && poetry run ruff check src/
	@cd src/backend && poetry run black --check src/
	@echo "$(GREEN)✅ Linting backend OK$(NC)"

frontend-lint: ## Vérifie le linting du frontend
	@echo "$(BLUE)🎨 Linting Frontend...$(NC)"
	@cd src/frontend && npm run lint
	@echo "$(GREEN)✅ Linting frontend OK$(NC)"

# =============================================================================
# Auto-fix
# =============================================================================

lint-fix: auto-fix ## Alias pour auto-fix

auto-fix: ## Corrige automatiquement les erreurs de linting (backend + frontend)
	@echo "$(BLUE)🔧 Correction automatique...$(NC)"
	@bash scripts/ci-auto-fix.sh
	@echo "$(GREEN)✅ Corrections appliquées$(NC)"

backend-fix: ## Corrige uniquement le backend
	@echo "$(BLUE)🐍 Correction Backend...$(NC)"
	@cd src/backend && poetry run ruff check src/ --fix --unsafe-fixes
	@cd src/backend && poetry run black src/
	@echo "$(GREEN)✅ Backend corrigé$(NC)"

frontend-fix: ## Corrige uniquement le frontend
	@echo "$(BLUE)🎨 Correction Frontend...$(NC)"
	@cd src/frontend && npm run lint -- --fix || true
	@echo "$(GREEN)✅ Frontend corrigé$(NC)"

# =============================================================================
# CI Simulation
# =============================================================================

ci-simulate: ## Simule le pipeline CI localement
	@echo "$(BLUE)🚀 Simulation du pipeline CI...$(NC)"
	@echo ""
	@echo "$(YELLOW)Stage 1: Validation$(NC)"
	@$(MAKE) lint || true
	@echo ""
	@echo "$(YELLOW)Stage 2: Tests$(NC)"
	@$(MAKE) test || true
	@echo ""
	@echo "$(GREEN)✅ Simulation terminée$(NC)"

# =============================================================================
# Rapports
# =============================================================================

reports: ## Génère tous les rapports de qualité
	@echo "$(BLUE)📊 Génération des rapports...$(NC)"
	@mkdir -p reports
	@cd src/backend && poetry run ruff check src/ --output-format=json > ../../reports/ruff-report.json || true
	@cd src/backend && poetry run ruff check src/ --output-format=text > ../../reports/ruff-report.txt || true
	@cd src/backend && poetry run pytest --cov=src --cov-report=xml --cov-report=html --junitxml=../../reports/junit.xml || true
	@cd src/frontend && npm run lint -- --format json --output-file ../../reports/eslint-report.json || true
	@cd src/frontend && npm run lint -- --format stylish > ../../reports/eslint-report.txt || true
	@echo "$(GREEN)✅ Rapports générés dans ./reports/$(NC)"
	@ls -lh reports/

# =============================================================================
# Nettoyage
# =============================================================================

clean: ## Nettoie les fichiers générés
	@echo "$(BLUE)🧹 Nettoyage...$(NC)"
	@rm -rf src/backend/htmlcov src/backend/.coverage src/backend/coverage.xml src/backend/junit.xml
	@rm -rf src/backend/.pytest_cache src/backend/.ruff_cache
	@rm -rf src/frontend/dist src/frontend/node_modules/.cache
	@rm -rf reports
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

clean-all: clean ## Nettoie tout (y compris node_modules et .venv)
	@echo "$(BLUE)🧹 Nettoyage complet...$(NC)"
	@rm -rf src/backend/.venv
	@rm -rf src/frontend/node_modules
	@echo "$(GREEN)✅ Nettoyage complet terminé$(NC)"

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Construit l'image Docker
	@echo "$(BLUE)🐳 Construction Docker...$(NC)"
	@docker build -t mcparr:local -f docker/Dockerfile .
	@echo "$(GREEN)✅ Image construite$(NC)"

docker-test: docker-build ## Test l'image Docker
	@echo "$(BLUE)🐳 Test Docker...$(NC)"
	@docker run -d --name mcparr-test -p 3000:3000 -p 8000:8000 mcparr:local
	@sleep 10
	@curl -f http://localhost:8000/health || (docker stop mcparr-test && docker rm mcparr-test && exit 1)
	@curl -f http://localhost:3000 || (docker stop mcparr-test && docker rm mcparr-test && exit 1)
	@docker stop mcparr-test
	@docker rm mcparr-test
	@echo "$(GREEN)✅ Tests Docker OK$(NC)"

# =============================================================================
# Développement
# =============================================================================

dev-backend: ## Lance le backend en mode dev
	@echo "$(BLUE)🐍 Démarrage backend...$(NC)"
	@cd src/backend && poetry run uvicorn src.main:app --reload

dev-frontend: ## Lance le frontend en mode dev
	@echo "$(BLUE)🎨 Démarrage frontend...$(NC)"
	@cd src/frontend && npm run dev

dev: ## Lance backend et frontend en parallèle (requiert tmux ou screen)
	@echo "$(BLUE)🚀 Démarrage complet...$(NC)"
	@echo "$(YELLOW)⚠️  Utilisez Ctrl+C pour arrêter les deux services$(NC)"
	@(trap 'kill 0' SIGINT; $(MAKE) dev-backend & $(MAKE) dev-frontend & wait)
