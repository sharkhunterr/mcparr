# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 📚 Documentation
- Comprehensive user guide with 26 screenshots covering all features
- Modern README with Mermaid architecture diagrams and badges
- Corrected Open WebUI integration to use OpenAPI (port 8000) instead of MCP
- Added step-by-step Open WebUI configuration guide
- Enhanced Docker Hub overview with "What's New" section

---

## [0.2.7] - 2026-01-01

### 📚 Documentation
- Added complete user guide (900+ lines) with screenshots
- Modernized README with architecture diagrams and collapsible galleries
- Added 26 professional screenshots of web interface
- Corrected Open WebUI integration documentation (OpenAPI vs MCP)
- Added comprehensive troubleshooting section

---

## [0.2.6] - 2025-12-31

### 📚 Documentation
- Integrated comprehensive documentation from reference structure
- Added "What's New" section to Docker Hub overview
- Enhanced installation and configuration guides

---

## [0.2.5] - 2025-12-30

### 📚 Documentation
- Modernized Docker Hub overview with unified image approach

---

## [0.2.4] - 2025-12-30

### 🐛 Fixed
- Install all npm dependencies for Docker build (including devDependencies)
- Resolved TypeScript and Vite build errors in Docker

---

## [0.2.3] - 2025-12-29

### 🐛 Fixed
- Resolved all backend linting errors (1031 errors → 0)
- Resolved all frontend linting errors (113 errors → 0)
- Fixed import ordering and formatting issues
- Fixed Loguru logger import paths

---

## [0.2.2] - 2025-12-29

### 🐛 Fixed
- Resolved CI build errors and Loguru formatting issues
- Fixed import statement for logger

---

## [0.2.1] - 2025-12-28

### ♻️ Refactored
- Simplified Docker Compose to use unified image

---

## [0.2.0] - 2025-12-28

### ✨ Added
- Unified Docker image with backend + frontend
- Single image deployment for easier production use
- Nginx serving frontend with FastAPI backend

### 🛠️ Improved
- Streamlined deployment process
- Reduced Docker image count from 2 to 1

---

## [0.1.0] - 2025-12-11

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
