#!/bin/bash
# Script pour corriger le linting backend (avec ou sans Poetry)

set -e

cd "$(dirname "$0")/../src/backend"

run_fix() {
    if command -v poetry &> /dev/null; then
        echo "🔧 Correction avec Poetry..."
        poetry run ruff check src/ --fix --unsafe-fixes
        poetry run black src/
    elif [ -f ".venv/bin/activate" ]; then
        echo "🔧 Correction avec venv..."
        source .venv/bin/activate
        ruff check src/ --fix --unsafe-fixes
        black src/
    else
        echo "❌ Erreur: Ni Poetry ni environnement virtuel trouvé"
        echo ""
        echo "Pour configurer le backend, exécutez:"
        echo "  bash scripts/setup-backend.sh"
        exit 1
    fi
}

run_fix
