#!/bin/bash
# Script d'initialisation du backend Python

set -e

echo "🐍 Configuration du backend Python..."

cd "$(dirname "$0")/../src/backend"

# Vérifier si Poetry est installé
if ! command -v poetry &> /dev/null; then
    echo "⚠️  Poetry n'est pas installé."
    echo "📦 Installation de Poetry..."

    # Installer Poetry
    curl -sSL https://install.python-poetry.org | python3 -

    # Ajouter Poetry au PATH pour cette session
    export PATH="$HOME/.local/bin:$PATH"

    echo "✅ Poetry installé"
fi

# Configurer Poetry pour créer le venv dans le projet
poetry config virtualenvs.in-project true

# Installer les dépendances
echo "📦 Installation des dépendances..."
poetry install

echo "✅ Backend configuré avec succès!"
echo ""
echo "Pour activer l'environnement virtuel:"
echo "  cd src/backend"
echo "  source .venv/bin/activate"
