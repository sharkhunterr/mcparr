# 🤖 MCParr AI Gateway

> **AI-powered homelab management with MCP server and web administration**

MCParr is a unified gateway for managing homelab services through AI. It provides a modern web interface and MCP (Model Context Protocol) server to control your self-hosted services with natural language commands.

## ✨ Features

🎯 **Unified Service Management**
- Configure and control 15+ homelab services (Plex, Radarr, Sonarr, Overseerr, Prowlarr, etc.)
- Centralized configuration and monitoring
- Real-time health checks and status

📊 **Real-time Observability**
- Live logs with WebSocket streaming
- System metrics and performance monitoring
- Alert management with customizable rules
- Correlation IDs for request tracing

🤖 **AI Training & Integration**
- Custom Ollama model training with GPU support
- Training progress tracking and session management
- MCP server for AI-powered homelab automation
- Open WebUI compatible tools

👥 **User Management**
- Automatic user mapping across services
- Centralized identity management
- Group-based permissions for AI tools
- Service-specific authentication

🔧 **Developer Friendly**
- Complete REST API with OpenAPI documentation
- WebSocket endpoints for real-time updates
- Comprehensive logging and observability
- Prometheus-compatible metrics

## 🏗️ Architecture

```
mcparr/
├── src/
│   ├── backend/           # FastAPI backend
│   │   ├── src/
│   │   │   ├── adapters/  # Service integrations (15+ services)
│   │   │   ├── mcp/       # MCP server and AI tools
│   │   │   ├── models/    # SQLAlchemy ORM models
│   │   │   ├── routers/   # API endpoints (12 routers)
│   │   │   ├── services/  # Business logic
│   │   │   ├── websocket/ # Real-time WebSocket handlers
│   │   │   ├── middleware/# Logging and correlation
│   │   │   └── schemas/   # Pydantic validation
│   │   ├── alembic/       # Database migrations
│   │   └── tests/         # Backend tests
│   └── frontend/          # React + TypeScript frontend
│       └── src/
│           ├── components/ # Reusable UI components
│           ├── pages/      # Main pages (7 pages)
│           ├── contexts/   # React contexts
│           ├── hooks/      # Custom hooks
│           └── lib/        # Utilities (API client, WebSocket)
├── docker/                 # Docker configuration
├── scripts/                # Utility scripts (testing, linting, setup)
└── docs/                   # Documentation
```

## 📋 Requirements

### For Docker Deployment (Recommended)
- Docker 24+
- Docker Compose 2.20+
- 4GB RAM minimum
- 10GB disk space

### For Local Development
- Python 3.11+
- Node.js 20+ (Vite requirement)
- Poetry (Python dependency management)
- SQLite (default) or PostgreSQL

## 🚀 Quick Start

### Docker Deployment (Production)

```bash
# Pull and run the unified Docker image
docker pull sharkhunterr/mcparr:latest

# Using Docker Compose (recommended)
curl -o docker-compose.yml https://raw.githubusercontent.com/sharkhunterr/mcparr/master/docker/docker-compose.yml
docker compose up -d

# Or via npm scripts
npm run docker        # Build and start
npm start            # Start in production mode
npm stop             # Stop services
npm run logs         # View logs
```

### Local Development

```bash
# Setup (first time only - installs Poetry and dependencies)
npm run setup

# Start backend and frontend concurrently
npm run dev

# Or start separately
npm run dev:backend   # Backend on port 8000
npm run dev:frontend  # Frontend on port 3000

# Testing and linting
npm test              # Run all tests
npm run lint          # Run all linters
npm run fix           # Auto-fix linting issues
npm run reports       # Generate test/lint reports
```

### Access Your Gateway

- 🌐 **Web UI**: http://localhost:3000
- 📡 **API Docs**: http://localhost:8000/docs
- 📗 **ReDoc**: http://localhost:8000/redoc
- 🤖 **MCP Server**: http://localhost:8001

## 📚 Documentation

- 📦 [Installation Guide](docs/INSTALLATION.md) - Complete installation and setup
- ⚙️ [Configuration Guide](docs/CONFIGURATION.md) - Environment variables and service config
- 🔌 [API Reference](docs/API.md) - REST API endpoint documentation
- 🛠️ [MCP Integration](docs/MCP.md) - Connect to Claude Desktop and AI assistants
- 👥 [User Guide](docs/USER_GUIDE.md) - End-user documentation

## 🔧 Supported Services

MCParr integrates with 15+ homelab services:

**Media Management**
| Service | Description | MCP Tools |
|---------|-------------|-----------|
| 🎬 Plex | Media server | Search libraries, get playback info |
| 📥 Overseerr | Request management | Request movies/TV shows |
| 🎥 Radarr | Movie management | Add, search, manage movies |
| 📺 Sonarr | TV management | Add, search, manage series |
| 📊 Tautulli | Plex analytics | View history, stats, users |
| 🔍 Prowlarr | Indexer manager | Search across indexers |

