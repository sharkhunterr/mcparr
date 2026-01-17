# 🐳 MCParr Docker Deployment

**AI-powered homelab gateway - Complete deployment guide**

This guide covers Docker deployment of MCParr. For Docker Hub overview, see [DOCKERHUB.md](DOCKERHUB.md).

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Download docker-compose.yml
curl -o docker-compose.yml https://raw.githubusercontent.com/sharkhunterr/mcparr/master/docker/docker-compose.yml

# Start MCParr
docker compose up -d

# View logs
docker compose logs -f mcparr
```

**Access**: http://localhost:3000

### Option 2: Docker Run

```bash
docker run -d \
  --name mcparr \
  -p 3000:3000 \
  -p 8000:8000 \
  -v mcparr-data:/app/data \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  sharkhunterr/mcparr:latest
```

---

## 📦 What's in the Image

The unified MCParr image includes:

| Component | Description | Port |
|-----------|-------------|------|
| 🖥️ **Web UI** | React frontend (nginx) | 3000 |
| ⚡ **API** | FastAPI backend | 8000 |
| 🤖 **MCP Server** | Model Context Protocol | 8001 |
| 🗄️ **Database** | SQLite (or PostgreSQL) | - |
| 🔄 **Redis** | Internal cache | - |

**Platforms**: `linux/amd64`, `linux/arm64`

---

## 🔧 Configuration

### Docker Compose Example

```yaml
version: '3.8'

services:
  mcparr:
    image: sharkhunterr/mcparr:latest
    container_name: mcparr
    hostname: mcparr
    ports:
      - "3000:3000"   # Web UI
      - "8000:8000"   # API
      - "8001:8001"   # MCP Server (optional)
    volumes:
      - mcparr-data:/app/data
    environment:
      # Logging
      - LOG_LEVEL=INFO

      # Database (SQLite default)
      - DATABASE_URL=sqlite+aiosqlite:///data/mcparr.db

      # Or PostgreSQL
      # - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/mcparr

      # Redis (optional external)
      # - REDIS_URL=redis://redis:6379

      # CORS (optional)
      - CORS_ORIGINS=*

    restart: unless-stopped

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  mcparr-data:
    driver: local
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/mcparr.db` | Database connection string |
| `REDIS_URL` | Internal | External Redis connection (optional) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |

---

## 💾 Backup & Restore

### Via Web UI

1. **Configuration → Backup** tab
2. Select data to export
3. Click **Export** → download JSON

### Via Volume

```bash
# Backup
docker run --rm \
  -v mcparr-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mcparr-$(date +%Y%m%d).tar.gz -C /data .

# Restore
docker run --rm \
  -v mcparr-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/mcparr-YYYYMMDD.tar.gz"
```

---

## 🔄 Updates

```bash
# Pull latest image
docker compose pull

# Recreate container
docker compose up -d

# Clean old images
docker image prune -f
```

### Version Pinning

```yaml
services:
  mcparr:
    image: sharkhunterr/mcparr:v0.2.33  # Pin to specific version
```

---

## 🐛 Troubleshooting

### Container Won't Start

Check logs: `docker compose logs mcparr`

Common issues:
- Port conflict: Change ports in compose file
- Permission: `chmod -R 755 ./data`
- Database locked: Stop all instances

### Services Can't Connect

**Mac/Windows**: Use `host.docker.internal` instead of `localhost`

**Linux**: Use your machine's IP (not `localhost`)

Test: `docker compose exec mcparr curl -I http://YOUR_SERVICE`

---

## 📚 Resources

- **🐳 Docker Hub**: https://hub.docker.com/r/sharkhunterr/mcparr
- **📘 GitHub**: https://github.com/sharkhunterr/mcparr
- **📖 Documentation**: https://github.com/sharkhunterr/mcparr/tree/master/docs

---

**Built with Docker 🐳 for the homelab community 🏠**
