# 🚀 MCParr AI Gateway

> **AI-powered homelab management with MCP server and web administration**

MCParr is your unified gateway for managing homelab services through AI. Built with FastAPI and React, it combines a powerful MCP (Model Context Protocol) server with a modern web interface for seamless AI-driven automation.

## 🆕 What's New in v1.0.0

- ✨ **15+ Service Integrations**: Plex, Overseerr, Radarr, Sonarr, Prowlarr, Deluge, Komga, Audiobookshelf, Wiki.js, Zammad, Authentik, Open WebUI, Ollama, Jackett, ROMM
- 🧠 **AI Training**: Custom Ollama model training with GPU support and real-time progress tracking
- 👥 **User Management**: Centralized user mapping across services with group-based permissions
- 📊 **Observability**: Real-time WebSocket logs, system metrics, and health monitoring
- 🔌 **MCP Server**: Complete Model Context Protocol implementation for AI assistants
- 💾 **Backup/Restore**: Full configuration export and import

See [CHANGELOG.md](https://github.com/sharkhunterr/mcparr/blob/master/CHANGELOG.md) for complete version history.

## ✨ Features

🎯 **Unified Service Management**
- Configure and control Plex, Overseerr, Sonarr, Radarr, Prowlarr, and 15+ services
- Single MCP endpoint for all your homelab automation

📊 **Real-time Monitoring**
- Live logs with WebSocket streaming
- System metrics and health checks
- Alert management with customizable rules

🤖 **AI Training & Integration**
- Custom Ollama model training with GPU support
- Training progress tracking and session management
- Open WebUI compatible MCP tools

👥 **User Synchronization**
- Automatic user mapping across services
- Centralized authentication
- Group-based permissions

🔧 **Developer Friendly**
- Complete REST API with OpenAPI docs
- WebSocket endpoints for real-time data
- Comprehensive logging and observability

## 🚢 Quick Start

### Single unified image (recommended)

```bash
# Pull the latest image
docker pull sharkhunterr/mcparr:latest

# Run with Docker Compose
curl -o docker-compose.yml https://raw.githubusercontent.com/sharkhunterr/mcparr/master/docker/docker-compose.yml
docker compose up -d
```

### Access your gateway

- 🌐 Web UI: http://localhost:3000
- 📡 API Docs: http://localhost:8000/docs
- 🤖 MCP Server: http://localhost:8001

## 🤖 Connect to Open WebUI

MCParr is designed for **Open WebUI** - use AI to control your entire homelab through chat!

### 1. Install Open WebUI

```bash
docker run -d -p 3001:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

### 2. Add MCParr Tools

In Open WebUI:
1. **Settings** → **Admin Settings** → **Tools**
2. Click **"+ Add Tool"**
3. Configure:
   - **Type**: Select **"OpenAPI"**
   - **URL**: `http://host.docker.internal:8000` (or your MCParr IP)
   - **OpenAPI Spec**: Select `/tools/openapi.json`
   - **Auth**: Select **"Session"**
   - **Username**: "MCParr Homelab"
   - **Visibility**: "Public"
4. Click **Save**

**Note**: Use `host.docker.internal` to access MCParr from Open WebUI container on macOS/Windows. On Linux, use your machine's IP (e.g., `192.168.1.21`).

### 3. Start Chatting!

Enable MCParr tools in your chat and control your homelab:

```
You: What's in my Plex library?
AI: You have 1,234 movies, 89 TV shows, and 456 albums

You: Request the new season of The Expanse
AI: Requested The Expanse Season 6 via Overseerr!

You: How are my downloads?
AI: 3 movies downloading in Radarr, 5 episodes in Sonarr
```

## 🏷️ Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `v0.2.x` | Specific version (e.g., `v0.2.3`) |
| `dev` | Development builds (not for production) |

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///data/mcparr.db` | Database connection string |
| `REDIS_URL` | `redis://redis:6379` | Redis cache URL |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `API_PORT` | `8000` | Backend API port |
| `MCP_PORT` | `8001` | MCP server port |
| `FRONTEND_PORT` | `3000` | Web UI port |

### Volumes

| Volume | Description |
|--------|-------------|
| `/app/data` | SQLite database and application data |
| `/app/logs` | Application logs (optional) |

### Ports

| Port | Service | Description |
|------|---------|-------------|
| `3000` | Web UI | React frontend served by nginx |
| `8000` | API | FastAPI REST API |
| `8001` | MCP | Model Context Protocol server |

## 🔍 Health Check

```bash
# Check backend API
curl http://localhost:8000/health

# Check web UI
curl http://localhost:3000

# Full stack check
docker compose ps
```

## 📖 Usage Examples

### Basic deployment

```yaml
version: '3.8'
services:
  mcparr:
    image: sharkhunterr/mcparr:latest
    ports:
      - "3000:3000"  # Web UI
      - "8000:8000"  # API
      - "8001:8001"  # MCP
    volumes:
      - mcparr-data:/app/data
    environment:
      - LOG_LEVEL=INFO
    restart: unless-stopped

volumes:
  mcparr-data:
```

### With Redis cache

```yaml
version: '3.8'
services:
  mcparr:
    image: sharkhunterr/mcparr:latest
    ports:
      - "3000:3000"
      - "8000:8000"
      - "8001:8001"
    volumes:
      - mcparr-data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  mcparr-data:
  redis-data:
```

### Production deployment

```yaml
version: '3.8'
services:
  mcparr:
    image: sharkhunterr/mcparr:latest
    ports:
      - "3000:3000"
      - "8000:8000"
      - "8001:8001"
    volumes:
      - mcparr-data:/app/data
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=sqlite:///data/mcparr.db
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=WARNING
      - CORS_ORIGINS=https://mcparr.yourdomain.com
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  mcparr-data:
  redis-data:
```

## 🛠️ Supported Services

MCParr integrates with 15+ homelab services:

**Media Management**
- Plex, Jellyfin, Emby
- Overseerr, Radarr, Sonarr, Prowlarr
- Tautulli

**Downloads**
- Deluge, qBittorrent
- Jackett

**Books & Games**
- Audiobookshelf, Komga
- ROMM

**Utilities**
- Authentik, Wiki.js, Zammad
- Open WebUI, Ollama

## 📚 Documentation

- 📘 [GitHub Repository](https://github.com/sharkhunterr/mcparr)
- 🔗 [API Documentation](http://localhost:8000/docs) (after deployment)
- 📖 [Wiki](https://github.com/sharkhunterr/mcparr/wiki)

## 🤝 Contributing

Contributions are welcome! Please visit the [GitHub repository](https://github.com/sharkhunterr/mcparr) for more information.

## 📄 License

MIT License - see [LICENSE](https://github.com/sharkhunterr/mcparr/blob/master/LICENSE) for details

---

**Built with** ❤️ **for the homelab community**
