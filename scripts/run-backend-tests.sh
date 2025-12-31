#!/bin/bash
# Script pour lancer les tests backend (avec ou sans Poetry)

set -e

cd "$(dirname "$0")/../src/backend"

# Fonction pour lancer les tests
run_tests() {
    if command -v poetry &> /dev/null; then
        echo "🐍 Lancement des tests avec Poetry..."
        poetry run pytest --cov=src --cov-report=xml --cov-report=html --cov-report=term --junitxml=junit.xml -v
    elif [ -f ".venv/bin/activate" ]; then
        echo "🐍 Lancement des tests avec venv..."
        source .venv/bin/activate
        pytest --cov=src --cov-report=xml --cov-report=html --cov-report=term --junitxml=junit.xml -v
    else
        echo "❌ Erreur: Ni Poetry ni environnement virtuel trouvé"
        echo ""
        echo "Pour configurer le backend, exécutez:"
        echo "  bash scripts/setup-backend.sh"
        exit 1
    fi
}

run_tests
