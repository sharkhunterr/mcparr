# MCParr AI Gateway

MCP (Model Context Protocol) server with web administration interface for AI-powered homelab management.

## Quick Start

```bash
# Clone and start with Docker Compose
git clone https://github.com/sharkhunterr/mcparr.git
cd mcparr
docker compose -f docker/docker-compose.yml up -d
```

Or pull individual images:

```bash
docker pull sharkhunterr/mcparr-backend:latest
docker pull sharkhunterr/mcparr-frontend:latest
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Web admin interface |
| Backend API | 8000 | REST API |
| MCP Server | 8001 | Model Context Protocol |

## Tags

- `latest` - Latest stable version
- `vX.Y.Z` - Specific version (e.g., `v0.2.0`)

## Features

- **Service Management**: Configure Plex, Overseerr, Sonarr, Radarr, and more
- **Real-time Monitoring**: Live logs, metrics, and health checks
- **AI Training**: Custom Ollama model training with progress tracking
- **User Mapping**: Automatic user synchronization across services
- **MCP Integration**: Open WebUI compatible AI assistant

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///data/mcparr.db` | Database connection |
| `REDIS_URL` | `redis://redis:6379` | Redis for caching |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |

## Health Check

```bash
# Backend health
curl http://localhost:8000/health

# Frontend (nginx)
curl http://localhost:3000
```

## Documentation

- API Docs: http://localhost:8000/docs
- GitHub: [sharkhunterr/mcparr](https://github.com/sharkhunterr/mcparr)
