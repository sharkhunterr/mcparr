#!/bin/bash

# Script de redémarrage propre pour MCParr AI Gateway
echo "🧹 Nettoyage complet..."

# Tuer tous les processus
echo "Arrêt des processus..."
pkill -9 -f "vite" 2>/dev/null || true
pkill -9 -f "esbuild" 2>/dev/null || true
pkill -9 -f "src/main.py" 2>/dev/null || true
pkill -9 -f "npm run dev" 2>/dev/null || true

# Nettoyer les caches
echo "Nettoyage des caches..."
rm -rf frontend/.vite
rm -rf frontend/node_modules/.vite
rm -rf frontend/dist
rm -rf .pids/

# Attendre que tout se termine
sleep 3

echo "🚀 Redémarrage..."

# Démarrer le backend
echo "Démarrage backend..."
cd backend
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi
nohup python3 src/main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
cd ..

# Attendre un peu
sleep 3

# Démarrer le frontend
echo "Démarrage frontend..."
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
cd ..

# Créer le dossier PIDs
mkdir -p .pids
echo $BACKEND_PID > .pids/backend.pid
echo $FRONTEND_PID > .pids/frontend.pid

sleep 5

echo "✅ Démarré !"
echo ""
echo "📊 Vérification des services:"

# Vérifier le backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend: http://localhost:8000"
else
    echo "❌ Backend: Erreur"
fi

# Trouver le port du frontend
FRONTEND_PORT=$(tail -10 frontend.log | grep "Local:" | grep -o "http://localhost:[0-9]*" | tail -1 | grep -o "[0-9]*" | tail -1)

if [ ! -z "$FRONTEND_PORT" ]; then
    echo "✅ Frontend: http://localhost:$FRONTEND_PORT"
else
    echo "❌ Frontend: Port non trouvé"
fi

echo ""
echo "📝 Logs:"
echo "Backend:  tail -f backend.log"
echo "Frontend: tail -f frontend.log"