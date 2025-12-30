# MCParr AI Gateway

An MCP (Model Context Protocol) server with a modern web administration interface for managing homelab service integration with AI.

## 🚀 Features

- **Web Interface**: Modern, responsive admin dashboard (UI-First approach)
- **Service Management**: Centralized configuration for Plex, Overseerr, Zammad, Tautulli, Authentik
- **Real-time Observability**: Live logs, metrics, and request tracing
- **AI Training**: Custom Ollama model training with progress tracking
- **MCP Server**: Open WebUI integration for AI-powered homelab interactions
- **User Mapping**: Automatic user identity synchronization across services

## 📋 Requirements

- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- 4GB RAM minimum
- 10GB disk space

## 🚀 Démarrage rapide

### Script de gestion automatique (Recommandé)

```bash
# Première installation (installe toutes les dépendances)
./manage.sh install

# Démarrer les services
./manage.sh start

# Arrêter les services
./manage.sh stop

# Redémarrer les services
./manage.sh restart

# Voir le statut
./manage.sh status
```

### Accès aux services :

- 🌐 **Interface Web**: http://localhost:5173
- 🔧 **API Backend**: http://localhost:8000
- 📚 **Documentation**: http://localhost:8000/docs

### Installation manuelle (Development)

#### Prérequis
- **Node.js** 20+ (Vite requirement)
- **Python** 3.9+

#### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary python-multipart websockets psutil python-dotenv pydantic-settings
python3 src/main.py
```

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
mcparr-gateway/
├── backend/          # FastAPI backend application
│   ├── src/         # Source code
│   │   ├── adapters/    # Service adapters
│   │   ├── models/      # Database models
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Business logic
│   │   └── websocket/   # WebSocket handlers
│   ├── alembic/     # Database migrations
│   └── tests/       # Backend tests
├── frontend/        # React TypeScript frontend
│   ├── src/        # Source code
│   │   ├── components/  # React components
│   │   ├── pages/      # Page components
│   │   ├── hooks/      # Custom hooks
│   │   └── lib/        # Utilities
│   └── public/     # Static assets
├── docker/         # Docker configurations
├── docs/          # Documentation
└── scripts/       # Utility scripts
```

## 🔌 Service Configuration

Configure your homelab services in the `.env` file:

### Plex
```env
PLEX_URL=http://your-plex-server:32400
PLEX_TOKEN=your-plex-token
```

### Overseerr
```env
OVERSEERR_URL=http://your-overseerr:5055
OVERSEERR_API_KEY=your-api-key
```

### Other Services
See `.env.example` for complete configuration options.

## 🎯 User Stories & MVP

The system is built following these prioritized user stories:

1. **Web Interface (P1)** - Complete admin dashboard ✅
2. **Service Management (P1)** - Configure and test homelab services
3. **Observability (P1)** - Real-time logs and metrics
4. **AI Training (P2)** - Custom Ollama model training
5. **MCP Server (P2)** - Open WebUI integration

## 🧪 Testing

### Manual Testing

Each user story includes independent test scenarios:

```bash
# Test dashboard loads under 2 seconds
curl -w "@curl-format.txt" http://localhost:8000/api/v1/dashboard/overview

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/logs
```

### Automated Tests

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test
```

## 📊 Monitoring

- **Metrics**: Prometheus-compatible metrics at `/metrics`
- **Health Check**: `/health` endpoint for Docker/Kubernetes
- **Logs**: Structured JSON logging with correlation IDs

## 🔒 Security

- No authentication required on local network (configurable)
- All secrets in environment variables
- Input validation and sanitization
- Rate limiting and circuit breakers

## 📝 API Documentation

- Interactive API docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
- MCP protocol docs: http://localhost:8001/docs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the task structure in `tasks.md`
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- Documentation: `/docs` directory
- Issues: GitHub Issues
- Discord: [Join our server](https://discord.gg/mcparr)

---

Built with ❤️ following UI-First principles for the homelab community