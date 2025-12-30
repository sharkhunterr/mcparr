#!/bin/bash

# MCParr Gateway - Script de gestion simple
# Usage: ./manage.sh [install|start|stop|restart|status]

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
PID_DIR="$PROJECT_DIR/.pids"

# Créer le dossier des PIDs si nécessaire
mkdir -p "$PID_DIR"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Fonction d'installation des dépendances
install_deps() {
    print_status "Installation des dépendances..."

    # Installation backend
    print_status "Installation des dépendances Python (backend)..."
    cd "$BACKEND_DIR"

    # Créer l'environnement virtuel s'il n'existe pas
    if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
        print_status "Création de l'environnement virtuel Python..."
        python3 -m venv .venv
    fi

    # Activer l'environnement virtuel et installer les dépendances
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # Installation des dépendances essentielles
    pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary python-multipart websockets psutil python-dotenv pydantic-settings

    # Créer requirements.txt si nécessaire
    if [ ! -f "requirements.txt" ]; then
        pip freeze > requirements.txt
    fi

    print_success "Dépendances Python installées"

    # Installation frontend
    print_status "Installation des dépendances Node.js (frontend)..."
    cd "$FRONTEND_DIR"

    # Vérifier si Node.js est disponible
    if ! command -v node &> /dev/null; then
        print_error "Node.js non trouvé. Veuillez installer Node.js 20+ avant de continuer."
        return 1
    fi

    # Vérifier la version de Node.js
    NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -lt 20 ]; then
        print_error "Node.js version $NODE_VERSION détectée. Version 20+ requise."
        print_warning "Installez Node.js 20+ avant de continuer."
        return 1
    fi

    npm install

    print_success "Dépendances Node.js installées"

    cd "$PROJECT_DIR"
    print_success "Installation terminée !"
}

# Fonction de démarrage
start_services() {
    print_status "Démarrage des services..."

    # Démarrer le backend
    print_status "Démarrage du backend..."
    cd "$BACKEND_DIR"

    # Vérifier si l'environnement virtuel existe
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        nohup python3 src/main.py > "$PID_DIR/backend.log" 2>&1 &
    elif [ -d "venv" ]; then
        source venv/bin/activate
        nohup python3 src/main.py > "$PID_DIR/backend.log" 2>&1 &
    elif [ -d "$PROJECT_DIR/.venv" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
        nohup python3 src/main.py > "$PID_DIR/backend.log" 2>&1 &
    else
        print_warning "Environnement virtuel non trouvé, utilisation de Python système"
        nohup python3 src/main.py > "$PID_DIR/backend.log" 2>&1 &
    fi

    echo $! > "$PID_DIR/backend.pid"
    print_success "Backend démarré (PID: $(cat "$PID_DIR/backend.pid"))"

    # Attendre un peu que le backend démarre
    sleep 3

    # Démarrer le frontend
    print_status "Démarrage du frontend..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$PID_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    print_success "Frontend démarré (PID: $(cat "$PID_DIR/frontend.pid"))"

    cd "$PROJECT_DIR"
    print_success "Services démarrés !"
    echo ""
    echo "🌐 Frontend: http://localhost:5173"
    echo "🔧 Backend:  http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
}

# Fonction d'arrêt
stop_services() {
    print_status "Arrêt des services..."

    # Arrêter le frontend
    if [ -f "$PID_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID"
            print_success "Frontend arrêté (PID: $FRONTEND_PID)"
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi

    # Arrêter le backend
    if [ -f "$PID_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID"
            print_success "Backend arrêté (PID: $BACKEND_PID)"
        fi
        rm -f "$PID_DIR/backend.pid"
    fi

    # Nettoyer les processus restants
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "src/main.py" 2>/dev/null || true

    print_success "Services arrêtés !"
}

# Fonction de redémarrage
restart_services() {
    print_status "Redémarrage des services..."
    stop_services
    sleep 2
    start_services
}

# Fonction de statut
check_status() {
    print_status "Statut des services:"
    echo ""

    # Vérifier le backend
    if [ -f "$PID_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            print_success "✅ Backend: En cours (PID: $BACKEND_PID)"
        else
            print_error "❌ Backend: Arrêté (PID obsolète)"
            rm -f "$PID_DIR/backend.pid"
        fi
    else
        print_error "❌ Backend: Arrêté"
    fi

    # Vérifier le frontend
    if [ -f "$PID_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            print_success "✅ Frontend: En cours (PID: $FRONTEND_PID)"
        else
            print_error "❌ Frontend: Arrêté (PID obsolète)"
            rm -f "$PID_DIR/frontend.pid"
        fi
    else
        print_error "❌ Frontend: Arrêté"
    fi

    echo ""
    echo "📝 Logs disponibles:"
    echo "   Backend:  tail -f $PID_DIR/backend.log"
    echo "   Frontend: tail -f $PID_DIR/frontend.log"
}

# Menu principal
show_usage() {
    echo "Usage: $0 [install|start|stop|restart|status]"
    echo ""
    echo "Commandes disponibles:"
    echo "  install  - Installer les dépendances (backend + frontend)"
    echo "  start    - Démarrer les services"
    echo "  stop     - Arrêter les services"
    echo "  restart  - Redémarrer les services"
    echo "  status   - Afficher le statut des services"
    echo ""
    echo "Exemple:"
    echo "  $0 install  # Première fois"
    echo "  $0 start    # Démarrer"
    echo "  $0 stop     # Arrêter"
}

# Script principal
case "$1" in
    install)
        install_deps
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac