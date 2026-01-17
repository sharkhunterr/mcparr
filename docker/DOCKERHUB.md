# 🎯 MCParr AI Gateway

[![GitHub](https://img.shields.io/github/v/tag/sharkhunterr/mcparr?label=version&color=blue)](https://github.com/sharkhunterr/mcparr/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/sharkhunterr/mcparr?color=2496ED)](https://hub.docker.com/r/sharkhunterr/mcparr)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/sharkhunterr/mcparr/blob/master/LICENSE)

**AI-powered homelab gateway with MCP server** — Control your entire homelab through natural language using Open WebUI, Claude, or any MCP-compatible AI assistant.

---

## 🚀 Quick Start

```bash
# Pull the image
docker pull sharkhunterr/mcparr:latest

# Run with Docker Compose
curl -o docker-compose.yml https://raw.githubusercontent.com/sharkhunterr/mcparr/master/docker/docker-compose.yml
docker compose up -d
```

**Access**: http://localhost:3000

---

## ✨ What You Get

| Component | Port | Description |
|-----------|------|-------------|
| 🖥️ **Web UI** | 3000 | Modern React interface |
| ⚡ **API** | 8000 | FastAPI REST API |
| 🤖 **MCP Server** | 8001 | Model Context Protocol |
| 🗄️ **Database** | - | SQLite/PostgreSQL |
| 🔄 **Redis** | - | Internal cache |

**Platforms**: `linux/amd64`, `linux/arm64`

---

## 🎬 Features

✅ **15+ Service Integrations** — Plex, Overseerr, Radarr, Sonarr, Prowlarr, Deluge, Komga, Audiobookshelf, Wiki.js, Zammad, Authentik, Open WebUI, Ollama, Jackett, RomM

✅ **100+ MCP Tools** — Natural language control with tool chains and IF/THEN logic

✅ **AI Training** — Custom Ollama model training with GPU support

✅ **Global Search** — Search across all services simultaneously

✅ **User Management** — Centralized users/groups with permissions

✅ **Real-time Monitoring** — WebSocket logs, metrics dashboard, alerts

✅ **Multi-language** — 5 languages (EN, FR, DE, ES, IT)

✅ **Backup/Restore** — Full configuration export/import

---

## 💬 AI Integration Example

```
You: Request the new season of Foundation
AI: ✅ I've requested Foundation Season 2 via Overseerr!

You: What movies do I have about space?
AI: 🎬 Found 23 space movies in your Plex library...

You: How are my downloads?
AI: 📥 You have 3 movies and 5 episodes downloading...
```

**[AI Integration Guide →](https://github.com/sharkhunterr/mcparr/blob/master/docs/AI_INTEGRATION.md)**

---

## ⚙️ Configuration

### Basic Deployment

```yaml
version: '3.8'

services:
  mcparr:
    image: sharkhunterr/mcparr:latest
    container_name: mcparr
    ports:
      - "3000:3000"   # Web UI
      - "8000:8000"   # API
      - "8001:8001"   # MCP Server
    volumes:
      - mcparr-data:/app/data
    environment:
      - LOG_LEVEL=INFO
      - DATABASE_URL=sqlite+aiosqlite:///data/mcparr.db
    restart: unless-stopped

volumes:
  mcparr-data:
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/mcparr.db` | Database connection |
| `REDIS_URL` | Internal | External Redis (optional) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

---

## 🏷️ Available Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `v0.2.33` | Specific version |
| `v0.2.x` | Version pinning |

```bash
# Pin to specific version
docker pull sharkhunterr/mcparr:v0.2.33
```

---

## 🔄 Update

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

---

## 📚 Documentation

- **🐳 [Docker Guide](https://github.com/sharkhunterr/mcparr/blob/master/docker/README.md)** — Complete deployment guide
- **📘 [GitHub](https://github.com/sharkhunterr/mcparr)** — Source code and docs
- **📖 [Services](https://github.com/sharkhunterr/mcparr/blob/master/docs/SERVICES.md)** — All supported services
- **🤖 [MCP Tools](https://github.com/sharkhunterr/mcparr/blob/master/docs/MCP.md)** — AI tool reference
- **📊 [Monitoring](https://github.com/sharkhunterr/mcparr/blob/master/docs/MONITORING.md)** — Metrics & observability

---

## 🛠️ Technology Stack

**Backend**: Python 3.11 • FastAPI • SQLAlchemy • Redis • MCP

**Frontend**: React 18 • TypeScript • Tailwind CSS • i18next

**DevOps**: Docker • GitLab CI • GitHub Actions • Prometheus

---

## 🙏 Built With

- **[Claude Code](https://claude.ai/claude-code)** — 100% of development
- **[GitHub Spec-Kit](https://github.com/github/spec-kit)** — Project architecture

**[Read the project story →](https://github.com/sharkhunterr/mcparr/blob/master/docs/PROJECT_STORY.md)**

---

## 📄 License

MIT License - see [LICENSE](https://github.com/sharkhunterr/mcparr/blob/master/LICENSE)

---

<div align="center">

**Built with Claude Code 🤖 for the homelab community 🏠**

[⭐ Star on GitHub](https://github.com/sharkhunterr/mcparr) • [🐛 Report Bug](https://github.com/sharkhunterr/mcparr/issues) • [💡 Request Feature](https://github.com/sharkhunterr/mcparr/issues)

</div>
