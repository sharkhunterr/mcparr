<div align="center">

# 🎯 MCParr AI Gateway

**Turn your homelab into an AI-powered automation hub**

[![Version](https://img.shields.io/github/v/tag/sharkhunterr/mcparr?label=version&color=blue)](https://github.com/sharkhunterr/mcparr/releases)
[![Docker](https://img.shields.io/docker/v/sharkhunterr/mcparr?label=docker&color=2496ED)](https://hub.docker.com/r/sharkhunterr/mcparr)
[![Docker Pulls](https://img.shields.io/docker/pulls/sharkhunterr/mcparr?color=2496ED)](https://hub.docker.com/r/sharkhunterr/mcparr)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=white)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![i18n](https://img.shields.io/badge/i18n-5_languages-blueviolet.svg)](#-multi-language-support)

![MCParr Dashboard](docs/images/dashboard_light.png)

**[Quick Start](#-quick-start)** •
**[Features](#-features)** •
**[Docker Hub](https://hub.docker.com/r/sharkhunterr/mcparr)** •
**[Documentation](docs/)** •
**[Screenshots](#-screenshots)**

</div>

---

## 🚀 What is MCParr?

MCParr bridges AI assistants with your homelab services through the **Model Context Protocol (MCP)**. Control your entire homelab using natural language with Open WebUI, Claude, or any MCP-compatible AI assistant.

**Perfect for:**
- 🏠 Homelab enthusiasts managing services for family/friends
- 🤖 AI automation of media requests and downloads
- 📊 Centralized monitoring and control
- 🔧 Developers building on MCP protocol

> [!WARNING]
> **Vibe Code Project** - This application was built **100% using AI-assisted development** with [Claude Code](https://claude.ai/claude-code) (Anthropic's CLI). See [Acknowledgments](#-acknowledgments) for details on why and how.

---

## ✨ Features

<table>
<tr>
<td width="33%" valign="top">

### 🎬 Service Integration
**15+ homelab services**
- Plex, Overseerr, Tautulli
- Radarr, Sonarr, Prowlarr
- Deluge, Jackett
- Komga, Audiobookshelf, RomM
- Wiki.js, Zammad, Authentik
- Open WebUI, Ollama

[Full service list →](docs/USER_GUIDE.md#services-management)

</td>
<td width="33%" valign="top">

### 🤖 AI Automation
**100+ MCP tools**
- Natural language control
- Tool chains with IF/THEN logic
- Global cross-service search
- Group-based permissions
- Auto-config for Open WebUI

[MCP docs →](docs/MCP.md)

</td>
<td width="33%" valign="top">

### 📊 Observability
**Complete monitoring**
- Real-time WebSocket logs
- System metrics dashboard
- Custom alert rules
- Prometheus metrics
- Correlation ID tracing

[Monitoring guide →](docs/USER_GUIDE.md#monitoring)

</td>
</tr>
</table>

### 🎨 Modern Web UI
- 🌐 **5 languages** (EN, FR, DE, ES, IT)
- 🌓 Light/Dark/Auto themes
- 📱 Fully responsive design
- 🧭 Interactive setup wizard
- 💾 Backup/restore configuration

### 🧠 AI Training (Experimental)
- Custom Ollama model training
- GPU worker support
- 94+ validated prompts
- Progress tracking

---

## 🏃 Quick Start

### Option 1: Docker (Recommended)

```bash
# Pull the latest image
docker pull sharkhunterr/mcparr:latest

# Run with Docker Compose
curl -o docker-compose.yml https://raw.githubusercontent.com/sharkhunterr/mcparr/master/docker/docker-compose.yml
docker compose up -d
```

**Access**: http://localhost:3000

📖 **[Complete Docker guide →](docker/README.md)** | **[Docker Hub →](https://hub.docker.com/r/sharkhunterr/mcparr)**

### Option 2: Local Development

```bash
# Clone and setup
git clone https://github.com/sharkhunterr/mcparr.git
cd mcparr
npm run setup

# Start dev servers
npm run dev

# Access
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

📖 **[Development guide →](docs/INTEGRATION_GUIDE.md)**

---

## 🔧 Configuration

MCParr requires minimal configuration to get started:

```yaml
# docker-compose.yml
environment:
  - LOG_LEVEL=INFO                        # debug, info, warning, error
  - DATABASE_URL=sqlite:///data/mcparr.db # or PostgreSQL
  - REDIS_URL=redis://localhost:6379     # optional cache
```

After first launch, use the **Setup Wizard** to:
1. Select your language
2. Import existing config (optional)
3. Tour MCParr features
4. Configure your services

📖 **[Configuration guide →](docs/CONFIGURATION.md)** | **[User guide →](docs/USER_GUIDE.md)**

---

## 💬 AI Integration

### With Open WebUI (Recommended)

1. **Add Open WebUI service** in MCParr
2. Go to **MCP → Configuration**
3. Click **Auto-Configure** → Select services
4. Enable tools in Open WebUI chat

```
You: Request the new season of Foundation
AI: ✅ I've requested Foundation Season 2 via Overseerr!

You: What movies do I have about space?
AI: 🎬 Found 23 space movies in your Plex library...

You: How are my downloads?
AI: 📥 You have 3 movies and 5 episodes downloading...
```

### With Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcparr": {
      "command": "curl",
      "args": ["-N", "http://localhost:8001/sse"]
    }
  }
}
```

📖 **[AI integration guide →](docs/MCP.md)**

---

## 📸 Screenshots

<details open>
<summary><b>🎯 Dashboard & Services</b></summary>

| Dashboard | Services Management |
|-----------|---------------------|
| ![Dashboard](docs/images/dashboard_light.png) | ![Services](docs/images/services.png) |

</details>

<details>
<summary><b>👥 User & Group Management</b></summary>

| User Auto-Detection | Group Permissions |
|---------------------|-------------------|
| ![Users](docs/images/user_auto.png) | ![Groups](docs/images/user_group_add_tool.png) |

</details>

<details>
<summary><b>📊 Monitoring & Logs</b></summary>

| System Metrics | Log Viewer |
|----------------|------------|
| ![Metrics](docs/images/monitoring_metrics.png) | ![Logs](docs/images/monitoring_log.png) |

</details>

**[View all screenshots →](docs/images/)**

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [Installation](docs/INSTALLATION.md) | Complete setup instructions |
| [Docker](docker/README.md) | Docker deployment guide |
| [Configuration](docs/CONFIGURATION.md) | Environment & service config |
| [User Guide](docs/USER_GUIDE.md) | Complete UI guide, services & monitoring |
| [MCP Integration](docs/MCP.md) | AI integration, tool chains & permissions |
| [API Reference](docs/API.md) | REST API endpoints |
| [Integration Guide](docs/INTEGRATION_GUIDE.md) | Developer guide for new services |
| [Scripts](scripts/README.md) | Release automation & CI/CD |

---

## 🌐 Multi-Language Support

MCParr is fully translated into **5 languages**:

🇬🇧 English • 🇫🇷 Français • 🇩🇪 Deutsch • 🇪🇸 Español • 🇮🇹 Italiano

All translations generated with Claude Code. Want to add a language? See [Integration Guide](docs/INTEGRATION_GUIDE.md#11-step-9-internationalization-i18n).

---

## 🛠️ Technology Stack

**Backend**: Python 3.11 • FastAPI • SQLAlchemy • Alembic • Redis • MCP

**Frontend**: React 18 • TypeScript • Tailwind CSS • Vite • i18next

**DevOps**: Docker • GitLab CI • GitHub Actions • Prometheus

**[Architecture details →](docs/INTEGRATION_GUIDE.md#1-architecture-overview)**

---

## 🏗️ Architecture

### Global Architecture

```mermaid
flowchart TB
    subgraph Clients["🖥️ AI Clients"]
        OW[Open WebUI]
        CD[Claude Desktop]
        API[REST API Client]
    end

    subgraph MCParr["🎯 MCParr Gateway"]
        subgraph Backend["FastAPI Backend :8000"]
            REST[REST API<br/>/api/*]
            OA[OpenAPI Tools<br/>/tools/*]
            TR[Tool Registry]
            PM[Permission Manager]
        end

        subgraph MCP["MCP Server :8001"]
            SSE[SSE Endpoint<br/>/sse]
            MSG[Message Handler]
        end

        subgraph Data["Data Layer"]
            DB[(SQLite/PostgreSQL)]
            REDIS[(Redis Cache)]
        end
    end

    subgraph Services["🔧 Homelab Services"]
        direction LR
        PLEX[Plex]
        OV[Overseerr]
        RAD[Radarr]
        SON[Sonarr]
        MORE[...]
    end

    OW -->|OpenAPI + JWT| OA
    CD -->|MCP Protocol| SSE
    API -->|REST| REST

    OA --> TR
    SSE --> MSG --> TR
    REST --> TR

    TR --> PM
    PM --> DB
    TR --> REDIS

    TR -->|HTTP| Services
```

### Request Flow Sequence

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant AI as 🤖 AI Assistant
    participant MCParr as 🎯 MCParr
    participant Service as 🔧 Service

    User->>AI: "Request Foundation Season 2"
    AI->>MCParr: Call overseerr_request_media

    Note over MCParr: Validate JWT Token
    Note over MCParr: Check User Permissions
    Note over MCParr: Resolve User Mapping

    MCParr->>Service: POST /api/v1/request
    Service-->>MCParr: 201 Created

    Note over MCParr: Log Request
    Note over MCParr: Update Metrics

    MCParr-->>AI: Success Response
    AI-->>User: "✅ Foundation S2 requested!"
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Read the [Integration Guide](docs/INTEGRATION_GUIDE.md) for development details
2. Fork and create a feature branch
3. Run tests: `npm run lint && npm test`
4. Submit a pull request

**Releases**: We use automated release scripts. See [Scripts documentation](scripts/README.md) for details.

---

## 📦 Releases & Docker

### Latest Release

Check [Releases](https://github.com/sharkhunterr/mcparr/releases) for changelogs and downloads.

### Docker Images

```bash
# Latest stable
docker pull sharkhunterr/mcparr:latest

# Specific version
docker pull sharkhunterr/mcparr:v0.2.33
```

**Platforms**: `linux/amd64`, `linux/arm64`

**[Docker Hub →](https://hub.docker.com/r/sharkhunterr/mcparr)** | **[Release automation →](scripts/README.md)**

---

## 🙏 Acknowledgments

**The Need**: Managing 15+ homelab services for family and friends became overwhelming — scattered UIs, manual requests, no unified control.

**The Solution**: MCParr was born to bridge AI assistants with homelab services, letting users make requests in natural language instead of learning multiple interfaces.

**The Approach**: As a young parent with limited time and no fullstack development experience (neither backend nor frontend), traditional coding wasn't an option. Built entirely through [Claude Code](https://claude.ai/claude-code) using "vibe coding" — pure conversation, no manual coding required.

**The Architecture**: Structured using [GitHub Spec-Kit](https://github.com/github/spec-kit) methodology for maintainable, scalable design.

Special thanks to the homelab community and all contributors!

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with Claude Code 🤖 for the homelab community 🏠**

[![GitHub](https://img.shields.io/badge/GitHub-sharkhunterr/mcparr-181717?logo=github)](https://github.com/sharkhunterr/mcparr)
[![Docker Hub](https://img.shields.io/badge/Docker-sharkhunterr/mcparr-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/r/sharkhunterr/mcparr)
[![Documentation](https://img.shields.io/badge/Docs-Read%20Now-blue?logo=bookstack)](docs/)

[⭐ Star on GitHub](https://github.com/sharkhunterr/mcparr) • [🐛 Report Bug](https://github.com/sharkhunterr/mcparr/issues) • [💡 Request Feature](https://github.com/sharkhunterr/mcparr/issues)

</div>
