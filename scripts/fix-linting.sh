#!/bin/bash
set -e

echo "==================================="
echo "MCParr - Auto-fix Linting Issues"
echo "==================================="

cd "$(dirname "$0")/.."

# Backend linting fixes
if [ -d "src/backend" ]; then
    echo ""
    echo "📦 Backend - Auto-fixing linting issues..."
    cd src/backend

    if command -v poetry &> /dev/null; then
        echo "  → Running ruff --fix..."
        poetry run ruff check src/ --fix --unsafe-fixes || true

        echo "  → Running black..."
        poetry run black src/ || true

        echo "  → Generating linting report..."
        poetry run ruff check src/ --output-format=json > ruff-report.json || true
        poetry run ruff check src/ --output-format=text > ruff-report.txt || true

        echo "✅ Backend linting fixes applied"
    else
        echo "⚠️  Poetry not found, skipping backend fixes"
    fi

    cd ../..
fi

# Frontend linting fixes
if [ -d "src/frontend" ]; then
    echo ""
    echo "🎨 Frontend - Auto-fixing linting issues..."
    cd src/frontend

    if command -v npm &> /dev/null; then
        echo "  → Running eslint --fix..."
        npm run lint:fix 2>/dev/null || npm run lint -- --fix 2>/dev/null || echo "  ℹ️  No lint:fix script available"

        echo "✅ Frontend linting fixes applied"
    else
        echo "⚠️  npm not found, skipping frontend fixes"
    fi

    cd ../..
fi

echo ""
echo "✅ All linting fixes completed!"
