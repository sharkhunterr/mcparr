<div align="center">

# 🤖 MCParr AI Gateway

**AI-powered homelab management with MCP server and web administration**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://hub.docker.com/r/sharkhunterr/mcparr)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)

![MCParr Dashboard](docs/images/02-dashboard.png)

[Features](#-features) •
[Quick Start](#-quick-start) •
[Documentation](#-documentation) •
[Screenshots](#-screenshots)

</div>

---

MCParr is your unified gateway for managing homelab services through AI. Built with FastAPI and React, it combines a powerful MCP (Model Context Protocol) server with a modern web interface for seamless AI-driven automation.

## 💡 Project Story

### The Need
As a homelab enthusiast managing services for family and friends, I found myself constantly receiving messages for simple requests: "Can you add this movie?", "I can't find that show", "Can you create my account?". Each request required manual intervention and back-and-forth communication.

**The Goal**: Provide an AI assistant (via Open WebUI) that could handle all these requests autonomously, allowing my users to interact directly with the homelab without requiring my intervention for every small task.

### Why Vibe Code?
This project was developed **100% using Claude Code (Anthropic's CLI) and GitHub's Spec-Kit** for a simple reason: **lack of time and technical expertise, but a growing need to do things right**.

As my homelab grew, so did the complexity and the number of user requests. I needed a robust, maintainable solution but lacked:
- Deep knowledge of FastAPI, React, and modern web development
- Time to learn all the best practices and architectural patterns
- Experience with AI integration and MCP protocol

**Claude Code enabled me to**:
- Build a production-grade application despite limited technical knowledge
- Implement complex features (MCP server, real-time monitoring, AI training) that would have taken months to learn
- Follow best practices and modern patterns guided by AI assistance
- Iterate quickly on features based on actual user needs
- Maintain high code quality with automated testing and linting

The result is a fully functional, well-documented homelab management platform that would have been impossible to build alone in a reasonable timeframe. This demonstrates how AI-assisted development can democratize software creation, allowing anyone with a vision to build complex systems regardless of their initial skill level.

## ✨ Features

🧙 **Setup Wizard & Configuration**
- Interactive first-time setup wizard
- Import/export complete configuration
- Guided step-by-step service configuration
- One-click data reset with wizard restart option

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

```mermaid
graph TB
    subgraph "Client Layer"
        WebUI[🌐 Web UI<br/>React + TypeScript]
        OpenWebUI[💬 Open WebUI<br/>AI Chat Interface]
    end

    subgraph "MCParr Gateway"
        API[⚡ FastAPI Backend<br/>Port 8000]
        MCP[🤖 MCP Server<br/>Port 8001]
        WS[📡 WebSocket<br/>Real-time Updates]

        API --> DB[(🗄️ SQLite<br/>Configuration)]
        API --> Cache[(⚡ Redis<br/>Cache)]
    end

    subgraph "Service Adapters"
        Media[🎬 Media Services<br/>Plex, Overseerr, Tautulli]
        Arr[📥 Arr Stack<br/>Radarr, Sonarr, Prowlarr]
        DL[⬇️ Downloads<br/>Deluge, Jackett]
        Books[📚 Books & Games<br/>Komga, Audiobookshelf, ROMM]
        Utils[🔧 Utilities<br/>Authentik, Wiki.js, Zammad]
        AI[🧠 AI Services<br/>Ollama, Open WebUI]
    end

    WebUI --> API
    WebUI --> WS
    OpenWebUI --> MCP
    MCP --> API

    API --> Media
    API --> Arr
    API --> DL
    API --> Books
    API --> Utils
    API --> AI

    style WebUI fill:#61dafb
    style OpenWebUI fill:#ab68ff
    style API fill:#009688
    style MCP fill:#ff6b6b
    style WS fill:#ffd93d
```

### Technology Stack

<table>
<tr>
<td width="50%">

**Backend**
- 🐍 Python 3.11+ with FastAPI
- 🗄️ SQLAlchemy ORM + Alembic migrations
- ⚡ Redis for caching
- 📡 WebSocket for real-time updates
- 🔌 15+ service adapters
- 🤖 MCP server implementation

</td>
<td width="50%">

**Frontend**
- ⚛️ React 18 + TypeScript
- 🎨 Tailwind CSS + shadcn/ui
- 📊 Recharts for visualization
- 🔄 Real-time WebSocket integration
- 📱 Responsive dark/light themes

</td>
</tr>
</table>

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

## 🧙 First-Time Setup Wizard

When you first access MCParr, you'll be greeted with an interactive setup wizard that guides you through the initial configuration:

### Wizard Features

**1. Welcome Screen**
- Option to import an existing configuration (skip all manual setup)
- Or start fresh with guided configuration

**2. Guided Steps**
- **Services**: Configure your homelab services (Plex, Radarr, Sonarr, etc.)
- **User Mapping**: Automatic user discovery across all services
- **Groups & Permissions**: Set up access control for AI tools
- **Information Pages**: Learn about MCP, Training, Monitoring, and Configuration features

**3. Configuration Import/Export**
- **Import at Welcome**: Upload a backup file to restore complete configuration
- **Export Anytime**: Backup your entire setup (services, users, groups, prompts, settings)
- **Selective Restore**: Choose which data categories to import
- **Merge Mode**: Import without overwriting existing data

**4. Data Reset**
- Complete application reset via Configuration → Backup tab
- Double confirmation to prevent accidental deletion
- Option to launch wizard after reset
- Deletes all services, user mappings, groups, training prompts, and settings

### Skip or Complete Later
- Click "Passer le guide" (Skip) to access the interface immediately
- Wizard completion is saved - it won't show again after first setup
- Access wizard anytime via Configuration → General → "Reinitialiser le guide"

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

```mermaid
sequenceDiagram
    participant User
    participant OpenWebUI
    participant MCParr
    participant Services

    User->>OpenWebUI: "Request the movie Inception"
    OpenWebUI->>MCParr: POST /tools/overseerr_request_movie
    MCParr->>Services: Search TMDB API
    Services-->>MCParr: Movie ID: 27205
    MCParr->>Services: POST to Overseerr API
    Services-->>MCParr: Request created
    MCParr-->>OpenWebUI: {status: "success", id: 123}
    OpenWebUI-->>User: "✅ Requested Inception via Overseerr!"

    Note over User,Services: AI automatically uses the right tools
```

### Quick Setup with Open WebUI

**1. Install Open WebUI (if not already installed)**

```bash
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

**2. Add MCParr Tools to Open WebUI**

In Open WebUI:
1. Go to **Settings** → **Admin Settings** → **Tools** (or **Outils**)
2. Click **"+ Add Tool"** or **"+ Nouvelle Connexion"**
3. Configure the connection:
   - **Type**: Select **"OpenAPI"**
   - **URL**: `http://YOUR_MCPARR_HOST:8000` (replace with your MCParr IP/hostname)
   - **OpenAPI Spec**: Select `/tools/openapi.json` from dropdown
   - **Auth**: Select **"Session"**
   - **Username**: Give it a descriptive name like "MCParr Homelab Tools"
   - **Description**: Optional description like "Outils serveur Homelab"
   - **Visibility**: Choose **"Public"** to share with all users
4. Click **Save** to add the tools

**Important Notes:**
- Use `localhost` if Open WebUI is running on the same machine
- Use `host.docker.internal` if Open WebUI is in Docker on macOS/Windows
- On Linux with Docker, use your machine's IP address (e.g., `192.168.1.21`)
- The port is `8000` (API port), not `8001` (MCP port)

**3. Enable Tools in Chat**

1. Start a new chat in Open WebUI
2. Click the **tools icon** (wrench) in the chat input bar
3. Enable the MCParr tools you want to use
4. Start chatting! The AI can now control your homelab

**4. Example Conversations**

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

## 📸 Screenshots

<details open>
<summary><b>🎯 Services Management</b></summary>

![Services List](docs/images/03-services-list.png)
*Manage 15+ homelab services with health monitoring and connection testing*

![Add Service](docs/images/06-add-service.png)
*Easy service configuration with automatic health checks*

</details>

<details>
<summary><b>👥 User & Group Management</b></summary>

![User Auto-Detection](docs/images/07-users-auto-detection.png)
*Automatic user discovery across all services*

![Group Permissions](docs/images/09-groups-tools-permissions.png)
*Granular tool permissions per group (112 MCP tools available)*

</details>

<details>
<summary><b>🤖 AI Training with Ollama</b></summary>

![Training Overview](docs/images/11-training-overview.png)
*Monitor training sessions with GPU support*

![Training Prompts](docs/images/14-training-prompts.png)
*94 validated prompts for fine-tuning models*

![Training Workers](docs/images/16-training-workers.png)
*GPU workers for distributed training*

</details>

<details>
<summary><b>📊 Monitoring & Observability</b></summary>

![System Metrics](docs/images/18-monitoring-metrics.png)
*Real-time system metrics with auto-refresh*

![Log Viewer](docs/images/19-monitoring-logs.png)
*Advanced log filtering and search (1700+ logs tracked)*

</details>

<details>
<summary><b>⚙️ Configuration</b></summary>

![Appearance Settings](docs/images/21-config-appearance.png)
*Light/Dark/System theme options*

![Backup & Restore](docs/images/26-config-backup.png)
*Complete configuration backup with selective export*

</details>

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `npm run lint && npm test`
5. Submit a pull request

## 🛠️ Development Tools

This project was built using modern AI-assisted development tools:

### Claude Code by Anthropic
**100% of the codebase** was developed using [Claude Code](https://claude.ai/claude-code), Anthropic's CLI tool for AI-assisted development. This enabled rapid iteration, best-practice implementation, and complex feature development without requiring deep expertise in every technology.

**Key benefits experienced:**
- Faster development cycle (features that would take weeks completed in hours)
- Consistent code quality and architecture across frontend/backend
- Automated testing and documentation generation
- Real-time problem-solving and debugging assistance
- Learning while building - understanding patterns through implementation

### GitHub Spec-Kit
Project planning and architecture were designed using [GitHub's Spec-Kit](https://github.com/github/spec-kit), enabling clear specification of features and requirements before implementation.

### Why This Matters
This project demonstrates that **AI-assisted development democratizes software creation**. You don't need to be an expert in React, FastAPI, Docker, WebSockets, MCP protocol, or any specific technology to build production-grade applications. With the right tools and a clear vision, anyone can create complex, maintainable software systems.

**If you're considering AI-assisted development:**
- ✅ You can build features you don't fully understand yet
- ✅ Best practices are enforced automatically
- ✅ Documentation writes itself alongside code
- ✅ Testing becomes integrated from day one
- ✅ Learning happens through building, not before

The entire MCParr project - from initial concept to production deployment - was built by someone with limited web development experience, proving that AI tools have fundamentally changed what's possible for individual developers.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🆘 Support

- 📘 [GitHub Repository](https://github.com/sharkhunterr/mcparr)
- 📖 [Documentation](docs/)
- 🐛 [Issues](https://github.com/sharkhunterr/mcparr/issues)

---

**Built with** ❤️ **for the homelab community**
