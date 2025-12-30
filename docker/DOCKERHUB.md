# MCParr

Template GitLab avec CI/CD complet pour vos projets.

## Quick Start

```bash
docker pull sharkhunterr/mcparr:latest
docker run -d -p 3000:3000 sharkhunterr/mcparr:latest
```

## Tags

- `latest` - Dernière version stable
- `vX.Y.Z` - Version spécifique (ex: `v0.1.12`)

## Usage

```bash
# Démarrer le conteneur
docker run -d -p 3000:3000 --name mcparr sharkhunterr/mcparr:latest

# Voir les logs
docker logs -f mcparr

# Arrêter
docker stop mcparr
```

## Configuration

Variables d'environnement disponibles :

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | `production` | Environnement Node.js |
| `PORT` | `3000` | Port d'écoute |

## Health Check

L'image inclut un health check sur `/health` :

```bash
curl http://localhost:3000/health
```

## Source

- GitLab : [mcparr/mcparr](https://gitlab.com/mcparr/mcparr)
- GitHub : [sharkhunterr/mcparr](https://github.com/sharkhunterr/mcparr)