**Downloads & Storage**
| Service | Description | MCP Tools |
|---------|-------------|-----------|
| ⬇️ Deluge | Torrent client | Manage torrents, view status |
| 🔎 Jackett | Torrent indexer | Search torrents |

**Books & Games**
| Service | Description | MCP Tools |
|---------|-------------|-----------|
| 📚 Komga | Comics library | Browse, read comics |
| 🎧 Audiobookshelf | Audiobook library | Manage audiobooks, playback |
| 🎮 ROMM | ROM manager | Manage game ROMs |

**Utilities**
| Service | Description | MCP Tools |
|---------|-------------|-----------|
| 📖 Wiki.js | Documentation | Search pages, create content |
| 🎫 Zammad | Ticketing system | Manage tickets, users |
| 🔑 Authentik | Identity provider | Manage users, groups, auth |
| 💬 Open WebUI | AI chat interface | Manage models, chats |
| 🤖 Ollama | Local LLM hosting | List models, generate text |

## 🤝 AI Integration with Open WebUI

MCParr is designed to work seamlessly with **Open WebUI**, providing a ChatGPT-like interface to control your entire homelab through natural language.

### Quick Setup with Open WebUI

**1. Install Open WebUI (if not already installed)**

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

**2. Configure MCParr MCP Server**

In Open WebUI:
1. Go to **Settings** → **Admin Settings** → **Tools** → **MCP Servers**
2. Add MCParr:
   ```json
   {
     "name": "MCParr Homelab",
     "url": "http://YOUR_MCPARR_HOST:8001",
     "enabled": true
   }
   ```
3. Enable tools in your chat and start controlling your homelab!

**3. Example Conversations**

```
You: What movies do I have about space?
AI: [Searches Plex] You have 23 space movies including Interstellar, The Martian...

You: Request the new season of Foundation
AI: [Uses Overseerr] I've requested Foundation Season 2 for you!

You: How are my downloads?
AI: [Checks Radarr/Sonarr] You have 3 movies and 5 episodes downloading...
```

### Other AI Assistants

MCParr also works with Claude Desktop and other MCP-compatible assistants.

**Claude Desktop Configuration:**

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcparr": {
      "command": "curl",
      "args": ["-N", "http://YOUR_MCPARR_HOST:8001/sse"]
    }
  }
}
```

### Available MCP Tools

Once connected, AI assistants can:
- 🎬 **Search Plex** libraries for movies, TV shows, music
- 📥 **Request media** via Overseerr with automatic quality selection
- 🎥 **Manage downloads** in Radarr, Sonarr, Prowlarr
- ⬇️ **Control torrents** in Deluge
- 📚 **Browse libraries** in Komga, Audiobookshelf, ROMM
- 🎫 **Create tickets** in Zammad
- 👥 **Manage users** in Authentik
- 📖 **Search documentation** in Wiki.js
- 🤖 **Interact with Ollama** for local AI models
- 📊 **Monitor system** health and metrics

See [MCP Integration Guide](docs/MCP.md) for complete tool documentation and advanced configuration.

## 📊 Monitoring & Observability

- **Metrics**: Prometheus-compatible metrics at `/metrics`
- **Health Check**: `/health` endpoint for Docker/Kubernetes
- **Logs**: Structured JSON logging with correlation IDs
- **WebSocket**: Real-time log streaming at `/ws/logs`
- **Alerts**: Customizable alert rules and notifications

## 🧪 Testing

```bash
# Run all tests
npm test

# Backend tests (pytest)
npm run test:back

# Frontend tests (build verification)
npm run test:front

# Generate coverage reports
npm run reports
```

## 🔒 Security

- Local network trust model (no auth required by default)
- Configurable CORS origins
- All API keys in environment variables
- Input validation and sanitization
- Rate limiting and circuit breakers
- Secure service-to-service communication

## 🐳 Docker Configuration

MCParr uses a **single unified Docker image** containing both backend (FastAPI + MCP) and frontend (React):

```yaml
version: '3.8'
services:
  mcparr:
    image: sharkhunterr/mcparr:latest
    ports:
      - "3000:3000"  # Web UI (nginx)
      - "8000:8000"  # API (FastAPI)
      - "8001:8001"  # MCP Server
    volumes:
      - mcparr-data:/app/data
    environment:
      - LOG_LEVEL=INFO
      - DATABASE_URL=sqlite:///data/mcparr.db
    restart: unless-stopped

volumes:
  mcparr-data:
```

See [docker/DOCKERHUB.md](docker/DOCKERHUB.md) for complete Docker documentation.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `npm run lint && npm test`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🆘 Support

- 📘 [GitHub Repository](https://github.com/sharkhunterr/mcparr)
- 📖 [Documentation](docs/)
- 🐛 [Issues](https://github.com/sharkhunterr/mcparr/issues)

---

**Built with** ❤️ **for the homelab community**
