# ⚙️ Configuration Guide

Complete guide to configuring MCParr AI Gateway.

## 🔧 Environment Variables

MCParr uses environment variables for configuration. Copy `.env.example` to `.env` and customize.

### Backend Configuration

#### Application Settings

```bash
# Application
APP_NAME=MCParr AI Gateway
APP_ENV=development          # development | production
DEBUG=true                   # Enable debug mode
LOG_LEVEL=INFO              # DEBUG | INFO | WARNING | ERROR

# API Configuration
API_HOST=0.0.0.0
API_PORT=8002
MCP_PORT=8001
```

#### Database

```bash
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///./data/mcparr.db

# PostgreSQL (recommended for production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mcparr
```

#### Redis (Optional)

```bash
REDIS_URL=redis://localhost:6379
CACHE_TTL=300  # Cache duration in seconds
```

#### Security

```bash
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### CORS

```bash
# Comma-separated list or JSON array
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

---

## 🔌 Service Configuration

### Media Services

#### Plex

```bash
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your-plex-token
```

To get your Plex token:
1. Sign in to Plex web app
2. Open any media item
3. Click "Get Info" → "View XML"
4. Find `X-Plex-Token` in the URL

#### Overseerr

```bash
OVERSEERR_URL=http://192.168.1.100:5055
OVERSEERR_API_KEY=your-api-key
```

Get API key from Overseerr → Settings → General.

#### Radarr

```bash
RADARR_URL=http://192.168.1.100:7878
RADARR_API_KEY=your-api-key
```

#### Sonarr

```bash
SONARR_URL=http://192.168.1.100:8989
SONARR_API_KEY=your-api-key
```

#### Tautulli

```bash
TAUTULLI_URL=http://192.168.1.100:8181
TAUTULLI_API_KEY=your-api-key
```

### Download Services

#### Prowlarr

```bash
PROWLARR_URL=http://192.168.1.100:9696
PROWLARR_API_KEY=your-api-key
```

#### Deluge

```bash
DELUGE_URL=http://192.168.1.100:8112
DELUGE_PASSWORD=your-password
```

### Other Services

#### Wiki.js

```bash
WIKIJS_URL=http://192.168.1.100:3000
WIKIJS_TOKEN=your-api-token
```

#### Zammad

```bash
ZAMMAD_URL=http://192.168.1.100:3000
ZAMMAD_TOKEN=your-token
```

#### Authentik

```bash
AUTHENTIK_URL=http://192.168.1.100:9000
AUTHENTIK_TOKEN=your-api-token
```

---

## 🤖 AI Configuration

### Ollama

```bash
OLLAMA_URL=http://192.168.1.100:11434
OLLAMA_MODEL=llama3.2
```

### Open WebUI

```bash
OPEN_WEBUI_URL=http://192.168.1.100:8080
OPEN_WEBUI_API_KEY=your-api-key
```

### Training Worker

```bash
TRAINING_WORKER_URL=http://192.168.1.200:8088
TRAINING_WORKER_API_KEY=optional-api-key
```

---

## 🌐 Frontend Configuration

Create `frontend/.env`:

```bash
# Backend API URL
VITE_API_URL=http://localhost:8002

# WebSocket URL for real-time updates
VITE_WS_URL=ws://localhost:8002
```

For production with different hosts:

```bash
VITE_API_URL=http://mcparr.yourdomain.com:8002
VITE_WS_URL=ws://mcparr.yourdomain.com:8002
```

---

## 🗄️ Database Configuration

### SQLite (Default)

Simple, no additional setup required:

```bash
DATABASE_URL=sqlite+aiosqlite:///./data/mcparr.db
```

### PostgreSQL (Recommended for Production)

1. Create database:
```sql
CREATE DATABASE mcparr;
CREATE USER mcparr_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mcparr TO mcparr_user;
```

2. Configure:
```bash
DATABASE_URL=postgresql+asyncpg://mcparr_user:secure_password@localhost:5432/mcparr
```

---

## 📊 Monitoring Configuration

### Metrics

```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

### Alerts (Optional)

#### Email Alerts

```bash
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_HOST=smtp.gmail.com
ALERT_EMAIL_PORT=587
ALERT_EMAIL_USER=your-email@gmail.com
ALERT_EMAIL_PASSWORD=app-password
ALERT_EMAIL_FROM=mcparr@yourdomain.com
ALERT_EMAIL_TO=admin@yourdomain.com
```

#### Webhook Alerts

```bash
ALERT_WEBHOOK_ENABLED=true
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

---

## 🔐 Security Best Practices

### Production Checklist

1. **Change SECRET_KEY**
   ```bash
   # Generate a secure key
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Set DEBUG=false**
   ```bash
   DEBUG=false
   APP_ENV=production
   ```

3. **Use HTTPS** (via reverse proxy like nginx/traefik)

4. **Restrict CORS origins**
   ```bash
   CORS_ORIGINS=["https://mcparr.yourdomain.com"]
   ```

5. **Use PostgreSQL** instead of SQLite

6. **Secure API keys** - Never commit `.env` files

---

## 🔄 Runtime Configuration

Some settings can be changed via the web interface without restart:

- Service configurations (URLs, API keys)
- User mappings
- Group permissions
- Training prompts

Go to **Configuration** tab in the web interface.

---

## 📚 Next Steps

- [🔌 API Reference](API.md)
- [🛠️ MCP Integration](MCP.md)
- [👥 User Guide](USER_GUIDE.md)
