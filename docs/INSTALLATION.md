# 📦 Installation Guide

This guide covers the complete installation process for MCParr AI Gateway.

## 📋 Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 4+ GB |
| Storage | 1 GB | 10+ GB |
| OS | Linux, macOS, Windows (WSL2) | Ubuntu 22.04+ |

### Software Requirements

- **Python 3.10+**
- **Node.js 18+** (for frontend)
- **Git**

### Optional
- **Docker & Docker Compose** (for containerized deployment)
- **PostgreSQL** (alternative to SQLite)
- **Redis** (for caching)

## 🚀 Installation Methods

### Method 1: Native Installation (Development)

#### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/mcparr.git
cd mcparr
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create configuration
cp .env.example .env
```

Edit `.env` with your settings (see [Configuration Guide](CONFIGURATION.md)).

```bash
# Initialize database
alembic upgrade head

# Start the server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload
```

#### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Create configuration
cp .env.example .env
```

Edit `.env`:
```bash
VITE_API_URL=http://localhost:8002
VITE_WS_URL=ws://localhost:8002
```

```bash
# Start development server
npm run dev
```

#### 4. Access the Application

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8002/docs
- **MCP Server**: http://localhost:8001

---

### Method 2: Docker Installation (Production)

#### 1. Clone and Configure

```bash
git clone https://github.com/your-repo/mcparr.git
cd mcparr

# Create configuration
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit the `.env` files with your production settings.

#### 2. Build and Start

```bash
docker-compose up -d
```

#### 3. Initialize Database

```bash
docker-compose exec backend alembic upgrade head
```

#### 4. Access the Application

- **Frontend**: http://localhost:5173
- **API**: http://localhost:8002

---

## 🔧 Post-Installation

### 1. Configure Services

1. Open the web interface at http://localhost:5173
2. Go to **Services** tab
3. Add your homelab services with their URLs and API keys

### 2. Create User Mappings

1. Go to **Users** tab
2. Map your users across different services
3. Create groups with appropriate permissions

### 3. Connect to Open WebUI

Open WebUI is the primary interface for using MCParr with AI.

#### Install Open WebUI

If you don't have Open WebUI yet:

```bash
# Using Docker (recommended)
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

Access Open WebUI at http://localhost:3000

#### Configure MCParr MCP Server in Open WebUI

1. **Open Open WebUI** → **Settings** (gear icon)
2. **Admin Settings** → **Tools** → **MCP Servers**
3. Click **"+ Add MCP Server"**
4. Configure MCParr:
   ```json
   {
     "name": "MCParr Homelab",
     "url": "http://YOUR_MCPARR_HOST:8001",
     "enabled": true
   }
   ```
   Replace `YOUR_MCPARR_HOST` with:
   - `localhost` if running locally
   - `host.docker.internal` if Open WebUI is in Docker (Linux: use your machine's IP)
   - Your server IP/hostname for remote access

5. Click **Save** and **Test Connection**
6. If successful, you'll see "Connected" with a list of available tools

#### Enable Tools in Chat

1. Start a **new chat** in Open WebUI
2. Click the **tools icon** (wrench) in the chat input bar
3. You'll see MCParr tools grouped by category:
   - **Media**: plex_search, overseerr_request_movie, overseerr_request_tv
   - **Management**: radarr_add_movie, sonarr_add_series, prowlarr_search
   - **System**: get_system_status, get_service_status
4. **Enable the tools** you want to use
5. Start chatting! The AI can now control your homelab

#### Example Chat Session

```
You: What sci-fi movies do I have in Plex?
AI: [Uses plex_search tool]
    You have 47 sci-fi movies including Interstellar, The Matrix,
    Inception, Blade Runner 2049, and Dune.

You: Request the latest season of The Expanse
AI: [Uses overseerr_request_tv tool]
    I've requested The Expanse Season 6. It should be available
    in Plex within a few hours once downloaded.

You: How are my services doing?
AI: [Uses get_system_status tool]
    All 10 services are healthy:
    ✅ Plex - 3 active streams
    ✅ Radarr - 5 movies downloading
    ✅ Sonarr - 2 episodes in queue
    ✅ Overseerr - 12 pending requests
```

### 4. Connect Other AI Assistants (Optional)

See [MCP Integration Guide](MCP.md) for connecting to Claude Desktop or other AI assistants.

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check dependencies
pip install -r requirements.txt

# Check database
alembic current
alembic upgrade head
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Database errors

```bash
# Reset database (WARNING: deletes all data)
rm backend/data/mcparr.db
alembic upgrade head
```

### Port conflicts

Check if ports are in use:
```bash
lsof -i :8002  # Backend
lsof -i :5173  # Frontend
lsof -i :8001  # MCP Server
```

---

## ⬆️ Updating

### Native Installation

```bash
git pull

# Backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Frontend
cd ../frontend
npm install
npm run build  # For production
```

### Docker Installation

```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

---

## 📚 Next Steps

- [⚙️ Configuration Guide](CONFIGURATION.md)
- [🔌 API Reference](API.md)
- [🛠️ MCP Integration](MCP.md)
