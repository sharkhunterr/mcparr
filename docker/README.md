# Docker

Configuration Docker pour le projet.

## Structure

```
docker/
├── Dockerfile          # Dockerfile de production
├── Dockerfile.template # Template pour nouveaux projets
├── docker-test.js      # Script de test local
└── README.md           # Ce fichier
```

## Build local

```bash
# Construire l'image
npm run docker:build

# Construire et tester
npm run docker:test
```

## Docker Hub

### Configuration

1. Créer un compte sur [Docker Hub](https://hub.docker.com)
2. Créer un repository (ex: `username/mcparr`)
3. Générer un Access Token : Account Settings > Security > New Access Token
4. Configurer les variables GitLab CI/CD :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DOCKER_HUB_USER` | Nom d'utilisateur Docker Hub | `sharkhunterr` |
| `DOCKER_HUB_TOKEN` | Access Token Docker Hub | `dckr_pat_xxx...` |

### Publication automatique

La publication sur Docker Hub se fait automatiquement lors d'un `npm run release:deploy` :

1. L'image est construite avec le tag de version (ex: `v0.1.0`)
2. L'image est poussée sur Docker Hub avec :
   - Tag de version : `username/mcparr:v0.1.0`
   - Tag latest : `username/mcparr:latest`

### Publication manuelle

```bash
# Se connecter
docker login

# Taguer l'image
docker tag mcparr:latest username/mcparr:v0.1.0

# Pousser
docker push username/mcparr:v0.1.0
docker push username/mcparr:latest
```

## Dockerfile

Le Dockerfile utilise un build multi-stage pour optimiser la taille de l'image :

1. **dependencies** : Installation des dépendances npm
2. **builder** : Build de l'application (si nécessaire)
3. **production** : Image finale minimale

### Personnalisation

Copier `Dockerfile.template` vers `Dockerfile` et adapter :

```dockerfile
# Changer la version Node.js
ARG NODE_VERSION=22

# Modifier les métadonnées
LABEL maintainer="votre-email@example.com"
LABEL org.opencontainers.image.title="Votre App"

# Adapter le port
EXPOSE 3000

# Modifier la commande de démarrage
CMD ["node", "src/index.js"]
```

## Exécution

```bash
# Démarrer le conteneur
docker run -d -p 3000:3000 username/mcparr:latest

# Voir les logs
docker logs -f <container_id>

# Arrêter
docker stop <container_id>
```

## Health Check

L'image inclut un health check sur `/health` :

```bash
# Vérifier la santé
docker inspect --format='{{.State.Health.Status}}' <container_id>
```
