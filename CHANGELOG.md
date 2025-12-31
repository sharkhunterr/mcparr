# 📝 Changelog

All notable changes to MCParr AI Gateway will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-11

### ✨ Added

#### 🏗️ Core Features
- FastAPI backend with async SQLAlchemy
- React + TypeScript frontend with Tailwind CSS
- MCP (Model Context Protocol) server for AI tool integration
- WebSocket support for real-time updates

#### 🔌 Service Integrations
- 🎬 Plex media server integration
- 📥 Overseerr request management
- 🎥 Radarr movie management
- 📺 Sonarr TV show management
- 📊 Tautulli statistics
- 🔍 Prowlarr indexer management
- ⬇️ Deluge torrent client
- 📚 Komga comics/manga library
- 🎧 Audiobookshelf audiobooks
- 📖 Wiki.js documentation
- 🎫 Zammad ticketing system
- 🔑 Authentik identity provider
- 💬 Open WebUI AI chat
- 🤖 Ollama LLM integration

#### 👥 User Management
- User mapping across services
- Group-based permissions
- Tool access control per group
- Centralized user dashboard

#### 🧠 AI Training
- Training session management
- Prompt library with categories
- Training worker integration
- Real-time training metrics via WebSocket
- Model export to Ollama (GGUF format)

#### ⚙️ Configuration
- Service health monitoring
- Backup/restore functionality
- Environment-based configuration
- CORS configuration

#### 📊 Dashboard
- Service status overview
- System metrics display
- Recent activity logs
- AI training statistics

### 🔐 Security
- API key authentication for services
- Group-based tool permissions
- Secure credential storage

---

## 🔮 Future Releases

### Planned Features
- 🔒 OAuth/OIDC authentication
- 🏢 Multi-tenant support
- ⏰ Scheduled tasks
- 🔔 Alert notifications (email, webhook)
- 📈 Extended Prometheus metrics
- ☸️ Kubernetes deployment manifests
