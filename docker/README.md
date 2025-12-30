# Docker

Configuration Docker pour MCParr AI Gateway.

## Structure

```
docker/
├── backend.Dockerfile       # Backend Python/FastAPI (production)
├── backend.dev.Dockerfile   # Backend (développement avec hot-reload)
├── frontend.Dockerfile      # Frontend React/Vite (production)
├── frontend.dev.Dockerfile  # Frontend (développement)
├── docker-compose.yml       # Stack complète (production)
├── docker-compose.dev.yml   # Override pour développement
├── DOCKERHUB.md             # Description Docker Hub
└── README.md                # Ce fichier
```

## Démarrage rapide

### Production

```bash
# Depuis la racine du projet
docker compose -f docker/docker-compose.yml up -d

# Ou via npm
npm start
```

### Développement (avec hot-reload)

```bash
# Depuis la racine du projet
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build

# Ou via npm
npm run dev
```

### Arrêter les services

```bash
docker compose -f docker/docker-compose.yml down

# Ou via npm
npm stop
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000, 8001 | API FastAPI + MCP Server |
| `frontend` | 3000 | Interface web React |
| `redis` | 6379 | Cache et sessions |
| `adminer` | 8080 | Viewer DB (dev only) |

## Build manuel

### Backend

```bash
docker build -f docker/backend.Dockerfile -t mcparr-backend:latest src/backend/
```

### Frontend

```bash
docker build -f docker/frontend.Dockerfile -t mcparr-frontend:latest src/frontend/
```

## Docker Hub

### Configuration CI/CD

Variables GitLab requises :

| Variable | Description |
|----------|-------------|
| `DOCKER_HUB_USER` | Nom d'utilisateur Docker Hub |
| `DOCKER_HUB_TOKEN` | Access Token (scope: Read, Write, Delete) |

### Publication automatique

La publication se fait via `npm run release:deploy` :

1. Crée un tag de version
2. Pousse les images sur Docker Hub
3. Met à jour le README Docker Hub (DOCKERHUB.md)

### Publication manuelle

```bash
# Login
docker login

# Tag et push backend
docker tag mcparr-backend:latest sharkhunterr/mcparr-backend:v0.2.0
docker push sharkhunterr/mcparr-backend:v0.2.0

# Tag et push frontend
docker tag mcparr-frontend:latest sharkhunterr/mcparr-frontend:v0.2.0
docker push sharkhunterr/mcparr-frontend:v0.2.0
```

## Volumes

| Volume | Description |
|--------|-------------|
| `gateway-data` | Base de données SQLite |
| `redis-data` | Données Redis persistantes |

## Réseaux

Tous les services sont sur le réseau `mcparr-network` (bridge).

## Health Checks

```bash
# Backend
curl http://localhost:8000/health

# Frontend (via nginx)
curl http://localhost:3000

# Redis
docker exec mcparr-redis redis-cli ping
```

## Logs

```bash
# Tous les services
docker compose -f docker/docker-compose.yml logs -f

# Service spécifique
docker compose -f docker/docker-compose.yml logs -f backend

# Ou via npm
npm run logs
```
